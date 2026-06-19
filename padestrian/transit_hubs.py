"""Curated OC Transpo hub stops for transit walk-zone polygons."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

from padestrian.geojson_io import write_feature_collection
from padestrian.paths import STOPS_GEOJSON_PATH, TRANSIT_HUBS_GEOJSON_PATH
from padestrian.zone_features import iter_point_features

# Major Transitway / Park & Ride platforms (deduped against nearby O-Train picks).
_EXPLICIT_HUB_STOP_IDS: frozenset[str] = frozenset(
    {
        "9641",  # Baseline 1A
        "818",  # Baseline STN
        "6607",  # Fallowfield A
        "9492",  # Heron 1A
        "9487",  # Lincoln Fields 1A
        "9531",  # Eagleson A
        "18",  # Queensway 1A
        "9476",  # Trim 1A
        "239",  # Millennium A
        "2127",  # Westboro A
        "9490",  # Billings Bridge 1A
        "9608",  # Carlingwood
        "9520",  # Pinecrest A
        "103",  # Riverside 1A
        "9527",  # Terry Fox 4A
        "9449",  # Mackenzie King A
        "1556",  # Place d'Orléans A
        "9872",  # Blair A
        "9942",  # Tunney's Pasture A
    }
)

_DEDUPE_RADIUS_M = 350.0

_OTRAIN_STATION_RE = re.compile(r"^(.+?)\s+O-TRAIN", re.IGNORECASE)


def _haversine_meters(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6_371_000.0
    p = math.pi / 180.0
    dlat = (lat2 - lat1) * p
    dlon = (lon2 - lon1) * p
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin(dlon / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def _coords(feature: dict[str, Any]) -> tuple[float, float]:
    lon, lat = feature["geometry"]["coordinates"]
    return float(lon), float(lat)


def _otrain_station_key(stop_name: str) -> str | None:
    match = _OTRAIN_STATION_RE.search(stop_name.strip())
    if not match:
        return None
    return match.group(1).strip().upper()


def _pick_otrain_representatives(
    features: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """One O-Train stop per station — prefer WEST/OUEST platform labels."""
    by_station: dict[str, list[dict[str, Any]]] = {}
    for feature in features:
        name = str((feature.get("properties") or {}).get("stop_name") or "")
        key = _otrain_station_key(name)
        if key is None:
            continue
        by_station.setdefault(key, []).append(feature)

    chosen: list[dict[str, Any]] = []
    for key in sorted(by_station):
        candidates = by_station[key]

        def rank(f: dict[str, Any]) -> tuple[int, str]:
            name = str((f.get("properties") or {}).get("stop_name") or "").upper()
            if " WEST" in name or " OUEST" in name:
                return (0, name)
            if " EAST" in name or " EST" in name:
                return (1, name)
            if " NORTH" in name or " NORD" in name:
                return (2, name)
            if " SOUTH" in name or " SUD" in name:
                return (3, name)
            return (4, name)

        chosen.append(sorted(candidates, key=rank)[0])
    return chosen


def _dedupe_by_proximity(
    features: list[dict[str, Any]],
    *,
    radius_m: float = _DEDUPE_RADIUS_M,
) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for feature in features:
        lon, lat = _coords(feature)
        if any(_haversine_meters(lon, lat, *_coords(k)) <= radius_m for k in kept):
            continue
        kept.append(feature)
    return kept


def select_transit_hub_features(
    stops_path: Path = STOPS_GEOJSON_PATH,
) -> list[dict[str, Any]]:
    """Return hub Point features: O-Train stations + major Transitway platforms."""
    all_features = list(iter_point_features(stops_path))
    by_id: dict[str, dict[str, Any]] = {}
    for feature in all_features:
        stop_id = str((feature.get("properties") or {}).get("stop_id") or "")
        if stop_id:
            by_id[stop_id] = feature

    ordered: list[dict[str, Any]] = []
    ordered.extend(_pick_otrain_representatives(all_features))
    for stop_id in sorted(_EXPLICIT_HUB_STOP_IDS):
        if stop_id in by_id:
            ordered.append(by_id[stop_id])

    deduped = _dedupe_by_proximity(ordered)
    deduped.sort(key=lambda f: str((f.get("properties") or {}).get("stop_name") or ""))
    return deduped


def export_transit_hubs_geojson(
    output_path: Path = TRANSIT_HUBS_GEOJSON_PATH,
    stops_path: Path = STOPS_GEOJSON_PATH,
) -> dict[str, int]:
    """Write data/transit-hubs.geojson for build-zones --transit."""
    features = select_transit_hub_features(stops_path)
    for feature in features:
        props = feature.setdefault("properties", {})
        props["hub"] = True

    write_feature_collection(
        output_path,
        features,
        metadata={
            "generator": "padestrian transit_hubs",
            "source": str(stops_path.name),
            "hub_count": len(features),
        },
    )
    return {"hub_count": len(features), "output": str(output_path)}


def hub_stop_ids(stops_path: Path = STOPS_GEOJSON_PATH) -> list[str]:
    return [
        str((f.get("properties") or {}).get("stop_id") or "")
        for f in select_transit_hub_features(stops_path)
    ]
