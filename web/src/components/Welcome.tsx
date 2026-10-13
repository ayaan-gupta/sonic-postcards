'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'

const KEY = 'sonic-postcards.welcomed'

const STEPS = [
  { art: 'listen', title: 'Listen for ten seconds', text: 'Rain on a roof, a market, the sea. Record wherever you are.' },
  { art: 'place', title: 'Pin it, roughly', text: 'Your pin lands on a 500 m square, never on your exact spot.' },
  { art: 'send', title: 'Get a postcard back', text: 'The sound is labelled, painted and added to the map.' },
]

/** Shown once, on the first visit. */
export function Welcome() {
  const [open, setOpen] = useState(false)
  useEffect(() => {
    try {
      if (!window.localStorage.getItem(KEY) && !new URLSearchParams(window.location.search).has('p')) setOpen(true)
    } catch {
      // No storage, no welcome.
    }
  }, [])
  if (!open) return null
  const close = () => {
    try {
      window.localStorage.setItem(KEY, '1')
    } catch {
      // Ignore.
    }
    setOpen(false)
  }
  return (
    <div className="scrim" role="dialog" aria-modal="true" aria-labelledby="welcome-title" onClick={close}>
      <div className="welcome" onClick={(event) => event.stopPropagation()}>
        <h2 id="welcome-title" className="title" style={{ fontSize: 25 }}>
          How places sound
        </h2>
        <div className="welcome__steps">
          {STEPS.map((step) => (
            <div key={step.art} className="welcome__step">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={`/art/onboarding/${step.art}.png`} alt="" width={76} height={57} />
              <div>
                <b>{step.title}</b>
                <span>{step.text}</span>
              </div>
            </div>
          ))}
        </div>
        <div className="row">
          <button type="button" className="button button--quiet" onClick={close}>
            Explore the map
          </button>
          <Link href="/record" className="button button--accent" onClick={close}>
            Record
          </Link>
        </div>
      </div>
    </div>
  )
}
