/**
 * Serves design-time art. A delivered file in assets/generated wins over the
 * code-drawn one at the same relative path in assets/interim, checked per
 * request, so dropping a file in is all it takes.
 */
import { NextResponse } from 'next/server'
import { resolveAsset } from '@/lib/assets'

export const dynamic = 'force-dynamic'

export async function GET(_: Request, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params
  const found = await resolveAsset(path.join('/'))
  if (!found) return new NextResponse('Not found', { status: 404 })
  return new NextResponse(new Uint8Array(found.bytes), {
    headers: {
      'Content-Type': found.contentType,
      'Cache-Control': 'public, max-age=300',
      'X-Art-Source': found.source,
    },
  })
}
