"""Where postcard art comes from. One interface, two implementations.

`ProceduralProvider` is the default: the built-in painter, no network.
`OpenAIImageProvider` calls an OpenAI-compatible images endpoint when
IMAGE_PROVIDER=openai and OPENAI_API_KEY are set. It has only ever been run
against a mocked transport, never the real service, so treat it as untested.
If it fails for any reason the postcard falls back to the painter.
"""

from __future__ import annotations

import base64
import io
import logging
from typing import Protocol

import httpx
from PIL import Image

from app.config import Settings
from app.postcard.brief import PostcardBrief
from app.postcard.scene import paint_scene

log = logging.getLogger(__name__)


class ImageProvider(Protocol):
    name: str

    def generate(self, brief: PostcardBrief) -> Image.Image:
        """Return the art only: no border, no text, no stamp."""
        ...


class ProceduralProvider:
    name = "procedural"

    def generate(self, brief: PostcardBrief) -> Image.Image:
        return paint_scene(brief)


class OpenAIImageProvider:
    """UNTESTED against the live API. Request and response shapes follow the public images API."""

    name = "openai"

    def __init__(self, *, api_key: str, base_url: str, model: str, timeout: float = 90.0, client: httpx.Client | None = None) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when IMAGE_PROVIDER=openai")
        self._model = model
        self._url = base_url.rstrip("/") + "/images/generations"
        self._client = client or httpx.Client(timeout=timeout)
        self._headers = {"Authorization": f"Bearer {api_key}"}

    def generate(self, brief: PostcardBrief) -> Image.Image:
        response = self._client.post(
            self._url,
            headers=self._headers,
            json={"model": self._model, "prompt": brief.prompt(), "size": "1536x1024", "n": 1},
        )
        response.raise_for_status()
        item = response.json()["data"][0]
        if "b64_json" in item:
            raw = base64.b64decode(item["b64_json"])
        else:
            download = self._client.get(item["url"])
            download.raise_for_status()
            raw = download.content
        with Image.open(io.BytesIO(raw)) as image:
            return image.convert("RGB")


class FallbackProvider:
    """Try the configured provider; on any failure paint the picture ourselves."""

    def __init__(self, primary: ImageProvider, fallback: ImageProvider) -> None:
        self._primary = primary
        self._fallback = fallback
        self.name = primary.name

    def generate(self, brief: PostcardBrief) -> Image.Image:
        try:
            image = self._primary.generate(brief)
            self.name = self._primary.name
            return image
        except Exception:  # noqa: BLE001 - a postcard must never fail because a vendor did
            log.exception("image provider %s failed, using the built-in painter", self._primary.name)
            self.name = self._fallback.name
            return self._fallback.generate(brief)


def make_provider(settings: Settings) -> ImageProvider:
    procedural = ProceduralProvider()
    if settings.image_provider == "openai" and settings.openai_api_key:
        real = OpenAIImageProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.image_model,
            timeout=settings.image_timeout_seconds,
        )
        return FallbackProvider(real, procedural)
    return procedural
