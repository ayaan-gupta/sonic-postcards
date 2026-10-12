"""What a postcard is about: the brief every image provider is given."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from app.audio.motifs import MOTIF_BY_SLUG

TimeOfDay = Literal["dawn", "day", "dusk", "night"]

_TIME_PHRASE: dict[str, str] = {
    "dawn": "at first light",
    "day": "in bright daylight",
    "dusk": "at dusk",
    "night": "at night",
}
_WEATHER_PHRASE: dict[str, str] = {
    "clear": "under a clear sky",
    "cloudy": "under heavy cloud",
    "fog": "in fog",
    "drizzle": "in light drizzle",
    "rain": "in the rain",
    "snow": "in falling snow",
    "storm": "under a storm",
}

STYLE = (
    "Vintage travel postcard illustration painted in gouache: flat opaque colour, visible brush texture, "
    "a limited palette of five or six colours, matte finish, simple bold shapes, mid-century travel poster "
    "composition. No text, no lettering, no numbers, no border, no stamp, no postmark, no people in close-up."
)


def time_of_day(hour: int) -> TimeOfDay:
    if 5 <= hour < 8:
        return "dawn"
    if 8 <= hour < 17:
        return "day"
    if 17 <= hour < 21:
        return "dusk"
    return "night"


@dataclass(frozen=True)
class PostcardBrief:
    postcard_id: str
    motifs: list[str]  # up to three motif slugs, strongest first
    labels: list[str]  # the tagger's own class names, strongest first
    time_of_day: TimeOfDay
    place_name: str
    country_name: str | None
    local_date: date
    weather: str | None = None
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def seed(self) -> int:
        """Stable per postcard, so re-rendering paints the same picture."""
        return int.from_bytes(hashlib.sha256(self.postcard_id.encode()).digest()[:4], "big")

    def prompt(self) -> str:
        """The text prompt for a generative provider: labels, time of day, place, weather."""
        sounds = [MOTIF_BY_SLUG[slug].phrase for slug in self.motifs if slug in MOTIF_BY_SLUG]
        heard = "a quiet place"
        if len(sounds) > 1:
            heard = ", ".join(sounds[:-1]) + " and " + sounds[-1]
        elif sounds:
            heard = sounds[0]
        where = self.place_name + (f", {self.country_name}" if self.country_name else "")
        when = _TIME_PHRASE[self.time_of_day]
        weather = f" {_WEATHER_PHRASE[self.weather]}" if self.weather in _WEATHER_PHRASE else ""
        return f"{where} {when}{weather}. The scene shows where you would hear {heard}. {STYLE}"
