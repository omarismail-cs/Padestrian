from pathlib import Path

from padestrian.geojson_io import write_feature_collection
from padestrian.ors import fetch_walking_isochrone
from padestrian.paths import (
    GROCERIES_POINTS_PATH,
    ISOCHRONES_DIR,
    SMOKE_ISOCHRONE_PATH,
    STOPS_GEOJSON_PATH,
)
from padestrian.zone_features import (
    center_feature,
    grocery_center_id,
    grocery_label,
    isochrone_features,
    iter_point_features,
    transit_center_id,
    transit_label,
)


def _first_point_feature(path: Path) -> dict:
    for feature in iter_point_features(path):
        return feature
    raise RuntimeError(f"No point features in {path}")


def run_smoke_isochrone(
    minutes: float = 10.0,
    output_path: Path = SMOKE_ISOCHRONE_PATH,
) -> Path:
    """
    Build one transit + one grocery walking zone (ORS) for a quick sanity check.

    Uses the first stop in stops.geojson and the first grocery in groceries-points.geojson.
    """
    stop = _first_point_feature(STOPS_GEOJSON_PATH)
    grocery = _first_point_feature(GROCERIES_POINTS_PATH)

    stop_id = transit_center_id(stop)
    grocery_id = grocery_center_id(grocery)
    stop_name = transit_label(stop)
    grocery_name = grocery_label(grocery)

    features: list[dict] = [
        center_feature(
            stop,
            role="center",
            label=f"Stop: {stop_name}",
            center_id=stop_id,
            center_kind="transit",
        ),
        center_feature(
            grocery,
            role="center",
            label=f"Grocery: {grocery_name}",
            center_id=grocery_id,
            center_kind="grocery",
        ),
    ]

    for source, role, label, center_id, center_kind in (
        (stop, "transit_zone", stop_name, stop_id, "transit"),
        (grocery, "grocery_zone", grocery_name, grocery_id, "grocery"),
    ):
        lon, lat = source["geometry"]["coordinates"]
        ors_result = fetch_walking_isochrone(lon, lat, minutes)
        features.extend(
            isochrone_features(
                ors_result,
                role=role,
                label=label,
                minutes=minutes,
                center_id=center_id,
                center_kind=center_kind,
            )
        )

    ISOCHRONES_DIR.mkdir(parents=True, exist_ok=True)
    write_feature_collection(
        output_path,
        features,
        metadata={
            "generator": "padestrian smoke-isochrone",
            "walk_minutes": minutes,
            "profile": "foot-walking",
            "provider": "OpenRouteService",
        },
    )
    return output_path
