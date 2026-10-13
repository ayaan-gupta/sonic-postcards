"""Seed data.

    python -m app.seed demo           about 40 postcards around the world, through the real pipeline
    python -m app.seed pins 5000      synthetic pins for the clustering test
    python -m app.seed clear-pins     remove the synthetic pins again
    python -m app.seed clear          remove everything that was seeded

Demo postcards are made from audio synthesised in code (app/fixtures/synth.py)
and are tagged by the real model, so their labels are whatever YAMNet makes
of a synthetic sound. If `make fetch-real` has downloaded ESC-50 clips, the
real recordings are used instead. Synthetic pins reuse the demo clips: each
copies a demo postcard's audio, labels and (slightly perturbed) embedding to
a new location.
"""

from __future__ import annotations

import csv
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np

from app.audio.clip import PLAYBACK_RATE, decode
from app.audio.motifs import pick_motifs
from app.audio.tagger import Tagging
from app.audio.wav import wav_bytes
from app.config import REPO_DIR, get_settings
from app.db import Database, as_array, migrate
from app.fixtures import synth
from app.geo.grid import snap
from app.geo.places import OfflinePlaceNamer
from app.postcard.brief import time_of_day
from app.service import COLUMNS, NewPostcard, PostcardService, insert_row, local_clock, new_id

REAL_DIR = REPO_DIR / "data" / "esc50"

# (latitude, longitude, sound, local hour, days ago). Places chosen so the map looks lived in.
DEMO: tuple[tuple[float, float, str, int, int], ...] = (
    (35.0116, 135.7681, "rain", 18, 1), (38.7223, -9.1393, "chimes", 9, 2), (19.076, 72.8777, "traffic", 19, 1),
    (-33.8568, 151.2153, "waves", 6, 3), (64.1466, -21.9426, "wind", 14, 4), (46.5197, 6.6323, "chimes", 12, 6),
    (-13.1631, -72.545, "stream", 10, 8), (41.9028, 12.4964, "strings", 20, 2), (59.3293, 18.0686, "birds", 5, 5),
    (30.0444, 31.2357, "traffic", 13, 3), (-1.2921, 36.8219, "crickets", 22, 2), (47.4979, 19.0402, "traffic", 17, 7),
    (55.9533, -3.1883, "rain", 11, 1), (21.0278, 105.8342, "thunderstorm", 16, 9), (-22.9068, -43.1729, "waves", 17, 4),
    (45.4408, 12.3155, "chimes", 7, 10), (40.7128, -74.006, "traffic", 8, 1), (37.7749, -122.4194, "wind", 18, 6),
    (49.2827, -123.1207, "rain", 21, 2), (-36.8485, 174.7633, "birds", 6, 3), (13.7563, 100.5018, "thunderstorm", 20, 5),
    (60.3913, 5.3221, "rain", 15, 12), (36.3932, 25.4615, "waves", 19, 11), (27.7172, 85.324, "chimes", 6, 14),
    (-34.6037, -58.3816, "strings", 23, 3), (52.52, 13.405, "traffic", 8, 4), (43.7696, 11.2558, "strings", 21, 9),
    (35.6895, 139.6917, "traffic", 7, 2), (1.3521, 103.8198, "crickets", 21, 6), (-17.7134, 178.065, "waves", 12, 15),
    (39.9042, 116.4074, "traffic", 18, 5), (48.8566, 2.3522, "birds", 7, 1), (51.5072, -0.1276, "rain", 16, 2),
    (-33.9249, 18.4241, "wind", 15, 7), (61.2181, -149.9003, "fire", 22, 10), (44.4268, 26.1025, "crickets", 23, 8),
    (25.2048, 55.2708, "wind", 17, 13), (4.711, -74.0721, "birds", 6, 4), (63.4305, 10.3951, "fire", 21, 16),
    (-41.2866, 174.7756, "stream", 13, 18), (34.0522, -118.2437, "strings", 19, 3), (50.0755, 14.4378, "chimes", 18, 5),
)

# ESC-50 category for each synthetic sound, used when real clips have been fetched.
ESC50_FOR: dict[str, str] = {
    "rain": "rain", "birds": "chirping_birds", "traffic": "engine", "waves": "sea_waves", "wind": "wind",
    "stream": "pouring_water", "chimes": "church_bells", "crickets": "crickets", "fire": "crackling_fire",
    "thunderstorm": "thunderstorm",
}


def real_clips(real_dir: Path = REAL_DIR) -> dict[str, list[Path]]:
    """Fetched ESC-50 files by category, or an empty dict when nothing was fetched."""
    manifest = real_dir / "manifest.csv"
    if not manifest.is_file():
        return {}
    clips: dict[str, list[Path]] = {}
    with manifest.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            path = real_dir / "audio" / row["filename"]
            if path.is_file():
                clips.setdefault(row["category"], []).append(path)
    return clips


def loop_to_ten_seconds(path: Path) -> bytes:
    """ESC-50 clips are 5 s long. Play them twice with a short crossfade to fill a postcard."""
    samples = decode(path.read_bytes(), rate=PLAYBACK_RATE, max_seconds=10.0)
    target = 10 * PLAYBACK_RATE
    if samples.size == 0:
        raise ValueError(f"{path} has no audio")
    fade = PLAYBACK_RATE // 20
    out = samples.copy()
    while out.size < target:
        head = samples.copy()
        if out.size > fade and head.size > fade:
            ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
            out[-fade:] = out[-fade:] * (1 - ramp) + head[:fade] * ramp
            head = head[fade:]
        out = np.concatenate([out, head])
    return wav_bytes(out[:target], PLAYBACK_RATE)


def seed_demo(service: PostcardService, *, real_dir: Path = REAL_DIR, now: datetime | None = None, render: bool = False) -> int:
    """Insert the demo postcards. Returns how many were added. Safe to run twice."""
    now = now or datetime.now(UTC)
    real = real_clips(real_dir)
    with service.db.connection() as conn:
        existing = {row["clip_key"] for row in conn.execute("SELECT clip_key FROM postcards WHERE seeded AND device_hash = 'seed'")}
    if existing:
        return 0  # already seeded; a second run must not add a second set (real clips have other keys)
    analysed: dict[str, Tagging] = {}
    added = 0
    for index, (lat, lon, kind, hour, days_ago) in enumerate(DEMO):
        variant = sum(1 for entry in DEMO[:index] if entry[2] == kind)
        candidates = real.get(ESC50_FOR.get(kind, ""), [])
        if candidates:
            source = candidates[variant % len(candidates)]
            clip_key = f"demo/esc50-{kind}-{source.stem.lower()}.mp3"
        else:
            source = None
            clip_key = f"demo/synth-{kind}-{variant}.mp3"
        if clip_key not in analysed:
            audio = loop_to_ten_seconds(source) if source else wav_bytes(synth.synthesise(kind, variant), synth.RATE)
            mp3, tagging = service.analyse(audio)
            service.store.put(clip_key, mp3, "audio/mpeg")
            analysed[clip_key] = tagging
        if clip_key in existing:
            continue
        existing.add(clip_key)
        point = snap(lat, lon)
        # Put the creation time at the requested local hour, a few days back.
        offset = timedelta(minutes=round(point.lon / 15.0 * 60.0))
        local = (now + offset - timedelta(days=days_ago)).replace(hour=hour, minute=(index * 7) % 60, second=0, microsecond=0)
        created = local - offset
        local_date, local_hour = local_clock(created, point, None)
        tagging = analysed[clip_key]
        service.insert(
            NewPostcard(
                point=point,
                source="seed",
                place=service.namer.name(point),
                local_date=local_date,
                local_hour=local_hour,
                tagging=tagging,
                tags=pick_motifs(tagging.labels),
                weather=None,
                device_hash="seed",
                clip_key=clip_key,
                seeded=True,
                created_at=created,
            ),
            render=render,
        )
        added += 1
    return added


def seed_pins(service: PostcardService, count: int, *, seed: int = 6, now: datetime | None = None) -> int:
    """Scatter `count` synthetic pins over the world's cities, weighted by population."""
    now = now or datetime.now(UTC)
    rng = np.random.default_rng(seed)
    with service.db.connection() as conn:
        templates = conn.execute(
            f"SELECT {COLUMNS}, embedding FROM postcards WHERE seeded AND clip_key LIKE 'demo/%%' AND device_hash = 'seed'"  # noqa: S608
        ).fetchall()
    if not templates:
        raise RuntimeError("seed the demo postcards first: python -m app.seed demo")
    namer = service.namer if isinstance(service.namer, OfflinePlaceNamer) else OfflinePlaceNamer()
    cities = namer.sample_cities(rng, count)
    rows = []
    for lat, lon in cities:
        # Up to about 12 km from the city centre, and never past the poles.
        point = snap(float(np.clip(lat + rng.normal(0, 0.05), -89.0, 89.0)), float((lon + rng.normal(0, 0.07) + 180.0) % 360.0 - 180.0))
        template = templates[int(rng.integers(0, len(templates)))]
        embedding = as_array(template["embedding"]) + rng.normal(0, 0.004, 1024).astype(np.float32)
        embedding /= float(np.linalg.norm(embedding))
        created = now - timedelta(minutes=int(rng.integers(0, 60 * 24 * 60)))
        local_date, local_hour = local_clock(created, point, None)
        place = namer.name(point)
        rows.append(
            {
                "id": new_id(),
                "created_at": created,
                "lat_md": point.lat_md,
                "lon_md": point.lon_md,
                "location_source": "seed",
                "place_name": place.name,
                "country_code": place.country_code,
                "country_name": place.country_name,
                "local_date": local_date,
                "local_hour": local_hour,
                "time_of_day": time_of_day(local_hour),
                "labels": template["labels"],
                "motifs": template["motifs"],
                "speech_prob": template["speech_prob"],
                "embedding": embedding,
                "weather": None,
                "clip_key": template["clip_key"],
                "image_key": None,
                "image_provider": "procedural",
                "prompt": "",
                "device_hash": "seed-pin",
                "seeded": True,
                "hidden": False,
            }
        )
    with service.db.connection() as conn:
        for row in rows:
            row["prompt"] = service.brief_for(row).prompt()
            insert_row(conn, row)
    return len(rows)


def clear(service: PostcardService, *, pins_only: bool) -> int:
    with service.db.connection() as conn:
        where = "seeded AND device_hash = 'seed-pin'" if pins_only else "seeded"
        rows = conn.execute(f"DELETE FROM postcards WHERE {where} RETURNING id, image_key, clip_key").fetchall()  # noqa: S608
        still_used = {row["clip_key"] for row in conn.execute("SELECT DISTINCT clip_key FROM postcards")}
    for row in rows:
        if row["image_key"]:
            service.store.delete(row["image_key"])
            service.store.delete(f"postcards/{row['id']}.webp")
        if row["clip_key"] not in still_used:
            service.store.delete(row["clip_key"])
    return len(rows)


def main(argv: list[str]) -> int:
    from app.main import build_service

    settings = get_settings()
    migrate(settings.database_url)
    db = Database(settings.database_url, max_size=2)
    db.open()
    try:
        service = build_service(settings, db=db)
        command = argv[0] if argv else "demo"
        if command == "demo":
            print(f"demo postcards added: {seed_demo(service)} (total now {service.count()})")
        elif command == "pins":
            count = int(argv[1]) if len(argv) > 1 else 5000
            if service.count() == 0:
                seed_demo(service)
            print(f"synthetic pins added: {seed_pins(service, count)} (total now {service.count()})")
        elif command == "clear-pins":
            print(f"synthetic pins removed: {clear(service, pins_only=True)}")
        elif command == "clear":
            print(f"seeded postcards removed: {clear(service, pins_only=False)}")
        else:
            print(__doc__)
            return 2
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
