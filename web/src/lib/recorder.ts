/**
 * Ten seconds from the microphone.
 *
 * Browsers process microphone audio for phone calls by default: echo
 * cancellation, noise suppression and automatic gain. Those are exactly the
 * things that erase rain and traffic, so all three are switched off.
 */
export const CLIP_SECONDS = 10
/** A little extra so the server always has a full ten seconds to trim to. */
export const CAPTURE_MS = CLIP_SECONDS * 1000 + 350

export const AUDIO_CONSTRAINTS: MediaTrackConstraints = {
  echoCancellation: false,
  noiseSuppression: false,
  autoGainControl: false,
  channelCount: 1,
}

const CANDIDATES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus']

export function pickMimeType(isSupported: (type: string) => boolean): string | undefined {
  return CANDIDATES.find((type) => isSupported(type))
}

export function extensionFor(mimeType: string): string {
  if (mimeType.includes('webm')) return 'webm'
  if (mimeType.includes('mp4') || mimeType.includes('aac')) return 'm4a'
  if (mimeType.includes('ogg')) return 'ogg'
  if (mimeType.includes('wav')) return 'wav'
  return 'bin'
}

export interface Recording {
  blob: Blob
  mimeType: string
  filename: string
  durationMs: number
  url: string
}

export interface RecorderHandle {
  /** Resolves when the clip is complete or the recording was cancelled (null). */
  done: Promise<Recording | null>
  cancel: () => void
}

export type MicrophoneError = 'unsupported' | 'denied' | 'unavailable'

export function microphoneError(error: unknown): MicrophoneError {
  const name = error instanceof DOMException ? error.name : ''
  if (name === 'NotAllowedError' || name === 'SecurityError') return 'denied'
  if (name === 'NotFoundError' || name === 'NotReadableError' || name === 'OverconstrainedError') return 'unavailable'
  return 'unsupported'
}

export async function startRecording(options: { onLevel: (level: number) => void; onProgress: (elapsedMs: number) => void }): Promise<RecorderHandle> {
  if (typeof MediaRecorder === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
    throw new DOMException('Recording is not supported in this browser', 'NotSupportedError')
  }
  const stream = await navigator.mediaDevices.getUserMedia({ audio: AUDIO_CONSTRAINTS })
  const mimeType = pickMimeType((type) => MediaRecorder.isTypeSupported(type))
  const recorder = new MediaRecorder(stream, mimeType ? { mimeType, audioBitsPerSecond: 96_000 } : undefined)
  const chunks: Blob[] = []
  recorder.addEventListener('dataavailable', (event) => event.data.size > 0 && chunks.push(event.data))

  // A level meter, so it is obvious the microphone is hearing something.
  const context = new AudioContext()
  const analyser = context.createAnalyser()
  analyser.fftSize = 1024
  context.createMediaStreamSource(stream).connect(analyser)
  const samples = new Float32Array(analyser.fftSize)

  let frame = 0
  let cancelled = false
  const started = performance.now()
  const loop = () => {
    analyser.getFloatTimeDomainData(samples)
    let sum = 0
    for (const sample of samples) sum += sample * sample
    const rms = Math.sqrt(sum / samples.length)
    // Map roughly -60 dBFS..-10 dBFS onto 0..1.
    options.onLevel(Math.max(0, Math.min(1, (20 * Math.log10(rms + 1e-6) + 60) / 50)))
    options.onProgress(performance.now() - started)
    frame = requestAnimationFrame(loop)
  }

  const cleanup = () => {
    cancelAnimationFrame(frame)
    for (const track of stream.getTracks()) track.stop()
    void context.close().catch(() => undefined)
  }

  const done = new Promise<Recording | null>((resolve) => {
    recorder.addEventListener('stop', () => {
      const durationMs = performance.now() - started
      cleanup()
      if (cancelled) return resolve(null)
      const type = recorder.mimeType || mimeType || 'audio/webm'
      const blob = new Blob(chunks, { type })
      resolve({ blob, mimeType: type, filename: `clip.${extensionFor(type)}`, durationMs, url: URL.createObjectURL(blob) })
    })
  })

  recorder.start(250)
  frame = requestAnimationFrame(loop)
  const timer = setTimeout(() => recorder.state !== 'inactive' && recorder.stop(), CAPTURE_MS)

  return {
    done,
    cancel: () => {
      cancelled = true
      clearTimeout(timer)
      if (recorder.state !== 'inactive') recorder.stop()
    },
  }
}
