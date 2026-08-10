# FloodIQ

**Real-time flood-aware emergency routing for Indian cities.**

> "1,600 Indians die in floods every year. Not from drowning — from ambulances that couldn't reach them."

FloodIQ dynamically reroutes emergency vehicles around flooded roads in real time. When rainfall triggers a flood zone, a modified Dijkstra algorithm recalculates the safest path within 2 seconds and broadcasts the update to dispatchers and citizens via WebSocket.

**Live demo:** [your-vercel-url]  
**Samsung Solve for Tomorrow 2026** — Environmental Sustainability track

---

## What This Is

- A **graph-algorithm-based dynamic routing engine** (flood-aware Dijkstra on OSM road data) with a live before/after route comparison and a real-time algorithm diff panel
- A **real-time WebSocket coordination dashboard** for emergency dispatchers, hardened against malformed input
- A **RandomForest ML flood prediction system** (82.4% accuracy, trained on 10-year IMD-calibrated data) that drives a genuine multi-zone cascade simulation, not a scripted animation
- A **citizen-facing safe route generator** (avoids flooded roads, not just fastest path)
- A **historical replay mode** that re-enacts real documented rainfall timelines (Bengaluru 2022, Chennai 2015) through the live system
- A **"Judge Verification Mode"** that re-runs the actual test suite on demand, live, with real timing — every documented number can be regenerated in front of you
- An **incident report generator** producing the data structure an NDMA Integrated Control Room would actually consume

## What This Is Not

- A flood alert app
- A weather dashboard  
- A chatbot
- A generic mapping application

---

## Quick Start (under 15 minutes)

**One-shot setup:**

```bash
./setup.sh
```

This creates the backend virtual environment, installs all dependencies, trains the ML model, and runs `npm install` for the frontend. Then start both servers:

```bash
# Terminal 1
cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
```

Open `http://localhost:5173`.

**Manual setup**, if you prefer step by step:

```bash
# Backend
cd backend
pip install -r requirements.txt
python -m ml.train_model          # trains RandomForest (~2 min)
uvicorn main:app --reload          # starts at http://localhost:8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev                        # starts at http://localhost:5173
```

See `docs/07_deployment_guide.md` for production deployment (Vercel + Render).

---

## Presentation

The 7-slide judged presentation deck is at `presentation/slides.html` — open it directly in any browser (no build step). Navigate with arrow keys, spacebar, or on-screen buttons. Designed to match the demo script in `demo/demo_script.md` exactly.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Leaflet.js, TailwindCSS, Framer Motion, Lucide icons, Socket.io client |
| Backend | FastAPI, NetworkX, WebSockets (native) |
| ML | scikit-learn RandomForest, pandas, numpy |
| Road data | OpenStreetMap via OSMnx |
| Elevation | SRTM (zone elevation features) |
| Training data | Synthetic IMD-calibrated rainfall (10 years, 438k rows) |
| Deployment | Vercel (frontend) + Render (backend) |

---

## Repository Structure

```
floodiq/
├── frontend/                React + Leaflet app
│   ├── .env.example         API/WS URL template
│   └── src/
│       ├── components/      FloodMap, EmergencyDashboard, CitizenView,
│       │                    PredictionPanel, AdminPanel
│       ├── hooks/           useWebSocket (auto-reconnect, tested against
│       │                    real disconnects — see hooks/useWebSocket.js)
│       └── utils/           mapHelpers (flood colors, formatting)
├── backend/                 FastAPI server
│   ├── core/
│   │   ├── graph_engine.py        OSMnx + NetworkX graph, .pkl cached
│   │   ├── flood_weights.py       edge weight modifier (2×/5×/∞)
│   │   ├── routing_engine.py      flood-aware pathfinding + algorithm
│   │   │                          diff trace, shared by REST + WebSocket
│   │   ├── cascade.py             ML-driven multi-zone cascade simulation
│   │   ├── historical_replay.py   real Bengaluru 2022 / Chennai 2015
│   │   │                          rainfall timelines, compressed
│   │   ├── verification.py        live re-run of the actual test suite
│   │   ├── incident_report.py     NDMA-style structured report generator
│   │   ├── state.py               in-memory + JSON state, input-validated
│   │   └── websocket_manager.py   broadcast manager
│   ├── routers/
│   │   ├── routing.py             POST /route (+ comparison + diff trace)
│   │   ├── flood_zones.py         GET /zones, /scenarios
│   │   ├── prediction.py          GET /predict, /predict/model-info
│   │   ├── vehicles.py            CRUD for emergency vehicles
│   │   └── verification.py        POST /verify, GET /incident-report[/markdown]
│   ├── ml/                  train_model, predict, backtest_chennai_2015
│   └── requirements.txt
├── setup.sh                 one-shot backend+frontend setup script
├── docs/                    9 documentation sections
│   ├── 01_executive_summary.md
│   ├── 02_problem_research.md
│   ├── 03_solution_architecture.md
│   ├── 04_algorithm_documentation.md
│   ├── 05_ml_model_documentation.md
│   ├── 06_api_reference.md
│   ├── 07_deployment_guide.md
│   ├── 08_impact_analysis.md
│   └── 09_limitations_and_future_work.md
├── demo/
│   └── demo_script.md       90-second judged demo script + bonus features
│                             + judge Q&A, including Verification Mode
└── presentation/
    └── slides.html           7-slide judged presentation deck
```

---

## Key Technical Facts (for judges)

| Claim | Evidence |
|---|---|
| Route recalculation < 2 seconds | Benchmarked at 3.8ms average on test graph |
| ML accuracy 82.4% | Reproducible: `python -m ml.train_model` |
| Chennai 2015 correctly flagged | Reproducible: `python -m ml.backtest_chennai_2015` |
| Zero proprietary data | OSM (open) + synthetic IMD-calibrated data (open methodology) |
| Multi-city ready | `get_graph(place="Chennai, India")` — 15 minutes per city |
| Every number above is live-reproducible, not just doc claims | `POST /verify` or the "RUN LIVE VERIFICATION" button in the Admin tab re-runs all of it on demand, with real per-check timing |
| WebSocket reconnect actually works under real disconnects | Verified with a hand-built test server simulating real connection drops — see `frontend/src/hooks/useWebSocket.js` header comment |
| Input validation rejects malformed data without dropping connections | `core/state.py` clamps/rejects bad coordinates and depths; `main.py`'s `_handle_ws_event` catches malformed payloads per-message |

---

## Documentation

All 9 documentation sections are in `/docs`. The API reference is also auto-generated at `http://localhost:8000/docs` (Swagger UI) when the backend is running.

---

## Team

[Your team names and roles here]  
[Your college/institution]  
Samsung Solve for Tomorrow 2026
