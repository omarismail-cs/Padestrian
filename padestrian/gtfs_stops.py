import csv
from pathlib import Path
from typing import Any

from padestrian.geojson_io import write_feature_collection
from padestrian.paths import STOPS_GEOJSON_PATH, STOPS_GTFS_PATH

# Rough Ottawa–Gatineau bounds for sanity checks (lon, lat).
OTTAWA_BBOX = (-76.35, 45.10, -74.95, 45.55)


def _parse_location_type(value: str | None) -> str:
    return (value or "").strip() or "0"


def _is_boarding_stop(row: dict[str, str]) -> bool:
    """Keep passenger boarding locations (GTFS location_type 0 or empty)."""
    location_type = _parse_location_type(row.get("location_type"))
    return location_type in ("0", "")


def _valid_coordinates(row: dict[str, str]) -> tuple[float, float] | None:
    try:
        lat = float(row["stop_lat"])
        lon = float(row["stop_lon"])
    except (KeyError, TypeError, ValueError):
        return None

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lon, lat


def _in_ottawa_bbox(lon: float, lat: float) -> bool:
    min_lon, min_lat, max_lon, max_lat = OTTAWA_BBOX
    return min_lon <= lon <= max_lon and min_lat <= lat <= max_lat


def load_stops_from_gtfs(stops_path: Path = STOPS_GTFS_PATH) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Parse GTFS stops.txt into GeoJSON Point features."""
    if not stops_path.is_file():
        raise FileNotFoundError(f"GTFS stops file not found: {stops_path}")

    features: list[dict[str, Any]] = []
    stats = {
        "rows_read": 0,
        "skipped_not_boarding_stop": 0,
        "skipped_invalid_coordinates": 0,
        "skipped_outside_bbox": 0,
        "features_written": 0,
    }

    with stops_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats["rows_read"] += 1

            if not _is_boarding_stop(row):
                stats["skipped_not_boarding_stop"] += 1
                continue

            coords = _valid_coordinates(row)
            if coords is None:
                stats["skipped_invalid_coordinates"] += 1
                continue

            lon, lat = coords
            if not _in_ottawa_bbox(lon, lat):
                stats["skipped_outside_bbox"] += 1
                continue

            stop_id = (row.get("stop_id") or "").strip()
            features.append(
                {
                    "type": "Feature",
                    "id": stop_id or None,
                    "properties": {
                        "stop_id": stop_id,
                        "stop_code": (row.get("stop_code") or "").strip() or None,
                        "stop_name": (row.get("stop_name") or "").strip(),
                        "wheelchair_boarding": (row.get("wheelchair_boarding") or "").strip() or None,
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat],
                    },
                }
            )

    stats["features_written"] = len(features)
    return features, stats


def export_stops_geojson(
    output_path: Path = STOPS_GEOJSON_PATH,
    stops_path: Path = STOPS_GTFS_PATH,
) -> dict[str, int]:
    features, stats = load_stops_from_gtfs(stops_path)
    write_feature_collection(
        output_path,
        features,
        metadata={
            "generator": "padestrian",
            "source": "OC Transpo GTFS stops.txt",
        },
    )
    return stats
