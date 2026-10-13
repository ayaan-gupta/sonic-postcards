/*
 * Sonic Postcards service worker.
 *
 * Postcard images and clips never change once made, so they are cached on
 * first use and served from the cache after that. Pages and API answers go
 * to the network first, with the cache as a fallback when offline.
 */
const VERSION = 'sonic-postcards-v1'
const SHELL = ['/', '/offline']

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(VERSION)
      .then((cache) => cache.addAll(SHELL))
      .then(() => self.skipWaiting()),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== VERSION).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  )
})

const IMMUTABLE = /^\/api\/postcards\/[^/]+\/(image|audio)$|^\/_next\/static\//

self.addEventListener('fetch', (event) => {
  const request = event.request
  if (request.method !== 'GET') return
  const url = new URL(request.url)
  if (url.origin !== self.location.origin) return
  // Range requests for audio go straight through; a cached partial answer would be wrong.
  if (request.headers.has('range')) return

  if (IMMUTABLE.test(url.pathname)) {
    event.respondWith(
      caches.open(VERSION).then(async (cache) => {
        const hit = await cache.match(request)
        if (hit) return hit
        const response = await fetch(request)
        if (response.ok && response.status === 200) cache.put(request, response.clone())
        return response
      }),
    )
    return
  }

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone()
          caches.open(VERSION).then((cache) => cache.put(request, copy))
          return response
        })
        .catch(async () => (await caches.match(request)) || (await caches.match('/offline')) || Response.error()),
    )
  }
})
