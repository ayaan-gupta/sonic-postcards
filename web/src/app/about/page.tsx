import Link from 'next/link'
import { Brand } from '@/components/Brand'

export const metadata = { title: 'About' }

const STEPS = [
  {
    art: 'listen',
    title: 'Listen for ten seconds',
    text: 'Open the recorder and hold still. The microphone runs for ten seconds and stops by itself. Phone-call processing is switched off, so rain stays rain.',
  },
  {
    art: 'place',
    title: 'Pin it, roughly',
    text: 'Use your location or drag the map. Either way the pin snaps to a square about 500 m wide before it leaves your device, and that square is all the server ever stores.',
  },
  {
    art: 'send',
    title: 'Get a postcard back',
    text: 'A model names what it heard, the three strongest sounds and the time of day decide the painting, and the postcard joins the map for anyone to play.',
  },
]

export default function AboutPage() {
  return (
    <main className="page">
      <header className="page__header">
        <Brand />
      </header>
      <h1 className="title">How places sound</h1>
      <p className="lede">Sonic Postcards is a shared map of ten-second recordings. Each one becomes a small painting you can send to someone.</p>

      <div className="how">
        {STEPS.map((step) => (
          <section key={step.art} className="card how__step">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={`/art/onboarding/${step.art}.png`} alt="" width={148} height={111} />
            <div>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </div>
          </section>
        ))}
      </div>

      <h2 className="section-title">Privacy</h2>
      <div className="prose">
        <p>
          <b>Voices are kept out.</b> Every clip is checked for speech before anything is saved. If more than 60% of it is someone talking, it is
          refused and nothing is stored.
        </p>
        <p>
          <b>Locations are blurred.</b> Coordinates are stored as whole steps on a grid. The database itself rejects anything more precise, so a
          postcard cannot point at a doorstep.
        </p>
        <p>
          <b>No accounts.</b> A random id in this browser is used to cap postcards at ten a day. The server keeps a salted hash of it and nothing
          else about you.
        </p>
        <p>
          <b>Anyone can flag a postcard.</b> Three reports hide it until someone has reviewed it.
        </p>
      </div>

      <h2 className="section-title">Credits</h2>
      <div className="prose">
        <p>
          Sound labels and embeddings come from YAMNet (Google, Apache 2.0). Place names come from{' '}
          <a href="https://www.geonames.org" target="_blank" rel="noreferrer">
            GeoNames
          </a>{' '}
          (CC BY 4.0). Maps use{' '}
          <a href="https://openfreemap.org" target="_blank" rel="noreferrer">
            OpenFreeMap
          </a>{' '}
          with data from{' '}
          <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">
            OpenStreetMap
          </a>{' '}
          contributors, and Natural Earth outlines when offline.
        </p>
      </div>

      <div style={{ marginTop: 28 }}>
        <Link href="/record" className="button button--accent">
          Record a postcard
        </Link>
      </div>
    </main>
  )
}
