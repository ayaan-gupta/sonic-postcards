import { Brand } from '@/components/Brand'
import { RecordFlow } from '@/components/RecordFlow'

export const metadata = { title: 'Record' }

export default function RecordPage() {
  return (
    <main className="page">
      <header className="page__header">
        <Brand />
      </header>
      <h1 className="title">Send a postcard</h1>
      <p className="lede">Ten seconds of sound, a rough place, and a painting comes back.</p>
      <RecordFlow />
    </main>
  )
}
