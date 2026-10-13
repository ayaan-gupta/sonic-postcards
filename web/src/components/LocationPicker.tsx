'use client'

import 'maplibre-gl/dist/maplibre-gl.css'
import type { GeoJSONSource, Map as MapLibreMap } from 'maplibre-gl'
import { useEffect, useRef, useState } from 'react'
import { cellRing, snap, wrapLon, type GridPoint } from '@/lib/grid'
import { imageFor } from '@/lib/mapImages'
import { resolveStyle } from '@/lib/mapStyle'
import { LocateIcon, PinGlyph } from './icons'

const START_KEY = 'sonic-postcards.last-centre'

interface Props {
  onChange: (point: GridPoint, source: 'gps' | 'manual') => void
}

function cellFeature(point: GridPoint): GeoJSON.Feature {
  return { type: 'Feature', geometry: { type: 'Polygon', coordinates: [cellRing(point)] }, properties: {} }
}

/**
 * Drag the map under a fixed pin, or jump to the device's position. Whatever
 * is chosen is snapped to the privacy grid here, in the browser, and the
 * shaded square shows the cell that will be stored.
 */
export function LocationPicker({ onChange }: Props) {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const sourceRef = useRef<'gps' | 'manual'>('manual')
  const pending = useRef<GridPoint | null>(null) // a GPS fix that arrived before the map did
  const loaded = useRef(false)
  const change = useRef(onChange)
  change.current = onChange
  const [locating, setLocating] = useState(false)
  const [problem, setProblem] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    let map: MapLibreMap | null = null
    async function start() {
      const [{ default: maplibregl }, resolved] = await Promise.all([import('maplibre-gl'), resolveStyle()])
      if (cancelled || !container.current) return
      let centre: [number, number] = [135.768, 35.0116]
      let zoom = Math.min(11, resolved.maxZoom - 1)
      try {
        const saved = JSON.parse(window.sessionStorage.getItem(START_KEY) ?? 'null') as [number, number, number] | null
        if (saved) [centre, zoom] = [[saved[0], saved[1]], Math.min(saved[2], resolved.maxZoom)]
      } catch {
        // Start in Kyoto.
      }
      map = new maplibregl.Map({
        container: container.current,
        style: resolved.style,
        center: centre,
        zoom,
        minZoom: 2,
        maxZoom: Math.min(resolved.maxZoom, 15),
        attributionControl: false,
        dragRotate: false,
        fadeDuration: 0,
      })
      mapRef.current = map
      map.touchZoomRotate.disableRotation()
      const ratio = Math.min(2, window.devicePixelRatio || 1)
      map.on('styleimagemissing', (event) => {
        const image = imageFor(event.id, ratio)
        if (image && map && !map.hasImage(event.id)) map.addImage(event.id, image, { pixelRatio: image.pixelRatio })
      })
      const report = () => {
        if (!map) return
        const { lng, lat } = map.getCenter()
        const point = snap(Math.max(-89.9, Math.min(89.9, lat)), wrapLon(lng))
        ;(map.getSource('cell') as GeoJSONSource | undefined)?.setData(cellFeature(point))
        try {
          window.sessionStorage.setItem(START_KEY, JSON.stringify([point.lon, point.lat, map.getZoom()]))
        } catch {
          // Ignore.
        }
        change.current(point, sourceRef.current)
      }
      map.on('load', () => {
        if (!map) return
        map.addSource('cell', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
        map.addLayer({ id: 'cell-fill', type: 'fill', source: 'cell', paint: { 'fill-color': '#e2583a', 'fill-opacity': 0.16 } })
        map.addLayer({ id: 'cell-line', type: 'line', source: 'cell', paint: { 'line-color': '#e2583a', 'line-width': 2 } })
        if (pending.current) map.jumpTo({ center: [pending.current.lon, pending.current.lat], zoom: Math.min(13, map.getMaxZoom()) })
        pending.current = null
        loaded.current = true
        report()
      })
      // A drag by hand means the location is no longer the GPS fix.
      map.on('dragstart', () => (sourceRef.current = 'manual'))
      map.on('moveend', report)
    }
    void start()
    return () => {
      cancelled = true
      loaded.current = false
      mapRef.current = null
      map?.remove()
    }
  }, [])

  const locate = () => {
    if (!navigator.geolocation) return setProblem('This browser cannot share a location. Drag the map instead.')
    setLocating(true)
    setProblem(null)
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocating(false)
        // Snap before anything else sees the fix; the exact coordinates are dropped here.
        const point = snap(position.coords.latitude, position.coords.longitude)
        sourceRef.current = 'gps'
        change.current(point, 'gps')
        const map = mapRef.current
        if (map && loaded.current) map.jumpTo({ center: [point.lon, point.lat], zoom: Math.min(13, map.getMaxZoom()) })
        else pending.current = point
      },
      () => {
        setLocating(false)
        setProblem('Location is switched off for this site. Drag the map to where you are.')
      },
      { enableHighAccuracy: false, timeout: 10_000, maximumAge: 60_000 },
    )
  }

  return (
    <div>
      <div className="picker">
        <div ref={container} className="picker__map" aria-label="Map for choosing where the postcard is pinned" role="application" />
        <PinGlyph className="picker__pin" />
        <button type="button" className="picker__locate glass" onClick={locate} disabled={locating}>
          <LocateIcon />
          {locating ? 'Finding you' : 'Use my location'}
        </button>
      </div>
      {problem && (
        <p className="note" role="status" style={{ marginTop: 10 }}>
          {problem}
        </p>
      )}
    </div>
  )
}
