'use client'

import { useEffect } from 'react'

/** Registers the service worker in production builds, where the files it caches are stable. */
export function ServiceWorker() {
  useEffect(() => {
    if (process.env.NODE_ENV !== 'production' || !('serviceWorker' in navigator)) return
    navigator.serviceWorker.register('/sw.js').catch(() => undefined)
  }, [])
  return null
}
