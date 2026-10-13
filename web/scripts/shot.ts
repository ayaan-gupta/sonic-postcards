/**
 * One-off screenshots while working on the UI.
 *
 *   npx tsx scripts/shot.ts <out-dir> <path> [<path> ...]
 *
 * Writes <name>-phone.png and <name>-desktop.png for every path.
 */
import { mkdirSync } from 'node:fs'
import path from 'node:path'
import { BASE, launch } from './lib/browser'

async function main() {
  const [outDir, ...routes] = process.argv.slice(2)
  if (!outDir || routes.length === 0) throw new Error('usage: shot.ts <out-dir> <path> [...]')
  mkdirSync(outDir, { recursive: true })
  const browser = await launch()
  for (const [label, viewport, scale] of [
    ['phone', { width: 390, height: 844 }, 2],
    ['desktop', { width: 1280, height: 800 }, 1],
  ] as const) {
    const context = await browser.newContext({ viewport, deviceScaleFactor: scale })
    await context.addInitScript(() => window.localStorage.setItem('sonic-postcards.welcomed', '1'))
    const page = await context.newPage()
    page.on('console', (message) => message.type() === 'error' && console.log(`[console] ${message.text()}`))
    page.on('pageerror', (error) => console.log(`[pageerror] ${error.message}`))
    for (const route of routes) {
      await page.goto(BASE + route, { waitUntil: 'networkidle' })
      await page.waitForTimeout(Number(process.env.SHOT_WAIT ?? 1500))
      const name = (route.replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '') || 'home') + `-${label}.png`
      await page.screenshot({ path: path.join(outDir, name) })
      console.log(name)
    }
    await context.close()
  }
  await browser.close()
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
