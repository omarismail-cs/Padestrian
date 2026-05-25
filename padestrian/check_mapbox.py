"""Verify MAPBOX_ACCESS_TOKEN works for the local dev map."""

import httpx

from padestrian.config import require_env

STYLE = "https://api.mapbox.com/styles/v1/mapbox/streets-v12"
TILE = (
    "https://api.mapbox.com/v4/"
    "mapbox.mapbox-streets-v8,mapbox.mapbox-terrain-v2,mapbox.mapbox-bathymetry-v2"
    "/12/1188/1467.vector.pbf"
)
SPRITE = "https://api.mapbox.com/styles/v1/mapbox/streets-v12/sprite.json"
LOCAL_HEADERS = {
    "Referer": "http://127.0.0.1:8765/",
    "Origin": "http://127.0.0.1:8765",
}


def check_mapbox_token() -> int:
    token = require_env("MAPBOX_ACCESS_TOKEN", fresh=True)
    print(f"Token ends with: …{token[-6:]} ({len(token)} chars)\n")

    ok = True
    for label, url in [
        ("Style streets-v12", f"{STYLE}?access_token={token}"),
        ("Vector tile (browser)", f"{TILE}?access_token={token}"),
        ("Sprite metadata", f"{SPRITE}?access_token={token}"),
    ]:
        r = httpx.get(url, headers=LOCAL_HEADERS, timeout=30)
        status = r.status_code
        print(f"  [{'OK' if status == 200 else 'FAIL'}] {label}: {status}")
        if status != 200:
            ok = False

    print()
    if ok:
        print("Token works. Run: python -m padestrian serve")
        return 0

    print("Fix token at https://account.mapbox.com/access-tokens/")
    print("Use a public pk. token with STYLES:READ, STYLES:TILES, FONTS:READ; no URL restrictions.")
    return 1


if __name__ == "__main__":
    raise SystemExit(check_mapbox_token())
