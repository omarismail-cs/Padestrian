# padestrian

Planning tools around walking, transit, and everyday errands in Ottawa—starting with local grocery locations and OC Transpo schedule data.

## Project layout

```
padestrian/
├── .env.example      # API key template (copy to .env)
├── data/
│   ├── groceries.geojson
│   ├── GTFSExport/   # OC Transpo GTFS (gitignored, large)
│   ├── manifest.json # Dataset metadata
│   └── README.md
└── README.md
```

## Setup

1. Copy the environment template and add your keys:

   ```bash
   cp .env.example .env
   ```

2. Place or refresh the OC Transpo GTFS export in `data/GTFSExport/` (see [data/README.md](data/README.md)). That folder is not committed because of size; `groceries.geojson` is included in the repo.

3. Required API keys (see `.env.example` for signup links):

   - **OpenRouteService** — routing / isochrones
   - **Mapbox** — maps

Never commit `.env` or paste live tokens into the repo.

## Data sources

| Dataset | Source | License / terms |
|---------|--------|-----------------|
| `data/groceries.geojson` | OpenStreetMap (Overpass) | ODbL |
| `data/GTFSExport/` | OC Transpo | Subject to OC Transpo terms of use |

## Status

Early data collection: no application code yet. Next steps might include a small loader, map UI, or routing experiments using the keys in `.env` and the files in `data/`.
