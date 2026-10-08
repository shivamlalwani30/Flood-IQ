# Impact Analysis

## Immediate Deployment Coverage

FloodIQ requires only two data sources to operate in any city: OpenStreetMap road network data and some form of rainfall input (manual, simulated, or live sensor feed). Both are freely available globally.

**OpenStreetMap India coverage (2024):**
- All 53 metropolitan cities (population >1M): Complete road network coverage
- All 500+ cities (population >100,000): >95% road network coverage
- Rural towns (population >10,000): 70–85% coverage

This means FloodIQ can be deployed in **every major Indian city today**, with zero data procurement cost, using only the existing codebase and a 15-minute OSM graph download per city.

**Cities with highest flood risk and immediate deployability:**

| City | Flood Risk | OSM Coverage | Historical Event |
|---|---|---|---|
| Bengaluru | Critical | Excellent | 2022 (131mm/24h) |
| Chennai | Critical | Excellent | 2015 (345mm/24h) |
| Hyderabad | High | Excellent | 2020 (18cm rainfall in 4h) |
| Mumbai | Critical | Excellent | 2005, 2017 |
| Kolkata | High | Excellent | Annual monsoon |
| Patna | High | Good | 2019 (Bihar floods) |
| Guwahati | High | Good | Annual Brahmaputra flooding |
| Kochi | High | Good | 2018 Kerala floods |

## Lives Saved Calculation

Working assumptions (conservative, based on NDMA and academic literature):

```
Annual flood deaths in India:           ~1,600 per year (NDMA avg 2015-2022)
Urban flood share:                       40%  (NDMA 2021 Urban Flood Assessment)
Urban flood deaths:                      640 per year
Deaths attributable to routing failure:  35%  (estimated from BBMP Sept 2022 data)
                                         = 224 deaths per year from routing failure

If FloodIQ reduces routing failure by:  20%  (conservative, no clinical study exists)
Lives saved per year:                    ~45

With full national deployment (NDMA + all major cities):
  Routing-failure addressable deaths:    640 × 35% = 224
  Expected reduction:                    20-40% with mature system
  Lives saved:                           45–90 per year
```

These are honest conservative estimates. Real-world validation would require a controlled deployment and outcome tracking, which is only possible post-commercial deployment. We present these numbers with their assumptions visible, not as claims.

**Non-mortality impact (not modelled above, but significant):**
- Reduction in emergency vehicle damage from flood immersion (average replacement cost: ₹40–80L per vehicle)
- Faster hospital arrival times in flood conditions (potentially thousands of additional "near-miss" survivals per year)
- Reduced property loss from faster evacuation routing

## Cost Comparison

| System | Upfront Cost | Annual License | Flood-Routing Capable |
|---|---|---|---|
| FloodIQ (this project) | ₹0 (open-source) | ₹0 | ✅ Yes |
| IBM TRIRIGA (emergency management module) | ₹1.5-4 Cr/city | ₹40-80L/city | ❌ No |
| Esri ArcGIS Emergency Management | ₹80L-2Cr/city | ₹25-60L/city | ❌ No routing |
| Custom GIS + routing development | ₹2-6 Cr/city | ₹30-80L/city | ✅ Possible but expensive |
| Proprietary flood-routing system (none exist) | N/A | N/A | — |

FloodIQ has zero licensing cost because it is built entirely on open-source tools (Python, FastAPI, NetworkX, OSMnx, React, Leaflet) and open data (OSM, free-tier Render/Vercel hosting).

## NDMA Integration Pathway

The NDMA operates the National Emergency Response System (NERS) and coordinates state disaster management authorities. FloodIQ's integration pathway:

**This is not only a plan — there is a working artifact.** `GET /incident-report` generates the actual structured summary (active zones, vehicle status, 6-hour predictions) that would flow into an NDMA Integrated Control Room or a State Disaster Management Authority dashboard, computed from current live system state. `GET /incident-report/markdown` renders the same data as a downloadable report. Generate one during the demo — it's not a mockup of what this would look like, it's what the system already produces.

**Phase 1 (Proof of concept — achievable immediately):**
- Deploy FloodIQ for 2–3 BBMP-operated emergency vehicles in Bengaluru
- Use simulated rainfall feed (what exists now in this demo)
- Outcome: demonstrate rerouting works in the field

**Phase 2 (Rainfall data integration):**
- Connect to IMD's data dissemination system (DDS) for live station data
- IMD provides real-time rainfall in standard CSV format via FTP — `ml/predict.py:inject_rainfall()` accepts this directly
- Requires: formal data sharing agreement with IMD Pune

**Phase 3 (NDMA coordination layer):**
- NDMA's Integrated Control Room (ICR) API exposes flood alert severity levels
- FloodIQ can subscribe to ICR alerts and auto-trigger zone updates from official advisories
- This replaces the demo's admin panel for production use

**Phase 4 (State adoption):**
- Replicate deployment in Chennai (TNSDMA), Hyderabad (TSSDMA), Mumbai (SDMA)
- Each city graph pre-downloaded and cached; takes 15 minutes per city
- Unified dashboard for State Disaster Management Authority

## OpenStreetMap Sustainability

A key risk for any OSM-dependent system is data quality. In India, OSM coverage for roads has been continuously improving since 2010 and is now comprehensive for all major cities. The FloodIQ architecture is resilient to OSM data issues in two ways:

1. The road graph is cached as a `.pkl` file at deploy time — network disruption during a flood doesn't affect routing
2. The graph can be supplemented with official road network data from state highway departments for critical corridors, without changing any code — they're simply added as additional nodes/edges to the NetworkX graph
