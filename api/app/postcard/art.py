"""Design-time art lookup. A delivered file in assets/generated wins over the
code-drawn one at the same relative path in assets/interim, one file at a time."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


def resolve_asset(assets_dir: Path, relative: str) -> Path | None:
    for folder in ("generated", "interim"):
        candidate = assets_dir / folder / relative
        if candidate.is_file():
            return candidate
    return None


def load_rgba(assets_dir: Path, relative: str) -> Image.Image | None:
    path = resolve_asset(assets_dir, relative)
    if path is None:
        return None
    with Image.open(path) as image:
        return image.convert("RGBA")
