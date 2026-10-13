/**
 * One audio element for the whole app, so starting a clip stops the last one.
 * Components subscribe with useSyncExternalStore.
 */
export interface PlayerState {
  src: string | null
  playing: boolean
  progress: number // 0 to 1
  error: boolean
}

const IDLE: PlayerState = { src: null, playing: false, progress: 0, error: false }
let state: PlayerState = IDLE
let audio: HTMLAudioElement | null = null
let frame = 0
const listeners = new Set<() => void>()

function set(next: Partial<PlayerState>) {
  state = { ...state, ...next }
  for (const listener of listeners) listener()
}

function tick() {
  if (!audio) return
  const duration = Number.isFinite(audio.duration) && audio.duration > 0 ? audio.duration : 10
  set({ progress: Math.min(1, audio.currentTime / duration) })
  if (!audio.paused) frame = requestAnimationFrame(tick)
}

function element(): HTMLAudioElement {
  if (audio) return audio
  audio = new Audio()
  audio.preload = 'none'
  audio.addEventListener('play', () => {
    set({ playing: true, error: false })
    cancelAnimationFrame(frame)
    frame = requestAnimationFrame(tick)
  })
  audio.addEventListener('pause', () => set({ playing: false }))
  audio.addEventListener('ended', () => set({ playing: false, progress: 0 }))
  audio.addEventListener('error', () => set({ playing: false, error: true }))
  return audio
}

export const player = {
  subscribe(listener: () => void) {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },
  snapshot: () => state,
  serverSnapshot: (): PlayerState => IDLE,
  toggle(src: string) {
    const el = element()
    if (state.src === src && !el.paused) {
      el.pause()
      return
    }
    if (state.src !== src) {
      el.src = src
      set({ src, progress: 0, error: false })
    }
    void el.play().catch(() => set({ playing: false, error: true }))
  },
  stop() {
    audio?.pause()
  },
}
