import { placeLine } from '@/lib/format'
import type { Postcard } from '@/lib/types'

/**
 * Share a postcard: the PNG itself where the device can share files, a link
 * otherwise, the clipboard as the last resort. Returns a short message to
 * show, or null when the system share sheet took over.
 */
export async function sharePostcard(card: Postcard): Promise<string | null> {
  const url = `${window.location.origin}/p/${card.id}`
  const title = `Sounds of ${placeLine(card)}`
  try {
    if (navigator.share) {
      let files: File[] | undefined
      try {
        const response = await fetch(card.image_url)
        const file = new File([await response.blob()], `sonic-postcard-${card.id}.png`, { type: 'image/png' })
        if (navigator.canShare?.({ files: [file] })) files = [file]
      } catch {
        // Share the link without the picture.
      }
      await navigator.share({ title, text: title, url, files })
      return null
    }
    await navigator.clipboard.writeText(url)
    return 'Link copied'
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') return null
    return 'Could not share from this browser'
  }
}
