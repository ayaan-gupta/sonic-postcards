/**
 * End-to-end check in a real browser, with a WAV file as the microphone.
 *
 *   make e2e        (needs the app running: make dev)
 *
 * 1. Records ten seconds of synthetic birdsong through MediaRecorder, picks a
 *    location with the geolocation API, sends it, and expects a postcard.
 * 2. Does the same with real speech and expects the clear refusal.
 */
import path from 'node:path'
import type { Page } from 'playwright'
import { BASE, launch } from './lib/browser'

const FIXTURES = path.resolve(process.cwd(), process.env.FIXTURE_DIR ?? '../.run/fixtures')
let failures = 0

function check(name: string, ok: boolean, detail = '') {
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${name}${detail ? `  (${detail})` : ''}`)
  if (!ok) failures += 1
}

export async function withMicrophone<T>(wav: string, run: (page: Page) => Promise<T>, viewport = { width: 390, height: 844 }): Promise<T> {
  const browser = await launch({
    args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream', `--use-file-for-fake-audio-capture=${path.join(FIXTURES, wav)}`],
  })
  try {
    const context = await browser.newContext({
      viewport,
      deviceScaleFactor: 1,
      permissions: ['microphone', 'geolocation'],
      geolocation: { latitude: 38.722252, longitude: -9.139337 }, // Lisbon, to six decimals
    })
    await context.addInitScript(() => window.localStorage.setItem('sonic-postcards.welcomed', '1'))
    const page = await context.newPage()
    return await run(page)
  } finally {
    await browser.close()
  }
}

export async function recordAndPlace(page: Page) {
  await page.goto(`${BASE}/record`, { waitUntil: 'networkidle' })
  await page.getByTestId('record-button').click()
  await page.getByTestId('to-place').waitFor({ timeout: 20_000 })
  await page.getByTestId('to-place').click()
  await page.getByRole('button', { name: 'Use my location' }).click()
  await page.getByTestId('place-name').filter({ hasText: 'Lisbon' }).waitFor({ timeout: 15_000 })
}

async function main() {
  await withMicrophone('birds.wav', async (page) => {
    // Chromium does not expose multipart bodies to the test, so note the form fields as they leave the page.
    await page.addInitScript(() => {
      const original = window.fetch.bind(window)
      window.fetch = (input, init) => {
        if (init?.body instanceof FormData) (window as unknown as { __upload?: unknown }).__upload = { lat: init.body.get('lat'), lon: init.body.get('lon') }
        return original(input, init)
      }
    })
    await recordAndPlace(page)
    check('place name comes back for the snapped point', (await page.getByTestId('place-name').innerText()).includes('Lisbon, Portugal'))
    await page.getByTestId('send').click()
    await page.getByTestId('arrival').waitFor({ timeout: 30_000 })
    const sent = await page.evaluate(() => (window as unknown as { __upload?: { lat: string; lon: string } }).__upload)
    check('upload carries the snapped location, not the GPS fix', sent?.lat === '38.720' && sent?.lon === '-9.140', JSON.stringify(sent))
    const tags = await page.locator('[data-testid=arrival] .pill').allInnerTexts()
    check('the postcard is tagged as birdsong', tags.includes('Birdsong'), tags.join(', '))
    const image = page.locator('[data-testid=arrival] .postcard img')
    await image.evaluate((img: HTMLImageElement) => img.decode())
    check('the postcard image loaded', (await image.evaluate((img: HTMLImageElement) => img.naturalWidth)) === 1200)
    await page.getByRole('link', { name: 'See it on the map' }).click()
    await page.locator('.sheet .sheet__place').filter({ hasText: 'Lisbon' }).waitFor({ timeout: 15_000 })
    check('the new pin opens on the map', true)
    await page.locator('.sheet .play').click()
    await page.waitForFunction(() => document.querySelector('.sheet .play')?.getAttribute('data-playing') === 'true', undefined, { timeout: 10_000 }).catch(() => undefined)
    check('the clip plays back', (await page.locator('.sheet .play').getAttribute('data-playing')) === 'true')
  })

  await withMicrophone('speech.wav', async (page) => {
    await recordAndPlace(page)
    await page.getByTestId('send').click()
    const banner = page.getByTestId('problem-speech')
    await banner.waitFor({ timeout: 30_000 })
    const text = await banner.innerText()
    check('speech is refused with a clear message', text.includes('mostly speech') && text.includes('not posted'), text.replace(/\s+/g, ' ').slice(0, 90))
  })

  console.log(failures === 0 ? '\nend-to-end: all checks passed' : `\nend-to-end: ${failures} check(s) failed`)
  process.exit(failures === 0 ? 0 : 1)
}

if (process.argv[1]?.endsWith('e2e.ts')) {
  main().catch((error) => {
    console.error(error)
    process.exit(1)
  })
}
