import { createClient } from "@supabase/supabase-js"
import type { Feature, FeatureCollection, Point } from "geojson"
import { NextResponse } from "next/server"

interface ListingRow {
  id: string
  title: string | null
  address: string
  lat: number
  lon: number
  rent_cad: number
  bedrooms: number
  bathrooms: number | null
  neighborhood: string | null
  source: string
  url: string | null
  near_grocery: boolean | null
  near_transit: boolean | null
  eligible: boolean | null
  walk_minutes: number | null
  transit_via: string | null
  nearest_stop_m: number | null
  scored_at: string | null
  updated_at: string | null
}

function rowToFeature(row: ListingRow): Feature<Point> {
  const props: Record<string, unknown> = {
    id: row.id,
    title: row.title ?? row.address,
    address: row.address,
    rent_cad: row.rent_cad,
    bedrooms: row.bedrooms,
    neighborhood: row.neighborhood ?? "",
    source: row.source,
  }
  if (row.bathrooms != null) props.bathrooms = row.bathrooms
  if (row.url) props.url = row.url
  if (row.near_grocery != null) props.near_grocery = row.near_grocery
  if (row.near_transit != null) props.near_transit = row.near_transit
  if (row.eligible != null) props.eligible = row.eligible
  if (row.walk_minutes != null) props.walk_minutes = row.walk_minutes
  if (row.transit_via) props.transit_via = row.transit_via
  if (row.nearest_stop_m != null) props.nearest_stop_m = row.nearest_stop_m

  return {
    type: "Feature",
    id: row.id,
    properties: props,
    geometry: {
      type: "Point",
      coordinates: [row.lon, row.lat],
    },
  }
}

export async function GET() {
  const url = process.env.SUPABASE_URL
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!url || !key) {
    return NextResponse.json(
      { error: "Supabase not configured" },
      { status: 503 },
    )
  }

  const supabase = createClient(url, key)
  const { data, error } = await supabase
    .from("listings")
    .select("*")
    .eq("active", true)
    .order("id")

  if (error) {
    console.error("Supabase listings fetch failed:", error.message)
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  const rows = (data ?? []) as ListingRow[]
  const features = rows.map(rowToFeature)

  const timestamps = rows
    .map((r) => r.scored_at ?? r.updated_at)
    .filter((t): t is string => Boolean(t))
  const generated_at =
    timestamps.length > 0
      ? timestamps.reduce((a, b) => (a > b ? a : b))
      : new Date().toISOString()

  const fc: FeatureCollection & {
    generated_at: string
    total: number
    eligible: number
  } = {
    type: "FeatureCollection",
    features,
    generated_at,
    total: features.length,
    eligible: rows.filter((r) => r.eligible).length,
  }

  return NextResponse.json(fc, {
    headers: { "Cache-Control": "public, s-maxage=60, stale-while-revalidate=300" },
  })
}
