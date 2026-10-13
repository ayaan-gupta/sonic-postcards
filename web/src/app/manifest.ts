import type { MetadataRoute } from 'next'

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'Sonic Postcards',
    short_name: 'Postcards',
    description: 'Record ten seconds of where you are and pin it to a shared world map as a painted postcard.',
    start_url: '/',
    display: 'standalone',
    background_color: '#f7f3ea',
    theme_color: '#f7f3ea',
    icons: [
      { src: '/art/brand/icon-192.png', sizes: '192x192', type: 'image/png' },
      { src: '/art/brand/icon-512.png', sizes: '512x512', type: 'image/png' },
      { src: '/art/brand/icon-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    ],
  }
}
