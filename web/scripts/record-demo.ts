/**
 * Records docs/demo.gif and three stills by driving the real app in a headless
 * browser, with a WAV file standing in for the microphone.
 *
 *   make start        (in one terminal; `make seed-pins` first to show clustering)
 *   make demo         (in another)
 */
import { writeFileSync } from 'node:fs'
import path from 'node:path'
import type { Page } from 'playwright'
import sharp from 'sharp'
import { withMicrophone } from './e2e'
import { BASE } from './lib/browser'
import type { Frame } from './lib/gif'
import { encodeGif } from './lib/gif'

const WIDTH = 390
const HEIGHT = 760
const SCALE = 1 // lower this if the GIF grows past about 3 MB
const DOCS = path.resolve(process.cwd(), '..', 'docs')

async function main() {
  const frames: Frame[] = []
  const outW = Math.round(WIDTH * SCALE)
  const outH = Math.round(HEIGHT * SCALE)

  await withMicrophone(
    'waves.wav',
    async (page: Page) => {
      const shoot = async (delay: number) => {
        const png = await page.screenshot({ type: 'png' })
        const { data } = await sharp(png).resize(outW, outH).ensureAlpha().raw().toBuffer({ resolveWithObject: true })
        frames.push({ rgba: new Uint8Array(data), delay })
      }
      const hold = async (ms: number, every = 200) => {
        for (let t = 0; t < ms; t += every) {
          await shoot(every)
          await page.waitForTimeout(every)
        }
      }
      const still = (name: string) => page.screenshot({ path: path.join(DOCS, name) })

      // 1. The world, clustered.
      await page.goto(BASE, { waitUntil: 'networkidle' })
      await page.waitForFunction(() => performance.getEntriesByName('sonic:pins-rendered').length > 0)
      await hold(1400)

      // 2. Open one postcard and play it.
      const cards = (await (await fetch(`${BASE}/api/postcards?limit=60`)).json()) as { items: Array<{ id: string; place_name: string }> }
      const pick = cards.items.find((card) => card.place_name === 'Sydney') ?? cards.items[0]!
      await page.goto(`${BASE}/?p=${pick.id}`, { waitUntil: 'networkidle' })
      await page.locator('.sheet .sheet__place').waitFor()
      await hold(1400)
      await page.locator('.sheet .play').click()
      await hold(2400)
      await page.locator('.sheet .play').click()

      // 3. Record ten seconds.
      await page.getByRole('link', { name: 'Record a postcard' }).click()
      await page.getByTestId('record-button').waitFor()
      await hold(900)
      await page.getByTestId('record-button').click()
      await page.waitForTimeout(600)
      await still('record-listening.png')
      for (let i = 0; i < 20; i++) {
        await shoot(240)
        await page.waitForTimeout(470)
      }
      await page.getByTestId('to-place').waitFor({ timeout: 20_000 })
      await hold(800)

      // 4. Pin it, roughly.
      await page.getByTestId('to-place').click()
      await page.getByRole('button', { name: 'Use my location' }).click()
      await page.getByTestId('place-name').filter({ hasText: 'Lisbon' }).waitFor({ timeout: 15_000 })
      await page.waitForTimeout(900)
      await still('record-place.png')
      await hold(1800)

      // 5. The postcard comes back.
      await page.getByTestId('send').click()
      await hold(600)
      await page.getByTestId('arrival').waitFor({ timeout: 30_000 })
      await page.locator('[data-testid=arrival] .postcard img').evaluate((img: HTMLImageElement) => img.decode())
      await hold(700, 120)
      await still('record-arrival.png')
      await hold(2600)

      // 6. And it is on the map.
      await page.getByRole('link', { name: 'View on map' }).click()
      await page.locator('.sheet .sheet__place').filter({ hasText: 'Lisbon' }).waitFor({ timeout: 15_000 })
      await hold(2600)
    },
    { width: WIDTH, height: HEIGHT },
  )

  const gif = encodeGif(frames, outW, outH)
  const out = path.join(DOCS, 'demo.gif')
  writeFileSync(out, gif)
  console.log(`${frames.length} frames, ${outW}x${outH}, ${(gif.length / 1024 / 1024).toFixed(2)} MB -> ${out}`)
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
