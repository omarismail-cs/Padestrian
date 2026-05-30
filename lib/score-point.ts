import booleanPointInPolygon from "@turf/boolean-point-in-polygon"
import { point } from "@turf/helpers"
import type { Feature, FeatureCollection, Geometry, Polygon, MultiPolygon } from "geojson"

const WALK_MINUTES = 10
const METERS_PER_MINUTE = 5000 / 60
const DETOUR_FACTOR = 1.35

export interface PointScore {
  near_grocery: boolean
  near_transit: boolean
  eligible: boolean
  walk_minutes: number
  transit_via: "zone" | "nearest_stop" | "none"
  nearest_stop_m?: number
  grocery_zone_source: string
  transit_zone_source: string
}

export class ScoringDataError extends Error {
  constructor(message: string) {
    super(message)
    this.name = "ScoringDataError"
  }
}

type PolyFeature = Feature<Polygon | MultiPolygon>

let groceryPolysCache: { polys: PolyFeature[]; source: string } | null = null
let transitPolysCache: { polys: PolyFeature[]; source: string } | null = null
let stopsCache: Array<[number, number]> | null = null

function walkThresholdMeters(minutes: number): number {
  return minutes * METERS_PER_MINUTE * DETOUR_FACTOR
}

function haversineMeters(lon1: number, lat1: number, lon2: number, lat2: number): number {
  const r = 6_371_000
  const p = Math.PI / 180
  const dlat = (lat2 - lat1) * p
  const dlon = (lon2 - lon1) * p
  const a =
    Math.sin(dlat / 2) ** 2 +
    Math.cos(lat1 * p) * Math.cos(lat2 * p) * Math.sin(dlon / 2) ** 2
  return 2 * r * Math.asin(Math.sqrt(a))
}

async function fetchGeoJson(url: string): Promise<FeatureCollection | null> {
  try {
    const resp = await fetch(url)
    if (!resp.ok) return null
    return (await resp.json()) as FeatureCollection
  } catch {
    return null
  }
}

function polygonsFromCollection(
  fc: FeatureCollection,
  roles: Set<string>,
): PolyFeature[] {
  const polys: PolyFeature[] = []
  for (const feature of fc.features) {
    const role = feature.properties?.role
    if (typeof role !== "string" || !roles.has(role)) continue
    const geom = feature.geometry
    if (geom?.type === "Polygon" || geom?.type === "MultiPolygon") {
      polys.push(feature as PolyFeature)
    }
  }
  return polys
}

function pointInAny(lon: number, lat: number, polygons: PolyFeature[]): boolean {
  if (polygons.length === 0) return false
  const pt = point([lon, lat])
  return polygons.some((poly) => booleanPointInPolygon(pt, poly as Feature<Geometry>))
}

async function resolveZonePolygons(
  kind: "grocery" | "transit",
  smokeRole: string,
): Promise<{ polys: PolyFeature[]; source: string }> {
  const mergedUrl = `/data/zones/${kind}-10min.geojson`
  const merged = await fetchGeoJson(mergedUrl)
  if (merged) {
    const zoneRole = `${kind}_zone`
    const polys = polygonsFromCollection(merged, new Set([zoneRole]))
    if (polys.length > 0) {
      return { polys, source: `${kind}-10min.geojson` }
    }
  }

  const smoke = await fetchGeoJson("/data/isochrones/smoke.geojson")
  if (smoke) {
    const polys = polygonsFromCollection(smoke, new Set([smokeRole]))
    if (polys.length > 0) {
      return { polys, source: "smoke.geojson (fallback)" }
    }
  }

  return { polys: [], source: "none" }
}

async function loadStops(): Promise<Array<[number, number]>> {
  if (stopsCache) return stopsCache
  const fc = await fetchGeoJson("/data/stops.geojson")
  const coords: Array<[number, number]> = []
  if (fc) {
    for (const feat of fc.features) {
      if (feat.geometry?.type !== "Point") continue
      const c = feat.geometry.coordinates
      if (c && c.length >= 2) {
        coords.push([Number(c[0]), Number(c[1])])
      }
    }
  }
  stopsCache = coords
  return coords
}

function nearestStopMeters(
  lon: number,
  lat: number,
  stops: Array<[number, number]>,
): number | null {
  if (stops.length === 0) return null
  let best = Infinity
  for (const [slon, slat] of stops) {
    const d = haversineMeters(lon, lat, slon, slat)
    if (d < best) best = d
  }
  return best === Infinity ? null : best
}

function scoreNearTransit(
  lon: number,
  lat: number,
  inTransitZone: boolean,
  stops: Array<[number, number]>,
  minutes: number,
): { near: boolean; via: "zone" | "nearest_stop" | "none"; nearestM?: number } {
  if (inTransitZone) {
    return { near: true, via: "zone" }
  }
  const threshold = walkThresholdMeters(minutes)
  const dist = nearestStopMeters(lon, lat, stops)
  if (dist != null && dist <= threshold) {
    return { near: true, via: "nearest_stop", nearestM: dist }
  }
  return { near: false, via: "none", nearestM: dist ?? undefined }
}

export async function scorePoint(
  lon: number,
  lat: number,
  minutes = WALK_MINUTES,
): Promise<PointScore> {
  if (!groceryPolysCache) {
    groceryPolysCache = await resolveZonePolygons("grocery", "grocery_zone")
  }
  if (!transitPolysCache) {
    transitPolysCache = await resolveZonePolygons("transit", "transit_zone")
  }

  const groceryPolys = groceryPolysCache.polys
  const transitPolys = transitPolysCache.polys

  if (groceryPolys.length === 0) {
    throw new ScoringDataError(
      "Grocery walk zones are not available. Run the data pipeline (build-zones) and deploy zone GeoJSON to /data.",
    )
  }

  const stops = await loadStops()
  const nearGrocery = pointInAny(lon, lat, groceryPolys)
  const inTransitZone = pointInAny(lon, lat, transitPolys)
  const transit = scoreNearTransit(lon, lat, inTransitZone, stops, minutes)
  const eligible = nearGrocery && transit.near

  return {
    near_grocery: nearGrocery,
    near_transit: transit.near,
    eligible,
    walk_minutes: minutes,
    transit_via: transit.via,
    nearest_stop_m:
      transit.nearestM != null ? Math.round(transit.nearestM) : undefined,
    grocery_zone_source: groceryPolysCache.source,
    transit_zone_source: transitPolysCache.source,
  }
}

/** Clear cached zone data (e.g. after hot reload in dev). */
export function clearScorePointCache(): void {
  groceryPolysCache = null
  transitPolysCache = null
  stopsCache = null
}
