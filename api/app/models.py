"""Shapes that cross the HTTP boundary."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.geo.grid import GridPoint


class TagOut(BaseModel):
    slug: str
    name: str
    score: float


class LabelOut(BaseModel):
    name: str
    score: float


class CellOut(BaseModel):
    """The privacy cell a pin stands for. The pin is its centre."""

    width_m: float
    height_m: float


class PostcardOut(BaseModel):
    id: str
    created_at: datetime
    lat: float
    lon: float
    cell: CellOut
    place_name: str
    country_code: str | None
    country_name: str | None
    local_date: date
    local_hour: int
    time_of_day: Literal["dawn", "day", "dusk", "night"]
    tags: list[TagOut]
    labels: list[LabelOut]
    speech_probability: float
    weather: dict[str, object] | None
    audio_url: str
    image_url: str
    thumb_url: str
    image_provider: str
    prompt: str
    seeded: bool
    distance_m: float | None = None
    similarity: float | None = None


class PostcardList(BaseModel):
    items: list[PostcardOut]


class PlaceOut(BaseModel):
    lat: float
    lon: float
    cell: CellOut
    place_name: str
    country_name: str | None


class QuotaOut(BaseModel):
    limit: int
    used: int
    remaining: int
    resets_at: datetime | None


class ReportIn(BaseModel):
    reason: Literal["speech", "private", "offensive", "other"] = "other"


class ReportOut(BaseModel):
    reported: bool
    hidden: bool


class ReportedPostcard(BaseModel):
    postcard: PostcardOut
    reports: int
    reasons: list[str]
    hidden: bool


class ErrorBody(BaseModel):
    code: str
    message: str
    detail: dict[str, object] = Field(default_factory=dict)


class ErrorOut(BaseModel):
    error: ErrorBody


def cell_of(point: GridPoint) -> CellOut:
    width, height = point.cell_size_m()
    return CellOut(width_m=round(width, 1), height_m=round(height, 1))
