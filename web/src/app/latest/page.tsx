import Link from 'next/link'
import { Brand } from '@/components/Brand'
import { FeedItem } from '@/components/FeedItem'
import { serverApi } from '@/lib/server'
import type { Postcard } from '@/lib/types'

export const metadata = { title: 'Latest' }
export const dynamic = 'force-dynamic'

export default async function LatestPage() {
  let items: Postcard[] | null = null
  try {
    items = await serverApi().recent(30)
  } catch {
    items = null
  }
  return (
    <main className="page">
      <header className="page__header">
        <Brand />
      </header>
      <h1 className="title">Latest postcards</h1>
      <p className="lede">The most recent ten seconds from anywhere.</p>
      <div className="feed" style={{ marginTop: 22 }}>
        {items?.map((card) => <FeedItem key={card.id} card={card} />)}
      </div>
      {items === null && <p className="note" style={{ marginTop: 20 }}>The postcards could not be loaded. Is the API running?</p>}
      {items?.length === 0 && (
        <div className="card empty">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/art/empty/quiet.png" alt="" width={560} height={360} />
          <b>No postcards yet</b>
          <p>The map is waiting for its first sound.</p>
          <Link href="/record" className="button button--accent">
            Record the first
          </Link>
        </div>
      )}
    </main>
  )
}
