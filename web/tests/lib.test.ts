import { mkdtempSync, mkdirSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { resolveAsset } from '@/lib/assets'
import { deviceId, newDeviceId } from '@/lib/device'
import { formatCount, formatDate, formatDistance, formatHour, untilText } from '@/lib/format'
import { clusterDiameter, clusterImageId, countFromImageId } from '@/lib/mapImages'
import { brandStyle, styleChoice } from '@/lib/mapStyle'
import { planarRing, unwrapLine } from '@/lib/planar'
import { AUDIO_CONSTRAINTS, extensionFor, pickMimeType } from '@/lib/recorder'

describe('formatting', () => {
  it('formats distances, counts, dates and waits', () => {
    expect(formatDistance(40)).toBe('100 m')
    expect(formatDistance(640)).toBe('600 m')
    expect(formatDistance(4321)).toBe('4.3 km')
    expect(formatDistance(43_200)).toBe('43 km')
    expect([formatCount(7), formatCount(999), formatCount(1000), formatCount(1250), formatCount(5000), formatCount(12_400)]).toEqual(['7', '999', '1k', '1.2k', '5k', '12k'])
    expect(formatDate('2026-10-12')).toBe('12 Oct 2026')
    expect([formatHour(0), formatHour(9), formatHour(12), formatHour(19)]).toEqual(['12 am', '9 am', '12 pm', '7 pm'])
    const now = new Date('2026-05-01T09:00:00Z')
    expect(untilText('2026-05-01T09:20:00Z', now)).toBe('in 20 min')
    expect(untilText('2026-05-01T12:20:00Z', now)).toBe('in 3 h 20 min')
  })
})

describe('recorder', () => {
  it('turns off phone-call processing, which would erase ambient sound', () => {
    expect(AUDIO_CONSTRAINTS).toMatchObject({ echoCancellation: false, noiseSuppression: false, autoGainControl: false })
  })

  it('prefers Opus in WebM, falls back to MP4 on Safari', () => {
    expect(pickMimeType(() => true)).toBe('audio/webm;codecs=opus')
    expect(pickMimeType((type) => type === 'audio/mp4')).toBe('audio/mp4')
    expect(pickMimeType(() => false)).toBeUndefined()
    expect([extensionFor('audio/webm;codecs=opus'), extensionFor('audio/mp4'), extensionFor('audio/ogg')]).toEqual(['webm', 'm4a', 'ogg'])
  })
})

describe('device id', () => {
  it('is created once and reused', () => {
    const store = new Map<string, string>()
    const storage = { getItem: (key: string) => store.get(key) ?? null, setItem: (key: string, value: string) => void store.set(key, value) }
    const first = deviceId(storage)
    expect(first).toMatch(/^d-[0-9a-f]{36}$/)
    expect(deviceId(storage)).toBe(first)
    expect(newDeviceId()).not.toBe(newDeviceId())
  })
})

describe('map', () => {
  it('names cluster images so that large counts share one per hundred', () => {
    expect(clusterImageId(42)).toBe('cluster:42')
    expect(clusterImageId(1249)).toBe('cluster:12h')
    expect(countFromImageId('cluster:42')).toBe(42)
    expect(countFromImageId('cluster:12h')).toBe(1200)
    expect(countFromImageId('label:Kyoto')).toBeNull()
    expect([clusterDiameter(3), clusterDiameter(30), clusterDiameter(300), clusterDiameter(3000)]).toEqual([32, 38, 46, 54])
  })

  it('rewrites globe outlines for a flat map', () => {
    // Chukotka: the coast steps from 179.9 to -179.9. Unwrapped it runs on past 180.
    const { line, turns } = unwrapLine([[179.5, 66], [179.9, 67], [-179.9, 68], [-179.5, 67], [179.5, 66]])
    expect(line.map((point) => point[0])).toEqual([179.5, 179.9, 180.1, 180.5, 179.5])
    expect(turns).toBe(0)
    // Antarctica: the ring circles the pole and never comes back, so it is closed along the pole.
    const ring = planarRing([[-180, -78], [-90, -75], [0, -70], [90, -72], [179, -78], [-180, -78]])
    expect(ring.slice(-3)).toEqual([[180, -90], [-180, -90], [-180, -78]])
    expect(ring.every((point, index) => index === 0 || Math.abs(point[0]! - ring[index - 1]![0]!) <= 360)).toBe(true)
  })

  it('recolours an OpenMapTiles style and drops the relief raster', () => {
    const style = brandStyle({
      version: 8,
      sources: { openmaptiles: { type: 'vector', url: 'x' }, relief: { type: 'raster', tiles: ['y'] } },
      layers: [
        { id: 'background', type: 'background', paint: { 'background-color': '#fff' } },
        { id: 'relief', type: 'raster', source: 'relief' },
        { id: 'water', type: 'fill', source: 'openmaptiles', 'source-layer': 'water', paint: { 'fill-color': '#00f' } },
        { id: 'label_city', type: 'symbol', source: 'openmaptiles', 'source-layer': 'place', layout: { 'text-field': '{name}' } },
      ],
    })
    expect(style.layers.map((layer) => layer.id)).toEqual(['background', 'water', 'label_city'])
    expect(Object.keys(style.sources)).toEqual(['openmaptiles'])
    expect((style.layers[1]!.paint as Record<string, string>)['fill-color']).toBe('#cfe1de')
    expect((style.layers[2]!.paint as Record<string, string>)['text-color']).toBe('#4a5068')
    expect([styleChoice(undefined), styleChoice(''), styleChoice('offline'), styleChoice('https://x/style.json')]).toEqual(['auto', 'auto', 'offline', 'https://x/style.json'])
  })
})

describe('design-time art', () => {
  it('serves a delivered file over the interim one, one file at a time', async () => {
    const root = mkdtempSync(path.join(tmpdir(), 'sonic-art-'))
    for (const folder of ['interim/stamps', 'generated/stamps']) mkdirSync(path.join(root, folder), { recursive: true })
    writeFileSync(path.join(root, 'interim/stamps/rain.png'), 'interim-rain')
    writeFileSync(path.join(root, 'interim/stamps/birds.png'), 'interim-birds')
    writeFileSync(path.join(root, 'generated/stamps/rain.png'), 'generated-rain')
    expect(await resolveAsset('stamps/rain.png', root)).toMatchObject({ source: 'generated', contentType: 'image/png' })
    expect((await resolveAsset('stamps/birds.png', root))?.bytes.toString()).toBe('interim-birds')
    expect(await resolveAsset('stamps/missing.png', root)).toBeNull()
    expect(await resolveAsset('../secrets.png', root)).toBeNull()
    expect(await resolveAsset('stamps/rain.txt', root)).toBeNull()
  })
})
