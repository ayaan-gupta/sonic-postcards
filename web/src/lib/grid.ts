/**
 * The privacy grid, mirrored from api/app/geo/grid.py.
 *
 * The browser snaps a location before it sends it anywhere, so an exact
 * position never leaves the device. The server snaps again (it trusts
 * nothing) and Postgres refuses anything off the grid. Both sides are tested
 * against the same vector file.
 */

export const LAT_STEP_MD = 5
const MAX_LAT_MD = 90_000
const HALF_TURN_MD = 180_000
const METRES_PER_DEGREE = 111_320

/** [latitude in millidegrees where the band starts, longitude step in millidegrees] */
export const LON_BANDS: ReadonlyArray<readonly [number, number]> = [
  [0, 5],
  [45_000, 10],
  [69_295, 20],
  [79_818, 40],
  [84_929, 80],
  [87_467, 160],
  [88_734, 320],
]

export interface GridPoint {
  latMd: number
  lonMd: number
  lat: number
  lon: number
  stepMd: number
}

export function lonStepMd(latMd: number): number {
  let step = 5
  for (const [start, bandStep] of LON_BANDS) if (Math.abs(latMd) >= start) step = bandStep
  return step
}

function roundHalfAway(value: number): number {
  return Math.sign(value) * Math.floor(Math.abs(value) + 0.5)
}

export function snap(lat: number, lon: number): GridPoint {
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) throw new RangeError('coordinates must be finite numbers')
  if (lat < -90 || lat > 90) throw new RangeError('latitude must be between -90 and 90')
  if (lon < -180 || lon > 180) throw new RangeError('longitude must be between -180 and 180')

  let latMd = roundHalfAway((lat * 1000) / LAT_STEP_MD) * LAT_STEP_MD
  latMd = Math.max(-MAX_LAT_MD, Math.min(MAX_LAT_MD, latMd))
  const stepMd = lonStepMd(latMd)
  let lonMd = roundHalfAway((lon * 1000) / stepMd) * stepMd
  if (lonMd >= HALF_TURN_MD) lonMd -= 2 * HALF_TURN_MD
  else if (lonMd < -HALF_TURN_MD) lonMd += 2 * HALF_TURN_MD
  // "+ 0" turns a negative zero into a plain zero.
  return { latMd: latMd + 0, lonMd: lonMd + 0, lat: latMd / 1000, lon: lonMd / 1000, stepMd }
}

/** Longitudes outside [-180, 180] happen when a map is panned around the world. */
export function wrapLon(lon: number): number {
  return ((((lon + 180) % 360) + 360) % 360) - 180
}

export function cellSizeMetres(point: GridPoint): { width: number; height: number } {
  return {
    width: (point.stepMd / 1000) * METRES_PER_DEGREE * Math.cos((point.lat * Math.PI) / 180),
    height: (LAT_STEP_MD / 1000) * METRES_PER_DEGREE,
  }
}

/** The square a grid point stands for, as a closed ring of [lon, lat] corners. */
export function cellRing(point: GridPoint): [number, number][] {
  const halfLat = LAT_STEP_MD / 2000
  const halfLon = point.stepMd / 2000
  const west = point.lon - halfLon
  const east = point.lon + halfLon
  const south = Math.max(-90, point.lat - halfLat)
  const north = Math.min(90, point.lat + halfLat)
  return [
    [west, south],
    [east, south],
    [east, north],
    [west, north],
    [west, south],
  ]
}
