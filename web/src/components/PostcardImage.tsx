import type { Postcard } from '@/lib/types'
import { placeLine } from '@/lib/format'

export function PostcardImage({ card, size = 'thumb', small = false, eager = false }: { card: Postcard; size?: 'thumb' | 'full'; small?: boolean; eager?: boolean }) {
  const tags = card.tags.map((tag) => tag.name.toLowerCase()).join(', ')
  return (
    <div className={small ? 'postcard postcard--small' : 'postcard'}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={size === 'full' ? card.image_url : card.thumb_url}
        alt={`Postcard from ${placeLine(card)}: a gouache painting for the sound of ${tags}`}
        width={1200}
        height={840}
        loading={eager ? 'eager' : 'lazy'}
        decoding="async"
      />
    </div>
  )
}
