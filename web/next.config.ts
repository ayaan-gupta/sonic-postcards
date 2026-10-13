import type { NextConfig } from 'next'

const config: NextConfig = {
  reactStrictMode: true,
  devIndicators: false,
  // Postcard images come from the API already sized; nothing here needs the optimiser.
  images: { unoptimized: true },
  // The art route reads ../assets at request time, which the tracer cannot see.
  outputFileTracingIncludes: {
    '/art/[...path]': ['../assets/generated/**', '../assets/interim/**'],
  },
}

export default config
