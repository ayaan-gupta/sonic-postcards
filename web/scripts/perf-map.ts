/**
 * Acceptance test: the map loads 5,000 pins in under 2 seconds using clustering.
 *
 *   make seed-pins && make start     (in one terminal)
 *   make perf                         (in another)
 *
 * Measures a cold page load in headless Chromium, several times, and splits
 * it into the parts that matter:
 *
 *   api       GET /api/pins over HTTP: query, transfer and JSON parse
 *   render    pins handed to MapLibre until the map is idle with clusters drawn
 *   total     navigation start until the clusters are on screen
 *
 * Headless Chromium has no GPU and rasterises WebGL in software, so `render`
 * here is slower than on a phone or a laptop. Exits non-zero over budget.
 */
import { BASE, launch } from './lib/browser'

const RUNS = Number(process.env.PERF_RUNS ?? 7)
const BUDGET_MS = 2000
const MIN_PINS = Number(process.env.PERF_MIN_PINS ?? 5000)

interface Sample {
  api: number
  render: number
  total: number
  pins: number
  symbols: number
  represented: number
  renderer: string
}

function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b)
  return sorted[Math.floor(sorted.length / 2)] ?? Number.NaN
}

async function main() {
  const browser = await launch()
  const samples: Sample[] = []
  for (let run = 0; run < RUNS + 1; run++) {
    // A fresh context each time: no HTTP cache, no warm workers.
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1 })
    await context.addInitScript(() => window.localStorage.setItem('sonic-postcards.welcomed', '1'))
    const page = await context.newPage()
    await page.goto(BASE, { waitUntil: 'commit' })
    await page.waitForFunction(() => performance.getEntriesByName('sonic:pins-rendered').length > 0, undefined, { timeout: 30_000 })
    const sample = await page.evaluate(() => {
      // No named helpers in here: the bundler would wrap them in a function the page does not have.
      const marks: Record<string, number> = {}
      for (const entry of performance.getEntriesByType('mark')) marks[entry.name] ??= entry.startTime
      const stats = (window as unknown as { __sonic: { total: number; symbols: number; represented: number } }).__sonic
      const gl = document.createElement('canvas').getContext('webgl')
      const info = gl?.getExtension('WEBGL_debug_renderer_info')
      return {
        api: marks['sonic:pins-received']! - marks['sonic:pins-requested']!,
        render: marks['sonic:pins-rendered']! - marks['sonic:pins-received']!,
        total: marks['sonic:pins-rendered']!,
        pins: stats.total,
        symbols: stats.symbols,
        represented: stats.represented,
        renderer: info && gl ? String(gl.getParameter(info.UNMASKED_RENDERER_WEBGL)) : 'unknown',
      }
    })
    await context.close()
    if (run === 0) continue // the first load warms the server's caches and is not counted
    samples.push(sample)
    console.log(`run ${run}: api ${sample.api.toFixed(0)} ms, render ${sample.render.toFixed(0)} ms, total ${sample.total.toFixed(0)} ms`)
  }
  await browser.close()

  const first = samples[0]!
  const total = median(samples.map((s) => s.total))
  const worst = Math.max(...samples.map((s) => s.total))
  console.log(`\n${first.pins} pins drawn as ${first.symbols} clusters and pins (standing for ${first.represented} postcards in view)`)
  console.log(`WebGL renderer: ${first.renderer}`)
  console.log(`median over ${samples.length} cold loads: api ${median(samples.map((s) => s.api)).toFixed(0)} ms, render ${median(samples.map((s) => s.render)).toFixed(0)} ms, total ${total.toFixed(0)} ms (worst ${worst.toFixed(0)} ms)`)
  const ok = first.pins >= MIN_PINS && worst < BUDGET_MS && first.symbols < first.pins / 10
  console.log(ok ? `PASS: under ${BUDGET_MS} ms on every run` : `FAIL: budget is ${BUDGET_MS} ms with at least ${MIN_PINS} pins, clustered`)
  process.exit(ok ? 0 : 1)
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
