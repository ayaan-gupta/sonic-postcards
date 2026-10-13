"""Acceptance test 3 on real recordings: does "sounds like this" on a rain clip return rain?

    make fetch-real && make eval

Every fetched ESC-50 clip goes through the real pipeline (decode, level, YAMNet,
embedding) into a scratch database, and the real pgvector search is asked for
the five nearest neighbours of each one. ESC-50 clips are 5 s long, so each is
played twice to fill the 10 s a postcard needs. Prints one line per class and
writes docs/eval-esc50.json.
"""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

from app.audio.motifs import pick_motifs  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import Database, ensure_database, migrate  # noqa: E402
from app.errors import ApiError  # noqa: E402
from app.geo.grid import snap  # noqa: E402
from app.main import build_service  # noqa: E402
from app.seed import REAL_DIR, loop_to_ten_seconds, real_clips  # noqa: E402
from app.service import NewPostcard  # noqa: E402

EXPECTED_MOTIF = {
    "rain": "rain", "chirping_birds": "birds", "sea_waves": "waves", "wind": "wind", "pouring_water": "water",
    "church_bells": "bells", "crickets": "insects", "crackling_fire": "fire", "thunderstorm": "storm",
    "engine": "traffic", "train": "train", "car_horn": "traffic",
}


def main() -> int:
    clips = real_clips(REAL_DIR)
    if not clips:
        print("No real clips found. Run `make fetch-real` first.")
        return 2
    base = get_settings()
    url = base.database_url.rsplit("/", 1)[0] + "/sonic_eval"
    ensure_database(url)
    migrate(url)
    db = Database(url, max_size=2)
    db.open()
    with db.connection() as conn:
        conn.execute("TRUNCATE postcards, reports, upload_events RESTART IDENTITY CASCADE")
    with tempfile.TemporaryDirectory() as tmp:
        settings = base.model_copy(update={"database_url": url, "storage_dir": Path(tmp)})
        service = build_service(settings, db=db)
        category_of: dict[str, str] = {}
        tagged_right: dict[str, int] = {}
        speech: dict[str, list[float]] = {}
        rejected: list[str] = []
        for category, paths in sorted(clips.items()):
            for index, path in enumerate(paths):
                try:
                    mp3, tagging = service.analyse(loop_to_ten_seconds(path))
                except ApiError as exc:
                    rejected.append(f"{path.name} ({category}): {exc.code}")
                    continue
                tags = pick_motifs(tagging.labels)
                point = snap(10.0 + index * 0.5, 20.0 + sorted(clips).index(category) * 5.0)
                card = service.insert(
                    NewPostcard(point=point, source="seed", place=service.namer.name(point), local_date=date(2026, 1, 1), local_hour=12,
                                tagging=tagging, tags=tags, weather=None, device_hash="eval", clip_key=f"demo/{path.stem.lower()}.mp3", seeded=True),
                    render=False,
                )
                category_of[card.id] = category
                speech.setdefault(category, []).append(tagging.speech_probability)
                if EXPECTED_MOTIF[category] in [tag.slug for tag in tags]:
                    tagged_right[category] = tagged_right.get(category, 0) + 1

        results: dict[str, dict[str, object]] = {}
        for category in sorted(clips):
            ids = [pid for pid, cat in category_of.items() if cat == category]
            same_in_top5 = []
            top1 = 0
            for pid in ids:
                neighbours = [category_of[item.id] for item in service.similar(pid, limit=5)]
                same_in_top5.append(sum(1 for cat in neighbours if cat == category))
                top1 += neighbours[0] == category
            results[category] = {
                "clips": len(ids),
                "queries_with_same_class_in_top5": sum(1 for n in same_in_top5 if n >= 1),
                "mean_same_class_in_top5": round(sum(same_in_top5) / max(1, len(ids)), 2),
                "min_same_class_in_top5": min(same_in_top5, default=0),
                "top1_same_class": top1,
                "tagged_with_expected_motif": tagged_right.get(category, 0),
                "max_speech_probability": round(max(speech.get(category, [0.0])), 3),
            }
    db.close()

    print(f"{len(category_of)} real clips, {len(clips)} classes, 7 other clips of the same class per query (chance is {7 / (len(category_of) - 1) * 5:.2f} of 5)\n")
    print(f"{'class':<16}{'clips':>6}{'top-5 has same':>16}{'mean same/5':>13}{'min':>5}{'top-1 same':>12}{'motif right':>13}{'max speech':>12}")
    for category, r in results.items():
        print(f"{category:<16}{r['clips']:>6}{str(r['queries_with_same_class_in_top5']) + '/' + str(r['clips']):>16}{r['mean_same_class_in_top5']:>13}"
              f"{r['min_same_class_in_top5']:>5}{str(r['top1_same_class']) + '/' + str(r['clips']):>12}{str(r['tagged_with_expected_motif']) + '/' + str(r['clips']):>13}{r['max_speech_probability']:>12}")
    if rejected:
        print("\nrefused by the pipeline:", "; ".join(rejected))
    rain = results.get("rain", {})
    total = sum(int(r["clips"]) for r in results.values())  # type: ignore[call-overload]
    mean_all = sum(float(r["mean_same_class_in_top5"]) * int(r["clips"]) for r in results.values()) / max(1, total)  # type: ignore[arg-type, call-overload]
    print(f"\nrain: {rain.get('queries_with_same_class_in_top5')}/{rain.get('clips')} rain clips have rain in their top 5; on average {rain.get('mean_same_class_in_top5')} of the 5 are rain")
    print(f"all classes: on average {mean_all:.2f} of the top 5 share the query's class")
    out = ROOT / "docs" / "eval-esc50.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"dataset": "ESC-50 subset, 8 clips x 12 classes, each looped to 10 s", "per_class": results, "refused": rejected, "mean_same_class_in_top5": round(mean_all, 2)}, indent=2) + "\n")
    return 0 if rain.get("queries_with_same_class_in_top5") == rain.get("clips") else 1


if __name__ == "__main__":
    sys.exit(main())
