import { readFileSync } from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { cellRing, cellSizeMetres, lonStepMd, snap, wrapLon } from '@/lib/grid'

interface Vector {
  lat: number
  lon: number
  lat_md: number
  lon_md: number
  step_md: number
}

// The same file the Python tests read, so the two implementations cannot drift.
const vectors = JSON.parse(readFileSync(path.resolve(__dirname, '../../api/tests/fixtures/grid_vectors.json'), 'utf8')) as Vector[]

describe('privacy grid', () => {
  it('matches the Python implementation on every shared vector', () => {
    expect(vectors.length).toBeGreaterThanOrEqual(200)
    for (const vector of vectors) {
      const point = snap(vector.lat, vector.lon)
      expect([point.latMd, point.lonMd, point.stepMd], `${vector.lat},${vector.lon}`).toEqual([vector.lat_md, vector.lon_md, vector.step_md])
    }
  })

  it('is idempotent and never returns a negative zero', () => {
    for (const vector of vectors) {
      const once = snap(vector.lat, vector.lon)
      expect(snap(once.lat, once.lon)).toEqual(once)
      expect(Object.is(once.latMd, -0) || Object.is(once.lonMd, -0)).toBe(false)
    }
  })

  it('keeps every cell roughly 500 m wide', () => {
    for (let latMd = 0; latMd < 89_300; latMd += 5) {
      const { width, height } = cellSizeMetres({ latMd, lonMd: 0, lat: latMd / 1000, lon: 0, stepMd: lonStepMd(latMd) })
      expect(height).toBeCloseTo(556.6, 1)
      expect(width).toBeGreaterThanOrEqual(393)
      expect(width).toBeLessThanOrEqual(788)
    }
  })

  it('draws the cell as a closed square around the point', () => {
    const ring = cellRing(snap(59.9139, 10.7522))
    expect(ring).toHaveLength(5)
    expect(ring[0]).toEqual(ring[4])
    expect(ring[1]![0]! - ring[0]![0]!).toBeCloseTo(0.01, 6) // Oslo uses the 10 millidegree step
    expect(ring[2]![1]! - ring[1]![1]!).toBeCloseTo(0.005, 6)
  })

  it('refuses coordinates off the globe and wraps map longitudes', () => {
    expect(() => snap(91, 0)).toThrow(RangeError)
    expect(() => snap(0, 200)).toThrow(RangeError)
    expect(() => snap(Number.NaN, 0)).toThrow(RangeError)
    expect(wrapLon(190)).toBeCloseTo(-170)
    expect(wrapLon(-540)).toBeCloseTo(-180)
    expect(wrapLon(45)).toBeCloseTo(45)
  })
})
