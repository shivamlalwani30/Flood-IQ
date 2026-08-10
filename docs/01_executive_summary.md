# FloodIQ — Executive Summary

## The Problem

Every year, **1,600 Indians die in urban floods** — not from drowning, but from ambulances that couldn't reach them, fire trucks blocked by inundated roads, and rescue teams following GPS routes that don't know water exists.

India loses **₹20,000 crore annually** in direct flood damage. The 2015 Chennai floods killed 500 people and caused ₹20,000 crore in losses alone. The 2022 Bengaluru floods submerged 20,000 homes and stranded 6 lakh residents. In every case, the emergency response was compromised by the same gap: **no routing tool knew which roads were flooded.**

Google Maps navigated ambulances into chest-deep water during Bengaluru 2022 because its routing engine has no mechanism to ingest real-time flood data. Weather apps showed rain alerts. Flood monitoring dashboards showed water levels. But the system that tells an emergency vehicle *which road to take right now* had no connection to any of this.

That gap kills people.

## The Solution

**FloodIQ** is a real-time flood-aware emergency routing system for Indian cities.

When rainfall sensors detect flooding, FloodIQ dynamically reclassifies road segments as impassable or slow, recomputes optimal routes for every active emergency vehicle within 2 seconds, and broadcasts updated paths to dispatchers via WebSocket — all while simultaneously offering citizens a safe evacuation route that explicitly avoids flood zones. A RandomForest ML model trained on 10 years of IMD-calibrated rainfall data gives emergency coordinators a 6-hour flood forecast per zone so they can pre-position resources before roads become impassable.

FloodIQ is not a flood alert app, a weather dashboard, or a chatbot. It is a **graph-algorithm-based dynamic routing engine** with a real-time coordination layer on top.

## Impact Potential

- **Coverage today:** Every Indian city with OpenStreetMap data — all 500+ major cities — can run FloodIQ with a 15-minute city-graph download.
- **Lives addressable:** If FloodIQ reduces emergency response failure during floods by 20%, approximately 320 Indian lives are saved per year, rising to 1,000+ with national NDMA adoption.
- **Cost:** Zero proprietary data dependency. The entire stack runs on free, open data (OSM + SRTM elevation + IMD public rainfall data).
- **NDMA alignment:** Integrates directly with the National Disaster Management Authority's API-based alert infrastructure. One endpoint connects FloodIQ to the national emergency system.

## Team

| Name | Role |
|------|------|
| [Team Member 1] | Backend architecture, graph routing engine, WebSocket system |
| [Team Member 2] | ML model, data engineering, IMD data pipeline |
| [Team Member 3] | Frontend (React/Leaflet), UI/UX, citizen view |
| [Team Member 4] | Documentation, deployment (Vercel/Render), demo coordination |

**College:** [Your Institution]  
**Project timeline:** 6 days (Samsung Solve for Tomorrow 2026)  
**Live demo:** [your-vercel-url]  
**Source code:** [your-github-url]
