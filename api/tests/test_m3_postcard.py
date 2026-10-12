"""Milestone 3: postcard generation and the share image."""

from __future__ import annotations

import base64
import io
import json
from datetime import date
from pathlib import Path

import httpx
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.audio.motifs import MOTIFS
from app.postcard.art import resolve_asset
from app.postcard.brief import PostcardBrief, time_of_day
from app.postcard.overlay import ART_BOX, CARD_SIZE, DISPLAY, compose_postcard, font, printable
from app.postcard.provider import FallbackProvider, OpenAIImageProvider, ProceduralProvider
from app.postcard.render import render_postcard
from app.postcard.scene import ART_SIZE, SETTING_FOR_MOTIF, paint_scene
from tests.conftest import post_clip

ASSETS = Path(__file__).resolve().parents[2] / "assets"
MAGENTA = (255, 0, 255)


def brief(**changes: object) -> PostcardBrief:
    values: dict[str, object] = {
        "postcard_id": "testcard01",
        "motifs": ["rain", "traffic", "birds"],
        "labels": ["Rain", "Car", "Bird"],
        "time_of_day": "dusk",
        "place_name": "Kyoto",
        "country_name": "Japan",
        "local_date": date(2026, 10, 12),
        "weather": None,
    }
    values.update(changes)
    return PostcardBrief(**values)  # type: ignore[arg-type]


class Flat:
    """A stand-in image model that returns one flat colour, so the template is easy to see."""

    name = "flat"

    def generate(self, _: PostcardBrief) -> Image.Image:
        return Image.new("RGB", (1536, 1024), MAGENTA)


def test_prompt_is_built_from_labels_time_place_and_weather() -> None:
    prompt = brief(weather="rain").prompt()
    assert prompt.startswith("Kyoto, Japan at dusk in the rain.")
    assert "rain falling, passing traffic and birdsong" in prompt
    assert "gouache" in prompt and "No text" in prompt
    assert "under" not in brief().prompt().split(".")[0]  # no weather, no weather phrase
    assert brief(motifs=["hum"], country_name=None).prompt().startswith("Kyoto at dusk. The scene shows where you would hear a low steady hum.")
    assert [time_of_day(h) for h in (4, 5, 7, 8, 16, 17, 20, 21, 23, 0)] == ["night", "dawn", "dawn", "day", "day", "dusk", "dusk", "night", "night", "night"]


def test_painter_is_deterministic_and_every_motif_paints() -> None:
    first, second = paint_scene(brief()), paint_scene(brief())
    assert first.size == ART_SIZE and first.tobytes() == second.tobytes()
    assert paint_scene(brief(postcard_id="another")).tobytes() != first.tobytes()
    times = ("dawn", "day", "dusk", "night")
    assert {m.slug for m in MOTIFS} == set(SETTING_FOR_MOTIF)
    for index, motif in enumerate(MOTIFS):
        others = [MOTIFS[(index + 7) % len(MOTIFS)].slug, MOTIFS[(index + 13) % len(MOTIFS)].slug]
        image = paint_scene(brief(postcard_id=f"m{index}", motifs=[motif.slug, *others], time_of_day=times[index % 4]))
        assert image.size == ART_SIZE
        assert len(image.resize((48, 27)).getcolors(maxcolors=4096) or []) > 40, motif.slug  # not a blank canvas


def test_time_of_day_and_motif_change_the_picture() -> None:
    def mean_brightness(image: Image.Image) -> float:
        return float(np.asarray(image.convert("L")).mean())

    assert mean_brightness(paint_scene(brief(time_of_day="day"))) > mean_brightness(paint_scene(brief(time_of_day="night"))) + 60
    # Rain draws light streaks over the sky; the same scene without it has none.
    wet = np.asarray(paint_scene(brief(motifs=["traffic", "rain"])).convert("L"), dtype=np.int16)
    dry = np.asarray(paint_scene(brief(motifs=["traffic"])).convert("L"), dtype=np.int16)
    assert np.abs(wet - dry).mean() > 3


def test_composite_is_the_template_around_whatever_art_arrives() -> None:
    card = compose_postcard(Flat().generate(brief()), brief(), ASSETS)
    assert card.size == CARD_SIZE == (1200, 840) and card.mode == "RGB"
    left, top, right, bottom = ART_BOX
    pixels = np.asarray(card)
    # The art window shows the provider's picture, untouched away from the stamp.
    assert tuple(pixels[bottom - 40, left + 40]) == MAGENTA and tuple(pixels[top + 300, left + 300]) == MAGENTA
    # The border is paper, not art.
    assert np.abs(pixels[10, 600].astype(int) - (246, 240, 225)).max() < 12
    # Caption strip: dark ink for the place name on the left, and the tags on the right.
    strip = pixels[bottom + 50 : bottom + 130]
    assert (strip[:, 40:400].sum(axis=2) < 200).sum() > 800
    assert (strip[:, 800:1164].sum(axis=2) < 200).sum() > 300
    # Stamp and postmark sit in the top right corner of the art, drawn by the template.
    corner = pixels[top : top + 240, right - 340 : right]
    assert (np.abs(corner.astype(int) - MAGENTA).sum(axis=2) > 60).mean() > 0.25


def test_text_comes_from_the_facts_not_from_the_art() -> None:
    """Same art, different city and date: the lettering changes, and only the lettering."""
    art = Flat().generate(brief())
    kyoto = np.asarray(compose_postcard(art, brief(), ASSETS), dtype=np.int16)
    lisbon = np.asarray(compose_postcard(art, brief(place_name="Lisbon", country_name="Portugal", local_date=date(2025, 3, 4)), ASSETS), dtype=np.int16)
    changed = np.abs(kyoto - lisbon).sum(axis=2) > 30
    left, top, right, bottom = ART_BOX
    assert changed[bottom:, :].sum() > 500  # caption strip
    assert changed[top : top + 240, right - 340 : right].sum() > 200  # postmark
    assert changed[top + 260 : bottom - 4, left:right].sum() == 0  # the picture itself
    # A name the display font cannot draw falls back to what it can, never to empty boxes.
    assert printable("KYOTO 京都", font(DISPLAY, 40)) == "KYOTO"


def test_render_gives_a_png_for_sharing_and_a_small_thumbnail() -> None:
    rendered = render_postcard(brief(), ProceduralProvider(), ASSETS)
    assert rendered.provider == "procedural" and rendered.size == (1200, 840)
    assert rendered.png[:8] == b"\x89PNG\r\n\x1a\n"
    with Image.open(io.BytesIO(rendered.png)) as png:
        assert png.size == (1200, 840)
    with Image.open(io.BytesIO(rendered.thumb_webp)) as thumb:
        assert thumb.format == "WEBP" and thumb.size == (600, 420)
    assert len(rendered.thumb_webp) < 120_000
    assert render_postcard(brief(), ProceduralProvider(), ASSETS).png == rendered.png


def test_delivered_art_overrides_interim_art_one_file_at_a_time(tmp_path: Path) -> None:
    interim = tmp_path / "interim" / "stamps"
    generated = tmp_path / "generated" / "stamps"
    interim.mkdir(parents=True)
    generated.mkdir(parents=True)
    Image.new("RGBA", (300, 372), (10, 10, 200, 255)).save(interim / "rain.png")
    Image.new("RGBA", (300, 372), (10, 10, 200, 255)).save(interim / "birds.png")
    assert resolve_asset(tmp_path, "stamps/rain.png") == interim / "rain.png"
    Image.new("RGBA", (300, 372), (0, 200, 0, 255)).save(generated / "rain.png")
    assert resolve_asset(tmp_path, "stamps/rain.png") == generated / "rain.png"
    assert resolve_asset(tmp_path, "stamps/birds.png") == interim / "birds.png"
    assert resolve_asset(tmp_path, "stamps/nothing.png") is None

    def stamp_colour(motif: str) -> tuple[int, ...]:
        card = compose_postcard(Flat().generate(brief()), brief(motifs=[motif]), tmp_path)
        return tuple(int(v) for v in np.asarray(card)[ART_BOX[1] + 80, ART_BOX[2] - 95])

    assert stamp_colour("rain")[1] > 150 and stamp_colour("rain")[2] < 80  # the delivered green stamp
    assert stamp_colour("birds")[2] > 150  # still the interim blue one


def test_every_interim_asset_is_on_disk() -> None:
    for motif in MOTIFS:
        assert resolve_asset(ASSETS, f"stamps/{motif.slug}.png") is not None, motif.slug
    for relative in ("postmark/ring.png", "brand/logo.png", "brand/icon-192.png", "brand/icon-512.png", "brand/icon-maskable-512.png",
                     "onboarding/listen.png", "onboarding/place.png", "onboarding/send.png", "empty/quiet.png", "empty/hush.png"):
        assert resolve_asset(ASSETS, relative) is not None, relative


def test_openai_provider_request_shape_and_fallback() -> None:
    """The real provider against a mocked transport. It has never been run against the live API."""
    seen: dict[str, object] = {}
    picture = io.BytesIO()
    Image.new("RGB", (64, 64), (1, 2, 3)).save(picture, format="PNG")

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"data": [{"b64_json": base64.b64encode(picture.getvalue()).decode()}]})

    provider = OpenAIImageProvider(api_key="test-key", base_url="https://images.example/v1", model="gpt-image-1", client=httpx.Client(transport=httpx.MockTransport(handler)))
    image = provider.generate(brief())
    assert image.size == (64, 64) and image.getpixel((0, 0)) == (1, 2, 3)
    assert seen["url"] == "https://images.example/v1/images/generations" and seen["auth"] == "Bearer test-key"
    assert seen["body"] == {"model": "gpt-image-1", "prompt": brief().prompt(), "size": "1536x1024", "n": 1}

    broken = OpenAIImageProvider(api_key="k", base_url="https://images.example/v1", model="m", client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(500))))
    fallback = FallbackProvider(broken, ProceduralProvider())
    assert fallback.generate(brief()).size == ART_SIZE and fallback.name == "procedural"
    with pytest.raises(ValueError):
        OpenAIImageProvider(api_key="", base_url="x", model="m")


def test_upload_produces_a_stored_postcard_image(client: TestClient, clips: dict[str, bytes], service) -> None:  # type: ignore[no-untyped-def]
    card = post_clip(client, clips["waves"]).json()
    assert card["image_provider"] == "procedural" and "Kyoto, Japan" in card["prompt"]
    image = client.get(card["image_url"])
    assert image.status_code == 200 and image.headers["content-type"] == "image/png"
    assert "immutable" in image.headers["cache-control"]
    with Image.open(io.BytesIO(image.content)) as png:
        assert png.size == (1200, 840)
    thumb = client.get(card["thumb_url"])
    assert thumb.headers["content-type"] == "image/webp" and len(thumb.content) < len(image.content) / 8
    assert service.store.exists(f"postcards/{card['id']}.png") and service.store.exists(f"postcards/{card['id']}.webp")
