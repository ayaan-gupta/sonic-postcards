export type TimeOfDay = 'dawn' | 'day' | 'dusk' | 'night'

export interface Tag {
  slug: string
  name: string
  score: number
}

export interface Label {
  name: string
  score: number
}

export interface Postcard {
  id: string
  created_at: string
  lat: number
  lon: number
  cell: { width_m: number; height_m: number }
  place_name: string
  country_code: string | null
  country_name: string | null
  local_date: string
  local_hour: number
  time_of_day: TimeOfDay
  tags: Tag[]
  labels: Label[]
  speech_probability: number
  weather: { condition?: string; temperature_c?: number | null } | null
  audio_url: string
  image_url: string
  thumb_url: string
  image_provider: string
  prompt: string
  seeded: boolean
  distance_m: number | null
  similarity: number | null
}

export interface Place {
  lat: number
  lon: number
  cell: { width_m: number; height_m: number }
  place_name: string
  country_name: string | null
}

export interface Quota {
  limit: number
  used: number
  remaining: number
  resets_at: string | null
}

export interface PinProperties {
  id: string | null
  motif: string
  count: number
}

export interface PinCollection {
  type: 'FeatureCollection'
  mode: 'pins' | 'cells'
  total: number
  features: Array<{
    type: 'Feature'
    geometry: { type: 'Point'; coordinates: [number, number] }
    properties: PinProperties
  }>
}
