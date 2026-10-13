'use client'

import Link from 'next/link'
import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError } from '@/lib/api'
import { deviceId } from '@/lib/device'
import { untilText } from '@/lib/format'
import { cellSizeMetres, type GridPoint } from '@/lib/grid'
import { CAPTURE_MS, CLIP_SECONDS, microphoneError, startRecording, type RecorderHandle, type Recording } from '@/lib/recorder'
import type { Place, Postcard, Quota } from '@/lib/types'
import { ArrowIcon, MicIcon, ShareIcon, StopIcon } from './icons'
import { LocationPicker } from './LocationPicker'
import { PlayButton } from './PlayButton'
import { PostcardImage } from './PostcardImage'
import { sharePostcard } from './share'
import { Tags } from './Tags'

type Step = 'record' | 'place' | 'sending' | 'done'
type Problem = { kind: 'speech' | 'limit' | 'clip' | 'mic' | 'other'; title: string; text: string }

const MIC_TEXT = {
  denied: 'The microphone is blocked for this site. Allow it in your browser settings, then try again.',
  unavailable: 'No microphone was found. Plug one in or check that another app is not using it.',
  unsupported: 'This browser cannot record audio. Try a current version of Safari, Chrome or Firefox.',
} as const

const BARS = 21

export function RecordFlow() {
  const [step, setStep] = useState<Step>('record')
  const [recording, setRecording] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [levels, setLevels] = useState<number[]>(() => new Array<number>(BARS).fill(0))
  const [clip, setClip] = useState<Recording | null>(null)
  const [point, setPoint] = useState<GridPoint | null>(null)
  const [source, setSource] = useState<'gps' | 'manual'>('manual')
  const [place, setPlace] = useState<Place | null>(null)
  const [card, setCard] = useState<Postcard | null>(null)
  const [problem, setProblem] = useState<Problem | null>(null)
  const [quota, setQuota] = useState<Quota | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const handle = useRef<RecorderHandle | null>(null)
  const lastLevel = useRef(0)
  const placeRequest = useRef(0)

  useEffect(() => {
    api.quota(deviceId()).then(setQuota).catch(() => undefined)
    return () => handle.current?.cancel()
  }, [])

  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(() => setToast(null), 2600)
    return () => clearTimeout(timer)
  }, [toast])

  const begin = async () => {
    setProblem(null)
    setClip(null)
    setElapsed(0)
    try {
      const started = await startRecording({
        onLevel: (level) => (lastLevel.current = level),
        onProgress: (ms) => {
          setElapsed(ms)
          setLevels((previous) => [...previous.slice(1), lastLevel.current])
        },
      })
      handle.current = started
      setRecording(true)
      const result = await started.done
      handle.current = null
      setRecording(false)
      setLevels(new Array<number>(BARS).fill(0))
      if (result) setClip(result)
    } catch (error) {
      setRecording(false)
      setProblem({ kind: 'mic', title: 'No microphone', text: MIC_TEXT[microphoneError(error)] })
    }
  }

  const stopEarly = () => {
    handle.current?.cancel()
    setElapsed(0)
  }

  const onPoint = useCallback((next: GridPoint, from: 'gps' | 'manual') => {
    setPoint(next)
    setSource(from)
    setPlace(null)
    // Only the answer to the latest question counts; the map may have moved on.
    const request = ++placeRequest.current
    api
      .place(next.lat, next.lon)
      .then((found) => request === placeRequest.current && setPlace(found))
      .catch(() => undefined)
  }, [])

  const send = async () => {
    if (!clip || !point) return
    setStep('sending')
    setProblem(null)
    try {
      const made = await api.upload({
        audio: clip.blob,
        filename: clip.filename,
        lat: point.lat,
        lon: point.lon,
        source,
        deviceId: deviceId(),
        tzOffsetMin: -new Date().getTimezoneOffset(),
      })
      setCard(made)
      setStep('done')
    } catch (error) {
      if (error instanceof ApiError && error.code === 'speech_detected') {
        setProblem({ kind: 'speech', title: 'That one had voices in it', text: error.message })
        setClip(null)
        setStep('record')
      } else if (error instanceof ApiError && error.code === 'rate_limited') {
        const resets = typeof error.detail.resets_at === 'string' ? ` You can send the next one ${untilText(error.detail.resets_at)}.` : ''
        setProblem({ kind: 'limit', title: 'That is ten for today', text: `Each device can send ten postcards in 24 hours.${resets}` })
        setStep('record')
      } else if (error instanceof ApiError && error.status === 400) {
        setProblem({ kind: 'clip', title: 'That clip did not work', text: error.message })
        setClip(null)
        setStep('record')
      } else {
        setProblem({ kind: 'other', title: 'It did not send', text: 'The server could not be reached. Your clip is still here, so you can try again.' })
        setStep('place')
      }
    }
  }

  const reset = () => {
    setCard(null)
    setClip(null)
    setProblem(null)
    setElapsed(0)
    setStep('record')
    api.quota(deviceId()).then(setQuota).catch(() => undefined)
  }

  const seconds = Math.min(CLIP_SECONDS, Math.floor(elapsed / 1000))
  const progress = Math.min(1, elapsed / CAPTURE_MS)
  const ring = 2 * Math.PI * 96
  const blocked = quota !== null && quota.remaining === 0
  const stepIndex = { record: 0, place: 1, sending: 2, done: 2 }[step]
  const size = point ? cellSizeMetres(point) : null

  return (
    <div>
      <div className="steps" aria-hidden="true">
        {[0, 1, 2].map((index) => (
          <span key={index} data-on={index <= stepIndex} />
        ))}
      </div>

      {problem && step !== 'sending' && (
        <div className={problem.kind === 'speech' ? 'card banner' : 'card banner banner--plain'} role="alert" data-testid={`problem-${problem.kind}`} style={{ marginBottom: 16 }}>
          {problem.kind === 'speech' && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src="/art/empty/hush.png" alt="" width={96} height={62} />
          )}
          <div>
            <b>{problem.title}</b>
            <p>{problem.text}</p>
          </div>
        </div>
      )}

      {step === 'record' && (
        <div className="stack">
          <section className="card recorder" aria-label="Recorder">
            <div className="dial">
              <svg className="dial__ring" viewBox="0 0 208 208" aria-hidden="true">
                <circle className="track" cx="104" cy="104" r="96" />
                <circle className="bar" cx="104" cy="104" r="96" strokeDasharray={ring} strokeDashoffset={ring * (1 - (clip ? 1 : progress))} />
              </svg>
              {recording ? (
                <button type="button" className="dial__button" data-state="recording" onClick={stopEarly} aria-label="Stop and discard">
                  <span className="dial__count" aria-live="off">
                    {CLIP_SECONDS - seconds}
                    <small>listening</small>
                  </span>
                </button>
              ) : (
                <button type="button" className="dial__button" onClick={begin} disabled={blocked} aria-label={clip ? 'Record again' : 'Start recording'} data-testid="record-button">
                  <MicIcon />
                </button>
              )}
            </div>
            <div className="meter" aria-hidden="true">
              {levels.map((level, index) => (
                <i key={index} style={{ height: `${4 + level * 40}px`, opacity: recording ? 0.85 : 0.18 }} />
              ))}
            </div>
            <p className="recorder__hint">
              {recording
                ? 'Hold still and let the place do the talking.'
                : clip
                  ? 'Got it. Have a listen, then choose where it goes.'
                  : 'Tap to record ten seconds of whatever is around you. Rain, birds, a tram, a kitchen.'}
            </p>
            {recording && (
              <button type="button" className="button button--quiet button--small" onClick={stopEarly}>
                <StopIcon />
                Cancel
              </button>
            )}
          </section>

          {clip && !recording && (
            <>
              <div className="card preview">
                <PlayButton src={clip.url} label="your recording" small />
                <div className="preview__text">
                  <b>Your ten seconds</b>
                  <span>Only this clip is sent. Nothing is recorded outside these ten seconds.</span>
                </div>
              </div>
              <button type="button" className="button button--accent button--block" onClick={() => setStep('place')} data-testid="to-place">
                Choose where it goes
                <ArrowIcon />
              </button>
            </>
          )}
          <p className="note" style={{ textAlign: 'center' }} data-testid="quota">
            {quota
              ? blocked
                ? `You have sent ${quota.limit} postcards in the last 24 hours.${quota.resets_at ? ` The next one opens up ${untilText(quota.resets_at)}.` : ''}`
                : `${quota.remaining} of ${quota.limit} postcards left today. Clips that are mostly speech are not posted.`
              : 'Clips that are mostly speech are not posted.'}
          </p>
        </div>
      )}

      {step === 'place' && (
        <div className="stack">
          <LocationPicker onChange={onPoint} />
          <div className="card place-row" aria-live="polite">
            <div>
              <b data-testid="place-name">{place ? (place.country_name ? `${place.place_name}, ${place.country_name}` : place.place_name) : 'Finding the nearest town'}</b>
              <span>{size ? `Pinned to a square about ${Math.round(size.width / 10) * 10} m wide. Your exact position stays on this device.` : 'Drag the map under the pin.'}</span>
            </div>
          </div>
          <div className="row">
            <button type="button" className="button button--quiet" onClick={() => setStep('record')}>
              Back
            </button>
            <button type="button" className="button button--accent" onClick={send} disabled={!point} data-testid="send">
              Send postcard
            </button>
          </div>
        </div>
      )}

      {step === 'sending' && (
        <div className="card working" role="status">
          <div className="spinner" />
          <div>
            <b style={{ fontSize: 18 }}>Making your postcard</b>
            <p className="note" style={{ marginTop: 4 }}>
              Listening for speech, naming the sounds, painting the picture.
            </p>
          </div>
        </div>
      )}

      {step === 'done' && card && (
        <div className="stack" data-testid="arrival">
          <div className="arrival">
            <PostcardImage card={card} size="full" eager />
          </div>
          <div className="card preview">
            <PlayButton src={card.audio_url} label={`ten seconds from ${card.place_name}`} small />
            <div className="preview__text">
              <b>{card.country_name ? `${card.place_name}, ${card.country_name}` : card.place_name}</b>
              <Tags card={card} />
            </div>
          </div>
          <div className="row">
            <Link href={`/?p=${card.id}`} className="button">
              See it on the map
            </Link>
            <button type="button" className="button button--quiet" onClick={() => void sharePostcard(card).then((result) => result && setToast(result))}>
              <ShareIcon />
              Share
            </button>
          </div>
          <button type="button" className="button button--quiet button--block" onClick={reset}>
            Record another
          </button>
        </div>
      )}

      {toast && (
        <div className="toast" role="status">
          {toast}
        </div>
      )}
    </div>
  )
}
