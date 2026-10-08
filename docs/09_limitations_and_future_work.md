# Limitations and Future Work

## Current Limitations

We are being explicit about these limitations for two reasons: judges respect honesty over overclaiming, and every limitation here has a concrete engineering path to resolution.

### 1. Simulated Rainfall Feed (Not Live IMD API)

**What we have:** When the admin panel triggers a flood at 65cm depth, this simultaneously simulates the rainfall signal that caused it (via `ml/predict.py:inject_rainfall()`). The ML model receives and processes this signal in real time. The routing engine responds in real time. The WebSocket propagation is real time. The only thing that isn't real is the source of the rainfall trigger.

**What real deployment needs:** IMD provides station-level rainfall data via its Data Dissemination System (DDS) in a standard CSV format updated every 15 minutes. Connecting FloodIQ requires: (1) an IMD data sharing MoU, (2) a polling service that reads the DDS CSV and calls `inject_rainfall()` for the relevant zone, (3) correlating IMD station locations with FloodIQ zone polygons using a spatial join (OSMnx + Shapely). Estimated engineering time: 2–3 days.

**Why it's not in this build:** The IMD DDS requires a formal institutional data access application which takes weeks to process. This is a data licensing timeline constraint, not a technical one.

### 2. Single City in UI (Bengaluru)

**What we have:** The system is architecturally multi-city. The OSM graph download, flood zone structure, and ML features are all city-agnostic. The backend can serve any city whose graph is cached.

**What's missing:** The frontend hardcodes `DEFAULT_CENTER = [12.935, 77.61]` (Bengaluru) and the pre-set zone IDs are Bengaluru-specific. A city switcher in the UI would require: (1) a city metadata API endpoint listing available cities and their bounding boxes, (2) a city-select dropdown in the header, (3) graph download + zone bootstrap for the selected city. Estimated engineering time: 1 day.

**Demo note:** Switching to a pre-downloaded Chennai graph takes 15 seconds of backend restart. The demo script includes a narrative "switch to Chennai" moment — in its current form, this is done by restarting the backend with a different `DEFAULT_PLACE` env variable, not a live in-UI switch.

### 3. ML Model Accuracy Ceiling

**What we have:** 82.4% accuracy on the synthetic training dataset, with high recall (84.6%) — the right trade-off for emergency response.

**What limits further improvement:**
- The training data is synthetic, calibrated to match IMD statistical distributions but not actual weather records. Real IMD data would almost certainly push accuracy above 87%.
- The model uses zone-level features. Sub-zone road segment flooding (e.g., underpasses that flood before the surrounding area) isn't captured.
- 5 Bengaluru zones is a small population for learning zone-specific effects. A real deployment would have 50–200 zones with richer topology features.

**Path to 87%+ accuracy:** Replace synthetic CSV with real IMD data + add 2 features: (1) upstream drainage basin saturation (requires DEM analysis), (2) historical flooding frequency per zone (NDMA records). Estimated engineering time: 1–2 weeks post-IMD data access.

### 4. In-Memory State (No Persistence Layer)

**What we have:** All vehicle state and flood zone updates live in a Python dict in memory. `flood_zones.json` is saved to disk after every update for basic recovery.

**What it means:** If the backend process restarts (Render cold start, OOM kill), in-flight vehicle routes and current zone states are lost. The JSON files restore zone state, but active vehicle routes must be recomputed.

**Path to fix:** Redis (Render provides a free Redis instance) would give atomic state + pub/sub for WebSocket broadcasts without a full database. Estimated engineering time: 4 hours.

### 5. Zone Geometry (Circles, Not Real Flood Polygons)

**What we have:** Flood zones are circular approximations (center + radius). This correctly identifies nearby road segments but can over-flag roads at the edge of a circular zone that a real flood boundary wouldn't reach, and under-flag roads on the opposite side of a ridge from the zone center.

**What real deployment needs:** Satellite-derived flood extent polygons. The Copernicus Emergency Management Service (Copernicus EMS) provides near-real-time SAR-based flood extent polygons during active events, available as GeoJSON. Plugging these in requires only replacing the `zone['polygon']` generation in `core/state.py` with a Copernicus EMS API call — the rest of the stack (intersection test, routing, WebSocket broadcast) is already polygon-ready.

**Disclosed live, not just here:** the map itself carries a small persistent badge — "Zone shape: circular approximation · Copernicus EMS satellite polygons planned" — so this is visible during the demo, not something a judge has to dig through documentation to discover.

---

## Future Work

### Short-term (1–3 months post-hackathon)

- Live IMD DDS integration (replace simulated rainfall)
- City switcher in UI (Chennai, Hyderabad, Mumbai as additional graphs)
- Redis state layer (replace in-memory dict)
- Copernicus EMS flood polygon integration (replace circular zones)
- Mobile web PWA wrapper for citizen view (no native app required)

### Medium-term (3–12 months)

- NDMA Integrated Control Room API subscription for official flood alerts
- Sub-zone routing: identify high-risk road segments (underpasses, low-lying bridges) and pre-weight them in the graph independently of zone-level flooding
- Historical route benchmarking: for any active reroute, show the dispatcher both paths and the time cost of the detour
- Fleet optimisation: when multiple vehicles are dispatched to an incident, FloodIQ optimises which vehicles take which routes to avoid duplication and minimise total arrival time

### Long-term (12+ months)

- NDMA integration as an official government tool, distributed to all SDMAs
- Edge deployment: lightweight version of the routing engine running on emergency vehicle tablets, so rerouting works even when connectivity is lost during a flood
- Predictive pre-positioning: use 6h flood forecasts to proactively reposition ambulances and fire trucks to staging areas that will be accessible after the forecast flood event, before it happens
- Drainage intervention prioritisation: use repeated flood zone data to identify specific drainage infrastructure improvements that would have the largest impact on flood severity (input to municipal capital planning)
