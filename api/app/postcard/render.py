"""Brief in, finished files out: the composite PNG for sharing and a small WebP for lists."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from app.postcard.brief import PostcardBrief
from app.postcard.overlay import compose_postcard
from app.postcard.provider import ImageProvider

THUMB_WIDTH = 600


@dataclass(frozen=True)
class RenderedPostcard:
    png: bytes
    thumb_webp: bytes
    provider: str
    size: tuple[int, int]


def render_postcard(brief: PostcardBrief, provider: ImageProvider, assets_dir: Path) -> RenderedPostcard:
    art = provider.generate(brief)
    card = compose_postcard(art, brief, assets_dir)
    png = io.BytesIO()
    card.save(png, format="PNG", optimize=False, compress_level=6)
    thumb = card.resize((THUMB_WIDTH, round(card.height * THUMB_WIDTH / card.width)), Image.Resampling.LANCZOS)
    webp = io.BytesIO()
    thumb.save(webp, format="WEBP", quality=82, method=4)
    return RenderedPostcard(png=png.getvalue(), thumb_webp=webp.getvalue(), provider=provider.name, size=card.size)
