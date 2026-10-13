/**
 * Forwards /api/* to the FastAPI service. Done here instead of in
 * next.config rewrites because those are frozen at build time, and the API
 * address is only known when the server starts.
 */
import { NextResponse, type NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const target = process.env.API_URL ?? 'http://127.0.0.1:8106'
  return NextResponse.rewrite(new URL(request.nextUrl.pathname + request.nextUrl.search, target))
}

export const config = { matcher: ['/api/:path*'] }
