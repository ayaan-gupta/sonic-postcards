"""Weather at a grid point, behind one interface. The default knows nothing and says so."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal, Protocol

import httpx

from app.geo.grid import GridPoint

Condition = Literal["clear", "cloudy", "fog", "drizzle", "rain", "snow", "storm"]


@dataclass(frozen=True)
class Weather:
    condition: Condition
    temperature_c: float | None
    wind_kph: float | None
    source: str

    def as_json(self) -> dict[str, object]:
        return asdict(self)


class WeatherSource(Protocol):
    def current(self, point: GridPoint) -> Weather | None: ...


class NoWeather:
    def current(self, point: GridPoint) -> Weather | None:
        return None


def condition_from_wmo(code: int) -> Condition:
    """WMO weather interpretation codes, as Open-Meteo reports them."""
    if code == 0 or code == 1:
        return "clear"
    if code in (2, 3):
        return "cloudy"
    if code in (45, 48):
        return "fog"
    if code in (51, 53, 55, 56, 57):
        return "drizzle"
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code in (95, 96, 99):
        return "storm"
    return "cloudy"


class OpenMeteoWeather:
    """Open-Meteo's forecast API: no key, free for non-commercial use. Opt in with WEATHER=open-meteo."""

    def __init__(self, *, url: str, user_agent: str, timeout: float = 4.0, client: httpx.Client | None = None) -> None:
        self._url = url
        self._client = client or httpx.Client(timeout=timeout, headers={"User-Agent": user_agent})

    def current(self, point: GridPoint) -> Weather | None:
        try:
            response = self._client.get(
                self._url,
                params={
                    "latitude": f"{point.lat:.3f}",
                    "longitude": f"{point.lon:.3f}",
                    "current": "temperature_2m,weather_code,wind_speed_10m",
                    "wind_speed_unit": "kmh",
                },
            )
            response.raise_for_status()
            return self.parse(response.json())
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return None

    @staticmethod
    def parse(payload: dict[str, object]) -> Weather | None:
        current = payload.get("current")
        if not isinstance(current, dict) or "weather_code" not in current:
            return None
        temperature = current.get("temperature_2m")
        wind = current.get("wind_speed_10m")
        return Weather(
            condition=condition_from_wmo(int(current["weather_code"])),
            temperature_c=float(temperature) if temperature is not None else None,
            wind_kph=float(wind) if wind is not None else None,
            source="open-meteo",
        )
