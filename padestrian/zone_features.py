"""GeoJSON helpers for walking-zone (isochrone) features."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterator


def load_feature_collection(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def iter_point_features(path: Path) -> Iterator[dict[str, Any]]:
    collection = load_feature_collection(path)
    for feature in collection.get("features", []):
        geom = feature.get("geometry") or {}
        if geom.get("type") == "Point":
            yield feature


def safe_cache_name(zone_id: str) -> str:
    """Filesystem-safe id from osm_id or stop_id."""
    return re.sub(r"[^\w.\-]+", "_", zone_id)[:120]


def center_feature(
    source: dict[str, Any],
    *,
    role: str,
    label: str,
    center_id: str,
    center_kind: str,
) -> dict[str, Any]:
    props = dict(source.get("properties") or {})
    return {
        "type": "Feature",
        "properties": {
            "role": role,
            "label": label,
            "center_id": center_id,
            "center_kind": center_kind,
            **props,
        },
        "geometry": source["geometry"],
    }


def isochrone_features(
    ors_collection: dict[str, Any],
    *,
    role: str,
    label: str,
    minutes: float,
    center_id: str,
    center_kind: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for feature in ors_collection.get("features", []):
        props = dict(feature.get("properties") or {})
        props.update(
            {
                "role": role,
                "label": label,
                "walk_minutes": minutes,
                "center_id": center_id,
                "center_kind": center_kind,
            }
        )
        out.append(
            {
                "type": "Feature",
                "properties": props,
                "geometry": feature["geometry"],
            }
        )
    return out


def grocery_center_id(feature: dict[str, Any]) -> str:
    props = feature.get("properties") or {}
    return str(props.get("osm_id") or feature.get("id") or props.get("name", "grocery"))


def transit_center_id(feature: dict[str, Any]) -> str:
    props = feature.get("properties") or {}
    return str(props.get("stop_id") or feature.get("id") or "stop")


def grocery_label(feature: dict[str, Any]) -> str:
    props = feature.get("properties") or {}
    return str(props.get("name") or "Grocery")


def transit_label(feature: dict[str, Any]) -> str:
    props = feature.get("properties") or {}
    return str(props.get("stop_name") or "Stop")
