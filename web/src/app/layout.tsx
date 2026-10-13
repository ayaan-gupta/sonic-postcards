import type { Metadata, Viewport } from 'next'
import type { ReactNode } from 'react'
import { ServiceWorker } from '@/components/ServiceWorker'
import { TabBar } from '@/components/TabBar'
import './globals.css'

export const metadata: Metadata = {
  title: { default: 'Sonic Postcards', template: '%s · Sonic Postcards' },
  description: 'Record ten seconds of where you are and pin it to a shared world map as a painted postcard.',
  applicationName: 'Sonic Postcards',
  appleWebApp: { capable: true, title: 'Sonic Postcards', statusBarStyle: 'default' },
  icons: { icon: '/art/brand/icon-192.png', apple: '/art/brand/icon-192.png' },
}

export const viewport: Viewport = {
  themeColor: '#f7f3ea',
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        {children}
        <TabBar />
        <ServiceWorker />
      </body>
    </html>
  )
}
