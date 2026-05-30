import { inOttawaBbox, OTTAWA_BBOX, OTTAWA_CENTER } from "@/lib/ottawa-bbox"

const MAPBOX_GEOCODE_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places"

export interface GeocodeResult {
  lon: number
  lat: number
  label: string
}

type MapboxFeature = {
  relevance?: number
  place_name?: string
  text?: string
  geometry?: { coordinates?: number[] }
}

const HOUSE_NUMBER_RE = /^(\d+)\s/

function queryHouseNumber(query: string): string | null {
  const m = HOUSE_NUMBER_RE.exec(query.trim())
  return m ? m[1] : null
}

function acceptFeature(query: string, feat: MapboxFeature): boolean {
  const relevance = Number(feat.relevance ?? 0)
  if (relevance < 0.72) return false
  const house = queryHouseNumber(query)
  if (!house) return true
  const label = feat.place_name || feat.text || ""
  if (label.includes(house)) return true
  return relevance >= 0.85
}

function featureToResult(
  feat: MapboxFeature,
  fallbackLabel: string,
): GeocodeResult | null {
  const coords = feat.geometry?.coordinates
  if (!coords || coords.length < 2) return null

  const lon = Number(coords[0])
  const lat = Number(coords[1])
  if (!Number.isFinite(lon) || !Number.isFinite(lat) || !inOttawaBbox(lon, lat)) {
    return null
  }

  return {
    lon,
    lat,
    label: feat.place_name || fallbackLabel,
  }
}

function getMapboxToken(): string {
  const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN
  if (!token?.trim()) {
    throw new Error("Mapbox token is not configured")
  }
  return token
}

async function fetchMapboxFeatures(
  query: string,
  options: { autocomplete: boolean; limit: number },
): Promise<MapboxFeature[]> {
  const trimmed = query.trim()
  if (!trimmed) return []

  const { minLon, minLat, maxLon, maxLat } = OTTAWA_BBOX
  const params = new URLSearchParams({
    access_token: getMapboxToken(),
    country: "CA",
    bbox: `${minLon},${minLat},${maxLon},${maxLat}`,
    proximity: `${OTTAWA_CENTER.lon},${OTTAWA_CENTER.lat}`,
    types: "address",
    limit: String(options.limit),
    language: "en",
    autocomplete: options.autocomplete ? "true" : "false",
  })

  const url = `${MAPBOX_GEOCODE_URL}/${encodeURIComponent(trimmed)}.json?${params}`

  try {
    const resp = await fetch(url)
    if (!resp.ok) return []
    const data = (await resp.json()) as { features?: MapboxFeature[] }
    return data.features ?? []
  } catch {
    return []
  }
}

/** Forward geocode a single best Ottawa address match. */
export async function geocodeAddress(query: string): Promise<GeocodeResult | null> {
  const trimmed = query.trim()
  if (!trimmed) return null

  const features = await fetchMapboxFeatures(trimmed, {
    autocomplete: false,
    limit: 5,
  })
  const feat = features.find((f) => acceptFeature(trimmed, f))
  if (!feat) return null
  return featureToResult(feat, trimmed)
}

/** Autocomplete suggestions while the user types (Ottawa addresses only). */
export async function suggestAddresses(
  query: string,
  limit = 5,
): Promise<GeocodeResult[]> {
  const trimmed = query.trim()
  if (trimmed.length < 3) return []

  const features = await fetchMapboxFeatures(trimmed, {
    autocomplete: true,
    limit: Math.min(limit, 8),
  })

  const seen = new Set<string>()
  const results: GeocodeResult[] = []

  for (const feat of features) {
    if (!acceptFeature(trimmed, feat)) continue
    const hit = featureToResult(feat, trimmed)
    if (!hit || seen.has(hit.label)) continue
    seen.add(hit.label)
    results.push(hit)
    if (results.length >= limit) break
  }

  return results
}
