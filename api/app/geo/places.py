"""Place names for a grid point, behind one interface.

The default never touches the network: it finds the nearest sizeable city in
a bundled GeoNames extract (34,160 places of 15,000 people or more, CC BY
4.0). The online provider asks OpenStreetMap's Nominatim and falls back to
the offline one on any error. Both are only ever given the snapped grid
point, so no service sees where a recording was really made.
"""

from __future__ import annotations

import gzip
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx
import numpy as np

from app.geo.grid import GridPoint

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
EARTH_RADIUS_KM = 6371.0088


@dataclass(frozen=True)
class Place:
    name: str
    country_code: str | None
    country_name: str | None
    source: str  # "geonames", "nominatim" or "coordinates"


class PlaceNamer(Protocol):
    def name(self, point: GridPoint) -> Place: ...


def coordinate_label(point: GridPoint) -> str:
    """What a postcard says when there is no town to name: open sea, ice, desert."""
    ns = "N" if point.lat >= 0 else "S"
    ew = "E" if point.lon >= 0 else "W"
    return f"{abs(point.lat):.2f}°{ns} {abs(point.lon):.2f}°{ew}"


class OfflinePlaceNamer:
    """Nearest city from the bundled table, leaning towards the bigger one.

    Plain nearest-neighbour names a postcard from central Tokyo after one of
    its wards. Each candidate within `near_km` is scored as distance minus a
    bonus for size, so a metropolis 12 km away beats a suburb 3 km away, and
    a real town 2 km away still beats a metropolis 24 km away.
    """

    def __init__(self, path: Path | None = None, *, near_km: float = 25.0, far_km: float = 120.0) -> None:
        table = path or DATA_DIR / "places.tsv.gz"
        names: list[str] = []
        countries: list[str] = []
        coords: list[tuple[float, float]] = []
        populations: list[int] = []
        with gzip.open(table, "rt", encoding="utf-8") as handle:
            for line in handle:
                name, country, lat, lon, population = line.rstrip("\n").split("\t")
                names.append(name)
                countries.append(country)
                coords.append((float(lat), float(lon)))
                populations.append(int(population))
        self._names = names
        self._countries = countries
        self._lat = np.radians(np.array([c[0] for c in coords]))
        self._lon = np.radians(np.array([c[1] for c in coords]))
        self._cos_lat = np.cos(self._lat)
        self._population = np.array(populations, dtype=np.float64)
        self._bonus = 6.0 * np.log10(np.maximum(np.array(populations, dtype=np.float64), 15_000.0) / 15_000.0)
        self._country_names: dict[str, str] = json.loads((DATA_DIR / "countries.json").read_text(encoding="utf-8"))
        self._near_km = near_km
        self._far_km = far_km

    def __len__(self) -> int:
        return len(self._names)

    def sample_cities(self, rng: np.random.Generator, count: int) -> list[tuple[float, float]]:
        """Random city centres as (lat, lon), bigger cities more often. Used to seed pins."""
        weights = np.sqrt(self._population)
        picks = rng.choice(len(self._names), size=count, p=weights / weights.sum())
        return [(float(np.degrees(self._lat[i])), float(np.degrees(self._lon[i]))) for i in picks]

    def _distances_km(self, point: GridPoint) -> np.ndarray:
        lat = math.radians(point.lat)
        lon = math.radians(point.lon)
        a = np.sin((self._lat - lat) / 2) ** 2 + math.cos(lat) * self._cos_lat * np.sin((self._lon - lon) / 2) ** 2
        distance: np.ndarray = 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))
        return distance

    def name(self, point: GridPoint) -> Place:
        distance = self._distances_km(point)
        near = np.flatnonzero(distance <= self._near_km)
        if near.size:
            best = int(near[np.argmin(distance[near] - self._bonus[near])])
            return self._place(best, prefix="")
        nearest = int(np.argmin(distance))
        if distance[nearest] <= self._far_km:
            return self._place(nearest, prefix="Near ")
        return Place(name=coordinate_label(point), country_code=None, country_name=None, source="coordinates")

    def _place(self, index: int, *, prefix: str) -> Place:
        code = self._countries[index]
        return Place(
            name=prefix + self._names[index],
            country_code=code,
            country_name=self._country_names.get(code),
            source="geonames",
        )


class NominatimPlaceNamer:
    """OpenStreetMap Nominatim. Opt in with GEOCODER=nominatim; mind their usage policy."""

    _KEYS = ("city", "town", "village", "municipality", "suburb", "county", "state_district", "state")

    def __init__(
        self,
        fallback: PlaceNamer,
        *,
        url: str,
        user_agent: str,
        timeout: float = 4.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._fallback = fallback
        self._url = url
        self._client = client or httpx.Client(timeout=timeout, headers={"User-Agent": user_agent})

    def name(self, point: GridPoint) -> Place:
        try:
            response = self._client.get(
                self._url,
                params={
                    "format": "jsonv2",
                    "lat": f"{point.lat:.3f}",
                    "lon": f"{point.lon:.3f}",
                    "zoom": 10,
                    "addressdetails": 1,
                    "accept-language": "en",
                },
            )
            response.raise_for_status()
            place = self.parse(response.json())
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            place = None
        return place or self._fallback.name(point)

    @classmethod
    def parse(cls, payload: dict[str, object]) -> Place | None:
        address = payload.get("address")
        if not isinstance(address, dict):
            return None
        name = next((str(address[key]) for key in cls._KEYS if address.get(key)), None)
        if not name:
            return None
        code = address.get("country_code")
        country = address.get("country")
        return Place(
            name=name,
            country_code=str(code).upper() if code else None,
            country_name=str(country) if country else None,
            source="nominatim",
        )
