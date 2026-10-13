import { readFile } from 'node:fs/promises'
import path from 'node:path'

const TYPES: Record<string, string> = { '.png': 'image/png', '.webp': 'image/webp', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml' }

export function assetsDir(): string {
  return process.env.ASSETS_DIR ?? path.resolve(process.cwd(), '..', 'assets')
}

export interface FoundAsset {
  bytes: Buffer
  contentType: string
  source: 'generated' | 'interim'
}

/** Looks in generated/ first, then interim/. Rejects anything that is not a plain relative image path. */
export async function resolveAsset(relative: string, root: string = assetsDir()): Promise<FoundAsset | null> {
  if (!/^[a-z0-9][a-z0-9/_-]*\.(png|webp|jpg|svg)$/.test(relative) || relative.includes('..')) return null
  const contentType = TYPES[path.extname(relative)]
  if (!contentType) return null
  for (const source of ['generated', 'interim'] as const) {
    try {
      return { bytes: await readFile(path.join(root, source, relative)), contentType, source }
    } catch {
      // Try the next folder.
    }
  }
  return null
}
