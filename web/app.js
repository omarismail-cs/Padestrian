/**
 * Padestrian map — Mapbox GL JS v3 + streets-v12.
 * Token: /config.js (regenerated from .env on every serve start).
 */
const CENTER = [-75.6972, 45.4215];
const ZOOM = 12.5;
const STYLE = "mapbox://styles/mapbox/streets-v12";

const LAYER_GROUPS = {
  listings: ["listings-circle"],
  groceries: ["groceries-circle"],
  smoke: ["smoke-zones-fill", "smoke-zones-outline", "smoke-centers"],
  stops: ["stops-clusters", "stops-circle"],
};

const HOVER_LAYERS = [
  "listings-circle",
  "groceries-circle",
  "stops-circle",
  "stops-clusters",
  "smoke-centers",
  "smoke-zones-fill",
];

const statusEl = document.getElementById("status");
let stopsAdded = false;
const hoverBound = new Set();

function setStatus(msg) {
  statusEl.textContent = msg;
}

function getToken() {
  const token = window.PADESTRIAN_MAPBOX_TOKEN;
  if (!token?.startsWith("pk.")) {
    throw new Error(
      "No Mapbox token. Fix .env, restart serve, then hard-refresh.",
    );
  }
  return token;
}

async function getGeoJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Missing ${url}`);
  return res.json();
}

function setVisibility(map, group, visible) {
  for (const id of LAYER_GROUPS[group] || []) {
    if (map.getLayer(id)) {
      map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
    }
  }
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatAddress(props) {
  const line1 = [props["addr:housenumber"], props["addr:street"]]
    .filter(Boolean)
    .join(" ");
  const line2 = props["addr:city"];
  return [line1, line2].filter(Boolean).join(", ");
}

function formatPopup(feature) {
  const p = feature.properties;
  const layerId = feature.layer.id;

  if (layerId === "stops-clusters" && p.point_count != null) {
    return `<strong>${p.point_count.toLocaleString()}</strong> stops — click to zoom in`;
  }

  if (p.label) {
    const title = escapeHtml(p.label);
    if (p.walk_minutes != null) {
      return `<strong>${title}</strong><br><span class="muted">${p.walk_minutes} min walk</span>`;
    }
    return `<strong>${title}</strong>`;
  }

  if (p.rent_cad != null) {
    const title = escapeHtml(p.title || p.address || "Listing");
    const rent = Number(p.rent_cad).toLocaleString();
    const beds =
      p.bedrooms === 0 ? "Studio" : `${p.bedrooms} bed${p.bedrooms === 1 ? "" : "s"}`;
    let html = `<strong>${title}</strong><br>$${rent}/mo · ${escapeHtml(beds)}`;
    if (p.neighborhood) {
      html += `<br><span class="muted">${escapeHtml(p.neighborhood)}</span>`;
    }
    if (p.address) {
      html += `<br><span class="muted">${escapeHtml(p.address)}</span>`;
    }
    return html;
  }

  if (p.stop_name) {
    let html = `<strong>${escapeHtml(p.stop_name)}</strong>`;
    if (p.stop_id) {
      html += `<br><span class="muted">Stop ${escapeHtml(p.stop_id)}</span>`;
    }
    return html;
  }

  if (p.name) {
    let html = `<strong>${escapeHtml(p.name)}</strong>`;
    if (p.shop) html += `<br>${escapeHtml(p.shop)}`;
    const addr = formatAddress(p);
    if (addr) html += `<br><span class="muted">${escapeHtml(addr)}</span>`;
    return html;
  }

  if (p.role === "transit_zone" || p.role === "grocery_zone") {
    const kind = p.role === "transit_zone" ? "Transit" : "Grocery";
    const name = p.label || kind;
    const mins = p.walk_minutes != null ? `${p.walk_minutes} min walk` : "Walk zone";
    return `<strong>${escapeHtml(name)}</strong><br><span class="muted">${escapeHtml(mins)}</span>`;
  }

  const rows = Object.entries(p)
    .filter(([k, v]) => v != null && v !== "" && k !== "role")
    .slice(0, 6)
    .map(([k, v]) => `${escapeHtml(k)}: ${escapeHtml(v)}`);
  return rows.join("<br>") || "No details";
}

function wireHover(map) {
  if (!map._hoverPopup) {
    map._hoverPopup = new mapboxgl.Popup({
      closeButton: false,
      closeOnClick: false,
      offset: 12,
      className: "pad-popup",
    });
  }
  const popup = map._hoverPopup;

  const show = (e) => {
    if (!e.features?.length) return;
    map.getCanvas().style.cursor = "pointer";
    popup
      .setLngLat(e.lngLat)
      .setHTML(formatPopup(e.features[0]))
      .addTo(map);
  };

  const hide = () => {
    map.getCanvas().style.cursor = "";
    popup.remove();
  };

  for (const layerId of HOVER_LAYERS) {
    if (!map.getLayer(layerId) || hoverBound.has(layerId)) continue;
    hoverBound.add(layerId);
    map.on("mouseenter", layerId, () => {
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", layerId, hide);
    map.on("mousemove", layerId, show);
  }
}

function addListings(map, data) {
  if (map.getSource("listings")) return;
  map.addSource("listings", { type: "geojson", data });
  map.addLayer({
    id: "listings-circle",
    type: "circle",
    source: "listings",
    paint: {
      "circle-radius": 8,
      "circle-color": [
        "interpolate",
        ["linear"],
        ["get", "rent_cad"],
        1200,
        "#22c55e",
        1900,
        "#eab308",
        2600,
        "#f97316",
        3400,
        "#dc2626",
      ],
      "circle-stroke-width": 2,
      "circle-stroke-color": "#fff",
      "circle-opacity": 0.92,
    },
  });
}

function addGroceries(map, data) {
  if (map.getSource("groceries")) return;
  map.addSource("groceries", { type: "geojson", data });
  map.addLayer({
    id: "groceries-circle",
    type: "circle",
    source: "groceries",
    paint: {
      "circle-radius": 7,
      "circle-color": "#16a34a",
      "circle-stroke-width": 2,
      "circle-stroke-color": "#fff",
    },
  });
}

function addSmoke(map, data) {
  if (map.getSource("smoke")) return;
  map.addSource("smoke", { type: "geojson", data });
  const zones = ["in", ["get", "role"], ["literal", ["transit_zone", "grocery_zone"]]];
  map.addLayer({
    id: "smoke-zones-fill",
    type: "fill",
    source: "smoke",
    filter: zones,
    paint: {
      "fill-color": [
        "match",
        ["get", "role"],
        "transit_zone",
        "#3b82f6",
        "grocery_zone",
        "#22c55e",
        "#94a3b8",
      ],
      "fill-opacity": 0.3,
    },
  });
  map.addLayer({
    id: "smoke-zones-outline",
    type: "line",
    source: "smoke",
    filter: zones,
    paint: { "line-width": 2, "line-color": "#334155" },
  });
  map.addLayer({
    id: "smoke-centers",
    type: "circle",
    source: "smoke",
    filter: ["==", ["get", "role"], "center"],
    paint: {
      "circle-radius": 6,
      "circle-color": "#111",
      "circle-stroke-width": 2,
      "circle-stroke-color": "#fff",
    },
  });
}

function addStops(map, data) {
  if (map.getSource("stops")) return;
  map.addSource("stops", {
    type: "geojson",
    data,
    cluster: true,
    clusterMaxZoom: 13,
    clusterRadius: 45,
  });
  map.addLayer({
    id: "stops-clusters",
    type: "circle",
    source: "stops",
    filter: ["has", "point_count"],
    paint: {
      "circle-color": "#2563eb",
      "circle-radius": ["step", ["get", "point_count"], 14, 50, 20, 200, 26],
      "circle-stroke-width": 2,
      "circle-stroke-color": "#fff",
    },
  });
  map.addLayer({
    id: "stops-circle",
    type: "circle",
    source: "stops",
    filter: ["!", ["has", "point_count"]],
    paint: {
      "circle-radius": 4,
      "circle-color": "#2563eb",
      "circle-stroke-width": 1,
      "circle-stroke-color": "#fff",
    },
  });
}

async function ensureStops(map) {
  if (stopsAdded) return;
  addStops(map, await getGeoJson("/data/stops.geojson"));
  stopsAdded = true;
  wireHover(map);
  map.on("click", "stops-clusters", (e) => {
    const id = e.features[0].properties.cluster_id;
    map.getSource("stops").getClusterExpansionZoom(id, (err, z) => {
      if (!err) map.easeTo({ center: e.lngLat, zoom: z });
    });
  });
}

async function loadOverlays(map) {
  const missing = [];
  let listingCount = 0;
  try {
    const listings = await getGeoJson("/data/listings.geojson");
    addListings(map, listings);
    listingCount = listings.features?.length ?? 0;
  } catch (e) {
    console.warn(e);
    missing.push("listings");
    const el = document.getElementById("layer-listings");
    if (el) {
      el.disabled = true;
      el.checked = false;
    }
  }
  try {
    addGroceries(map, await getGeoJson("/data/groceries-points.geojson"));
  } catch (e) {
    console.warn(e);
    const el = document.getElementById("layer-groceries");
    if (el) el.checked = false;
  }
  try {
    addSmoke(map, await getGeoJson("/data/isochrones/smoke.geojson"));
  } catch (e) {
    console.warn(e);
    missing.push("smoke");
    const el = document.getElementById("layer-smoke");
    if (el) {
      el.disabled = true;
      el.checked = false;
    }
  }

  wireHover(map);

  for (const id of Object.keys(LAYER_GROUPS)) {
    const box = document.getElementById(`layer-${id}`);
    if (!box) continue;
    box.onchange = () => {
      (async () => {
        if (id === "stops" && box.checked) await ensureStops(map);
        setVisibility(map, id, box.checked);
      })().catch((err) => setStatus(err.message));
    };
    setVisibility(map, id, box.checked);
  }
  const parts = [];
  if (listingCount) parts.push(`${listingCount} listings`);
  if (missing.includes("listings")) {
    parts.push("run validate-listings");
  } else if (missing.length) {
    parts.push("walk zones not loaded");
  }
  setStatus(parts.length ? `Ready — ${parts.join(" · ")}` : "Ready");
}

async function main() {
  try {
    mapboxgl.accessToken = getToken();
    setStatus("Loading map…");

    const map = new mapboxgl.Map({
      container: "map",
      style: STYLE,
      center: CENTER,
      zoom: ZOOM,
    });

    map.addControl(new mapboxgl.NavigationControl(), "top-right");
    window.addEventListener("resize", () => map.resize());
    map.on("error", (e) => console.warn("[mapbox]", e.error));

    map.once("load", () => {
      map.resize();
      loadOverlays(map).catch((err) => setStatus(err.message));
    });
  } catch (err) {
    console.error(err);
    setStatus(err.message);
  }
}

main();
