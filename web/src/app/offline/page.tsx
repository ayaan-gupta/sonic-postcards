import { Brand } from '@/components/Brand'

export const metadata = { title: 'Offline' }

export default function Offline() {
  return (
    <main className="page">
      <header className="page__header">
        <Brand />
      </header>
      <div className="card empty">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/art/empty/quiet.png" alt="" width={560} height={360} />
        <b>You are offline</b>
        <p>Postcards you have already opened still play. The map and new recordings need a connection.</p>
      </div>
    </main>
  )
}
