'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { deviceId } from '@/lib/device'
import type { Postcard } from '@/lib/types'
import { FlagIcon, MapIcon, ShareIcon } from './icons'
import { sharePostcard } from './share'

const REASONS = [
  { key: 'speech', label: 'Someone can be heard talking' },
  { key: 'private', label: 'It reveals something private' },
  { key: 'offensive', label: 'It is offensive' },
  { key: 'other', label: 'Something else' },
] as const

export function PostcardActions({ card }: { card: Postcard }) {
  const [menu, setMenu] = useState(false)
  const [reported, setReported] = useState(false)
  const [toast, setToast] = useState<string | null>(null)

  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(() => setToast(null), 2600)
    return () => clearTimeout(timer)
  }, [toast])

  const report = async (reason: (typeof REASONS)[number]['key']) => {
    setMenu(false)
    try {
      await api.report(card.id, reason, deviceId())
      setReported(true)
      setToast('Thanks. It has been flagged for review.')
    } catch {
      setToast('The report could not be sent')
    }
  }

  return (
    <>
      <div className="detail__actions">
        <button type="button" className="button button--small" onClick={() => void sharePostcard(card).then((result) => result && setToast(result))}>
          <ShareIcon />
          Share
        </button>
        <a className="button button--quiet button--small" href={card.image_url} download={`sonic-postcard-${card.id}.png`}>
          Save image
        </a>
        <Link href={`/?p=${card.id}`} className="button button--quiet button--small">
          <MapIcon />
          On the map
        </Link>
        <button type="button" className="button button--quiet button--small" onClick={() => setMenu((open) => !open)} disabled={reported} aria-expanded={menu} data-testid="report">
          <FlagIcon />
          {reported ? 'Reported' : 'Report'}
        </button>
      </div>
      {menu && (
        <div className="card menu" role="menu" aria-label="Why are you reporting this postcard?" style={{ marginTop: 10 }}>
          {REASONS.map((reason) => (
            <button key={reason.key} type="button" role="menuitem" onClick={() => void report(reason.key)}>
              {reason.label}
            </button>
          ))}
        </div>
      )}
      {toast && (
        <div className="toast" role="status">
          {toast}
        </div>
      )}
    </>
  )
}
