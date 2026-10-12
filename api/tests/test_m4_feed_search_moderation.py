"""Milestone 4: nearby feed, "sounds like this" search, moderation and rate limits."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.audio.motifs import pick_motifs
from app.audio.wav import wav_bytes
from app.errors import RateLimited
from app.fixtures import synth
from app.geo.grid import snap
from app.service import NewPostcard, PostcardService
from tests.conftest import DEVICE, post_clip

ADMIN = {"Authorization": "Bearer test-admin-token"}
KYOTO = (35.0116, 135.7681)


def add(service: PostcardService, kind: str, seed: int, lat: float, lon: float, *, minutes_ago: int = 0) -> str:
    """Put a synthetic clip on the map through the real pipeline, without painting it."""
    mp3, tagging = service.analyse(wav_bytes(synth.synthesise(kind, seed), synth.RATE))
    key = f"demo/test-{kind}-{seed}.mp3"
    service.store.put(key, mp3, "audio/mpeg")
    point = snap(lat, lon)
    created = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    card = service.insert(
        NewPostcard(point=point, source="seed", place=service.namer.name(point), local_date=created.date(), local_hour=12, tagging=tagging,
                    tags=pick_motifs(tagging.labels), weather=None, device_hash="seed", clip_key=key, seeded=True, created_at=created),
        render=False,
    )
    return card.id


# -- nearby feed -------------------------------------------------------------------


def test_nearby_feed_uses_a_radius_and_reports_distance(client: TestClient, service: PostcardService) -> None:
    here = add(service, "rain", 0, *KYOTO, minutes_ago=30)
    osaka = add(service, "birds", 0, 34.6937, 135.5023, minutes_ago=20)  # about 43 km away
    add(service, "waves", 0, 35.6895, 139.6917, minutes_ago=10)  # Tokyo, about 365 km away

    close = client.get("/api/nearby", params={"lat": KYOTO[0], "lon": KYOTO[1], "radius_km": 5}).json()["items"]
    assert [item["id"] for item in close] == [here] and close[0]["distance_m"] < 600

    wider = client.get("/api/nearby", params={"lat": KYOTO[0], "lon": KYOTO[1], "radius_km": 60}).json()["items"]
    assert [item["id"] for item in wider] == [osaka, here]  # newest first
    assert 40_000 < wider[0]["distance_m"] < 46_000

    nearest = client.get("/api/nearby", params={"lat": KYOTO[0], "lon": KYOTO[1], "radius_km": 500, "sort": "nearest"}).json()["items"]
    assert len(nearest) == 3 and [item["distance_m"] for item in nearest] == sorted(item["distance_m"] for item in nearest)
    assert client.get("/api/nearby", params={"lat": 0, "lon": 0, "radius_km": 100}).json()["items"] == []
    assert client.get("/api/nearby", params={"lat": 0, "lon": 0, "radius_km": 0}).status_code == 400


# -- sounds like this --------------------------------------------------------------

FIXTURE_KINDS = ("rain", "birds", "traffic", "waves", "wind", "stream", "crickets", "fire")


def test_acceptance_sounds_like_this_on_rain_returns_rain_in_the_top_five(client: TestClient, service: PostcardService) -> None:
    """PRD acceptance test 3 on the synthetic fixture set: 8 sounds x 6 takes = 48 clips, 6 of them rain.

    The clips are synthesised, so this shows the search works, not that the embedding understands rain.
    scripts/eval_similarity.py runs the same check on real ESC-50 recordings.
    """
    ids: dict[str, str] = {}
    for kind in FIXTURE_KINDS:
        for seed in range(6):
            ids[add(service, kind, seed, 10.0 + seed * 3.1, 20.0 + FIXTURE_KINDS.index(kind) * 7.3)] = kind
    rain = [pid for pid, kind in ids.items() if kind == "rain"]
    assert len(rain) == 6
    for query in rain:
        top = client.get(f"/api/postcards/{query}/similar", params={"limit": 5}).json()["items"]
        kinds = [ids[item["id"]] for item in top]
        assert kinds == ["rain"] * 5, kinds
        assert query not in [item["id"] for item in top]
        scores = [item["similarity"] for item in top]
        assert scores == sorted(scores, reverse=True) and scores[-1] > 0.9


def test_similar_respects_the_geographic_filter(client: TestClient, service: PostcardService) -> None:
    query = add(service, "rain", 0, *KYOTO)
    far_twin = add(service, "rain", 1, -33.8568, 151.2153)  # Sydney: the closest sound, the wrong place
    near_other = add(service, "birds", 0, 34.6937, 135.5023)  # Osaka: the right place, a different sound
    near_rain = add(service, "rain", 2, 34.9858, 135.7588)  # 3 km south

    worldwide = [item["id"] for item in client.get(f"/api/postcards/{query}/similar").json()["items"]]
    assert worldwide[:2] in ([far_twin, near_rain], [near_rain, far_twin]) and worldwide[-1] == near_other

    local = client.get(f"/api/postcards/{query}/similar", params={"lat": KYOTO[0], "lon": KYOTO[1], "radius_km": 60}).json()["items"]
    assert [item["id"] for item in local] == [near_rain, near_other]
    assert client.get("/api/postcards/missing/similar").status_code == 404


# -- rate limit --------------------------------------------------------------------


def test_eleventh_postcard_in_a_day_is_refused(client: TestClient, clips: dict[str, bytes], service: PostcardService) -> None:
    for index in range(10):
        assert post_clip(client, clips["rain"]).status_code == 201, index
    quota = client.get("/api/quota", headers={"X-Device-Id": DEVICE}).json()
    assert (quota["limit"], quota["used"], quota["remaining"]) == (10, 10, 0) and quota["resets_at"]

    refused = post_clip(client, clips["rain"])
    assert refused.status_code == 429
    assert refused.json()["error"]["code"] == "rate_limited" and "limit" in refused.json()["error"]["message"]
    assert "retry-after" in refused.headers
    assert service.count() == 10

    # Another device is unaffected.
    assert post_clip(client, clips["rain"], device="device-bbbbbbbbbbbb").status_code == 201


def test_limit_is_a_rolling_24_hours_and_deleting_does_not_refund(service: PostcardService, clips: dict[str, bytes]) -> None:
    start = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
    made = [service.create(audio=clips["birds"], lat=1.0, lon=1.0, source="manual", device_id=DEVICE, now=start + timedelta(minutes=i)) for i in range(10)]
    service.delete(made[0].id)
    with pytest.raises(RateLimited):
        service.create(audio=clips["birds"], lat=1.0, lon=1.0, source="manual", device_id=DEVICE, now=start + timedelta(hours=23))
    later = service.create(audio=clips["birds"], lat=1.0, lon=1.0, source="manual", device_id=DEVICE, now=start + timedelta(hours=24, minutes=1))
    # By then the first three uploads have aged out of the window: seven remain, plus this one.
    assert later.id and service.quota(DEVICE, now=start + timedelta(hours=24, minutes=2)).used == 8


def test_rejected_speech_does_not_use_up_the_allowance(client: TestClient, clips: dict[str, bytes]) -> None:
    from tests.conftest import FIXTURES

    for _ in range(3):
        assert post_clip(client, (FIXTURES / "speech" / "monologue_chrome.webm").read_bytes()).status_code == 422
    assert client.get("/api/quota", headers={"X-Device-Id": DEVICE}).json()["used"] == 0


# -- report and delete -------------------------------------------------------------


def test_three_reports_hide_a_postcard_everywhere(client: TestClient, service: PostcardService) -> None:
    target = add(service, "rain", 0, *KYOTO)
    other = add(service, "rain", 1, 35.02, 135.76)
    for index in range(2):
        body = client.post(f"/api/postcards/{target}/report", json={"reason": "speech"}, headers={"X-Device-Id": f"reporter-{index:08d}"}).json()
        assert body == {"reported": True, "hidden": False}
    # The same device reporting again changes nothing.
    again = client.post(f"/api/postcards/{target}/report", json={"reason": "other"}, headers={"X-Device-Id": "reporter-00000000"}).json()
    assert again["hidden"] is False
    third = client.post(f"/api/postcards/{target}/report", json={"reason": "private"}, headers={"X-Device-Id": "reporter-00000002"}).json()
    assert third["hidden"] is True

    assert client.get(f"/api/postcards/{target}").status_code == 404
    assert client.get(f"/api/postcards/{target}/audio").status_code == 404
    assert json.loads(client.get("/api/pins").text)["total"] == 1
    assert [item["id"] for item in client.get("/api/nearby", params={"lat": KYOTO[0], "lon": KYOTO[1], "radius_km": 50}).json()["items"]] == [other]
    assert target not in [item["id"] for item in client.get(f"/api/postcards/{other}/similar").json()["items"]]
    assert client.post(f"/api/postcards/{target}/report", json={"reason": "nonsense"}, headers={"X-Device-Id": "reporter-00000009"}).status_code == 400
    assert client.post("/api/postcards/missing/report", json={}, headers={"X-Device-Id": "reporter-00000009"}).status_code == 404


def test_admin_can_review_restore_and_delete(client: TestClient, clips: dict[str, bytes], service: PostcardService) -> None:
    card = post_clip(client, clips["fire"]).json()
    client.post(f"/api/postcards/{card['id']}/report", json={"reason": "offensive"}, headers={"X-Device-Id": "reporter-00000001"})

    assert client.get("/api/admin/reports").status_code == 401
    assert client.get("/api/admin/reports", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.delete(f"/api/admin/postcards/{card['id']}").status_code == 401

    queue = client.get("/api/admin/reports", headers=ADMIN).json()
    assert len(queue) == 1 and queue[0]["postcard"]["id"] == card["id"] and queue[0]["reasons"] == ["offensive"] and queue[0]["reports"] == 1

    assert client.post(f"/api/admin/postcards/{card['id']}/restore", headers=ADMIN).status_code == 204
    assert client.get("/api/admin/reports", headers=ADMIN).json() == []

    files = [f"clips/{card['id']}.mp3", f"postcards/{card['id']}.png", f"postcards/{card['id']}.webp"]
    assert all(service.store.exists(key) for key in files)
    assert client.delete(f"/api/admin/postcards/{card['id']}", headers=ADMIN).status_code == 204
    assert client.get(f"/api/postcards/{card['id']}").status_code == 404
    assert not any(service.store.exists(key) for key in files)
    assert client.delete(f"/api/admin/postcards/{card['id']}", headers=ADMIN).status_code == 404


def test_admin_endpoints_are_off_without_a_token(settings, service: PostcardService) -> None:  # type: ignore[no-untyped-def]
    from app.main import create_app

    service.settings = settings.model_copy(update={"admin_token": ""})
    with TestClient(create_app(service.settings, service=service)) as locked:
        response = locked.delete("/api/admin/postcards/anything", headers={"Authorization": "Bearer "})
    assert response.status_code == 503 and response.json()["error"]["code"] == "admin_disabled"
