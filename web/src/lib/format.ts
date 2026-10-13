import type { Postcard, TimeOfDay } from './types'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

export function formatDistance(metres: number): string {
  if (metres < 950) return `${Math.max(100, Math.round(metres / 100) * 100)} m`
  if (metres < 9_950) return `${(metres / 1000).toFixed(1)} km`
  return `${Math.round(metres / 1000).toLocaleString('en-US')} km`
}

export function formatCount(count: number): string {
  if (count < 1000) return String(count)
  if (count < 10_000) return `${(Math.floor(count / 100) / 10).toFixed(1).replace(/\.0$/, '')}k`
  return `${Math.floor(count / 1000)}k`
}

/** "12 Oct 2026" from the ISO local date the API stores. */
export function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.split('-').map(Number)
  if (!year || !month || !day) return isoDate
  return `${day} ${MONTHS[month - 1]} ${year}`
}

const TIME_WORD: Record<TimeOfDay, string> = { dawn: 'Early morning', day: 'Daytime', dusk: 'Evening', night: 'Night' }

export function timeWord(time: TimeOfDay): string {
  return TIME_WORD[time]
}

export function formatHour(hour: number): string {
  const suffix = hour < 12 ? 'am' : 'pm'
  const twelve = hour % 12 === 0 ? 12 : hour % 12
  return `${twelve} ${suffix}`
}

export function placeLine(card: Pick<Postcard, 'place_name' | 'country_name'>): string {
  return card.country_name ? `${card.place_name}, ${card.country_name}` : card.place_name
}

export function whenLine(card: Pick<Postcard, 'local_date' | 'local_hour' | 'time_of_day'>): string {
  return `${formatDate(card.local_date)}, around ${formatHour(card.local_hour)}`
}

export function percent(value: number): string {
  return `${Math.round(value * 100)}%`
}

/** "in 3 h 20 min" until an ISO timestamp, for the rate limit message. */
export function untilText(iso: string, now: Date = new Date()): string {
  const minutes = Math.max(1, Math.ceil((new Date(iso).getTime() - now.getTime()) / 60_000))
  if (minutes < 60) return `in ${minutes} min`
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return rest ? `in ${hours} h ${rest} min` : `in ${hours} h`
}
