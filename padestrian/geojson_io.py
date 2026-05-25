import json
from pathlib import Path
from typing import Any


def write_feature_collection(path: Path, features: list[dict[str, Any]], metadata: dict[str, Any] | None = None) -> None:
    """Write a GeoJSON FeatureCollection to disk."""
    collection: dict[str, Any] = {
        "type": "FeatureCollection",
        "features": features,
    }
    if metadata:
        collection.update(metadata)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(collection, f, ensure_ascii=False, indent=2)
        f.write("\n")
