/** Line icons drawn by hand at 24 px. One stroke weight, round joins. */
import type { SVGProps } from 'react'

function Icon({ children, ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.9} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
      {children}
    </svg>
  )
}

export const MapIcon = (props: SVGProps<SVGSVGElement>) => (
  <Icon {...props}>
    <path d="M9 4 3.5 6v14L9 18l6 2 5.5-2V4L15 6 9 4Z" />
    <path d="M9 4v14M15 6v14" />
  </Icon>
)

export const NearbyIcon = (props: SVGProps<SVGSVGElement>) => (
  <Icon {...props}>
    <path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11Z" />
    <circle cx="12" cy="10" r="2.4" />
  </Icon>
)

export const MicIcon = (props: SVGProps<SVGSVGElement>) => (
  <Icon strokeWidth={2} {...props}>
    <rect x="9" y="3" width="6" height="11" rx="3" />
    <path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21" />
  </Icon>
)

export const SentIcon = (props: SVGProps<SVGSVGElement>) => (
  <Icon {...props}>
    <rect x="3" y="5.5" width="18" height="13" rx="2" />
    <path d="M12 9v6M7 10.5h2.5M7 13.5h2.5" />
    <rect x="15" y="8.5" width="3.5" height="4" rx="0.5" />
  </Icon>
)

export const InfoIcon = (props: SVGProps<SVGSVGElement>) => (
  <Icon {...props}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 11v5.5" />
    <circle cx="12" cy="7.8" r="0.6" fill="currentColor" />
  </Icon>
)

export const PlayIcon = (props: SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...props}>
    <path d="M7.5 4.6c0-1 1-1.6 1.9-1.1l11 6.9c.8.5.8 1.7 0 2.2l-11 6.9c-.9.5-1.9-.1-1.9-1.1V4.6Z" transform="translate(-1.5 1)" />
  </svg>
)

export const PauseIcon = (props: SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...props}>
    <rect x="5" y="4" width="5" height="16" rx="1.6" />
    <rect x="14" y="4" width="5" height="16" rx="1.6" />
  </svg>
)

export const StopIcon = (props: SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...props}>
    <rect x="5.5" y="5.5" width="13" height="13" rx="3" />
  </svg>
)

export const CloseIcon = (props: SVGProps<SVGSVGElement>) => (
  <Icon strokeWidth={2.4} {...props}>
    <path d="m6 6 12 12M18 6 6 18" />
  </Icon>
)

export const ShareIcon = (props: SVGProps<SVGSVGElement>) => (
  <Icon {...props}>
    <path d="M12 15V3.5M8 7l4-3.5L16 7" />
    <path d="M6 11.5H5a1.5 1.5 0 0 0-1.5 1.5v6A1.5 1.5 0 0 0 5 20.5h14a1.5 1.5 0 0 0 1.5-1.5v-6a1.5 1.5 0 0 0-1.5-1.5h-1" />
  </Icon>
)

export const FlagIcon = (props: SVGProps<SVGSVGElement>) => (
  <Icon {...props}>
    <path d="M5.5 21V4M5.5 4.5h11l-2 4 2 4h-11" />
  </Icon>
)

export const WavesIcon = (props: SVGProps<SVGSVGElement>) => (
  <Icon strokeWidth={2.1} {...props}>
    <path d="M4 10v4M8 6.5v11M12 9v6M16 4.5v15M20 10v4" />
  </Icon>
)

export const LocateIcon = (props: SVGProps<SVGSVGElement>) => (
  <Icon {...props}>
    <path d="m20 4-7 16-2.2-6.8L4 11l16-7Z" />
  </Icon>
)

export const ArrowIcon = (props: SVGProps<SVGSVGElement>) => (
  <Icon strokeWidth={2.2} {...props}>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </Icon>
)

export function PinGlyph(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 34 44" aria-hidden="true" {...props}>
      <path d="M17 43C17 43 3 28.5 3 16.5a14 14 0 0 1 28 0C31 28.5 17 43 17 43Z" fill="#e2583a" stroke="#fffdf8" strokeWidth="2.5" />
      <circle cx="17" cy="16.5" r="5" fill="#fffdf8" />
    </svg>
  )
}
