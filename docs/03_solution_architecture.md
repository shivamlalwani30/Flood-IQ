# Solution Architecture

## System Overview

FloodIQ is a three-tier real-time system: a React/Leaflet frontend communicates with a FastAPI backend over both REST (for initial data load) and WebSocket (for live event streaming), while an embedded ML layer predicts flood expansion using a trained RandomForest model.

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                       │
│                                                           │
│  EmergencyDashboard  │  CitizenView  │  PredictionPanel  │
│         FloodMap (Leaflet + CARTO dark tiles)            │
│              AdminPanel (demo control)                    │
└──────────────┬──────────────────────┬────────────────────┘
               │ REST /route          │ WebSocket /ws
               │ GET /zones           │ ← flood_zone_update
               │ GET /vehicles        │ ← vehicle_rerouted
               │ GET /predict         │ ← prediction_update
               │                      │ ← alert
               │                      │ → trigger_flood
               │                      │ → add_vehicle
               ▼                      ▼
┌─────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                      │
│                                                           │
│  routers/routing.py    → flood-aware Dijkstra            │
│  routers/flood_zones.py → zone state management          │
│  routers/prediction.py  → ML inference endpoint          │
│  routers/vehicles.py    → vehicle CRUD                   │
│                                                           │
│  core/graph_engine.py   → OSMnx + NetworkX graph         │
│  core/flood_weights.py  → edge weight modifier           │
│  core/routing_engine.py → flood-aware pathfinding         │
│  core/cascade.py        → multi-zone cascade simulation   │
│  core/websocket_manager.py → broadcast manager           │
│  core/state.py          → in-memory + JSON state         │
│                                                           │
│  ml/train_model.py      → RandomForest trainer           │
│  ml/predict.py          → inference + rainfall state     │
│  ml/backtest_chennai_2015.py → historical validation     │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│                   DATA LAYER (files)                      │
│                                                           │
│  data/bengaluru_graph.pkl   — cached OSM road network    │
│  data/flood_zones.json      — active flood zone state    │
│  data/rainfall_history.csv  — ML training data (10y)    │
│  ml/model.pkl               — trained RandomForest       │
└─────────────────────────────────────────────────────────┘
```

## Component Breakdown

### Frontend

**FloodMap.jsx** — The visual centerpiece. Renders a CARTO dark-tile Leaflet base map with three dynamic layers: flood zone polygons (color-coded by depth, pulsing red when impassable), emergency vehicle markers (emoji div-icons, clickable), and route polylines (teal, ~5px weight). Designed as the primary "hero" of the interface — the map is the product, everything else is a control panel around it.

**EmergencyDashboard.jsx** — Dispatcher right-rail. Lists active vehicles, shows ETA/distance, exposes the "Recalculate Route" button that triggers the core demo moment. "ROUTE BLOCKED" badge appears automatically when a vehicle's path intersects a new flood zone via WebSocket.

**CitizenView.jsx** — Minimal safe-route finder. Three interactions: enter origin → enter destination → click Find Safe Route. Returns the safest path (not the fastest), with a count of flood zones avoided on the original fastest route.

**PredictionPanel.jsx** — ML forecast display. Lists all zones with a 0–100% probability bar, predicted depth, and color coding (teal < 40%, amber 40–70%, red > 70%). Model accuracy badge shown in header.

**AdminPanel.jsx** — Demo control surface. Zone flood trigger (dropdown + depth slider), manual vehicle add, and the full scripted-demo run button that sequences all demo steps automatically.

### Backend

**core/graph_engine.py** — Loads the Bengaluru drivable road network via OSMnx, caches to `.pkl` for fast startup (~1ms vs 30–60s download). Includes a synthetic 144-node grid fallback that lets the rest of the stack run without network access (venue wifi protection).

**core/flood_weights.py** — Applies per-zone flood multipliers to graph edge weights: `∞` for >60cm (impassable), `5×` for 30–60cm (very slow), `2×` for 0–30cm (minor slowdown). This is the core innovation — standard Dijkstra becomes flood-aware simply by having accurate edge weights.

**core/routing_engine.py** — The actual pathfinding computation: runs `nx.shortest_path` with `weight="flood_weight"`, then computes distance and a flood-adjusted ETA (the same per-edge multiplier used for routing cost is also applied to travel time, so a "slow" edge correctly adds real minutes, not just abstract routing score). This module is shared identically by the REST `/route` endpoint and the WebSocket handler's auto-reroute logic — they were originally separate implementations, and the WebSocket copy had two bugs (ETA ignoring flood slowdown entirely, and missing the case where a path exists topologically but every option crosses an impassable zone, giving it infinite cost without NetworkX raising `NoPathError`). Both were caught via direct testing against the routing logic and fixed by consolidating to one shared, tested implementation.

**core/cascade.py** — Multi-zone cascade simulation. Triggering a sufficiently severe flood (>30cm) computes which nearby zones (within 3km, via haversine distance on real zone coordinates) are most likely to flood next, scored as a blend of geographic proximity (45%) and the ML model's own predicted risk for that specific candidate zone (55%) — with a regional rainfall signal injected into each candidate first, since a storm severe enough to flood one zone is realistically raining on its neighbors too, just less intensely with distance. This is deliberately weighted toward the model's assessment rather than pure proximity, so the cascade is a genuine demonstration of the prediction system influencing what happens next, not a scripted "zone 2 floods after zone 1" animation with the ML model along for show.

**core/websocket_manager.py** — Singleton manager tracking all connected WebSocket clients, broadcasting events to all of them. Dead connections are silently pruned on next broadcast.

**core/state.py** — In-memory application state. Flood zone depths (mirrored to `data/flood_zones.json`), vehicle positions and ETAs. All shared via a module-level singleton imported by both routers and the WebSocket handler.

**ml/train_model.py** — Generates a 10-year, 438,000-row synthetic IMD-style rainfall dataset, trains a RandomForest classifier (flood/no-flood) and regressor (depth_cm). Achieved 82.4% accuracy on held-out test set.

**ml/predict.py** — Inference layer with a per-zone rainfall accumulator. When flood events are triggered via WebSocket, rainfall signals are injected into the accumulator, so subsequent predictions reflect the current simulated state of the city rather than static values.

## Data Flow: Rainfall → Reroute → UI

```
1. Admin panel triggers flood event
        │
        ▼
2. WebSocket server receives { event: "trigger_flood", zone_id: "KRM_01", depth_cm: 65 }
        │
        ▼
3. core/state.py: set_flood_depth("KRM_01", 65)  →  updates flood_zones.json
        │
        ▼
4. ml/predict.py: inject_rainfall("KRM_01", ~52mm)  →  updates zone rainfall state
        │
        ▼
5. core/flood_weights.py: apply_flood_weights(G, active_zones)
        │   → marks ~18 edges as ∞ weight (impassable around KRM_01)
        │
        ▼
6. For each active vehicle with a destination:
        │   nx.shortest_path(G, origin, dest, weight="flood_weight")
        │   → new path avoids impassable edges
        │
        ▼
7. WebSocket broadcast to ALL connected clients:
        │   { event: "flood_zone_update", data: { zone_id, depth_cm, polygon } }
        │   { event: "vehicle_rerouted",  data: { vehicle_id, new_path, new_eta } }
        │   { event: "prediction_update", data: { zone_id, 6h_probability } }
        │   { event: "alert",             data: { severity: "HIGH", message } }
        │
        ▼
8. React state updates:
        │   FloodMap: re-renders flood zone polygon as red
        │   EmergencyDashboard: shows new ETA, "ROUTE BLOCKED" if prior path cut
        │   PredictionPanel: updates probability bar for KRM_01 → 99%
        │   Polyline: redraws around the flood zone
        │
        ▼
9. Total latency from admin trigger to map update: < 200ms (LAN)
```

## Technology Choices Justified

**OSMnx + NetworkX** over commercial routing APIs: Free, open data, works for every Indian city immediately, and gives us direct access to the graph structure so we can mutate edge weights — which a black-box routing API cannot expose.

**RandomForest** over deep learning: Interpretable (feature importances presentable to judges), handles tabular data well, trains in minutes not hours on modest hardware, and achieves the target accuracy (82.4%) without needing a GPU. NDMA data scientists use similar ensemble methods.

**WebSocket (native FastAPI)** over polling: Push architecture means dispatcher and citizen views update within ~100ms of a flood event, not within the next polling interval. This is what makes the live demo visually dramatic and immediately intelligible to judges.

**No database (JSON files + in-memory)** for MVP: Eliminates a failure mode. No database means no connection string, no migration, no auth, no instance to spin up. State.json can be inspected and edited by hand if anything goes wrong during the demo.

**Vercel + Render** for deployment: Both have free tiers with sufficient CPU for the demo, both support Python (Render) and React (Vercel) natively, and both deploy from GitHub push — meaning a hotfix can be live in under 3 minutes if a judge finds a bug.
