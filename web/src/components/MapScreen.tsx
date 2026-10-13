'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { useCallback, useEffect, useState } from 'react'
import { api } from '@/lib/api'
import type { Postcard } from '@/lib/types'
import { MapView, type MapStats } from './MapView'
import { PostcardSheet } from './PostcardSheet'
import { Welcome } from './Welcome'

export function MapScreen() {
  const router = useRouter()
  const params = useSearchParams()
  const selectedId = params.get('p')
  const [card, setCard] = useState<Postcard | null>(null)
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState<MapStats | null>(null)
  const [attribution, setAttribution] = useState('')

  const select = useCallback(
    (id: string | null) => {
      router.replace(id ? `/?p=${id}` : '/', { scroll: false })
    },
    [router],
  )

  useEffect(() => {
    if (!selectedId) {
      setCard(null)
      return
    }
    let cancelled = false
    setLoading(true)
    api
      .postcard(selectedId)
      .then((found) => !cancelled && setCard(found))
      .catch(() => !cancelled && select(null))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [selectedId, select])

  const shown = card && card.id === selectedId ? card : null

  return (
    <main className="map-screen">
      <MapView
        selectedId={shown?.id ?? null}
        focus={shown ? { lat: shown.lat, lon: shown.lon } : null}
        refreshKey={0}
        onSelect={select}
        onStats={setStats}
        onAttribution={setAttribution}
      />
      <div className="map-top">
        <div className="map-chip glass">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/art/brand/logo.png" alt="" width={30} height={30} />
          <h1 style={{ font: 'inherit' }}>Sonic Postcards</h1>
        </div>
        {stats && (
          <div className="map-chip map-chip--count glass" data-testid="pin-count">
            {stats.total.toLocaleString('en-US')} {stats.total === 1 ? 'postcard' : 'postcards'}
          </div>
        )}
      </div>
      {attribution && <div className="map-attribution" dangerouslySetInnerHTML={{ __html: attribution }} />}
      {selectedId && <PostcardSheet card={shown} loading={loading} onClose={() => select(null)} />}
      <Welcome />
    </main>
  )
}
