"""Seed data and the server half of the "5,000 pins in under 2 seconds" acceptance test."""

from __future__ import annotations

import json
import statistics
import time

from fastapi.testclient import TestClient

from app.geo.grid import is_on_grid
from app.seed import DEMO, clear, seed_demo, seed_pins
from app.service import PostcardService

BUDGET_SECONDS = 0.5  # a quarter of the 2 s the whole map load is allowed


def test_demo_seed_runs_the_real_pipeline_and_is_idempotent(service: PostcardService) -> None:
    assert seed_demo(service) == len(DEMO)
    assert seed_demo(service) == 0
    cards = service.recent(60)
    assert len(cards) == len(DEMO) and all(card.seeded for card in cards)
    assert {"Kyoto", "Lisbon", "Mumbai", "Reykjavik"} <= {card.place_name for card in cards}
    assert len({card.tags[0].slug for card in cards}) >= 6  # a spread of sounds, as tagged by the real model
    assert all(service.store.exists(f"demo/synth-{kind}-0.mp3") for kind in {entry[2] for entry in DEMO})


def test_acceptance_api_serves_5000_pins_well_inside_the_budget(client: TestClient, service: PostcardService, database) -> None:  # type: ignore[no-untyped-def]
    """PRD acceptance test 4, server side. The browser side is measured by web/scripts/perf-map.ts."""
    seed_demo(service)
    assert seed_pins(service, 5000) == 5000
    with database.connection() as conn:
        rows = conn.execute("SELECT lat_md, lon_md FROM postcards").fetchall()
    assert len(rows) == 5000 + len(DEMO)
    assert all(is_on_grid(row["lat_md"], row["lon_md"]) for row in rows)  # seeded pins obey the privacy grid too

    timings = []
    for _ in range(7):
        started = time.perf_counter()
        response = client.get("/api/pins", params={"bbox": "-180,-85,180,85", "zoom": 1.35})
        timings.append(time.perf_counter() - started)
    assert response.status_code == 200
    body = json.loads(response.text)
    assert body["mode"] == "pins" and body["total"] == len(rows) == len(body["features"])
    median = statistics.median(timings)
    print(f"\n/api/pins with {body['total']} pins: median {median * 1000:.0f} ms, max {max(timings) * 1000:.0f} ms, {len(response.content) / 1024:.0f} KB of GeoJSON")
    assert median < BUDGET_SECONDS, timings

    # A lazily painted pin still yields a picture, and clearing the pins leaves the demo set.
    some_pin = next(feature["properties"]["id"] for feature in body["features"])
    assert client.get(f"/api/postcards/{some_pin}/image", params={"size": "thumb"}).headers["content-type"] == "image/webp"
    assert clear(service, pins_only=True) == 5000
    assert service.count() == len(DEMO)


def test_database_groups_pins_on_a_grid_when_there_are_too_many(client: TestClient, service: PostcardService) -> None:
    seed_demo(service)
    seed_pins(service, 600)
    service.settings = service.settings.model_copy(update={"max_pins": 200})
    world = json.loads(client.get("/api/pins", params={"bbox": "-180,-85,180,85", "zoom": 1}).text)
    assert world["mode"] == "cells" and world["total"] == 600 + len(DEMO)
    assert len(world["features"]) < 200
    assert sum(feature["properties"]["count"] for feature in world["features"]) == world["total"]
    singles = [feature for feature in world["features"] if feature["properties"]["count"] == 1]
    assert all(feature["properties"]["id"] for feature in singles)
    # Zooming in makes the cells smaller, so there are more of them for the same area.
    europe_far = json.loads(client.get("/api/pins", params={"bbox": "-10,35,30,60", "zoom": 2}).text)
    europe_near = json.loads(client.get("/api/pins", params={"bbox": "-10,35,30,60", "zoom": 9}).text)
    assert europe_far["total"] == europe_near["total"]
    if europe_near["mode"] == "cells":
        assert len(europe_near["features"]) >= len(europe_far["features"])
    # A box across the antimeridian finds Fiji and Auckland, not the whole world.
    pacific = json.loads(client.get("/api/pins", params={"bbox": "170,-50,-170,-10", "zoom": 3}).text)
    assert 0 < pacific["total"] < world["total"]
