# Padestrian

![Next.js](https://img.shields.io/badge/Next.js-000000?style=flat-square&logo=next.js&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?style=flat-square&logo=react&logoColor=61DAFB)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=flat-square&logo=tailwind-css&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Mapbox](https://img.shields.io/badge/Mapbox-4264FB?style=flat-square&logo=mapbox&logoColor=white)

**Find rentals you can actually live in without a car, on one map.**

Padestrian is a full-stack Ottawa rental explorer built around a simple idea: **walkability should mean a real walk**, not a straight line on a map. Most listing sites hand you a generic score that ignores highways, missing sidewalks, and how long winter walks actually feel. This project scores each apartment using **pedestrian routing**, official **transit stop data**, and real **grocery locations**, then shows you the results instantly.

## Screenshots

<table>
  <tr>
    <td width="65%" valign="middle" align="center">
      <div align="left">
        <strong>Map</strong>: color-coded rentals, groceries, transit stops, and a listing card with walkability badge
      </div>
      <br />
      <img src="public/images/screenshot-map.png" alt="Padestrian map with walkable listing popup" width="100%" />
    </td>
    <td width="35%" valign="middle">
      <strong>Filters &amp; layers</strong>: rent, bedrooms, walkable-only toggle, legend, and grocery/transit/Kijiji sources<br /><br />
      <img src="public/images/screenshot-filters.png" alt="Padestrian filter panel and layer controls" width="100%" />
    </td>
  </tr>
</table>

---

## Why this exists

Apartment hunting without a car usually means:

- Rental site in one tab, Google Maps in another  
- Guessing whether “15 minutes to transit” includes a fence, a parking lot, or a road with no sidewalk  
- No single view of **price + location + grocery + bus** at once  

Padestrian puts that in one place: hover a pin, see rent and address, know at a glance if the listing is walkable to **both** transit and a full grocery store.

---

## What you’ll see when you run it

- **Interactive Mapbox map** with dark/light theme, rent and bedroom filters, and a “walkable only” toggle  
- **~180 demo listings** placed on real City of Ottawa address coordinates (not random pins)  
- **Color-coded house markers**: walkable, grocery-only, transit-only, or neither  
- **Grocery + transit layers** you can turn on and off  
- **Listing cards** on hover (price, beds/baths, address, Kijiji link when available)  
- **Check an address** in the sidebar: Ottawa autocomplete, then the same color-coded house pin and walkability badge as rentals (saved in your browser until you clear it)  
- **Optional live Kijiji import** via the Python CLI (batch scrape → score → map)

---

## How it works (the interesting part)

```mermaid
flowchart TB
    L["Listings (JSON)"]
    G["Groceries (OSM)"]
    T["Transit (GTFS)"]
    W["10-min walk zones<br/>(OpenRouteService isochrones)"]
    P["Point-in-polygon + nearest-stop check"]
    M["listings-scored.geojson → Map"]

    L --> W
    G --> W
    T --> W
    W --> P
    P --> M
```

1. **Listings** land on the map with real lat/lon from municipal address points (demo set) or imported Kijiji ads.  
2. **Groceries** come from OpenStreetMap; **transit stops** from OC Transpo GTFS.  
3. **Walk zones** are built with OpenRouteService: actual sidewalk/path routing for a **10-minute** budget, drawn as polygons around each store (and optionally stops).  
4. Each listing is scored: near grocery? near transit? **eligible** only when both are true.  
5. The Next.js app loads the scored GeoJSON and paints pins by category.  
6. **Custom addresses** (sidebar) geocode in the browser via Mapbox, score with the same grocery-zone + nearest-transit rules as the Python CLI (Turf.js point-in-polygon), and merge into the listings layer as `source: "custom"` pins.

No database. Datasets are GeoJSON and JSON on disk, rebuilt with a CLI and served to the frontend. That keeps the demo fast to clone and easy to inspect.

---

## Tech stack

| Layer | Tools |
|-------|--------|
| **Frontend** | Next.js 16, React 19, Mapbox GL, Tailwind, Turf.js (client walk scoring) |
| **Backend / data** | Python 3.11+, Shapely, httpx, Playwright (Kijiji) |
| **Routing & map APIs** | OpenRouteService (walk isochrones, CLI), Mapbox (tiles + geocoding + address autocomplete) |
| **Data sources** | OC Transpo GTFS, OpenStreetMap groceries, City of Ottawa address points |

---

<details>
<summary>🛠️ Local Setup / Quick Start</summary>

<br />

**Requirements:** Node 18+, Python 3.11+, API keys for Mapbox and OpenRouteService.

#### Step 1: Prerequisites & API Keys

Copy the example env file and add your API keys before running the data pipeline or the map.

```bash
cp .env.example .env            # ORS_API_KEY, MAPBOX_ACCESS_TOKEN
# .env.local → NEXT_PUBLIC_MAPBOX_TOKEN=<same mapbox token>
```

#### Step 2: Backend & Data Pipeline Setup

Create the Python environment, install the CLI, then build and score the datasets the map reads.

```bash
# Clone, then:
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -e .

python -m padestrian build-essentials
python -m padestrian validate-listings
python -m padestrian build-zones
python -m padestrian filter-listings
```

**First-time grocery refresh (optional):**

```bash
python -m padestrian fetch-groceries
python -m padestrian build-essentials
python -m padestrian build-zones
python -m padestrian filter-listings
```

**Kijiji import (optional, needs `playwright install chromium`):**

```bash
python -m padestrian scrape-listings --pages 3 --max 30 --append
python -m padestrian validate-listings
python -m padestrian filter-listings
```

#### Step 3: Frontend Setup & Run

Install frontend dependencies and start the Next.js dev server.

```bash
npm install

npm run dev
```

Open **http://localhost:3000**. The map should load with listings already scored.  
Use **Check an address** in the sidebar to score any Ottawa street address (needs `data/zones/grocery-10min.geojson` from `build-zones`).  
After changing data: `Ctrl+Shift+R` to hard refresh.

</details>

---

## CLI reference

| Command | What it does |
|---------|----------------|
| `build-essentials` | Export transit stops + grocery points |
| `fetch-groceries` | Pull supermarkets from OpenStreetMap |
| `build-zones` | Generate 10-minute walk polygons |
| `filter-listings` | Score every listing → `listings-scored.geojson` |
| `validate-listings` | Validate catalog + export map layer |
| `seed-listings` | Generate the demo rental set |
| `scrape-listings` | Import ads from Kijiji |
| `prune-kijiji` | Drop listings no longer active on Kijiji |
| `validate-scoring` | Compare scores to a hand-labeled test CSV |
| `check-mapbox` | Sanity-check your Mapbox token |

Full dataset notes: [data/README.md](data/README.md).

---

## Deploying to Vercel

The map and **Check an address** feature are fully static at runtime: no Python on Vercel. The browser geocodes via Mapbox and scores points against GeoJSON you ship in `public/data`.

**Environment variables** (Vercel project settings):

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_MAPBOX_TOKEN` | Map tiles + address geocoding |

Restrict the token to your production URL in the Mapbox dashboard.

**Data files to include before deploy** (run the pipeline locally, then ensure these are served under `/data/` via `public/data` → `data/`):

| File | Required for |
|------|----------------|
| `data/listings-scored.geojson` | Colored listing pins on the map |
| `data/zones/grocery-10min.geojson` | Grocery walk scoring + custom address check |
| `data/stops.geojson` | Nearest-transit fallback (already in repo) |
| `data/groceries-points.geojson` | Grocery layer (already in repo) |

Optional: `data/zones/transit-10min.geojson`, `data/isochrones/smoke.geojson` (fallback if merged zones are missing).

Generated zone and scored listing files are gitignored by default. Either commit them for the demo deploy or add a CI step that runs `build-zones` and `filter-listings` and copies outputs into `data/` before `vercel build`.

Custom addresses are stored in the user’s browser (`localStorage`) only; they are not written to the server.

---

## Project layout

```text
padestrian/     Python CLI (ingest, zones, scoring, scrape)
components/     Map UI (filters, popups, address search, layers)
lib/            Browser geocoding + walk scoring (Vercel-safe, no Python at runtime)
app/            Next.js entry
data/           Source + generated GeoJSON
public/data/    Served to the browser (/data/… in the app)
public/images/  Map markers + README screenshots
```

---

Built as a portfolio-grade geospatial demo: real APIs, real city open data, and a product story that solves an everyday problem: **where can I rent and still walk to the bus and the store?**
