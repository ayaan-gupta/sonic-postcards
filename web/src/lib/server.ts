/** Server-side access to the API, for pages that render on the server. */
import { createApi } from './api'

export function serverApi() {
  const base = process.env.API_URL ?? 'http://127.0.0.1:8106'
  return createApi(base, (input, init) => fetch(input, { ...init, cache: 'no-store' }))
}
