'use client'

import Link from 'next/link'
import { placeLine, whenLine } from '@/lib/format'
import type { Postcard } from '@/lib/types'
import { CloseIcon, WavesIcon } from './icons'
import { PlayButton } from './PlayButton'
import { PostcardImage } from './PostcardImage'
import { Tags } from './Tags'

/** The card that rises over the map when a pin is tapped. */
export function PostcardSheet({ card, loading, onClose }: { card: Postcard | null; loading: boolean; onClose: () => void }) {
  return (
    <aside className="sheet glass" aria-label="Selected postcard" aria-busy={loading}>
      {card ? (
        <>
          <Link href={`/p/${card.id}`} aria-label={`Open the postcard from ${placeLine(card)}`}>
            <PostcardImage card={card} eager />
          </Link>
          <div className="sheet__body">
            <PlayButton src={card.audio_url} label={`ten seconds from ${card.place_name}`} />
            <div className="sheet__text">
              <h2 className="sheet__place">{placeLine(card)}</h2>
              <p className="sheet__when">{whenLine(card)}</p>
            </div>
            <button type="button" className="sheet__close" onClick={onClose} aria-label="Close">
              <CloseIcon />
            </button>
          </div>
          <div className="sheet__tags">
            <Tags card={card} />
          </div>
          <div className="sheet__actions">
            <Link href={`/p/${card.id}#similar`} className="button button--quiet button--small">
              <WavesIcon />
              Sounds like this
            </Link>
            <Link href={`/p/${card.id}`} className="button button--small">
              Open postcard
            </Link>
          </div>
        </>
      ) : (
        <div className="sheet__skeleton" />
      )}
    </aside>
  )
}
