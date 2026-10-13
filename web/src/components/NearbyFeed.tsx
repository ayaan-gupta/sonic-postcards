'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { snap, type GridPoint } from '@/lib/grid'
import type { Place, Postcard } from '@/lib/types'
import { FeedItem } from './FeedItem'
import { LocateIcon } from './icons'

const RADII = [5, 25, 100, 500] as const
const KEY = 'sonic-postcards.nearby-origin'

/** Postcards within a radius of where you are. The origin is snapped to the grid before it is sent. */
export function NearbyFeed() {
  const [origin, setOrigin] = useState<GridPoint | null>(null)
  const [place, setPlace] = useState<Place | null>(null)
  const [radius, setRadius] = useState<(typeof RADII)[number]>(25)
  const [sort, setSort] = useState<'recent' | 'nearest'>('recent')
  const [items, setItems] = useState<Postcard[] | null>(null)
  const [state, setState] = useState<'idle' | 'locating' | 'denied' | 'loading' | 'error'>('idle')

  useEffect(() => {
    // Restore the last origin, or accept one from the address bar (?lat=..&lon=..).
    const params = new URLSearchParams(window.location.search)
    const lat = Number(params.get('lat'))
    const lon = Number(params.get('lon'))
    try {
      if (params.has('lat') && params.has('lon') && Number.isFinite(lat) && Number.isFinite(lon)) return setOrigin(snap(lat, lon))
      const saved = JSON.parse(window.sessionStorage.getItem(KEY) ?? 'null') as [number, number] | null
      if (saved) setOrigin(snap(saved[0], saved[1]))
    } catch {
      // Ask for a location instead.
    }
  }, [])

  useEffect(() => {
    if (!origin) return
    let cancelled = false
    setState('loading')
    try {
      window.sessionStorage.setItem(KEY, JSON.stringify([origin.lat, origin.lon]))
    } catch {
      // Ignore.
    }
    api.place(origin.lat, origin.lon).then((found) => !cancelled && setPlace(found)).catch(() => undefined)
    api
      .nearby(origin.lat, origin.lon, radius, sort)
      .then((found) => {
        if (cancelled) return
        setItems(found)
        setState('idle')
      })
      .catch(() => !cancelled && setState('error'))
    return () => {
      cancelled = true
    }
  }, [origin, radius, sort])

  const locate = () => {
    if (!navigator.geolocation) return setState('denied')
    setState('locating')
    navigator.geolocation.getCurrentPosition(
      (position) => setOrigin(snap(position.coords.latitude, position.coords.longitude)),
      () => setState('denied'),
      { enableHighAccuracy: false, timeout: 10_000, maximumAge: 60_000 },
    )
  }

  if (!origin) {
    return (
      <div className="card empty" style={{ marginTop: 24 }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/art/onboarding/place.png" alt="" width={360} height={270} />
        <b>What does it sound like around here?</b>
        <p>
          {state === 'denied'
            ? 'Location is switched off for this site. Turn it on in your browser, or browse the map instead.'
            : 'Share your rough location to hear postcards recorded nearby. It is rounded to a 500 m square before it leaves your device.'}
        </p>
        <button type="button" className="button button--accent" onClick={locate} disabled={state === 'locating'} data-testid="locate">
          <LocateIcon />
          {state === 'locating' ? 'Finding you' : 'Use my location'}
        </button>
        <Link href="/" className="button button--quiet button--small">
          Browse the map
        </Link>
      </div>
    )
  }

  return (
    <div>
      <div className="toolbar">
        <div className="segmented" role="group" aria-label="Radius">
          {RADII.map((value) => (
            <button key={value} type="button" aria-pressed={radius === value} onClick={() => setRadius(value)}>
              {value} km
            </button>
          ))}
        </div>
        <div className="segmented" role="group" aria-label="Order">
          <button type="button" aria-pressed={sort === 'recent'} onClick={() => setSort('recent')}>
            Newest
          </button>
          <button type="button" aria-pressed={sort === 'nearest'} onClick={() => setSort('nearest')}>
            Nearest
          </button>
        </div>
      </div>
      <p className="note" style={{ marginBottom: 14 }} aria-live="polite">
        {place ? `Around ${place.place_name}` : 'Around you'}
        {items ? ` · ${items.length} ${items.length === 1 ? 'postcard' : 'postcards'} within ${radius} km` : ''}
        {' · '}
        <button type="button" onClick={locate} style={{ textDecoration: 'underline', color: 'inherit' }}>
          Update my location
        </button>
      </p>
      {state === 'error' && <p className="note">The feed could not be loaded. Check your connection and try again.</p>}
      {items && items.length === 0 && (
        <div className="card empty">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/art/empty/quiet.png" alt="" width={560} height={360} />
          <b>It is quiet around here</b>
          <p>No postcards within {radius} km yet. Widen the circle, or be the first to send one.</p>
          <Link href="/record" className="button button--accent">
            Record the first
          </Link>
        </div>
      )}
      <div className="feed">{items?.map((card) => <FeedItem key={card.id} card={card} />)}</div>
    </div>
  )
}
