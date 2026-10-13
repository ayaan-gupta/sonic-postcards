# Notes for the README

Plain facts for whoever writes the README. Every number here was measured in the build session on the M5 Pro, with the command given next to it.

## Quickstart

- One command from a clean clone: `make dev`, then open http://localhost:4106
- Needs: Docker (plain `docker build` and `docker run`, no compose), Python 3.12, Node 22. Nothing else is installed on the host: FFmpeg comes inside the PyAV wheel, the audio model is a 16 MB file in the repo.
- What `make dev` does: builds a Postgres 16 image with PostGIS 3.6 and pgvector 0.8.7 (`db/Dockerfile`, 15 s once the base image is pulled), starts it, creates `api/.venv`, runs `npm ci`, applies migrations, seeds 42 demo postcards (about 9 s, first run only), then starts the API and the web app with hot reload.
- Fresh-clone check: `git clone` into a temp directory, `make dev` against a new empty database. Healthy after 37 s with warm pip and npm caches. In that clone `make test` gave 70 passed and 17 passed, and `make e2e` passed all 7 checks.
- Why not `docker compose up`: this machine runs colima with no compose plugin and no buildx (`docker compose` is "unknown command"), so a compose file could not have been tested. There is none in the repo.
- Ports: web 4106, API 8106, Postgres 5506 (host side). Override with `WEB_PORT`, `API_PORT`, `DB_PORT`.
- Other commands: `make start` (production build), `make test`, `make lint`, `make e2e`, `make seed-pins`, `make clear-pins`, `make perf`, `make fetch-real`, `make eval`, `make interim`, `make shots`, `make demo`, `make db-stop`. `make help` lists them.

## Environment variables (all optional, defaults in `.env.example`)

| Variable | Default | What it does |
|---|---|---|
| `WEB_PORT`, `API_PORT`, `DB_PORT` | 4106, 8106, 5506 | ports |
| `DATABASE_URL` | `postgresql://sonic:sonic@127.0.0.1:5506/sonic` | Postgres with PostGIS and pgvector; the database is created if missing |
| `API_URL` | `http://127.0.0.1:8106` | where the web server proxies `/api/*`, read at runtime |
| `NEXT_PUBLIC_MAP_STYLE` | `auto` | `auto` tries OpenFreeMap then falls back to the bundled basemap, `offline` never uses the network, or any MapLibre style URL. Baked in at build |
| `STORAGE_BACKEND`, `STORAGE_DIR` | `local`, `./storage` | clip and image storage. `s3` plus `S3_BUCKET`, `S3_ENDPOINT_URL`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_PUBLIC_BASE_URL` needs `pip install boto3` |
| `ASSETS_DIR` | `./assets` | design-time art |
| `SPEECH_THRESHOLD` | `0.6` | clips above this speech probability are refused |
| `MIN_CLIP_SECONDS`, `MAX_UPLOAD_BYTES` | `8`, `8000000` | upload limits |
| `GEOCODER` | `offline` | `offline` (bundled GeoNames) or `nominatim` |
| `WEATHER` | `none` | `none` or `open-meteo` |
| `IMAGE_PROVIDER` | `procedural` | `procedural` or `openai`, with `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `IMAGE_MODEL` |
| `DAILY_POSTCARD_LIMIT`, `REPORT_HIDE_THRESHOLD` | `10`, `3` | moderation |
| `ADMIN_TOKEN` | empty | enables the admin endpoints; empty means they answer 503 |
| `DEVICE_SALT` | `change-me-in-production` | salt for hashing device ids |
| `MAX_PINS` | `8000` | above this many postcards in view the database groups pins on a grid |
| `SEED_ON_START` | `true` | seed demo postcards when the table is empty |

## What each milestone delivered

- **M1 record, upload, store, play back, map pin.** Browser recorder (MediaRecorder, 10 s, voice processing switched off), `POST /api/postcards`, PyAV decode of WebM/Opus and MP4/AAC, trim and level, MP3 storage behind a `BlobStore` interface, range-request playback, PostGIS point, `GET /api/pins`, MapLibre map with clustering. Tests: `api/tests/test_m1_clip_and_pin.py` (9), `api/tests/test_privacy_grid.py` (15).
- **M2 tagging, speech rejection, embeddings.** YAMNet through LiteRT, 20 motifs from 353 AudioSet classes, speech probability, 1,024-d embedding in pgvector. Tests: `api/tests/test_m2_tagging.py` (20 with parameters).
- **M3 postcard and share image.** Prompt builder, image provider adapter, procedural gouache painter (6 settings, 20 motifs, 4 palettes), template overlay with stamp, postmark and caption, 1200x840 PNG plus a 600x420 WebP, Web Share and download. Tests: `api/tests/test_m3_postcard.py` (10).
- **M4 nearby, similar, moderation, rate limits.** `GET /api/nearby` (radius), `GET /api/postcards/{id}/similar` (cosine, optional radius), report button with auto-hide at 3, 10 per device per rolling 24 h, admin delete, restore and review. Tests: `api/tests/test_m4_feed_search_moderation.py` (9).
- Also: `api/tests/test_perf_and_seed.py` (3), `api/tests/test_outside_services.py` (4), `web/tests/*.test.ts` (17), `web/scripts/e2e.ts` (7 browser checks).
- Totals: 70 pytest tests against a real Postgres and the real model, 17 vitest tests, all passing. `ruff` and `mypy --strict` clean, `tsc` strict clean.

## Acceptance tests

| PRD acceptance test | Result | Measured | Where |
|---|---|---|---|
| A clip of mostly speech is rejected with a clear message | **met** | Real speech from macOS `say`, real model, real endpoint. Speech probability 0.998 (Opus/WebM monologue), 0.999 (AAC/MP4 chat), 0.817 (speech over rain); all refused with HTTP 422 and a message that says what happened, why, and what to do. Rain with one "hello there" scored 0.021 and was accepted. Also checked in a real browser with the speech played into the microphone. | `api/tests/test_m2_tagging.py::test_acceptance_mostly_speech_is_rejected_with_a_clear_message`, `make e2e` |
| Stored coordinates never contain more precision than the rounding rule, verified in the database | **met** | Uploads with 6 and 7 decimal places; afterwards Postgres itself finds 0 rows off the grid, the sent digits appear nowhere in the stored rows, and a direct `INSERT` of an off-grid value fails with a CHECK violation (6 cases). The point column is generated and cannot be written. | `api/tests/test_privacy_grid.py` |
| "Sounds like this" on a rain clip returns rain clips in its top 5 on the fixture set | **met on synthetic data, and met on real data** | Synthetic fixture set (48 clips, 6 rain): all 6 rain queries return 5 of 5 rain. Real ESC-50 subset (96 clips, 8 rain): 8 of 8 rain queries have rain in the top 5, on average 4.5 of the 5 are rain, worst query 1 of 5. Across all 12 classes 3.62 of 5 share the query's class (chance is 0.37). Weakest classes: wind 1.62, engine 2.0, crickets 2.38. | `api/tests/test_m4_feed_search_moderation.py::test_acceptance_sounds_like_this_on_rain_returns_rain_in_the_top_five`; `make fetch-real && make eval`, results in `docs/eval-esc50.json` |
| Map loads 5,000 pins in under 2 seconds using clustering | **met** | 5,042 pins. API alone: median 36 ms in process, 781 KB of GeoJSON (89 KB gzipped). Browser, cold load of the production build, 7 runs, headless Chromium with software GL (SwiftShader): bundled basemap median 1,083 ms, worst 1,116 ms (fetch 187 ms, cluster and draw 389 ms); OpenFreeMap basemap over the network median 1,559 ms, worst 1,935 ms. The 5,042 pins are drawn as about 50 symbols. | `api/tests/test_perf_and_seed.py::test_acceptance_api_serves_5000_pins_well_inside_the_budget`; `make seed-pins && make start`, then `make perf` |

Notes on honesty for that table:
- "Real speech" is synthetic voices from `say` (Samantha, Daniel, Karen). No human recordings were used.
- ESC-50 clips are 5 s long and are played twice to fill 10 s. 96 clips is a small set. The audio is CC BY-NC, is not in the repo, and is fetched by `scripts/fetch_esc50.py`.
- The 2 s figure with the online basemap depends on a third party's tile server and was 65 ms inside the limit on its worst run.

## Interesting problems

1. **A "500 m" grid is not 500 m in Oslo.** First version rounded both coordinates to 0.005 degrees. That is 556 m of latitude everywhere but only 278 m of longitude at 60 degrees north, so the privacy cell halves exactly where it should not. The longitude step now doubles in bands (5, 10, 20, 40, 80, 160, 320 millidegrees, switching where 1/cos(lat) crosses odd powers of the square root of two), which keeps every cell between 393 m and 786 m wide. Coordinates are stored as integer millidegrees so the rule is exact in Python, TypeScript and a Postgres CHECK, and the PostGIS point is a generated column. The band list stops at 320 because 640 does not divide 360,000 and the grid has to close at the antimeridian. A shared file of 253 vectors is checked by both test suites.
2. **Synthesising sounds for a model that has only heard real ones.** With no dataset on the machine, the fixtures are noise and sine waves, tagged by the real YAMNet. My first "wind" (a resonant band of noise sweeping over a rumble) came back as Vehicle 0.36, so it is now the traffic fixture. My second wind came back as Ocean 0.90 and is now the waves fixture. Wind finally worked as noise below 250 Hz with a 20 Hz flutter (Wind 0.70): what the model knows as wind is a microphone being buffeted. Rain sits on a ridge between Waterfall (too much hiss) and Fire/Fireworks (too many droplets); the committed version is still tagged "Running water" first and "Rain" second. A train never worked (Music, then Rain) and was dropped. Four attempts at bells still read as Music with Bell at 0.13.
3. **Map text without a font server.** MapLibre sets text from glyph files fetched over HTTP, which breaks the "works with no network" rule. Cluster counts and the offline city labels are instead drawn on a canvas in the system font and handed to the map as images when it raises `styleimagemissing`. A side effect showed up in the 5,000 pin screenshot: two bubbles looked corrupted. It was not a rendering bug. Cluster centres drift as points merge, so two clusters had landed almost on top of each other and were both drawn. Collision detection with a sort key on the count fixed it.
4. **A globe's outlines on a flat map.** The bundled basemap uses Natural Earth via `world-atlas`, which is made for spherical projection. Eurasia's ring steps from longitude 179.9 to -179.9 (Chukotka) and Antarctica's ring never returns to its start, so MapLibre drew cream streaks across the Atlantic. `web/src/lib/planar.ts` unwraps the jumps and closes circumpolar rings along the pole.
5. **A WAV file as the microphone.** Chromium can feed a file into `getUserMedia`, so `make e2e` runs the real recorder, the real upload and the real model in a headless browser. It found two bugs that no unit test would: the progress ring SVG sat on top of the record button and swallowed every tap, and a GPS fix that arrived before the map had loaded was silently dropped.
6. **Voice processing erases the subject.** Browsers apply echo cancellation, noise suppression and automatic gain to microphone audio by default, which is exactly the rain. All three are switched off in `web/src/lib/recorder.ts`. Related: the 16 kHz copy for the model lost up to 3 dB on hissy clips after the low-pass, so it is levelled a second time.

## Surprises and things I got wrong first

- `docker compose` does not exist on this machine, despite the brief. Found in the first five minutes.
- Next.js rewrites are frozen at build time, so the API proxy had to become middleware that reads `API_URL` at runtime.
- pgvector's psycopg adapter returns its own `Vector` type, which `np.asarray` cannot convert. Everything goes through `app.db.as_array`.
- The pool's `configure` hook must leave the connection idle; `register_vector` opens a transaction.
- `printable()` (dropping characters the caption font cannot draw) first checked for an empty glyph box. Missing glyphs are not empty, they are the "not defined" box, so the check now compares against a glyph that is certainly missing.
- My own rolling-window test expected 10 uploads still counted after 24 h 2 min. Three had aged out; the code was right and the test was wrong.
- Painting first gave all three ground slots to the main motif, so a "market, music, bells" postcard had no guitar. Slots are now dealt one per motif before extras.
- Playwright cannot see multipart bodies in Chromium, so the end-to-end check reads the form fields inside the page instead.
- `tsx` wraps named arrow functions in a `__name` helper that does not exist inside `page.evaluate`.

## Limitations

- The demo postcards on a clean clone are synthetic sound, and their tags are whatever YAMNet makes of it. They are marked "Sample" in the UI. The 5,000 pins from `make seed-pins` reuse those clips, so "sounds like this" on them returns near-duplicates.
- The speech check is one number per clip. Five seconds of clear speech in ten scores about 0.5 and is accepted. It has not been tested on human recordings, other languages, or crowd babble.
- The rate limit keys on a random id in localStorage. Clearing storage resets it. There is no IP limit.
- The built-in painter is a rule-based illustrator, not a model: six settings and twenty motifs. Two postcards with the same motifs and time of day look like siblings.
- The OpenAI image provider and the S3 store have only been run against mocks. Nominatim and Open-Meteo were each called once to record a fixture and are otherwise tested against those recordings.
- The bundled basemap has coasts, borders and 260 city labels but no streets, so choosing a 500 m cell with no network is guesswork. The default map needs OpenFreeMap to be reachable.
- No real phone was used. Safari's MP4 path is tested with an AAC file encoded by PyAV, not a recording made by Safari. The microphone needs HTTPS anywhere other than localhost.
- The service worker is registered only in production builds and has no automated test.
- Moderation has endpoints and no admin screen.
- Filtered similarity search relies on pgvector's iterative HNSW scan; recall at scale was not measured.
- Each postcard PNG is about 1.4 MB because paper grain does not compress.
- The CI workflow has not run, since nothing was pushed.
- A clean clone still needs the network once, for pip, npm and the Postgres base image.

## Next three ideas

1. Search by description ("rain on a tin roof") with CLAP embeddings next to the YAMNet ones.
2. Mute the frames that contain speech instead of refusing the whole clip, so a street recording with one passer-by survives.
3. A page per grid cell: how the same 500 m square sounds at dawn, at night, in January.

## Real and stand-in

| Part | What runs by default | Real alternative |
|---|---|---|
| Audio tagging, speech detection, embeddings | real: YAMNet (Apache 2.0) on LiteRT, chosen over PANNs because it is a 16 MB file and a 13 MB wheel with no PyTorch | none needed |
| Database | real: Postgres 16, PostGIS, pgvector in Docker | |
| Audio decode and encode | real: PyAV with its bundled FFmpeg | |
| Recording | real: MediaRecorder in the browser | |
| Postcard art | stand-in: built-in procedural painter | `IMAGE_PROVIDER=openai`, untested against the live API |
| Stamp, postmark, caption | real: drawn by the template in code, always | |
| Place names | stand-in: nearest city from a bundled GeoNames table (34,160 places, CC BY 4.0) | `GEOCODER=nominatim` |
| Weather | stand-in: none | `WEATHER=open-meteo` |
| Object storage | stand-in: local directory | `STORAGE_BACKEND=s3`, untested against a real bucket |
| Basemap | real when online: OpenFreeMap, recoloured; stand-in when not: bundled Natural Earth outlines | any style URL |
| Demo audio | stand-in: synthesised in `api/app/fixtures/synth.py` | real ESC-50 clips after `make fetch-real` |
| Design-time art (30 images) | stand-in: code-drawn files in `assets/interim` | requested in `assets/prompts.md`, none delivered |

## Files in `docs/`

- `demo.gif`: 390x760, 99 frames, 0.56 MB. The clustered world map, a postcard opened and played, ten seconds recorded through the real recorder (a synthetic waves clip as the microphone), the location step, the postcard arriving, and the new pin on the map. Recorded with 5,000 synthetic pins seeded.
- `map-desktop.png`: the map as a clean clone shows it, 42 demo postcards.
- `map-5000-pins.png`: the same map with 5,042 pins, clustered.
- `map-selected-desktop.png`, `map-selected-phone.png`: a pin selected, with the postcard sheet.
- `postcard-page.png`: a postcard page with "sounds like this", the model's labels and the pin's precision.
- `record-listening.png`, `record-place.png`, `record-arrival.png`: the three steps of sending a postcard, on a phone-sized screen. `record-place.png` shows the privacy square.
- `nearby-phone.png`: the nearby feed.
- `welcome-phone.png`: the first-visit sheet with the three interim illustrations.
- `about-phone.png`: the About page.
- `eval-esc50.json`: per-class results of `make eval` on the real clips.

All screenshots and the GIF use the default OpenFreeMap basemap. The 1,083 ms figure above is with the bundled basemap, the 1,559 ms figure with the one in the screenshots.
