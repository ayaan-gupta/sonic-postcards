/**
 * Where the basemap comes from. One function, two sources.
 *
 * - "offline": a world drawn from Natural Earth outlines that ship with the
 *   app (the world-atlas package). No network, no key. Good down to about
 *   zoom 6; it has coasts, borders and big-city labels but no streets.
 * - a style URL: any MapLibre style. The default is OpenFreeMap's keyless
 *   Positron style, recoloured here to match the postcards.
 *
 * NEXT_PUBLIC_MAP_STYLE picks one. "auto" (the default) tries the online
 * style and falls back to the offline one if it cannot be fetched.
 */
import type { LayerSpecification, StyleSpecification } from 'maplibre-gl'
import type { Topology } from 'topojson-specification'
import cities from '@/data/cities.json'
import { planarFeatures } from './planar'

export const MAP_COLOURS = {
  sea: '#cfe1de',
  land: '#f4ecd9',
  coast: '#b9c9bf',
  border: '#c9bda3',
  park: '#dbe3c2',
  wood: '#d3dfc0',
  building: '#e9dfc9',
  road: '#fffaf0',
  roadCasing: '#e2d6bd',
  rail: '#cbbfa8',
  ink: '#1d2440',
  label: '#4a5068',
  paper: '#f7f3ea',
} as const

export const DEFAULT_ONLINE_STYLE = 'https://tiles.openfreemap.org/styles/positron'
export const OFFLINE_MAX_ZOOM = 9

export type StyleChoice = 'auto' | 'offline' | (string & {})

export function styleChoice(env: string | undefined = process.env.NEXT_PUBLIC_MAP_STYLE): StyleChoice {
  const value = (env ?? '').trim()
  return value === '' ? 'auto' : value
}

export interface ResolvedStyle {
  style: StyleSpecification
  source: 'offline' | 'online'
  maxZoom: number
  attribution: string
}

/** Recolour an OpenMapTiles-schema style in the postcard palette. Unknown layers are left alone. */
export function brandStyle(style: StyleSpecification): StyleSpecification {
  const c = MAP_COLOURS
  const layers = style.layers.map((layer): LayerSpecification => {
    const sourceLayer = 'source-layer' in layer ? layer['source-layer'] : undefined
    const paint: Record<string, unknown> = { ...(layer.paint as Record<string, unknown> | undefined) }
    if (layer.type === 'background') paint['background-color'] = c.land
    else if (layer.type === 'fill') {
      if (sourceLayer === 'water') paint['fill-color'] = c.sea
      else if (sourceLayer === 'park') paint['fill-color'] = c.park
      else if (sourceLayer === 'landcover') paint['fill-color'] = layer.id.includes('wood') ? c.wood : '#f8f4ea'
      else if (sourceLayer === 'landuse') paint['fill-color'] = '#efe6d2'
      else if (sourceLayer === 'building') {
        paint['fill-color'] = c.building
        delete paint['fill-outline-color']
      }
    } else if (layer.type === 'line') {
      if (sourceLayer === 'waterway') paint['line-color'] = c.sea
      else if (sourceLayer === 'boundary') paint['line-color'] = c.border
      else if (sourceLayer === 'transportation') {
        if (layer.id.includes('rail')) paint['line-color'] = c.rail
        else paint['line-color'] = layer.id.includes('casing') ? c.roadCasing : c.road
      }
    } else if (layer.type === 'symbol') {
      paint['text-color'] = sourceLayer === 'water_name' || sourceLayer === 'waterway' ? '#6f8f94' : c.label
      paint['text-halo-color'] = 'rgba(247,243,234,0.85)'
      paint['text-halo-width'] = 1.2
    }
    return { ...layer, paint } as LayerSpecification
  })
  // The shaded relief raster fights with flat colour, so it goes.
  const kept = layers.filter((layer) => layer.type !== 'raster')
  const sources = Object.fromEntries(Object.entries(style.sources).filter(([, source]) => source.type !== 'raster'))
  return { ...style, sources, layers: kept }
}

export async function offlineStyle(): Promise<StyleSpecification> {
  const [{ feature, mesh }, atlas] = await Promise.all([import('topojson-client'), import('world-atlas/countries-50m.json')])
  const topology = (atlas.default ?? atlas) as unknown as Topology
  const countries = topology.objects.countries
  const land = topology.objects.land
  if (!countries || !land) throw new Error('basemap data is missing its layers')
  const c = MAP_COLOURS
  return {
    version: 8,
    name: 'Sonic Postcards offline',
    sources: {
      land: { type: 'geojson', data: planarFeatures(feature(topology, land) as GeoJSON.GeoJSON) },
      borders: {
        type: 'geojson',
        data: planarFeatures(mesh(topology, countries as Parameters<typeof mesh>[1], (a, b) => a !== b) as GeoJSON.GeoJSON),
      },
      cities: {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: (cities as [string, number, number, number][]).map(([name, lat, lon, rank]) => ({
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [lon, lat] },
            properties: { name, rank },
          })),
        },
      },
    },
    layers: [
      { id: 'sea', type: 'background', paint: { 'background-color': c.sea } },
      { id: 'land', type: 'fill', source: 'land', paint: { 'fill-color': c.land } },
      { id: 'coast', type: 'line', source: 'land', paint: { 'line-color': c.coast, 'line-width': 1.2 } },
      { id: 'borders', type: 'line', source: 'borders', paint: { 'line-color': c.border, 'line-width': 0.8, 'line-dasharray': [3, 2] } },
      {
        id: 'city-dots',
        type: 'circle',
        source: 'cities',
        filter: ['<', ['get', 'rank'], ['interpolate', ['linear'], ['zoom'], 1, 12, 3, 60, 5, 400]],
        paint: { 'circle-radius': 2, 'circle-color': c.label, 'circle-opacity': 0.55 },
      },
      {
        // Labels are pictures drawn on a canvas at runtime (see mapImages.ts), so no glyph server is needed.
        id: 'city-labels',
        type: 'symbol',
        source: 'cities',
        filter: ['<', ['get', 'rank'], ['interpolate', ['linear'], ['zoom'], 1, 12, 3, 60, 5, 400]],
        layout: {
          'icon-image': ['concat', 'label:', ['get', 'name']],
          'icon-anchor': 'top',
          'icon-offset': [0, 4],
          'symbol-sort-key': ['get', 'rank'],
          'icon-padding': 6,
        },
      },
    ],
  }
}

export async function resolveStyle(choice: StyleChoice = styleChoice(), fetcher: typeof fetch = fetch): Promise<ResolvedStyle> {
  const offline = async (): Promise<ResolvedStyle> => ({
    style: await offlineStyle(),
    source: 'offline',
    maxZoom: OFFLINE_MAX_ZOOM,
    attribution: 'Basemap: Natural Earth',
  })
  if (choice === 'offline') return offline()
  const url = choice === 'auto' ? DEFAULT_ONLINE_STYLE : choice
  try {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 4000)
    const response = await fetcher(url, { signal: controller.signal })
    clearTimeout(timer)
    if (!response.ok) throw new Error(`style request failed: ${response.status}`)
    const style = (await response.json()) as StyleSpecification
    return {
      style: brandStyle(style),
      source: 'online',
      maxZoom: 18,
      attribution: '<a href="https://openfreemap.org" target="_blank" rel="noreferrer">OpenFreeMap</a> © <a href="https://www.openmaptiles.org/" target="_blank" rel="noreferrer">OpenMapTiles</a> Data from <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a>',
    }
  } catch (error) {
    if (choice !== 'auto') console.warn('Map style could not be loaded, using the offline basemap instead.', error)
    return offline()
  }
}
