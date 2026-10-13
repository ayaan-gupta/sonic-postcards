/**
 * Screenshots for docs/, taken from the running app.
 *
 *   make shots
 */
import path from 'node:path'
import { BASE, launch } from './lib/browser'

const DOCS = path.resolve(process.cwd(), '..', 'docs')

async function main() {
  const cards = (await (await fetch(`${BASE}/api/postcards?limit=60`)).json()) as { items: Array<{ id: string; place_name: string }> }
  const lisbon = cards.items.find((card) => card.place_name === 'Lisbon') ?? cards.items[0]!
  const kyoto = cards.items.find((card) => card.place_name === 'Kyoto') ?? cards.items[0]!
  const browser = await launch()
  const shots: Array<[string, { width: number; height: number }, number, string, number]> = [
    ['map-desktop.png', { width: 1280, height: 800 }, 1, '/', 1800],
    ['map-selected-desktop.png', { width: 1280, height: 800 }, 1, `/?p=${lisbon.id}`, 2200],
    ['map-selected-phone.png', { width: 390, height: 844 }, 2, `/?p=${kyoto.id}`, 2200],
    ['postcard-page.png', { width: 1280, height: 900 }, 1, `/p/${lisbon.id}`, 1800],
    ['nearby-phone.png', { width: 390, height: 844 }, 2, '/nearby?lat=48.86&lon=2.35', 1800],
    ['about-phone.png', { width: 390, height: 844 }, 2, '/about', 1200],
  ]
  for (const [name, viewport, scale, route, wait] of shots) {
    const context = await browser.newContext({ viewport, deviceScaleFactor: scale })
    await context.addInitScript(() => window.localStorage.setItem('sonic-postcards.welcomed', '1'))
    const page = await context.newPage()
    await page.goto(BASE + route, { waitUntil: 'networkidle' })
    await page.waitForTimeout(wait)
    await page.screenshot({ path: path.join(DOCS, name) })
    console.log(name)
    await context.close()
  }
  // The welcome sheet, as a first-time visitor sees it.
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 })
  const page = await context.newPage()
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1500)
  await page.screenshot({ path: path.join(DOCS, 'welcome-phone.png') })
  console.log('welcome-phone.png')
  await browser.close()
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
