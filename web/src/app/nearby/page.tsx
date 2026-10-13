import { Brand } from '@/components/Brand'
import { NearbyFeed } from '@/components/NearbyFeed'

export const metadata = { title: 'Nearby' }

export default function NearbyPage() {
  return (
    <main className="page">
      <header className="page__header">
        <Brand />
      </header>
      <h1 className="title">Nearby sounds</h1>
      <NearbyFeed />
    </main>
  )
}
