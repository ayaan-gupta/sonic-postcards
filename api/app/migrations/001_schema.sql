CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

-- Longitude step of the privacy grid, in millidegrees, for a latitude that is
-- already on the grid. Mirrors app/geo/grid.py and web/src/lib/grid.ts.
CREATE FUNCTION sp_lon_step_md(lat_md integer) RETURNS integer
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
  SELECT CASE
    WHEN abs(lat_md) >= 88734 THEN 320
    WHEN abs(lat_md) >= 87467 THEN 160
    WHEN abs(lat_md) >= 84929 THEN 80
    WHEN abs(lat_md) >= 79818 THEN 40
    WHEN abs(lat_md) >= 69295 THEN 20
    WHEN abs(lat_md) >= 45000 THEN 10
    ELSE 5
  END
$$;

CREATE TABLE postcards (
  id              text PRIMARY KEY,
  created_at      timestamptz NOT NULL DEFAULT now(),

  -- The only coordinates that exist. Integer millidegrees on the privacy
  -- grid; the PostGIS point is generated from them, so there is no column
  -- that could hold a more precise value.
  lat_md          integer NOT NULL,
  lon_md          integer NOT NULL,
  geom            geometry(Point, 4326) GENERATED ALWAYS AS (
                    ST_SetSRID(ST_MakePoint(lon_md / 1000.0, lat_md / 1000.0), 4326)
                  ) STORED,
  location_source text NOT NULL,

  place_name      text NOT NULL,
  country_code    text,
  country_name    text,
  local_date      date NOT NULL,
  local_hour      smallint NOT NULL,
  time_of_day     text NOT NULL,

  labels          jsonb NOT NULL,
  motifs          text[] NOT NULL,
  speech_prob     real NOT NULL,
  embedding       vector(1024) NOT NULL,
  weather         jsonb,

  clip_key        text NOT NULL,
  image_key       text,
  image_provider  text NOT NULL DEFAULT 'procedural',
  prompt          text NOT NULL DEFAULT '',

  device_hash     text NOT NULL,
  seeded          boolean NOT NULL DEFAULT false,
  hidden          boolean NOT NULL DEFAULT false,

  CONSTRAINT lat_on_privacy_grid CHECK (lat_md BETWEEN -90000 AND 90000 AND lat_md % 5 = 0),
  CONSTRAINT lon_in_range CHECK (lon_md >= -180000 AND lon_md < 180000),
  CONSTRAINT lon_on_privacy_grid CHECK (lon_md % sp_lon_step_md(lat_md) = 0),
  CONSTRAINT location_source_known CHECK (location_source IN ('gps', 'manual', 'seed')),
  CONSTRAINT local_hour_valid CHECK (local_hour BETWEEN 0 AND 23),
  CONSTRAINT time_of_day_known CHECK (time_of_day IN ('dawn', 'day', 'dusk', 'night')),
  CONSTRAINT speech_prob_valid CHECK (speech_prob >= 0 AND speech_prob <= 1)
);

CREATE INDEX postcards_geom_gix ON postcards USING gist (geom);
CREATE INDEX postcards_geog_gix ON postcards USING gist ((geom::geography));
CREATE INDEX postcards_embedding_hnsw ON postcards USING hnsw (embedding vector_cosine_ops);
CREATE INDEX postcards_created_idx ON postcards (created_at DESC);

-- One row per accepted upload. Kept apart from postcards so that deleting a
-- postcard does not hand its author a slot back.
CREATE TABLE upload_events (
  id          bigserial PRIMARY KEY,
  device_hash text NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX upload_events_device_idx ON upload_events (device_hash, created_at DESC);

CREATE TABLE reports (
  id          bigserial PRIMARY KEY,
  postcard_id text NOT NULL REFERENCES postcards (id) ON DELETE CASCADE,
  device_hash text NOT NULL,
  reason      text NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT one_report_per_device UNIQUE (postcard_id, device_hash),
  CONSTRAINT reason_known CHECK (reason IN ('speech', 'private', 'offensive', 'other'))
);
