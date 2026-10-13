import Link from 'next/link'
import { formatDate, formatDistance, percent, placeLine } from '@/lib/format'
import type { Postcard } from '@/lib/types'
import { PlayButton } from './PlayButton'
import { PostcardImage } from './PostcardImage'
import { Tags } from './Tags'

/** One postcard in a list: picture, place, tags and a play button. */
export function FeedItem({ card }: { card: Postcard }) {
  const extra =
    card.similarity !== null ? `${percent(card.similarity)} alike` : card.distance_m !== null ? `${formatDistance(card.distance_m)} away` : null
  return (
    <article className="card feed-item" data-testid="feed-item">
      <Link href={`/p/${card.id}`} aria-label={`Open the postcard from ${placeLine(card)}`}>
        <PostcardImage card={card} small />
      </Link>
      <Link href={`/p/${card.id}`} className="feed-item__text">
        <h3 className="feed-item__place">{placeLine(card)}</h3>
        <p className="feed-item__meta">{[extra, formatDate(card.local_date)].filter(Boolean).join(' · ')}</p>
        <Tags card={card} max={2} />
      </Link>
      <PlayButton src={card.audio_url} label={`ten seconds from ${card.place_name}`} small />
    </article>
  )
}
