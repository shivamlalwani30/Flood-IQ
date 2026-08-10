# API Reference

Interactive docs auto-generated at: `http://localhost:8000/docs` (Swagger UI) when the backend is running.

---

## REST Endpoints

### Health Check

**GET /health**

Returns service liveness status.

```json
{ "status": "ok", "service": "floodiq-backend" }
```

---

### Routing

**POST /route**

Computes a flood-aware shortest path between two points. Accepts either lat/lng coordinates or free-text place names (resolved against a Bengaluru landmark lookup).

Request body:
```json
{
  "origin_lat": 12.9352,
  "origin_lng": 77.6142,
  "destination_lat": 12.9610,
  "destination_lng": 77.6387,
  "vehicle_id": "AMB_01"
}
```

Or with place text:
```json
{
  "origin_text": "Koramangala",
  "destination_text": "Manipal Hospital"
}
```

Response:
```json
{
  "path_coords": [[12.935, 77.614], [12.937, 77.618], "..."],
  "distance_m": 4320.5,
  "eta_seconds": 847,
  "impassable_edges_avoided": 18,
  "compute_ms": 3.8,
  "original_path_coords": [[12.935, 77.614], "..."],
  "original_distance_m": 3980.0,
  "original_eta_seconds": 620,
  "crosses_flood_zone": true,
  "edge_weight_changes": [
    { "from_node": 0, "to_node": 12, "base_length_m": 444.0, "flood_weight": 2220.0, "multiplier": "5.0×" }
  ]
}
```

`original_*` fields show what a flood-naive system (e.g. standard Google Maps) would have computed for the same trip, using plain distance/travel-time with flood conditions ignored entirely — used by the frontend to render both routes for comparison. `crosses_flood_zone` is `true` when that naive route would have crossed an active zone; the comparison is only shown to the user in that case. `edge_weight_changes` traces which edges on the *final chosen* route had a flood-modified weight, capped at 8 entries, for the algorithm diff panel.
Errors:
- `404` — place name could not be resolved
- `409` — no passable route exists under current flood conditions

---

### Flood Zones

**GET /zones**

Returns all flood zones with current depth and rendered polygon.

```json
{
  "zones": [
    {
      "zone_id": "KRM_01",
      "label": "Koramangala 5th Block",
      "depth_cm": 65,
      "center_lat": 12.935,
      "center_lng": 77.614,
      "radius_m": 600,
      "polygon": [[12.940, 77.614], "... 16 points"]
    }
  ]
}
```

**GET /zones/{zone_id}**

Returns a single zone by ID. `404` if the zone ID is unknown.

---

### Historical Replay Scenarios

**GET /scenarios**

Lists available historical replay scenarios for the admin panel's replay selector.

```json
{
  "scenarios": [
    { "id": "bengaluru_2022", "label": "Bengaluru, September 5 2022", "summary": "131mm of rain in 24 hours...", "total_duration_s": 48 },
    { "id": "chennai_2015", "label": "Chennai, December 1-3 2015", "summary": "345mm in 24 hours at peak...", "total_duration_s": 52 }
  ]
}
```

**GET /scenarios/{scenario_id}**

Returns the full step-by-step timeline for one scenario (zone, depth, delay, narration per step) — see `core/historical_replay.py`. `404` if the scenario ID is unknown.

### Prediction

**GET /predict**

Returns the ML model's 6-hour-ahead flood probability and predicted depth for all zones.

```json
{
  "predictions": [
    {
      "zone_id": "KRM_01",
      "probability_6h": 0.993,
      "predicted_depth_cm": 98.8
    },
    {
      "zone_id": "BTM_01",
      "probability_6h": 0.124,
      "predicted_depth_cm": 0.0
    }
  ]
}
```

**GET /predict/model-info**

Returns trained model evaluation metrics.

```json
{
  "accuracy": 0.824,
  "precision": 0.596,
  "recall": 0.846,
  "f1": 0.699,
  "confusion_matrix": [[54311, 12129], [3259, 17901]],
  "feature_importance": {
    "rainfall_6h_mm": 0.4158,
    "rainfall_24h_mm": 0.2957,
    "soil_saturation": 0.166,
    "...": "..."
  },
  "n_train": 350400,
  "n_test": 87600
}
```

---

### Verification

**POST /verify**

"Judge Verification Mode" — re-runs the actual core test suite live and returns real results: graph load, a real flood-aware route computation against current state, the trained model's held-out evaluation metrics, the Chennai 2015 backtest, and a live input-validation check. Every number is computed at request time, not cached. Takes roughly 1–4 seconds depending on whether the ML model needs to load from disk first.

```json
{
  "checks": [
    { "name": "Road graph load", "passed": true, "detail": "144 nodes, 528 edges", "ms": 1.2 },
    { "name": "Flood-aware route computation", "passed": true, "detail": "23 waypoints, 9768m, 1172.2s ETA", "ms": 2.1 },
    { "name": "ML model evaluation", "passed": true, "detail": "accuracy=0.8243, precision=0.5961, recall=0.8460, f1=0.6994", "ms": 8.4 },
    { "name": "Chennai 2015 historical backtest", "passed": true, "detail": "peak probability=0.9925, predicted depth=98.8cm, correctly flagged=True", "ms": 412.3 },
    { "name": "Input validation (malformed depth values)", "passed": true, "detail": "3/3 invalid inputs correctly rejected, zone state preserved=True (0.0cm unchanged)", "ms": 0.3 }
  ],
  "total_ms": 424.3,
  "all_passed": true
}
```

**GET /incident-report**

Generates a point-in-time incident report (JSON) from current live state — active flood zones, vehicle status, and 6-hour predictions. This is the data shape that would feed an NDMA Integrated Control Room or a State Disaster Management Authority dashboard; see `docs/08_impact_analysis.md` for the full integration pathway.

**GET /incident-report/markdown**

Same report, rendered as a downloadable `.md` file (sent with a `Content-Disposition: attachment` header so it saves directly rather than rendering in-browser).

**POST /reset**

Demo-day recovery: clears every flood zone back to dry (0cm), removes all vehicles, and clears the ML prediction rainfall accumulators — a genuinely clean restart without stopping the backend process. Broadcasts a `state_reset` WebSocket event so every connected client (not just whoever called this endpoint) clears its local state too.

### Vehicles

**GET /vehicles**

Returns all registered emergency vehicles.

```json
{
  "vehicles": [
    {
      "id": "AMB_01",
      "lat": 12.9341,
      "lng": 77.6119,
      "type": "ambulance",
      "eta_seconds": 847,
      "distance_m": 4320,
      "status": "en_route"
    }
  ]
}
```

**POST /vehicles**

Register a new vehicle. `400` if `lat`/`lng` are out of valid range (`lat` in [-90, 90], `lng` in [-180, 180]).

```json
{ "id": "AMB_04", "lat": 12.97, "lng": 77.59, "type": "ambulance" }
```

**GET /vehicles/{vehicle_id}**

Single vehicle by ID.

**DELETE /vehicles/{vehicle_id}**

Remove a vehicle from the system.

---

## WebSocket API

Endpoint: `ws://localhost:8000/ws`

The frontend connects to this endpoint at startup and maintains a persistent connection with auto-reconnect (exponential backoff, max 8s interval). All real-time events travel over this single connection.

### Server → Client Events

**flood_zone_update** — Emitted when a zone's flood depth changes.
```json
{
  "event": "flood_zone_update",
  "data": {
    "zone_id": "KRM_01",
    "label": "Koramangala 5th Block",
    "depth_cm": 65,
    "polygon": [[12.940, 77.614], "..."],
    "center_lat": 12.935,
    "center_lng": 77.614,
    "radius_m": 600
  }
}
```

**vehicle_rerouted** — Emitted when any vehicle is given a new path due to a flood event.
```json
{
  "event": "vehicle_rerouted",
  "data": {
    "vehicle_id": "AMB_01",
    "new_path": [[12.935, 77.614], "..."],
    "new_eta": 1020
  }
}
```

**prediction_update** — Emitted when the ML model updates its forecast for a zone.
```json
{
  "event": "prediction_update",
  "data": {
    "zone_id": "KRM_01",
    "6h_probability": 0.993,
    "predicted_depth_cm": 98.8
  }
}
```

**vehicle_added** — Broadcast to all connected clients when any client adds a vehicle, so multiple simultaneous viewers (e.g. dispatch on one screen, citizen view on another) stay in sync.
```json
{
  "event": "vehicle_added",
  "data": {
    "id": "AMB_04",
    "lat": 12.97,
    "lng": 77.59,
    "type": "ambulance",
    "destination_lat": null,
    "destination_lng": null,
    "eta_seconds": null,
    "distance_m": null,
    "status": "idle"
  }
}
```

**state_reset** — Broadcast after `POST /reset`. All clients should clear their local flood zones, vehicles, predictions, and any active route/comparison state.
```json
{ "event": "state_reset", "data": { "message": "All zones dry, all vehicles cleared." } }
```

**alert** — High-severity operational alert broadcast to all clients.
```json
{
  "event": "alert",
  "data": {
    "severity": "HIGH",
    "message": "Koramangala 5th Block is now impassable (65cm). Rerouting affected vehicles.",
    "zones_affected": ["KRM_01"]
  }
}
```

### Client → Server Events

All events below are validated server-side. Malformed payloads (missing fields, wrong types, out-of-range values) are rejected with a logged warning and a `LOW` severity alert sent back to that client — the connection is never dropped because of a bad message.

**trigger_flood** — Admin/demo panel sends this to simulate a flood event.
```json
{ "event": "trigger_flood", "data": { "zone_id": "KRM_01", "depth_cm": 65 } }
```
`depth_cm` must be numeric; it is clamped to the 0–500cm range regardless of the value sent.

**trigger_cascade** — Floods the given zone exactly like `trigger_flood`, then plans and schedules secondary flooding of nearby zones (within 3km), weighted by a blend of geographic proximity and the ML model's own predicted risk for each candidate zone. Each cascade step is broadcast as its own `flood_zone_update` + `prediction_update` + `alert` sequence over the following several seconds — see `core/cascade.py` for the scoring logic.
```json
{ "event": "trigger_cascade", "data": { "zone_id": "KRM_01", "depth_cm": 75 } }
```
Only triggers below severity 30cm produce no cascade (too minor a basis for spreading). Zones beyond 3km of the origin are never included regardless of severity.

**add_vehicle** — Register a new vehicle from the admin panel.
```json
{ "event": "add_vehicle", "data": { "id": "AMB_04", "lat": 12.97, "lng": 77.59, "type": "ambulance" } }
```
`lat` must be in [-90, 90] and `lng` in [-180, 180]; both must be numeric.

**request_route** — Request a flood-aware route for a vehicle to a destination. Fully implemented and uses the same `compute_flood_aware_path` logic as everything else, but not wired to any UI control in this demo — `AdminPanel`'s flood/cascade triggers and `EmergencyDashboard`'s recalculate button cover the demo's actual interaction surface. This endpoint exists for direct API/system integration (e.g. a dispatch system assigning a new destination to a vehicle programmatically) rather than manual use through the FloodIQ UI.
```json
{
  "event": "request_route",
  "data": {
    "vehicle_id": "AMB_04",
    "destination_lat": 12.98,
    "destination_lng": 77.60
  }
}
```
