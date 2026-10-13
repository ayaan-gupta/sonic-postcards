import Link from 'next/link'
import { Brand } from '@/components/Brand'

export default function PostcardNotFound() {
  return (
    <main className="page">
      <header className="page__header">
        <Brand />
      </header>
      <div className="card empty">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/art/empty/quiet.png" alt="" width={560} height={360} />
        <b>This postcard is not here</b>
        <p>It may have been taken down, or the link is missing a letter.</p>
        <Link href="/" className="button">
          Back to the map
        </Link>
      </div>
    </main>
  )
}
