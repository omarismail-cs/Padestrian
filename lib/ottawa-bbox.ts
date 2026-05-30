/** Ottawa–Gatineau bounds (lon, lat) — matches padestrian/gtfs_stops.py */
export const OTTAWA_BBOX = {
  minLon: -76.35,
  minLat: 45.1,
  maxLon: -74.95,
  maxLat: 45.55,
} as const

export const OTTAWA_CENTER = { lon: -75.6972, lat: 45.4215 } as const

export function inOttawaBbox(lon: number, lat: number): boolean {
  const { minLon, minLat, maxLon, maxLat } = OTTAWA_BBOX
  return minLon <= lon && lon <= maxLon && minLat <= lat && lat <= maxLat
}
