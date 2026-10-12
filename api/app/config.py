"""Runtime configuration. Every value has a default that works offline with no keys."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

API_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = API_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(REPO_DIR / ".env",), extra="ignore")

    # Postgres with PostGIS and pgvector. 5506 is the host port of the bundled container.
    database_url: str = "postgresql://sonic:sonic@127.0.0.1:5506/sonic"

    # Object storage for clips and postcard images.
    storage_backend: Literal["local", "s3"] = "local"
    storage_dir: Path = REPO_DIR / "storage"
    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    s3_region: str = "auto"
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_public_base_url: str = ""

    # Design-time art. A file in generated/ wins over the same path in interim/.
    assets_dir: Path = REPO_DIR / "assets"

    # Audio pipeline.
    clip_seconds: float = 10.0
    min_clip_seconds: float = 8.0
    max_upload_bytes: int = 8_000_000
    speech_threshold: float = Field(0.6, ge=0.0, le=1.0)

    # Place names and weather. "offline" and "none" never touch the network.
    geocoder: Literal["offline", "nominatim"] = "offline"
    nominatim_url: str = "https://nominatim.openstreetmap.org/reverse"
    weather: Literal["none", "open-meteo"] = "none"
    open_meteo_url: str = "https://api.open-meteo.com/v1/forecast"
    http_user_agent: str = "sonic-postcards/0.1 (self-hosted demo)"
    http_timeout_seconds: float = 4.0

    # Postcard art. "procedural" is the built-in painter and needs no network.
    image_provider: Literal["procedural", "openai"] = "procedural"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    image_model: str = "gpt-image-1"
    image_timeout_seconds: float = 90.0

    # Moderation.
    daily_postcard_limit: int = 10
    report_hide_threshold: int = 3
    admin_token: str = ""
    device_salt: str = "change-me-in-production"

    # Map queries.
    max_pins: int = 8000

    # Seed the demo postcards on first start when the table is empty.
    seed_on_start: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
