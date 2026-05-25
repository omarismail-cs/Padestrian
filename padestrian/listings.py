"""Static rental listings — validate JSON and export GeoJSON for the map."""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from padestrian.geojson_io import write_feature_collection
from padestrian.gtfs_stops import OTTAWA_BBOX, _in_ottawa_bbox as _in_bbox
from padestrian.paths import LISTINGS_GEOJSON_PATH, LISTINGS_JSON_PATH

REQUIRED_FIELDS = ("id", "address", "lat", "lon", "rent_cad", "bedrooms")


class ListingValidationError(Exception):
    """Raised when listings.json fails validation."""


def _load_catalog(path: Path = LISTINGS_JSON_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise ListingValidationError(f"Missing {path}")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ListingValidationError("Root must be a JSON object")
    listings = data.get("listings")
    if not isinstance(listings, list):
        raise ListingValidationError("Expected a 'listings' array")
    return data


def validate_listing(row: dict[str, Any], index: int) -> list[str]:
    errors: list[str] = []
    prefix = f"listings[{index}]"

    for field in REQUIRED_FIELDS:
        if field not in row or row[field] is None or row[field] == "":
            errors.append(f"{prefix}: missing '{field}'")

    listing_id = row.get("id")
    if listing_id is not None and not isinstance(listing_id, str):
        errors.append(f"{prefix}: id must be a string")

    try:
        lat = float(row["lat"])
        lon = float(row["lon"])
    except (KeyError, TypeError, ValueError):
        errors.append(f"{prefix}: lat/lon must be numbers")
        return errors

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        errors.append(f"{prefix}: lat/lon out of range")
    elif not _in_bbox(lon, lat):
        errors.append(f"{prefix}: coordinates outside Ottawa bbox {OTTAWA_BBOX}")

    try:
        rent = float(row["rent_cad"])
        if rent <= 0:
            errors.append(f"{prefix}: rent_cad must be positive")
    except (KeyError, TypeError, ValueError):
        errors.append(f"{prefix}: rent_cad must be a number")

    try:
        beds = int(row["bedrooms"])
        if beds < 0 or beds > 10:
            errors.append(f"{prefix}: bedrooms must be 0–10")
    except (KeyError, TypeError, ValueError):
        errors.append(f"{prefix}: bedrooms must be an integer")

    baths = row.get("bathrooms")
    if baths is not None:
        try:
            b = float(baths)
            if b <= 0 or b > 10:
                errors.append(f"{prefix}: bathrooms out of range")
        except (TypeError, ValueError):
            errors.append(f"{prefix}: bathrooms must be a number")

    return errors


def validate_catalog(path: Path = LISTINGS_JSON_PATH) -> tuple[dict[str, Any], list[str]]:
    data = _load_catalog(path)
    listings = data["listings"]
    errors: list[str] = []
    seen_ids: set[str] = set()

    for i, row in enumerate(listings):
        if not isinstance(row, dict):
            errors.append(f"listings[{i}]: must be an object")
            continue
        errors.extend(validate_listing(row, i))
        lid = row.get("id")
        if isinstance(lid, str):
            if lid in seen_ids:
                errors.append(f"listings[{i}]: duplicate id '{lid}'")
            seen_ids.add(lid)

    return data, errors


def listing_to_feature(row: dict[str, Any]) -> dict[str, Any]:
    props = {
        "id": row["id"],
        "title": row.get("title") or row["address"],
        "address": row["address"],
        "rent_cad": int(row["rent_cad"]) if float(row["rent_cad"]).is_integer() else float(row["rent_cad"]),
        "bedrooms": int(row["bedrooms"]),
        "neighborhood": row.get("neighborhood") or "",
        "source": row.get("source") or "demo",
    }
    if row.get("bathrooms") is not None:
        props["bathrooms"] = float(row["bathrooms"])
    if row.get("url"):
        props["url"] = row["url"]

    lon, lat = float(row["lon"]), float(row["lat"])
    return {
        "type": "Feature",
        "id": row["id"],
        "properties": props,
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
    }


def export_listings_geojson(
    path: Path = LISTINGS_JSON_PATH,
    output: Path = LISTINGS_GEOJSON_PATH,
) -> dict[str, int]:
    data, errors = validate_catalog(path)
    if errors:
        raise ListingValidationError("\n".join(errors))

    features = [listing_to_feature(row) for row in data["listings"]]
    write_feature_collection(
        output,
        features,
        metadata={
            "city": data.get("city", "Ottawa, ON"),
            "source": data.get("source", "demo"),
            "listingCount": len(features),
        },
    )
    rents = [f["properties"]["rent_cad"] for f in features]
    return {
        "count": len(features),
        "rent_min": int(min(rents)),
        "rent_max": int(max(rents)),
    }


# Demo seed — plausible Ottawa neighborhoods (lon, lat) with jitter.
_DEMO_NEIGHBORHOODS: list[tuple[str, float, float]] = [
    ("ByWard Market", -75.692, 45.428),
    ("Centretown", -75.698, 45.421),
    ("Glebe", -75.689, 45.398),
    ("Sandy Hill", -75.675, 45.424),
    ("Lowertown", -75.685, 45.435),
    ("Hintonburg", -75.725, 45.403),
    ("Westboro", -75.752, 45.392),
    ("Little Italy", -75.712, 45.409),
    ("Vanier", -75.665, 45.432),
    ("Alta Vista", -75.662, 45.385),
    ("Billings Bridge", -75.655, 45.375),
    ("Orleans", -75.510, 45.470),
    ("Kanata", -75.900, 45.308),
    ("Barrhaven", -75.735, 45.278),
    ("Nepean", -75.760, 45.348),
    ("Stittsville", -75.920, 45.258),
    ("Rockcliffe", -75.655, 45.448),
    ("New Edinburgh", -75.680, 45.445),
]

_STREETS = [
    "Bank St",
    "Somerset St W",
    "Gladstone Ave",
    "Preston St",
    "Rideau St",
    "Wellington St W",
    "Richmond Rd",
    "Carling Ave",
    "Montreal Rd",
    "St Laurent Blvd",
    "Baseline Rd",
    "Hunt Club Rd",
    "Catherine St",
    "Laurier Ave E",
    "Cooper St",
]


def seed_demo_listings(count: int = 180, *, seed: int = 42) -> dict[str, Any]:
    """Build a reproducible demo catalog for Ottawa."""
    rng = random.Random(seed)
    listings: list[dict[str, Any]] = []

    for i in range(count):
        hood, base_lon, base_lat = rng.choice(_DEMO_NEIGHBORHOODS)
        lon = base_lon + rng.uniform(-0.018, 0.018)
        lat = base_lat + rng.uniform(-0.012, 0.012)
        lon = max(OTTAWA_BBOX[0], min(OTTAWA_BBOX[2], lon))
        lat = max(OTTAWA_BBOX[1], min(OTTAWA_BBOX[3], lat))

        bedrooms = rng.choices([0, 1, 2, 3], weights=[12, 38, 35, 15])[0]
        bathrooms = 1.0 if bedrooms <= 1 else (1.5 if bedrooms == 2 else 2.0)
        if bedrooms == 0:
            base_rent = rng.randint(1150, 1750)
            title = "Studio apartment"
        elif bedrooms == 1:
            base_rent = rng.randint(1450, 2200)
            title = "1 bedroom"
        elif bedrooms == 2:
            base_rent = rng.randint(1750, 2850)
            title = "2 bedroom"
        else:
            base_rent = rng.randint(2200, 3400)
            title = "3 bedroom"

        street = rng.choice(_STREETS)
        number = rng.randint(12, 999)
        address = f"{number} {street}, Ottawa, ON"

        listings.append(
            {
                "id": f"ott-{i + 1:04d}",
                "title": f"{title} — {hood}",
                "address": address,
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "rent_cad": base_rent,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "neighborhood": hood,
                "source": "padestrian-demo",
                "url": f"https://example.com/listings/ott-{i + 1:04d}",
            }
        )

    return {
        "city": "Ottawa, ON",
        "source": "padestrian demo seed (not live listings)",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "listings": listings,
    }


def write_seed_catalog(path: Path = LISTINGS_JSON_PATH, count: int = 180) -> Path:
    catalog = seed_demo_listings(count)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return path
