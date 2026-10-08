# Deployment Guide

Target: Fresh machine to fully running demo in under 15 minutes.

---

## Prerequisites

- Python 3.11+ (`python3 --version`)
- Node.js 18+ (`node --version`)
- Git

---

## Local Setup

### 1. Clone

```bash
git clone https://github.com/[your-org]/floodiq.git
cd floodiq
```

### 2. Backend (FastAPI)

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate       # macOS/Linux
# venv\Scripts\activate        # Windows

# Install dependencies
pip install -r requirements.txt

# Train the ML model (first run only — takes ~2 minutes)
python -m ml.train_model

# Start the server
uvicorn main:app --reload --port 8000
```

**If `pip install` reports a dependency conflict:** the heaviest packages here (`osmnx`, `geopandas`, `shapely`) pull in their own sub-dependencies, and pip's resolver can occasionally surface a version clash that wasn't visible just from reading `requirements.txt`. This has not been verified with an actual live install in the environment this project was built in (no network access there). If you hit a conflict, the safe fix is usually to loosen the specific pinned version pip complains about to a compatible range (e.g. `networkx>=3.3,<4.0` instead of `networkx==3.3`) rather than fighting the exact pin — none of this project's own code depends on an exact patch version of any dependency.

**Important exception — do not casually bump `osmnx` past 1.x:** `core/graph_engine.py`'s `bbox=` tuple is ordered `(north, south, east, west)`, which is correct for OSMnx 1.x (the pinned `osmnx==1.9.4`) but **silently wrong** for OSMnx 2.x, which reorders the same parameter to `(west, south, east, north)`. This isn't a version pip will refuse to install or that will throw an error — the call still succeeds, it just downloads the wrong geographic bounding box with no warning. If you ever upgrade this dependency, also flip that tuple order (see the comment directly above the call site in `graph_engine.py`).

Server starts at `http://localhost:8000`. Visit `http://localhost:8000/docs` for interactive API explorer.

**First startup note:** On first run with no cached `.pkl`, the server will download the Bengaluru road graph from OpenStreetMap (~60 seconds, requires internet). Subsequent startups load from cache in ~1 second. If you're in a no-internet environment, the server automatically falls back to a synthetic 144-node test graph that exercises all routing and flood-weight logic correctly.

**ML model warm-up:** every startup also loads the trained model into memory (~1.3 seconds), so the very first request to `/predict` or the Forecast tab doesn't race a cold disk read. You'll see the server take roughly 1–2 seconds total before logging `Application startup complete` — that's expected, not a hang.

### 3. Frontend (React)

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

App starts at `http://localhost:5173`.

### 4. Verify everything works

Open `http://localhost:5173`. You should see:

- Dark map of Bengaluru with CARTO tiles loaded
- Header showing "LIVE" in teal (WebSocket connected)
- Admin tab → click "TRIGGER FLOOD: KRM_01 @ 65cm" → red polygon appears on map
- Dispatch tab → click "Add ambulance" → ambulance emoji appears on map
- Click "RECALCULATE ROUTE" → teal polyline appears on map
- Forecast tab → KRM_01 shows ~99% flood probability

If WebSocket shows "RECONNECTING…", check that the backend is running on port 8000.

---

## Environment Variables

### Backend

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8000` | Server port (set by Render automatically) |

No API keys required for MVP. All data sources are open/free.

### Frontend

Create `frontend/.env` (or set in Vercel dashboard):

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Backend REST URL |
| `VITE_WS_URL` | `ws://localhost:8000/ws` | Backend WebSocket URL |

For production (after deploying backend to Render):
```env
VITE_API_URL=https://floodiq-backend.onrender.com
VITE_WS_URL=wss://floodiq-backend.onrender.com/ws
```

---

## Production Deployment

### Backend → Render

1. Push backend code to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Settings:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt && python -m ml.train_model`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Free (512MB RAM is sufficient for the synthetic graph; upgrade to Starter for the full OSM graph)
5. Click Deploy
6. Note your Render URL (e.g. `https://floodiq-backend.onrender.com`)

### Frontend → Vercel

1. Push frontend code to GitHub
2. Go to [vercel.com](https://vercel.com) → New Project
3. Import your GitHub repo
4. Settings:
   - **Root Directory:** `frontend`
   - **Framework Preset:** Vite
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
5. Add environment variables (in Vercel dashboard → Settings → Environment Variables):
   ```
   VITE_API_URL = https://floodiq-backend.onrender.com
   VITE_WS_URL  = wss://floodiq-backend.onrender.com/ws
   ```
6. Click Deploy

### Vercel config file (`frontend/vercel.json`)

```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

---

## Health Check Endpoints

After deployment, verify with:

```bash
curl https://floodiq-backend.onrender.com/health
# Expected: {"status":"ok","service":"floodiq-backend"}

curl https://floodiq-backend.onrender.com/zones
# Expected: {"zones":[...]}

curl https://floodiq-backend.onrender.com/predict
# Expected: {"predictions":[...]}
```

---

## Pre-Demo Checklist (Day of Presentation)

Run through this at least 30 minutes before judges arrive:

- [ ] Backend health check returns 200 (`curl http://localhost:8000/health`)
- [ ] Admin tab → "RESET TO CLEAN STATE" once, just to start from a known-clean baseline
- [ ] Admin tab → "RUN LIVE VERIFICATION" → all 5 checks pass (confirms graph, routing, ML, Chennai backtest, and input validation are all genuinely working, not just the UI)
- [ ] Frontend loads at your Vercel URL
- [ ] Header shows neither "BACKEND UNREACHABLE" nor "WEBSOCKET CONNECTING" — should read "LIVE FEED" in teal
- [ ] Trigger flood in KRM_01 → red polygon appears on map within 1 second
- [ ] Add an ambulance → emoji marker appears on map
- [ ] Recalculate route → teal polyline appears, curves around KRM_01
- [ ] Citizen view: "Koramangala" → "Manipal Hospital" → route displayed
- [ ] Forecast tab: KRM_01 shows >90% probability after flood trigger
- [ ] Open DevTools → Network → WS tab: confirm WebSocket messages flowing
- [ ] Admin tab → "RESET TO CLEAN STATE" again, leaving the system in a clean state for the actual demo start
- [ ] Backup demo video loaded and playable on a separate device
- [ ] Demo script memorized, timed to 90 seconds
