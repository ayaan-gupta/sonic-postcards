"""Downloads a small labelled set of real recordings from ESC-50 into data/esc50 (git-ignored).

    make fetch-real

ESC-50 (Karol J. Piczak, https://github.com/karolpiczak/ESC-50) is 2,000 five
second clips in 50 classes, taken from Freesound and released under Creative
Commons Attribution Non-Commercial. That licence is why the audio is fetched
on demand and never committed, and why it must not ship in anything commercial.
This takes 8 clips from each of 12 ambient classes: 96 files, about 42 MB.
"""

from __future__ import annotations

import csv
import io
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "esc50"
BASE = "https://raw.githubusercontent.com/karolpiczak/ESC-50/master"
CATEGORIES = (
    "rain", "chirping_birds", "sea_waves", "wind", "pouring_water", "church_bells",
    "crickets", "crackling_fire", "thunderstorm", "engine", "train", "car_horn",
)
PER_CATEGORY = 8


def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "sonic-postcards-fixtures/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 - fixed https URL
        data: bytes = response.read()
    return data


def main() -> int:
    (OUT / "audio").mkdir(parents=True, exist_ok=True)
    meta = get(f"{BASE}/meta/esc50.csv").decode("utf-8")
    chosen: list[dict[str, str]] = []
    counts: dict[str, int] = {}
    # Sorted by filename, so everyone who runs this gets the same 96 clips.
    for row in sorted(csv.DictReader(io.StringIO(meta)), key=lambda r: r["filename"]):
        category = row["category"]
        if category in CATEGORIES and counts.get(category, 0) < PER_CATEGORY:
            counts[category] = counts.get(category, 0) + 1
            chosen.append({"filename": row["filename"], "category": category, "fold": row["fold"], "src_file": row["src_file"]})
    for index, row in enumerate(chosen, 1):
        path = OUT / "audio" / row["filename"]
        if not path.is_file() or path.stat().st_size < 1000:
            path.write_bytes(get(f"{BASE}/audio/{row['filename']}"))
        if index % 16 == 0:
            print(f"{index}/{len(chosen)} clips")
    with (OUT / "manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["filename", "category", "fold", "src_file"])
        writer.writeheader()
        writer.writerows(chosen)
    (OUT / "LICENSE.txt").write_text(
        "ESC-50: Dataset for Environmental Sound Classification, Karol J. Piczak.\n"
        "https://github.com/karolpiczak/ESC-50\n"
        "Creative Commons Attribution Non-Commercial. Clips originate from freesound.org;\n"
        "the src_file column of manifest.csv is the Freesound clip id.\n",
        encoding="utf-8",
    )
    size = sum(p.stat().st_size for p in (OUT / "audio").iterdir()) / 1e6
    print(f"\n{len(chosen)} clips in {len(counts)} classes, {size:.0f} MB, in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
