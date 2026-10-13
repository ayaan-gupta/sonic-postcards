import { Suspense } from 'react'
import { MapScreen } from '@/components/MapScreen'

export default function Home() {
  return (
    <Suspense fallback={<main className="map-screen" />}>
      <MapScreen />
    </Suspense>
  )
}
