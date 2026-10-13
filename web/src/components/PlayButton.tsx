'use client'

import { useSyncExternalStore } from 'react'
import { player } from '@/lib/player'
import { PauseIcon, PlayIcon } from './icons'

/** Plays one clip. The ring fills over its ten seconds. */
export function PlayButton({ src, label, small = false }: { src: string; label: string; small?: boolean }) {
  const state = useSyncExternalStore(player.subscribe, player.snapshot, player.serverSnapshot)
  const mine = state.src === src
  const playing = mine && state.playing
  const progress = mine ? state.progress : 0
  const radius = 46
  const length = 2 * Math.PI * radius
  return (
    <button
      type="button"
      className={small ? 'play play--small' : 'play'}
      onClick={(event) => {
        event.preventDefault()
        event.stopPropagation()
        player.toggle(src)
      }}
      aria-label={playing ? `Pause ${label}` : `Play ${label}`}
      aria-pressed={playing}
      data-playing={playing}
    >
      <svg className="play__ring" viewBox="0 0 100 100" aria-hidden="true">
        <circle className="track" cx="50" cy="50" r={radius} />
        {progress > 0 && <circle className="bar" cx="50" cy="50" r={radius} strokeDasharray={length} strokeDashoffset={length * (1 - progress)} />}
      </svg>
      {playing ? <PauseIcon className="play__icon" /> : <PlayIcon className="play__icon" />}
    </button>
  )
}
