import { existsSync, readdirSync } from 'node:fs'
import { homedir } from 'node:os'
import path from 'node:path'
import { chromium, type Browser, type LaunchOptions } from 'playwright'

/** Reuses whatever Chromium Playwright has already downloaded, any revision. */
export function cachedChromium(): string | undefined {
  const caches = [path.join(homedir(), 'Library', 'Caches', 'ms-playwright'), path.join(homedir(), '.cache', 'ms-playwright')]
  for (const cache of caches) {
    if (!existsSync(cache)) continue
    const builds = readdirSync(cache)
      .filter((dir) => dir.startsWith('chromium_headless_shell-'))
      .sort()
      .reverse()
    for (const dir of builds) {
      for (const arch of ['chrome-headless-shell-mac-arm64', 'chrome-mac', 'chrome-headless-shell-mac-x64', 'chrome-linux', 'chrome-headless-shell-linux64']) {
        for (const name of ['chrome-headless-shell', 'headless_shell']) {
          const bin = path.join(cache, dir, arch, name)
          if (existsSync(bin)) return bin
        }
      }
    }
  }
  return undefined
}

export async function launch(options: LaunchOptions = {}): Promise<Browser> {
  return chromium.launch({ executablePath: cachedChromium(), ...options })
}

export const BASE = process.env.WEB_URL ?? 'http://localhost:4106'
