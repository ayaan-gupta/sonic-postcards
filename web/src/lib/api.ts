/**
 * Typed client for the API. Every call goes to /api on the same origin; the
 * Next middleware forwards it to the FastAPI service.
 */
import { snap } from './grid'
import type { PinCollection, Place, Postcard, Quota } from './types'

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly detail: Record<string, unknown> = {},
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

type Fetch = typeof fetch

export async function parse<T>(response: Response): Promise<T> {
  if (response.ok) return (await response.json()) as T
  let code = 'http_error'
  let message = `The server answered ${response.status}.`
  let detail: Record<string, unknown> = {}
  try {
    const body = (await response.json()) as { error?: { code?: string; message?: string; detail?: Record<string, unknown> } }
    if (body.error) {
      code = body.error.code ?? code
      message = body.error.message ?? message
      detail = body.error.detail ?? {}
    }
  } catch {
    // Not JSON: keep the generic message.
  }
  throw new ApiError(response.status, code, message, detail)
}

function query(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) if (value !== undefined) search.set(key, String(value))
  return search.toString()
}

export interface UploadInput {
  audio: Blob
  filename: string
  lat: number
  lon: number
  source: 'gps' | 'manual'
  deviceId: string
  tzOffsetMin: number
}

/** Builds the multipart body. The location is snapped here, before it leaves the browser. */
export function uploadForm(input: UploadInput): FormData {
  const point = snap(input.lat, input.lon)
  const form = new FormData()
  form.set('audio', input.audio, input.filename)
  form.set('lat', point.lat.toFixed(3))
  form.set('lon', point.lon.toFixed(3))
  form.set('source', input.source)
  form.set('tz_offset_min', String(input.tzOffsetMin))
  return form
}

export function createApi(base = '', fetcher: Fetch = fetch) {
  const get = async <T>(path: string, init?: RequestInit) => parse<T>(await fetcher(base + path, init))
  return {
    postcard: (id: string) => get<Postcard>(`/api/postcards/${encodeURIComponent(id)}`),
    recent: (limit = 24) => get<{ items: Postcard[] }>(`/api/postcards?${query({ limit })}`).then((r) => r.items),
    pins: (bbox: [number, number, number, number], zoom: number) =>
      get<PinCollection>(`/api/pins?${query({ bbox: bbox.map((v) => v.toFixed(4)).join(','), zoom: zoom.toFixed(2) })}`),
    nearby: (lat: number, lon: number, radiusKm: number, sort: 'recent' | 'nearest' = 'recent') => {
      const point = snap(lat, lon)
      return get<{ items: Postcard[] }>(`/api/nearby?${query({ lat: point.lat, lon: point.lon, radius_km: radiusKm, sort })}`).then((r) => r.items)
    },
    similar: (id: string, near?: { lat: number; lon: number; radiusKm: number }) => {
      const point = near ? snap(near.lat, near.lon) : undefined
      const params = { limit: 5, lat: point?.lat, lon: point?.lon, radius_km: near?.radiusKm }
      return get<{ items: Postcard[] }>(`/api/postcards/${encodeURIComponent(id)}/similar?${query(params)}`).then((r) => r.items)
    },
    place: (lat: number, lon: number) => {
      const point = snap(lat, lon)
      return get<Place>(`/api/place?${query({ lat: point.lat, lon: point.lon })}`)
    },
    quota: (deviceId: string) => get<Quota>('/api/quota', { headers: { 'X-Device-Id': deviceId } }),
    upload: async (input: UploadInput) =>
      parse<Postcard>(
        await fetcher(`${base}/api/postcards`, { method: 'POST', body: uploadForm(input), headers: { 'X-Device-Id': input.deviceId } }),
      ),
    report: (id: string, reason: 'speech' | 'private' | 'offensive' | 'other', deviceId: string) =>
      get<{ reported: boolean; hidden: boolean }>(`/api/postcards/${encodeURIComponent(id)}/report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Device-Id': deviceId },
        body: JSON.stringify({ reason }),
      }),
  }
}

export const api = createApi()
