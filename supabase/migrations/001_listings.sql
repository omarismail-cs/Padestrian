-- Padestrian Phase 1: listing catalog with PostGIS points and 10-min scores.
-- Run in Supabase SQL Editor (Database → Extensions: enable postgis first).

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS listings (
  id              TEXT PRIMARY KEY,
  title           TEXT,
  address         TEXT NOT NULL,
  lat             DOUBLE PRECISION NOT NULL,
  lon             DOUBLE PRECISION NOT NULL,
  geom            geography(POINT, 4326)
                  GENERATED ALWAYS AS (
                    ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography
                  ) STORED,
  rent_cad        INTEGER NOT NULL,
  bedrooms        SMALLINT NOT NULL,
  bathrooms       REAL,
  neighborhood    TEXT NOT NULL DEFAULT '',
  source          TEXT NOT NULL,
  url             TEXT,
  active          BOOLEAN NOT NULL DEFAULT TRUE,
  near_grocery    BOOLEAN,
  near_transit    BOOLEAN,
  eligible        BOOLEAN,
  walk_minutes    REAL DEFAULT 10,
  transit_via     TEXT,
  nearest_stop_m  INTEGER,
  scored_at       TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS listings_geom_gix ON listings USING GIST (geom);
CREATE INDEX IF NOT EXISTS listings_active_idx ON listings (active) WHERE active = TRUE;
CREATE INDEX IF NOT EXISTS listings_source_idx ON listings (source);

ALTER TABLE listings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS listings_public_read ON listings;
CREATE POLICY listings_public_read ON listings
  FOR SELECT USING (active = TRUE);
