/**
 * Natural Earth outlines from world-atlas are meant for a globe: a ring may
 * step from longitude 179.9 to -179.9, and the ring around Antarctica never
 * returns to where it started. A flat map draws both as a streak across the
 * whole world. These helpers rewrite such rings for a plane.
 */
type Position = number[]

/** Remove the 360 degree jumps from a line so it is continuous, letting it run past 180. */
export function unwrapLine(line: Position[]): { line: Position[]; turns: number } {
  const out: Position[] = []
  let offset = 0
  for (let i = 0; i < line.length; i++) {
    const point = line[i]!
    const previous = line[i - 1]
    if (previous) {
      const step = point[0]! - previous[0]!
      if (step > 180) offset -= 360
      else if (step < -180) offset += 360
    }
    out.push([point[0]! + offset, point[1]!])
  }
  return { line: out, turns: Math.round(offset / 360) }
}

/** A ring that circles a pole is closed by walking to the pole and back along it. */
export function planarRing(ring: Position[]): Position[] {
  const { line, turns } = unwrapLine(ring)
  if (turns === 0 || line.length < 2) return line
  const first = line[0]!
  const last = line[line.length - 1]!
  const meanLat = line.reduce((sum, point) => sum + point[1]!, 0) / line.length
  const pole = meanLat < 0 ? -90 : 90
  return [...line, [last[0]!, pole], [first[0]!, pole], [first[0]!, first[1]!]]
}

export function planarGeometry<T extends GeoJSON.Geometry>(geometry: T): T {
  switch (geometry.type) {
    case 'Polygon':
      return { ...geometry, coordinates: geometry.coordinates.map(planarRing) }
    case 'MultiPolygon':
      return { ...geometry, coordinates: geometry.coordinates.map((polygon) => polygon.map(planarRing)) }
    case 'LineString':
      return { ...geometry, coordinates: unwrapLine(geometry.coordinates).line }
    case 'MultiLineString':
      return { ...geometry, coordinates: geometry.coordinates.map((line) => unwrapLine(line).line) }
    default:
      return geometry
  }
}

export function planarFeatures(data: GeoJSON.GeoJSON): GeoJSON.GeoJSON {
  if (data.type === 'FeatureCollection') {
    return { ...data, features: data.features.map((feature) => ({ ...feature, geometry: planarGeometry(feature.geometry) })) }
  }
  if (data.type === 'Feature') return { ...data, geometry: planarGeometry(data.geometry) }
  return planarGeometry(data)
}
