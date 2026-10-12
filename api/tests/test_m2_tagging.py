"""Milestone 2: tagging, speech rejection and embeddings."""

from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.audio.clip import prepare_clip
from app.audio.motifs import MOTIFS, pick_motifs, unknown_classes
from app.audio.tagger import EMBEDDING_DIM, SPEECH_CLASSES, Label, YamnetTagger, speech_probability
from app.audio.wav import wav_bytes
from app.db import Database, as_array
from app.fixtures import synth
from app.service import PostcardService
from tests.conftest import FIXTURES, post_clip

SPEECH = ["monologue_chrome.webm", "chat_safari.m4a", "speech_over_rain.webm"]


@pytest.mark.parametrize("name", SPEECH)
def test_acceptance_mostly_speech_is_rejected_with_a_clear_message(client: TestClient, service: PostcardService, database: Database, name: str) -> None:
    """PRD acceptance test 1. Real speech (macOS `say`), real model, through the real endpoint."""
    response = post_clip(client, (FIXTURES / "speech" / name).read_bytes(), filename=name)
    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert error["code"] == "speech_detected"
    assert error["detail"]["speech_probability"] > 0.6
    assert error["detail"]["threshold"] == 0.6
    # The message says what happened, why, and what to do next.
    assert "mostly speech" in error["message"]
    assert "not posted" in error["message"]
    assert "protect the people around you" in error["message"]
    assert "Try again" in error["message"]
    # Nothing was kept: no row, no clip, no quota spent.
    with database.connection() as conn:
        assert conn.execute("SELECT count(*) AS n FROM postcards").fetchone()["n"] == 0  # type: ignore[index]
        assert conn.execute("SELECT count(*) AS n FROM upload_events").fetchone()["n"] == 0  # type: ignore[index]
    assert not list(service.settings.storage_dir.rglob("*.mp3"))


def test_rain_with_one_passing_hello_is_accepted(client: TestClient) -> None:
    response = post_clip(client, (FIXTURES / "speech" / "rain_with_a_hello.webm").read_bytes(), filename="rain.webm")
    assert response.status_code == 201, response.text
    card = response.json()
    assert card["speech_probability"] < 0.2
    assert "rain" in [tag["slug"] for tag in card["tags"]]


def test_speech_probability_is_the_share_of_frames_with_speech() -> None:
    index = [0, 1]
    frames = np.zeros((10, 5), dtype=np.float32)
    frames[:7, 0] = 0.95  # seven of ten frames are speech
    frames[8, 1] = 0.5  # a child speaks in one more
    assert speech_probability(frames, index) == pytest.approx((7 * 0.95 + 0.5) / 10, abs=1e-4)
    assert speech_probability(np.zeros((0, 5), dtype=np.float32), index) == 0.0


@pytest.mark.parametrize("kind", sorted(synth.SOUNDS))
def test_tagger_names_each_synthetic_sound(tagger: YamnetTagger, kind: str) -> None:
    """The real model, on audio made from noise and sine waves, lands on the expected motif."""
    for seed in (0, 1):
        clip = prepare_clip(wav_bytes(synth.synthesise(kind, seed), synth.RATE))
        tagging = tagger.tag(clip.analysis)
        slugs = [tag.slug for tag in pick_motifs(tagging.labels)]
        assert synth.EXPECTED_MOTIF[kind] in slugs[:2], (kind, seed, slugs, tagging.labels[:5])
        assert tagging.speech_probability < 0.1


def test_embedding_is_unit_length_and_similar_sounds_sit_close(tagger: YamnetTagger) -> None:
    def embed(kind: str, seed: int) -> np.ndarray:
        return tagger.tag(prepare_clip(wav_bytes(synth.synthesise(kind, seed), synth.RATE)).analysis).embedding

    rain_a, rain_b, birds = embed("rain", 0), embed("rain", 1), embed("birds", 0)
    for vector in (rain_a, rain_b, birds):
        assert vector.shape == (EMBEDDING_DIM,) and vector.dtype == np.float32
        assert float(np.linalg.norm(vector)) == pytest.approx(1.0, abs=1e-5)
    assert float(rain_a @ rain_b) > 0.9
    assert float(rain_a @ rain_b) > float(rain_a @ birds) + 0.2


def test_embedding_and_labels_are_stored(client: TestClient, clips: dict[str, bytes], database: Database) -> None:
    card = post_clip(client, clips["crickets"]).json()
    with database.connection() as conn:
        row = conn.execute("SELECT embedding, vector_dims(embedding) AS dims, labels, motifs, speech_prob FROM postcards WHERE id = %s", (card["id"],)).fetchone()
    assert row is not None
    assert row["dims"] == 1024
    assert float(np.linalg.norm(as_array(row["embedding"]))) == pytest.approx(1.0, abs=1e-4)
    assert row["motifs"][0] == "insects"
    assert {"Insect", "Cricket"} <= {item["name"] for item in row["labels"]}
    assert 0.0 <= row["speech_prob"] < 0.1


def test_every_motif_class_exists_in_the_model(tagger: YamnetTagger) -> None:
    assert unknown_classes(tagger.class_names) == []
    assert all(name in tagger.class_names for name in SPEECH_CLASSES)
    assert len({motif.slug for motif in MOTIFS}) == len(MOTIFS)


def test_motif_picking_rules() -> None:
    labels = [Label("White noise", 0.9), Label("Rain", 0.3), Label("Bird", 0.2), Label("Car", 0.15), Label("Animal", 0.99)]
    assert [t.slug for t in pick_motifs(labels)] == ["hum", "rain", "birds"]  # 0.9 * 0.35 still beats 0.3
    assert [t.slug for t in pick_motifs([Label("White noise", 0.5), Label("Rain", 0.3)])] == ["rain", "hum"]
    assert [t.slug for t in pick_motifs([Label("Animal", 0.9), Label("Sound effect", 0.5)])] == ["hum"]  # nothing recognisable
    assert [t.slug for t in pick_motifs([Label("Rain", 0.05)])] == ["hum"]  # below the floor
