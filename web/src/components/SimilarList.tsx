'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import type { Postcard } from '@/lib/types'
import { FeedItem } from './FeedItem'

const SCOPES = [
  { key: 'world', label: 'Worldwide', radiusKm: null },
  { key: 'region', label: 'Within 500 km', radiusKm: 500 },
  { key: 'near', label: 'Within 50 km', radiusKm: 50 },
] as const

/** "Sounds like this": the five nearest clips by embedding, optionally only those near this postcard. */
export function SimilarList({ card }: { card: Postcard }) {
  const [scope, setScope] = useState<(typeof SCOPES)[number]['key']>('world')
  const [items, setItems] = useState<Postcard[] | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    setItems(null)
    setFailed(false)
    const radiusKm = SCOPES.find((option) => option.key === scope)?.radiusKm
    api
      .similar(card.id, radiusKm ? { lat: card.lat, lon: card.lon, radiusKm } : undefined)
      .then((found) => !cancelled && setItems(found))
      .catch(() => !cancelled && setFailed(true))
    return () => {
      cancelled = true
    }
  }, [card.id, card.lat, card.lon, scope])

  return (
    <section id="similar" aria-labelledby="similar-title" style={{ scrollMarginTop: 20 }}>
      <h2 id="similar-title" className="section-title">
        Sounds like this
      </h2>
      <div className="segmented" role="group" aria-label="Where to look" style={{ marginBottom: 14 }}>
        {SCOPES.map((option) => (
          <button key={option.key} type="button" aria-pressed={scope === option.key} onClick={() => setScope(option.key)}>
            {option.label}
          </button>
        ))}
      </div>
      <div className="feed" data-testid="similar-list" aria-busy={items === null && !failed}>
        {items?.map((item) => <FeedItem key={item.id} card={item} />)}
      </div>
      {items?.length === 0 && <p className="note">Nothing else has been recorded in that circle yet.</p>}
      {failed && <p className="note">Similar sounds could not be loaded.</p>}
    </section>
  )
}
