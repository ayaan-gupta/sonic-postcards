import { describe, expect, it } from 'vitest'
import { ApiError, createApi, parse, uploadForm } from '@/lib/api'

function fakeFetch(handler: (url: string, init?: RequestInit) => Response) {
  const calls: Array<{ url: string; init?: RequestInit }> = []
  const fetcher = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ url: String(input), init })
    return handler(String(input), init)
  }) as typeof fetch
  return { fetcher, calls }
}

describe('api client', () => {
  it('snaps the location before the upload leaves the browser', () => {
    const form = uploadForm({ audio: new Blob(['x']), filename: 'clip.webm', lat: 35.011635, lon: 135.768029, source: 'gps', deviceId: 'd-123456789', tzOffsetMin: 540 })
    expect(form.get('lat')).toBe('35.010')
    expect(form.get('lon')).toBe('135.770')
    expect(form.get('source')).toBe('gps')
    expect(form.get('tz_offset_min')).toBe('540')
    expect([...form.keys()].sort()).toEqual(['audio', 'lat', 'lon', 'source', 'tz_offset_min'])
  })

  it('never puts an exact position in a query string', async () => {
    const { fetcher, calls } = fakeFetch(() => Response.json({ items: [] }))
    const api = createApi('', fetcher)
    await api.nearby(64.146582, -21.942635, 25, 'nearest')
    await api.similar('abc', { lat: 64.146582, lon: -21.942635, radiusKm: 50 })
    await api.place(64.146582, -21.942635).catch(() => undefined)
    for (const call of calls) {
      expect(call.url).not.toContain('64.1465')
      expect(call.url).not.toContain('21.9426')
      expect(call.url).toContain('lat=64.145')
      expect(call.url).toContain('lon=-21.94')
    }
    expect(calls[0]!.url).toBe('/api/nearby?lat=64.145&lon=-21.94&radius_km=25&sort=nearest')
  })

  it('turns the API error body into a typed error', async () => {
    const body = { error: { code: 'speech_detected', message: 'This clip sounds like mostly speech', detail: { speech_probability: 0.99 } } }
    const error = await parse(Response.json(body, { status: 422 })).catch((caught: unknown) => caught)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 422, code: 'speech_detected', message: body.error.message, detail: { speech_probability: 0.99 } })
    const plain = await parse(new Response('bad gateway', { status: 502 })).catch((caught: unknown) => caught)
    expect(plain).toMatchObject({ status: 502, code: 'http_error' })
  })

  it('sends the device id as a header, and the report reason as JSON', async () => {
    const { fetcher, calls } = fakeFetch(() => Response.json({ reported: true, hidden: false }))
    await createApi('http://api', fetcher).report('abc', 'speech', 'd-123456789')
    expect(calls[0]!.url).toBe('http://api/api/postcards/abc/report')
    expect(calls[0]!.init?.method).toBe('POST')
    expect((calls[0]!.init?.headers as Record<string, string>)['X-Device-Id']).toBe('d-123456789')
    expect(calls[0]!.init?.body).toBe('{"reason":"speech"}')
  })
})
