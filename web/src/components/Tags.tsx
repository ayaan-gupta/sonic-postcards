import type { Postcard } from '@/lib/types'

/** The motif tags of a postcard as a row of pills, strongest first. */
export function Tags({ card, max = 3 }: { card: Pick<Postcard, 'tags' | 'seeded'>; max?: number }) {
  return (
    <div className="pills">
      {card.tags.slice(0, max).map((tag, index) => (
        <span key={tag.slug} className={index === 0 ? 'pill pill--first' : 'pill'}>
          {tag.name}
        </span>
      ))}
      {card.seeded && (
        <span className="pill pill--sample" title="Seeded with a synthetic sound so the map is not empty">
          Sample
        </span>
      )}
    </div>
  )
}
