"""Draws every interim asset into assets/interim.

    api/.venv/bin/python scripts/draw_interim.py

The output is deterministic, so running it again changes nothing unless the
drawing code changed. Real artwork goes in assets/generated at the same
relative path and takes over, one file at a time.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

from app.postcard import interim  # noqa: E402


def main() -> None:
    out = ROOT / "assets" / "interim"
    written: list[str] = []

    def save(relative: str, image: object) -> None:
        path = out / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path, format="PNG", optimize=True)  # type: ignore[attr-defined]
        written.append(relative)

    for motif in interim.stamp_motifs():
        save(f"stamps/{motif}.png", interim.draw_stamp(motif))
    save("postmark/ring.png", interim.draw_postmark())
    save("brand/logo.png", interim.draw_logo(512))
    save("brand/icon-192.png", interim.draw_logo(192))
    save("brand/icon-512.png", interim.draw_logo(512))
    save("brand/icon-maskable-512.png", interim.draw_logo(512, maskable=True))
    for relative, image in interim.draw_illustrations().items():
        save(relative, image)
    print(f"{len(written)} files written to {out}")


if __name__ == "__main__":
    main()
