"""Shared fixtures. The suite talks to a real Postgres with PostGIS and pgvector
(the container from `make db`) and runs the real tagger; nothing is mocked
except HTTP calls to outside services."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.audio.tagger import YamnetTagger
from app.audio.wav import wav_bytes
from app.config import Settings
from app.db import Database, migrate
from app.fixtures import synth
from app.geo.places import OfflinePlaceNamer
from app.main import build_service, create_app
from app.service import PostcardService

FIXTURES = Path(__file__).parent / "fixtures"
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql://sonic:sonic@127.0.0.1:5506/sonic_test")


def _ensure_database(url: str) -> None:
    base, _, name = url.rpartition("/")
    try:
        with psycopg.connect(f"{base}/postgres", autocommit=True) as conn:
            exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone()
            if not exists:
                conn.execute(f'CREATE DATABASE "{name}"')
    except psycopg.OperationalError as exc:  # pragma: no cover - only without a database
        pytest.exit(f"Postgres is not reachable at {base}. Start it with `make db`. ({exc})", returncode=2)


@pytest.fixture(scope="session")
def database() -> Iterator[Database]:
    _ensure_database(TEST_DATABASE_URL)
    migrate(TEST_DATABASE_URL)
    db = Database(TEST_DATABASE_URL, max_size=4)
    db.open()
    yield db
    db.close()


@pytest.fixture(scope="session")
def tagger() -> YamnetTagger:
    return YamnetTagger()


@pytest.fixture(scope="session")
def namer() -> OfflinePlaceNamer:
    return OfflinePlaceNamer()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=TEST_DATABASE_URL,
        storage_dir=tmp_path / "storage",
        assets_dir=Path(__file__).resolve().parents[2] / "assets",
        admin_token="test-admin-token",
        device_salt="test-salt",
        seed_on_start=False,
        _env_file=None,  # type: ignore[call-arg]
    )


@pytest.fixture
def service(settings: Settings, database: Database, tagger: YamnetTagger, namer: OfflinePlaceNamer) -> PostcardService:
    with database.connection() as conn:
        conn.execute("TRUNCATE postcards, reports, upload_events RESTART IDENTITY CASCADE")
    return build_service(settings, db=database, tagger=tagger, namer=namer)


@pytest.fixture
def client(settings: Settings, service: PostcardService) -> Iterator[TestClient]:
    with TestClient(create_app(settings, service=service)) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def clips() -> dict[str, bytes]:
    """One WAV per synthetic sound, made once per run."""
    return {kind: wav_bytes(synth.synthesise(kind, 0), synth.RATE) for kind in synth.SOUNDS}


DEVICE = "device-aaaaaaaaaaaa"


def post_clip(client: TestClient, audio: bytes, *, lat: float = 35.011635, lon: float = 135.768029, device: str = DEVICE, filename: str = "clip.wav"):  # type: ignore[no-untyped-def]
    return client.post(
        "/api/postcards",
        files={"audio": (filename, audio, "application/octet-stream")},
        data={"lat": str(lat), "lon": str(lon), "source": "gps", "tz_offset_min": "540"},
        headers={"X-Device-Id": device},
    )
