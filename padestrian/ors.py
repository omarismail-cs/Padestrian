"""OpenRouteService pedestrian isochrones."""

from typing import Any

import httpx

from padestrian.config import require_env

ORS_ISOCHRONE_URL = "https://api.openrouteservice.org/v2/isochrones/foot-walking"


def fetch_walking_isochrone(
    lon: float,
    lat: float,
    minutes: float,
    *,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """
    Return a GeoJSON FeatureCollection for a time-based walking isochrone.

    ORS expects locations as [longitude, latitude].
    """
    api_key = require_env("ORS_API_KEY")
    range_seconds = int(minutes * 60)

    payload = {
        "locations": [[lon, lat]],
        "range": [range_seconds],
        "range_type": "time",
    }
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }

    owns_client = client is None
    if owns_client:
        client = httpx.Client(timeout=60.0)

    try:
        response = client.post(ORS_ISOCHRONE_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
    finally:
        if owns_client:
            client.close()

    if data.get("type") != "FeatureCollection":
        raise RuntimeError(f"Unexpected ORS response: {data!r:.200}")

    return data
