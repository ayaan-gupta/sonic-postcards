# Sonic Postcards: working notes for Claude Code

Project 6 of 11 from "Project PRDs: 11 Builds for Claude Code". Slug `sonic-postcards`.

## Commands

- `make dev` runs everything with hot reload: web on 4106, API on 8106, Postgres (Docker) on 5506. Ports 3000, 8000 and 5432 are taken on this machine.
- `make start` runs the production build, which is what `make perf` measures
- `make test` runs pytest (real Postgres, real YAMNet), tsc and vitest. `make lint` runs ruff, mypy and tsc
- `make e2e` drives the real recorder in headless Chromium with a WAV file as the microphone (needs the app running)
- `make seed-pins` / `make clear-pins` add and remove 5,000 synthetic pins; `make perf` measures the map load
- `make fetch-real && make eval` downloads 96 ESC-50 clips (CC BY-NC, git-ignored) and runs "sounds like this" on them
- `make interim` redraws `assets/interim` and rewrites `assets/prompts.md`
- `make shots` and `make demo` write the images in `docs/`

There is no `docker compose` on this machine (colima without the plugin, legacy builder only), which is why the one command is `make dev`.

## Shared conventions

- **Repo:** one repo per project, named by its slug, MIT license, README.md with a demo GIF and a one-command quickstart.
- **Default stack:** TypeScript with Vite or Next.js for web, Python (FastAPI) for ML and audio services, SQLite for local data and Postgres for hosted. This PRD overrides it: Next.js PWA, MapLibre GL, FastAPI, Postgres with PostGIS and pgvector, object storage for clips.
- **Creative direction:** these are portfolio pieces, so every project should feel designed. Style bible here: vintage travel postcard, gouache look, a stamp in the corner and a postmark with the date and city.
- **Image requests:** Claude Code does not generate images. Every design-time image is requested with a numbered asset ID, the exact prompt, size, transparency and format, the save path under `/assets/generated`, and what it is for, logged in `/assets/prompts.md` with a status.
- **Runtime image generation:** the app generates one image per postcard, so that is an adapter (`api/app/postcard/provider.py`) with a built-in painter as the default.
- **Quality bar:** typed code, at least 3 automated tests per milestone, no secrets in git (`.env.example` only), and an ARCHITECTURE.md of at most one page.
- **Definition of done:** runs from a clean clone with one command, passes all acceptance tests, recorded demo, README lists limitations and the next three ideas.

## How the image rule was applied here

Thirty design-time images (20 stamps, the blank postmark, logo and icons, three onboarding pictures, two empty states) are requested in `assets/prompts.md` without waiting for delivery. Code-drawn versions in `assets/interim` stand in, painted with the same gouache engine as the postcards. A delivered file in `assets/generated` at the same relative path takes over, per file, in both the API (`app/postcard/art.py`) and the web app (`/art/...`).

Every letter on a postcard is set by `app/postcard/overlay.py` from stored facts. No image model is ever asked to spell.

## Writing

No em dashes anywhere, in docs, comments or UI copy, and no en dashes in prose. README prose should sound like a person: varied sentences, no rule-of-three lists, no "it's not X, it's Y" constructions.

## Things that will bite

- Coordinates exist only as integer millidegrees on the privacy grid (`lat_md`, `lon_md`). `geom` is generated from them. Never add a float coordinate column, and keep `api/app/geo/grid.py`, `web/src/lib/grid.ts` and `sp_lon_step_md` in the first migration identical; `api/tests/fixtures/grid_vectors.json` is checked by both test suites.
- The synthetic sounds in `app/fixtures/synth.py` are named after what YAMNet hears in them. Changing one can change its tags; `test_tagger_names_each_synthetic_sound` will say so.
- `next.config` rewrites are frozen at build time, so `/api/*` is proxied by `web/src/middleware.ts`, which reads `API_URL` at runtime. `NEXT_PUBLIC_MAP_STYLE` is the opposite: it is baked in at build.
- MapLibre text needs a glyph server. Cluster counts and offline city labels are canvas images made in `web/src/lib/mapImages.ts` instead. Do not add `text-field` layers to the offline style.
- pgvector returns its own `Vector` type from psycopg; go through `app.db.as_array`.
- Tests truncate the `sonic_test` database, never `sonic`. Seed tests pass `real_dir` so fetched ESC-50 clips do not change their outcome.
- Background servers started with `nohup ... &` inside a tool call do not survive it here. Use the tool's own background mode.
