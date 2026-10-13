'use client'

import 'maplibre-gl/dist/maplibre-gl.css'
import type { GeoJSONSource, Map as MapLibreMap, MapGeoJSONFeature } from 'maplibre-gl'
import { useEffect, useRef, useState } from 'react'
import { api } from '@/lib/api'
import { clusterImageId, imageFor } from '@/lib/mapImages'
import { MAP_COLOURS, resolveStyle } from '@/lib/mapStyle'
import type { PinCollection } from '@/lib/types'

export interface MapStats {
  total: number
  mode: 'pins' | 'cells'
  basemap: 'offline' | 'online'
}

interface Props {
  selectedId: string | null
  focus: { lat: number; lon: number } | null
  refreshKey: number
  onSelect: (id: string | null) => void
  onStats: (stats: MapStats) => void
  onAttribution: (html: string) => void
}

const WORLD: [number, number, number, number] = [-180, -85, 180, 85]

/** Maps a count to the image id the cluster layer shows, as a style expression. */
const CLUSTER_IMAGE = [
  'case',
  ['>=', ['get', 'sum'], 1000],
  ['concat', 'cluster:', ['to-string', ['round', ['/', ['get', 'sum'], 100]]], 'h'],
  ['concat', 'cluster:', ['to-string', ['get', 'sum']]],
] as unknown as string

/**
 * The shared map. Postcards arrive as GeoJSON and MapLibre clusters them in
 * a worker, so five thousand pins cost a few dozen symbols on screen.
 */
export function MapView({ selectedId, focus, refreshKey, onSelect, onStats, onAttribution }: Props) {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const modeRef = useRef<'pins' | 'cells'>('pins')
  const callbacks = useRef({ onSelect, onStats, onAttribution })
  callbacks.current = { onSelect, onStats, onAttribution }
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let cancelled = false
    let map: MapLibreMap | null = null
    let basemapRef: 'offline' | 'online' = 'offline'

    async function load(viewport: boolean) {
      if (!map) return
      const bounds = map.getBounds()
      const box: [number, number, number, number] = viewport ? [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()] : WORLD
      performance.mark('sonic:pins-requested')
      let pins: PinCollection
      try {
        pins = await api.pins(box, map.getZoom())
      } catch {
        return
      }
      if (cancelled || !map) return
      performance.mark('sonic:pins-received')
      modeRef.current = pins.mode
      const source = map.getSource('pins') as GeoJSONSource | undefined
      source?.setData(pins as unknown as GeoJSON.FeatureCollection)
      callbacks.current.onStats({ total: pins.total, mode: pins.mode, basemap: basemapRef })
      map.once('idle', () => {
        if (!map) return
        performance.mark('sonic:pins-rendered')
        const drawn = map.queryRenderedFeatures({ layers: ['clusters', 'pins'] })
        const seen = new Set<string>()
        let represented = 0
        for (const feature of drawn) {
          const key = String(feature.properties.cluster_id ?? feature.properties.id ?? feature.id)
          if (seen.has(key)) continue
          seen.add(key)
          represented += Number(feature.properties.sum ?? feature.properties.count ?? 1)
        }
        ;(window as unknown as { __sonic?: object }).__sonic = { total: pins.total, symbols: seen.size, represented, mode: pins.mode }
      })
    }

    async function start() {
      performance.mark('sonic:map-start')
      const [{ default: maplibregl }, resolved] = await Promise.all([import('maplibre-gl'), resolveStyle()])
      if (cancelled || !container.current) return
      basemapRef = resolved.source
      callbacks.current.onAttribution(resolved.attribution)
      map = new maplibregl.Map({
        container: container.current,
        style: resolved.style,
        center: [12, 28],
        zoom: 1.35,
        minZoom: 1,
        maxZoom: resolved.maxZoom,
        attributionControl: false,
        dragRotate: false,
        pitchWithRotate: false,
        renderWorldCopies: true,
        fadeDuration: 0,
      })
      mapRef.current = map
      map.touchZoomRotate.disableRotation()
      map.keyboard.disableRotation()
      const ratio = Math.min(2, window.devicePixelRatio || 1)
      map.on('styleimagemissing', (event) => {
        const image = imageFor(event.id, ratio)
        if (image && map && !map.hasImage(event.id)) map.addImage(event.id, image, { pixelRatio: image.pixelRatio })
      })

      map.on('load', () => {
        if (!map) return
        // Small counts are on nearly every screen, so have their bubbles ready before any tile asks.
        for (let count = 2; count <= 120; count++) {
          const id = clusterImageId(count)
          const image = imageFor(id, ratio)
          if (image && !map.hasImage(id)) map.addImage(id, image, { pixelRatio: image.pixelRatio })
        }
        map.addSource('pins', {
          type: 'geojson',
          data: { type: 'FeatureCollection', features: [] },
          cluster: true,
          clusterRadius: 46,
          clusterMaxZoom: 13,
          // Server-side cells carry a count, so sum counts instead of counting points.
          clusterProperties: { sum: ['+', ['get', 'count']] },
        })
        map.addSource('selected', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
        map.addLayer({
          id: 'clusters',
          type: 'symbol',
          source: 'pins',
          filter: ['any', ['has', 'point_count'], ['>', ['get', 'count'], 1]],
          layout: {
            'icon-image': ['case', ['has', 'point_count'], CLUSTER_IMAGE, ['concat', 'cluster:', ['to-string', ['get', 'count']]]],
            // Cluster centres drift as points merge, so two can land almost on top of each other.
            // Let the larger one win the spot; the smaller reappears one zoom step in.
            'icon-allow-overlap': false,
            'icon-padding': 0,
            'symbol-sort-key': ['-', ['coalesce', ['get', 'sum'], ['get', 'count']]],
          },
        })
        map.addLayer({
          id: 'pins',
          type: 'circle',
          source: 'pins',
          filter: ['all', ['!', ['has', 'point_count']], ['==', ['get', 'count'], 1]],
          paint: {
            'circle-radius': ['interpolate', ['linear'], ['zoom'], 1, 6, 8, 8.5],
            'circle-color': '#e2583a',
            'circle-stroke-width': 2.5,
            'circle-stroke-color': MAP_COLOURS.paper,
          },
        })
        map.addLayer({
          id: 'selected-halo',
          type: 'circle',
          source: 'selected',
          paint: { 'circle-radius': 19, 'circle-color': 'rgba(226,88,58,0.2)', 'circle-stroke-width': 2, 'circle-stroke-color': '#e2583a' },
        })
        map.addLayer({
          id: 'selected-dot',
          type: 'circle',
          source: 'selected',
          paint: { 'circle-radius': 9.5, 'circle-color': '#e2583a', 'circle-stroke-width': 3, 'circle-stroke-color': MAP_COLOURS.paper },
        })

        map.on('click', 'pins', (event) => {
          const feature = event.features?.[0] as MapGeoJSONFeature | undefined
          const id = feature?.properties.id as string | undefined
          if (id) callbacks.current.onSelect(id)
        })
        map.on('click', 'clusters', (event) => {
          const feature = event.features?.[0]
          if (!feature || !map) return
          const centre = (feature.geometry as GeoJSON.Point).coordinates as [number, number]
          const clusterId = feature.properties.cluster_id as number | undefined
          if (clusterId === undefined) {
            map.easeTo({ center: centre, zoom: Math.min(map.getZoom() + 2, map.getMaxZoom()) })
            return
          }
          const source = map.getSource('pins') as GeoJSONSource
          void source.getClusterExpansionZoom(clusterId).then((zoom) => map?.easeTo({ center: centre, zoom: Math.min(zoom + 0.4, map.getMaxZoom()) }))
        })
        map.on('click', (event) => {
          if (!map) return
          if (map.queryRenderedFeatures(event.point, { layers: ['pins', 'clusters'] }).length === 0) callbacks.current.onSelect(null)
        })
        for (const layer of ['pins', 'clusters']) {
          map.on('mouseenter', layer, () => map && (map.getCanvas().style.cursor = 'pointer'))
          map.on('mouseleave', layer, () => map && (map.getCanvas().style.cursor = ''))
        }
        // When the server is grouping for us, each view needs its own answer.
        map.on('moveend', () => {
          if (modeRef.current === 'cells') void load(true)
        })
        setReady(true)
        void load(false)
      })
    }

    void start()
    return () => {
      cancelled = true
      mapRef.current = null
      map?.remove()
    }
  }, [])

  // New postcards (or a moderation change) ask for a fresh set of pins.
  useEffect(() => {
    const map = mapRef.current
    if (!ready || !map || refreshKey === 0) return
    void api
      .pins(WORLD, map.getZoom())
      .then((pins) => (map.getSource('pins') as GeoJSONSource | undefined)?.setData(pins as unknown as GeoJSON.FeatureCollection))
      .catch(() => undefined)
  }, [refreshKey, ready])

  useEffect(() => {
    const map = mapRef.current
    if (!ready || !map) return
    const source = map.getSource('selected') as GeoJSONSource | undefined
    const features: GeoJSON.Feature[] = selectedId && focus ? [{ type: 'Feature', geometry: { type: 'Point', coordinates: [focus.lon, focus.lat] }, properties: {} }] : []
    source?.setData({ type: 'FeatureCollection', features })
    if (selectedId && focus) {
      const zoom = Math.max(map.getZoom(), Math.min(5, map.getMaxZoom()))
      // Keep the pin clear of the sheet: above it on phones, left of it on wide screens.
      const wide = window.innerWidth >= 900
      map.easeTo({ center: [focus.lon, focus.lat], zoom, offset: wide ? [-200, 0] : [0, -170], duration: 700 })
    }
  }, [selectedId, focus, ready])

  return <div ref={container} className="map-canvas" data-ready={ready} aria-label="World map of sound postcards" role="application" />
}
