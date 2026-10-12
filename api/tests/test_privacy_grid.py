"""The privacy rule: locations are snapped to a roughly 500 m grid before they
are stored, and the database refuses anything that is not on the grid."""

from __future__ import annotations

import json
import math
from datetime import UTC, date, datetime

import numpy as np
import psycopg
import pytest
from fastapi.testclient import TestClient

from app.db import Database
from app.geo.grid import LON_BANDS, GridPoint, is_on_grid, lon_step_md, snap
from tests.conftest import FIXTURES, post_clip

VECTORS = FIXTURES / "grid_vectors.json"

# A recording made at the gate of a real house would give coordinates like these.
PRECISE = [
    (35.011635, 135.768029),
    (64.146582, -21.942635),
    (-33.856784, 151.215297),
    (78.223417, 15.646892),
    (0.000912, -0.001377),
    (-54.801912, -68.302951),
    (51.4999999, 179.9993),
]


def test_snap_is_idempotent_and_never_moves_a_point_far() -> None:
    rng = np.random.default_rng(12)
    for _ in range(4000):
        lat, lon = float(rng.uniform(-89.5, 89.5)), float(rng.uniform(-180, 180))
        point = snap(lat, lon)
        assert is_on_grid(point.lat_md, point.lon_md)
        assert snap(point.lat, point.lon) == point
        assert abs(point.lat - lat) <= 0.0025 + 1e-9
        dlon = abs((point.lon - lon + 180) % 360 - 180)
        assert dlon <= point.lon_step_md / 2000 + 1e-9


def test_every_cell_is_roughly_500_metres_wide_at_every_latitude() -> None:
    """The longitude step doubles with latitude so a cell never shrinks below 393 m."""
    for lat_md in range(0, 89_300, 5):
        width, height = GridPoint(lat_md=lat_md, lon_md=0).cell_size_m()
        assert height == pytest.approx(556.6, abs=0.1)
        assert 393.0 <= width <= 788.0, (lat_md, width)
    # A fixed 0.005 degree step would have been 278 m wide in Oslo.
    assert 0.005 * 111_320 * math.cos(math.radians(60)) < 280
    assert GridPoint(lat_md=59_915, lon_md=10_750).cell_size_m()[0] > 550


def test_bands_close_at_the_antimeridian() -> None:
    for _, step in LON_BANDS:
        assert 360_000 % step == 0
    wrapped = snap(10.0, 179.9999)
    assert wrapped.lon_md == -180_000
    assert snap(10.0, -180.0).lon_md == -180_000
    # At the widest step the last cell east of zero and the first one west of it are one step apart.
    east, west = snap(89.99, 179.9), snap(89.99, -179.9)
    assert (east.lon_md, west.lon_md) == (179_840, -179_840)
    assert (west.lon_md - east.lon_md) % 360_000 == 320
    assert snap(89.99, 180.0).lon_md == -179_840


def test_python_matches_the_shared_vectors() -> None:
    """The same file is checked by the TypeScript tests, so the two implementations cannot drift."""
    vectors = json.loads(VECTORS.read_text())
    assert len(vectors) >= 200
    for item in vectors:
        point = snap(item["lat"], item["lon"])
        assert (point.lat_md, point.lon_md, point.lon_step_md) == (item["lat_md"], item["lon_md"], item["step_md"])


def test_out_of_range_coordinates_are_refused() -> None:
    for lat, lon in ((91.0, 0.0), (0.0, 181.0), (float("nan"), 0.0), (0.0, float("inf"))):
        with pytest.raises(ValueError):
            snap(lat, lon)


def _insert(conn: psycopg.Connection, lat_md: int, lon_md: int) -> None:  # type: ignore[type-arg]
    conn.execute(
        """
        INSERT INTO postcards (id, lat_md, lon_md, location_source, place_name, local_date, local_hour, time_of_day,
                               labels, motifs, speech_prob, embedding, clip_key, device_hash)
        VALUES (%s, %s, %s, 'manual', 'Test', %s, 12, 'day', '[]', '{hum}', 0, %s, 'clips/x.mp3', 'device')
        """,
        (f"t{abs(lat_md)}x{abs(lon_md)}", lat_md, lon_md, date(2026, 1, 1), np.zeros(1024, dtype=np.float32)),
    )


@pytest.mark.parametrize(
    ("lat_md", "lon_md", "constraint"),
    [
        (35_012, 135_770, "lat_on_privacy_grid"),  # latitude to the millidegree
        (35_010, 135_768, "lon_on_privacy_grid"),  # longitude to the millidegree
        (59_915, 10_745, "lon_on_privacy_grid"),  # on the 5 md grid, but Oslo needs 10
        (78_220, 15_650, "lon_on_privacy_grid"),  # Svalbard needs 20
        (35_010, 180_000, "lon_in_range"),
        (90_005, 0, "lat_on_privacy_grid"),
    ],
)
def test_acceptance_database_refuses_coordinates_off_the_grid(service, database: Database, lat_md: int, lon_md: int, constraint: str) -> None:  # type: ignore[no-untyped-def]
    """PRD acceptance test 2, the hard half: even a direct INSERT cannot store more precision."""
    with pytest.raises(psycopg.errors.CheckViolation) as error, database.connection() as conn:
        _insert(conn, lat_md, lon_md)
    assert error.value.diag.constraint_name == constraint


def test_database_accepts_grid_points_and_derives_the_postgis_point(service, database: Database) -> None:  # type: ignore[no-untyped-def]
    with database.connection() as conn:
        _insert(conn, 59_915, 10_750)
        row = conn.execute("SELECT ST_X(geom) AS x, ST_Y(geom) AS y, ST_SRID(geom) AS srid FROM postcards").fetchone()
        assert row is not None and (row["x"], row["y"], row["srid"]) == (10.75, 59.915, 4326)
        # The point is generated from the integers and cannot be written on its own.
        with pytest.raises(psycopg.errors.GeneratedAlways):
            conn.execute("UPDATE postcards SET geom = ST_SetSRID(ST_MakePoint(10.7512345, 59.9151234), 4326)")


def test_acceptance_stored_coordinates_never_exceed_the_rounding_rule(client: TestClient, clips: dict[str, bytes], database: Database) -> None:
    """PRD acceptance test 2, end to end: upload with seven decimals, then inspect the database itself."""
    for index, (lat, lon) in enumerate(PRECISE):
        response = post_clip(client, clips["rain"], lat=lat, lon=lon, device=f"device-{index:012d}")
        assert response.status_code == 201, response.text
        body = response.json()
        assert is_on_grid(round(body["lat"] * 1000), round(body["lon"] * 1000))

    with database.connection() as conn:
        rows = conn.execute("SELECT lat_md, lon_md, sp_lon_step_md(lat_md) AS step, ST_X(geom) AS x, ST_Y(geom) AS y, (to_jsonb(postcards) - 'embedding' - 'labels')::text AS everything FROM postcards").fetchall()
        # 1. The rule, evaluated by Postgres over every row.
        off_grid = conn.execute(
            "SELECT count(*) AS n FROM postcards WHERE lat_md % 5 <> 0 OR lon_md % sp_lon_step_md(lat_md) <> 0 "
            "OR abs(ST_X(geom) * 1000 - lon_md) > 1e-6 OR abs(ST_Y(geom) * 1000 - lat_md) > 1e-6"
        ).fetchone()
        # 2. No other column could hold a location: these are all the numeric and spatial columns there are.
        columns = conn.execute(
            "SELECT column_name, data_type, udt_name FROM information_schema.columns WHERE table_name = 'postcards' "
            "AND (data_type IN ('double precision', 'real', 'numeric', 'integer', 'smallint', 'USER-DEFINED'))"
        ).fetchall()
    assert off_grid is not None and off_grid["n"] == 0
    assert len(rows) == len(PRECISE)
    assert {(c["column_name"], c["udt_name"]) for c in columns} == {
        ("lat_md", "int4"), ("lon_md", "int4"), ("geom", "geometry"), ("local_hour", "int2"), ("speech_prob", "float4"), ("embedding", "vector"),
    }
    for row in rows:
        assert is_on_grid(row["lat_md"], row["lon_md"])
        assert row["step"] == lon_step_md(row["lat_md"])
    everything = " ".join(row["everything"] for row in rows)
    for lat, lon in PRECISE:
        # 3. The digits that were sent appear nowhere in what was stored.
        for raw in (f"{abs(lat):.4f}", f"{abs(lon):.4f}"):
            assert raw not in everything, raw


def test_queries_snap_their_origin_too(client: TestClient) -> None:
    place = client.get("/api/place", params={"lat": 35.011635, "lon": 135.768029}).json()
    assert (place["lat"], place["lon"], place["place_name"]) == (35.01, 135.77, "Kyoto")
    assert 393 <= place["cell"]["width_m"] <= 788 and place["cell"]["height_m"] == pytest.approx(556.6)


def test_created_at_is_the_only_timestamp_and_it_is_server_time(client: TestClient, clips: dict[str, bytes]) -> None:
    before = datetime.now(UTC)
    card = post_clip(client, clips["rain"]).json()
    created = datetime.fromisoformat(card["created_at"])
    assert (created - before).total_seconds() < 30
    assert card["local_hour"] == (created.hour + 9) % 24  # tz_offset_min=540 from the browser
