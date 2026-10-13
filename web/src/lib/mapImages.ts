/**
 * Map symbols drawn on a canvas when the map first asks for them.
 *
 * MapLibre normally sets text from glyph files fetched from a font server.
 * Cluster counts and offline city labels are instead rendered here in the
 * system font and handed to the map as images, which works with any style
 * and with no network.
 */
import { formatCount } from './format'
import { MAP_COLOURS } from './mapStyle'

export const SYSTEM_FONT = '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'

export interface MapImage {
  width: number
  height: number
  data: Uint8ClampedArray
  pixelRatio: number
}

type Draw = (ctx: CanvasRenderingContext2D, width: number, height: number) => void

function render(width: number, height: number, pixelRatio: number, draw: Draw): MapImage | null {
  const canvas = document.createElement('canvas')
  canvas.width = Math.ceil(width * pixelRatio)
  canvas.height = Math.ceil(height * pixelRatio)
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  if (!ctx) return null
  ctx.scale(pixelRatio, pixelRatio)
  draw(ctx, width, height)
  const image = ctx.getImageData(0, 0, canvas.width, canvas.height)
  return { width: canvas.width, height: canvas.height, data: image.data, pixelRatio }
}

/** How big a cluster bubble is, in CSS pixels, for a given number of postcards. */
export function clusterDiameter(count: number): number {
  if (count < 10) return 32
  if (count < 100) return 38
  if (count < 1000) return 46
  return 54
}

/** The id the cluster layer asks for. Counts of 1,000 and up share an image per hundred. */
export function clusterImageId(count: number): string {
  return count >= 1000 ? `cluster:${Math.round(count / 100)}h` : `cluster:${count}`
}

export function countFromImageId(id: string): number | null {
  const match = /^cluster:(\d+)(h?)$/.exec(id)
  if (!match?.[1]) return null
  return Number(match[1]) * (match[2] ? 100 : 1)
}

export function clusterImage(count: number, pixelRatio: number): MapImage | null {
  const diameter = clusterDiameter(count)
  const size = diameter + 8
  return render(size, size, pixelRatio, (ctx) => {
    const centre = size / 2
    ctx.beginPath()
    ctx.arc(centre, centre + 1.5, diameter / 2 + 1, 0, Math.PI * 2)
    ctx.fillStyle = 'rgba(29,36,64,0.18)'
    ctx.fill()
    ctx.beginPath()
    ctx.arc(centre, centre, diameter / 2, 0, Math.PI * 2)
    ctx.fillStyle = MAP_COLOURS.paper
    ctx.fill()
    ctx.beginPath()
    ctx.arc(centre, centre, diameter / 2 - 2.5, 0, Math.PI * 2)
    ctx.fillStyle = MAP_COLOURS.ink
    ctx.fill()
    ctx.fillStyle = MAP_COLOURS.paper
    ctx.font = `600 ${count < 100 ? 13 : 12.5}px ${SYSTEM_FONT}`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(formatCount(count), centre, centre + 0.5)
  })
}

export function labelImage(text: string, pixelRatio: number): MapImage | null {
  const font = `500 11.5px ${SYSTEM_FONT}`
  const probe = document.createElement('canvas').getContext('2d')
  if (!probe) return null
  probe.font = font
  const width = Math.ceil(probe.measureText(text).width) + 8
  return render(width, 18, pixelRatio, (ctx, w, h) => {
    ctx.font = font
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.lineJoin = 'round'
    ctx.lineWidth = 3
    ctx.strokeStyle = 'rgba(244,236,217,0.9)'
    ctx.strokeText(text, w / 2, h / 2)
    ctx.fillStyle = MAP_COLOURS.label
    ctx.fillText(text, w / 2, h / 2)
  })
}

/** Resolve an image id the style asked for, or null if it is not one of ours. */
export function imageFor(id: string, pixelRatio: number): MapImage | null {
  const count = countFromImageId(id)
  if (count !== null) return clusterImage(count, pixelRatio)
  if (id.startsWith('label:')) return labelImage(id.slice('label:'.length), pixelRatio)
  return null
}
