"""Batch walking zones (ORS isochrones) with per-center cache and merged GeoJSON."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import httpx

from padestrian.geojson_io import write_feature_collection
from padestrian.ors import fetch_walking_isochrone
from padestrian.paths import (
    GROCERIES_POINTS_PATH,
    STOPS_GEOJSON_PATH,
    TRANSIT_HUBS_GEOJSON_PATH,
    ZONES_CACHE_DIR,
    ZONES_DIR,
    minute_tag,
    zone_merged_path,
)
from padestrian.zone_features import (
    grocery_center_id,
    grocery_label,
    isochrone_features,
    iter_point_features,
    safe_cache_name,
    transit_center_id,
    transit_label,
)

CenterKind = Literal["grocery", "transit"]


@dataclass
class LayerBuildStats:
    kind: str
    total: int = 0
    fetched: int = 0
    cached: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class BuildZonesResult:
    minutes: float
    layers: list[LayerBuildStats] = field(default_factory=list)
    outputs: list[Path] = field(default_factory=list)


def _cache_path(kind: CenterKind, zone_id: str, minutes: float) -> Path:
    return ZONES_CACHE_DIR / minute_tag(minutes) / kind / f"{safe_cache_name(zone_id)}.geojson"


def _read_cached_polygons(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return list(data.get("features", []))


def _write_cached_polygons(path: Path, features: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, ensure_ascii=False)
        f.write("\n")


def _fetch_isochrone(
    lon: float,
    lat: float,
    minutes: float,
    *,
    client: httpx.Client,
    max_retries: int = 4,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            return fetch_walking_isochrone(lon, lat, minutes, client=client)
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code in (429, 503) and attempt < max_retries - 1:
                time.sleep(5.0 * (attempt + 1))
                continue
            raise
    raise RuntimeError("unreachable") from last_error


def _build_layer(
    kind: CenterKind,
    source_path: Path,
    *,
    minutes: float,
    delay_seconds: float,
    force: bool,
    dry_run: bool,
    limit: int | None,
    client: httpx.Client | None,
) -> tuple[LayerBuildStats, Path | None]:
    if kind == "grocery":
        role = "grocery_zone"
        center_kind = "grocery"
        id_fn = grocery_center_id
        label_fn = grocery_label
    else:
        role = "transit_zone"
        center_kind = "transit"
        id_fn = transit_center_id
        label_fn = transit_label

    points = list(iter_point_features(source_path))
    if limit is not None:
        points = points[:limit]

    stats = LayerBuildStats(kind=kind, total=len(points))
    merged_features: list[dict[str, Any]] = []
    owns_client = client is None
    if owns_client and not dry_run:
        client = httpx.Client(timeout=90.0)

    try:
        for index, feature in enumerate(points, start=1):
            zone_id = id_fn(feature)
            label = label_fn(feature)
            cache_file = _cache_path(kind, zone_id, minutes)

            if cache_file.is_file() and not force:
                stats.cached += 1
                if not dry_run:
                    merged_features.extend(_read_cached_polygons(cache_file))
                print(f"  [{index}/{stats.total}] {zone_id} (cached)")
                continue

            lon, lat = feature["geometry"]["coordinates"]
            if dry_run:
                print(f"  [{index}/{stats.total}] {zone_id} (would fetch)")
                continue

            print(f"  [{index}/{stats.total}] {zone_id} …")
            try:
                assert client is not None
                ors_result = _fetch_isochrone(lon, lat, minutes, client=client)
                zone_polys = isochrone_features(
                    ors_result,
                    role=role,
                    label=label,
                    minutes=minutes,
                    center_id=zone_id,
                    center_kind=center_kind,
                )
                if not zone_polys:
                    raise RuntimeError("ORS returned no polygon features")
                _write_cached_polygons(cache_file, zone_polys)
                merged_features.extend(zone_polys)
                stats.fetched += 1
            except Exception as exc:  # noqa: BLE001 — collect and continue batch
                stats.failed += 1
                stats.errors.append(f"{zone_id}: {exc}")
                print(f"    FAILED: {exc}")

            if delay_seconds > 0 and index < stats.total:
                time.sleep(delay_seconds)
    finally:
        if owns_client and client is not None:
            client.close()

    if dry_run:
        return stats, None

    output = zone_merged_path(kind, minutes)
    write_feature_collection(
        output,
        merged_features,
        metadata={
            "generator": "padestrian build-zones",
            "center_kind": center_kind,
            "walk_minutes": minutes,
            "profile": "foot-walking",
            "provider": "OpenRouteService",
            "polygon_count": len(merged_features),
            "center_count": stats.total,
            "fetched": stats.fetched,
            "cached": stats.cached,
            "failed": stats.failed,
        },
    )
    return stats, output


def _resolve_transit_source(
    *,
    transit_hubs: bool,
    transit_all: bool,
) -> Path:
    if transit_all:
        return STOPS_GEOJSON_PATH
    if transit_hubs:
        if TRANSIT_HUBS_GEOJSON_PATH.is_file():
            return TRANSIT_HUBS_GEOJSON_PATH
        raise FileNotFoundError(
            f"Missing {TRANSIT_HUBS_GEOJSON_PATH}. "
            "Run: python -m padestrian build-transit-hubs"
        )
    return STOPS_GEOJSON_PATH


def run_build_zones(
    *,
    minutes: float = 10.0,
    groceries: bool = True,
    transit: bool = False,
    grocery_limit: int | None = None,
    transit_limit: int | None = None,
    transit_hubs: bool = True,
    transit_all: bool = False,
    delay_seconds: float = 1.2,
    force: bool = False,
    dry_run: bool = False,
) -> BuildZonesResult:
    """
    Fetch ORS walking isochrones and write merged zone layers under data/zones/.

    Groceries default on; transit default off.
    Transit defaults to curated hub stops (see build-transit-hubs); use --transit-all
    with --transit-limit for the legacy first-N-stops behaviour.
    """
    if not groceries and not transit:
        raise ValueError("Enable at least one of groceries or transit")

    if groceries and not GROCERIES_POINTS_PATH.is_file():
        raise FileNotFoundError(
            f"Missing {GROCERIES_POINTS_PATH}. Run: python -m padestrian build-essentials"
        )
    if transit and not STOPS_GEOJSON_PATH.is_file():
        raise FileNotFoundError(
            f"Missing {STOPS_GEOJSON_PATH}. Run: python -m padestrian build-essentials"
        )

    ZONES_DIR.mkdir(parents=True, exist_ok=True)
    result = BuildZonesResult(minutes=minutes)

    shared_client = None if dry_run else httpx.Client(timeout=90.0)
    try:
        if groceries:
            print(f"Groceries ({minutes:g} min walk)…")
            stats, path = _build_layer(
                "grocery",
                GROCERIES_POINTS_PATH,
                minutes=minutes,
                delay_seconds=delay_seconds,
                force=force,
                dry_run=dry_run,
                limit=grocery_limit,
                client=shared_client,
            )
            result.layers.append(stats)
            if path:
                result.outputs.append(path)

        if transit:
            transit_source = _resolve_transit_source(
                transit_hubs=transit_hubs,
                transit_all=transit_all,
            )
            label = "Transit hubs" if transit_source == TRANSIT_HUBS_GEOJSON_PATH else "Transit stops"
            print(f"{label} ({minutes:g} min walk)…")
            stats, path = _build_layer(
                "transit",
                transit_source,
                minutes=minutes,
                delay_seconds=delay_seconds,
                force=force,
                dry_run=dry_run,
                limit=transit_limit if transit_all else None,
                client=shared_client,
            )
            result.layers.append(stats)
            if path:
                result.outputs.append(path)
    finally:
        if shared_client is not None:
            shared_client.close()

    return result
