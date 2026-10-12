"""The privacy grid.

A location is snapped to a grid before anything else sees it, and only the
snapped value is ever stored. Coordinates are integers in millidegrees so the
rule can be checked exactly, in Python, in TypeScript and in a Postgres CHECK
constraint, with no floating point involved.

Latitude snaps to 5 millidegrees, which is 556 m everywhere. A fixed
longitude step would shrink with cos(latitude): 0.005 degrees is 556 m wide on
the equator and 278 m in Oslo. So the longitude step doubles each time the
cell would otherwise get narrower than 556 / sqrt(2) m, which keeps every
cell between 393 m and 786 m wide up to 89.3 degrees.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

LAT_STEP_MD = 5
MAX_LAT_MD = 90_000
HALF_TURN_MD = 180_000

# (latitude in millidegrees where the band starts, longitude step in millidegrees).
# Band k starts where 1 / cos(lat) reaches 2 ** (k - 0.5). The last step is 320
# because 640 does not divide 360,000 and the grid has to close at the antimeridian.
LON_BANDS: tuple[tuple[int, int], ...] = (
    (0, 5),
    (45_000, 10),
    (69_295, 20),
    (79_818, 40),
    (84_929, 80),
    (87_467, 160),
    (88_734, 320),
)

METRES_PER_DEGREE = 111_320.0


@dataclass(frozen=True)
class GridPoint:
    """A location on the privacy grid, in integer millidegrees."""

    lat_md: int
    lon_md: int

    @property
    def lat(self) -> float:
        return self.lat_md / 1000.0

    @property
    def lon(self) -> float:
        return self.lon_md / 1000.0

    @property
    def lon_step_md(self) -> int:
        return lon_step_md(self.lat_md)

    def cell_size_m(self) -> tuple[float, float]:
        """Width and height of the cell this point stands for, in metres."""
        width = self.lon_step_md / 1000.0 * METRES_PER_DEGREE * math.cos(math.radians(self.lat))
        height = LAT_STEP_MD / 1000.0 * METRES_PER_DEGREE
        return width, height


def lon_step_md(lat_md: int) -> int:
    """Longitude step, in millidegrees, for a latitude that is already on the grid."""
    step = LON_BANDS[0][1]
    for start, band_step in LON_BANDS:
        if abs(lat_md) >= start:
            step = band_step
    return step


def _round_half_away(value: float) -> int:
    return int(math.floor(abs(value) + 0.5)) * (1 if value >= 0 else -1)


def snap(lat: float, lon: float) -> GridPoint:
    """Snap a raw coordinate to the privacy grid. Raises ValueError outside the globe."""
    if not (math.isfinite(lat) and math.isfinite(lon)):
        raise ValueError("coordinates must be finite numbers")
    if not -90.0 <= lat <= 90.0:
        raise ValueError("latitude must be between -90 and 90")
    if not -180.0 <= lon <= 180.0:
        raise ValueError("longitude must be between -180 and 180")

    lat_md = _round_half_away(lat * 1000.0 / LAT_STEP_MD) * LAT_STEP_MD
    lat_md = max(-MAX_LAT_MD, min(MAX_LAT_MD, lat_md))

    step = lon_step_md(lat_md)
    lon_md = _round_half_away(lon * 1000.0 / step) * step
    if lon_md >= HALF_TURN_MD:
        lon_md -= 2 * HALF_TURN_MD
    elif lon_md < -HALF_TURN_MD:
        lon_md += 2 * HALF_TURN_MD
    return GridPoint(lat_md=lat_md, lon_md=lon_md)


def is_on_grid(lat_md: int, lon_md: int) -> bool:
    """The same rule the database CHECK constraints enforce."""
    return (
        -MAX_LAT_MD <= lat_md <= MAX_LAT_MD
        and lat_md % LAT_STEP_MD == 0
        and -HALF_TURN_MD <= lon_md < HALF_TURN_MD
        and lon_md % lon_step_md(lat_md) == 0
    )
