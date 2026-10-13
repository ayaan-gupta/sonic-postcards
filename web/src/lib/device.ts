/**
 * A random id kept in localStorage. It is the only thing that identifies a
 * device to the rate limiter, and the server stores a salted hash of it.
 */
const KEY = 'sonic-postcards.device'

export function newDeviceId(random: (bytes: Uint8Array) => Uint8Array = (bytes) => crypto.getRandomValues(bytes)): string {
  const bytes = random(new Uint8Array(18))
  let text = ''
  for (const byte of bytes) text += byte.toString(16).padStart(2, '0')
  return `d-${text}`
}

export function deviceId(storage: Pick<Storage, 'getItem' | 'setItem'> | undefined = safeStorage()): string {
  try {
    const existing = storage?.getItem(KEY)
    if (existing && /^[A-Za-z0-9_-]{8,128}$/.test(existing)) return existing
    const created = newDeviceId()
    storage?.setItem(KEY, created)
    return created
  } catch {
    // Private mode can refuse storage. A fresh id per visit still works.
    return newDeviceId()
  }
}

function safeStorage(): Storage | undefined {
  try {
    return typeof window === 'undefined' ? undefined : window.localStorage
  } catch {
    return undefined
  }
}
