"""Milestone 1: record, upload, store and play back a clip, with a map pin."""

from __future__ import annotations

import io
import json
import wave

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.audio.clip import ANALYSIS_RATE, TARGET_RMS_DBFS, ClipError, decode, prepare_clip, rms_dbfs
from app.audio.wav import wav_bytes
from app.fixtures import synth
from app.service import PostcardService
from app.storage import LocalDirStore, check_key
from tests.conftest import FIXTURES, post_clip


def stereo_wav(seconds: float, rate: int = 44_100) -> bytes:
    rng = np.random.default_rng(4)
    left = (rng.standard_normal(int(seconds * rate)) * 0.02).astype(np.float32)
    right = left * 0.5
    pcm = (np.stack([left, right], axis=1) * 32767).astype("<i2")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(pcm.tobytes())
    return buffer.getvalue()


def test_clip_is_trimmed_to_ten_seconds_mono_16k_and_levelled() -> None:
    clip = prepare_clip(stereo_wav(12.5))
    assert clip.analysis.shape == (10 * ANALYSIS_RATE,)
    assert clip.analysis.dtype == np.float32
    assert clip.source_seconds == pytest.approx(10.0)
    assert rms_dbfs(clip.analysis) == pytest.approx(TARGET_RMS_DBFS, abs=1.5)
    assert float(np.max(np.abs(clip.analysis))) <= 1.0


def test_stored_clip_is_a_ten_second_mp3() -> None:
    clip = prepare_clip(wav_bytes(synth.rain(0), synth.RATE))
    assert clip.playback_mp3[:3] == b"ID3" or clip.playback_mp3[0] == 0xFF
    assert len(clip.playback_mp3) < 120_000
    assert decode(clip.playback_mp3, rate=16_000, max_seconds=30).size / 16_000 == pytest.approx(10.0, abs=0.1)


@pytest.mark.parametrize("name", ["monologue_chrome.webm", "chat_safari.m4a"])
def test_browser_containers_decode(name: str) -> None:
    """Chrome records Opus in WebM, Safari records AAC in MP4. Both must decode without ffmpeg installed."""
    samples = decode((FIXTURES / "speech" / name).read_bytes(), rate=16_000, max_seconds=10)
    assert samples.size == 160_000


def test_short_silent_and_broken_uploads_are_refused_with_a_reason() -> None:
    with pytest.raises(ClipError) as short:
        prepare_clip(stereo_wav(3.0))
    assert short.value.code == "too_short" and "3.0 seconds" in short.value.message
    with pytest.raises(ClipError) as silent:
        prepare_clip(wav_bytes(np.zeros(11 * 16_000, dtype=np.float32), 16_000))
    assert silent.value.code == "silent"
    with pytest.raises(ClipError) as broken:
        prepare_clip(b"this is not audio at all")
    assert broken.value.code == "unreadable_audio"


def test_local_store_round_trip_and_key_rules(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = LocalDirStore(tmp_path)
    store.put("clips/abc.mp3", b"hello", "audio/mpeg")
    assert store.exists("clips/abc.mp3") and store.get("clips/abc.mp3") == b"hello"
    assert store.public_url("clips/abc.mp3") is None
    store.delete("clips/abc.mp3")
    assert not store.exists("clips/abc.mp3")
    for bad in ("../etc/passwd", "/abs.mp3", "clips//x.mp3", "Clips/x.mp3", "noext"):
        with pytest.raises(ValueError):
            check_key(bad)


def test_upload_then_fetch_then_play_then_find_the_pin(client: TestClient, clips: dict[str, bytes], service: PostcardService) -> None:
    response = post_clip(client, clips["birds"])
    assert response.status_code == 201, response.text
    card = response.json()
    assert card["place_name"] == "Kyoto" and card["country_code"] == "JP"
    assert card["tags"][0]["slug"] == "birds"

    fetched = client.get(f"/api/postcards/{card['id']}")
    assert fetched.status_code == 200 and fetched.json()["id"] == card["id"]

    audio = client.get(card["audio_url"])
    assert audio.status_code == 200 and audio.headers["content-type"] == "audio/mpeg"
    assert audio.headers["accept-ranges"] == "bytes"
    assert decode(audio.content, rate=16_000, max_seconds=30).size == pytest.approx(160_000, abs=1_600)
    assert service.store.exists(f"clips/{card['id']}.mp3")

    pins = client.get("/api/pins", params={"bbox": "135,34,137,36", "zoom": 9})
    assert pins.status_code == 200
    collection = json.loads(pins.text)
    assert collection["mode"] == "pins" and collection["total"] == 1
    feature = collection["features"][0]
    assert feature["properties"] == {"id": card["id"], "motif": "birds", "count": 1}
    assert feature["geometry"]["coordinates"] == [card["lon"], card["lat"]]
    assert json.loads(client.get("/api/pins", params={"bbox": "0,0,10,10"}).text)["features"] == []


def test_audio_supports_range_requests(client: TestClient, clips: dict[str, bytes]) -> None:
    card = post_clip(client, clips["rain"]).json()
    whole = client.get(card["audio_url"]).content
    part = client.get(card["audio_url"], headers={"Range": "bytes=100-199"})
    assert part.status_code == 206
    assert part.headers["content-range"] == f"bytes 100-199/{len(whole)}"
    assert part.content == whole[100:200]
    tail = client.get(card["audio_url"], headers={"Range": "bytes=-50"})
    assert tail.status_code == 206 and tail.content == whole[-50:]
    assert client.get(card["audio_url"], headers={"Range": f"bytes={len(whole)}-"}).status_code == 416


def test_missing_device_id_and_missing_postcard_have_clear_errors(client: TestClient, clips: dict[str, bytes]) -> None:
    response = client.post("/api/postcards", files={"audio": ("a.wav", clips["rain"])}, data={"lat": "1", "lon": "1"})
    assert response.status_code == 400 and "device id" in response.json()["error"]["message"]
    bad = client.post("/api/postcards", files={"audio": ("a.wav", clips["rain"])}, data={"lat": "95", "lon": "1"}, headers={"X-Device-Id": "d" * 12})
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "invalid_request"
    missing = client.get("/api/postcards/nope")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "not_found"
