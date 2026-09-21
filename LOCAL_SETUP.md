# Gridlock — Local Setup Guide

Run the full Gridlock stack (backend + frontend) on your local machine. No cloud, no Docker, no Nginx — just two terminal windows.

---

## Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | 3.11+ | `python3 --version` |
| pip | any recent | `pip --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Git | any | `git --version` |

---

## 1. Clone the repo

```bash
git clone <repo-url> gridlock
cd gridlock
```

You now have two main directories: `backend/` (Python/FastAPI) and `frontend/` (React/Vite).

---

## 2. Backend setup

### 2.1 Create a virtual environment and install dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2.2 Configure environment variables

```bash
cp .env.example .env
```

This creates `backend/.env`. Open it and review:

```env
DATA_DIR=./data
DATABASE_URL=sqlite:///./data/gridlock.db
RETRAIN_DELAY_S=2.0
CORS_ORIGINS=["http://localhost:5173"]
PREDICTOR=spectral
CIS_API_KEY=
CIS_TOP_K=20
MAPPLS_CLIENT_ID=
MAPPLS_CLIENT_SECRET=
GEOCODE_DATA_PATH=../api_data/api_responses_predict/reverse_geocode_predict.json
```

**For basic local use, the defaults work as-is.** Here is what each variable does:

| Variable | What it does | Do you need to change it? |
|---|---|---|
| `DATA_DIR` | Where uploaded CSVs and the SQLite database are stored. | No. `./data` is created automatically on startup. |
| `DATABASE_URL` | SQLite connection string. | No. |
| `RETRAIN_DELAY_S` | Artificial delay (seconds) so the UI can show the "Training…" state visibly. | No. `2.0` is fine. |
| `CORS_ORIGINS` | Allowed frontend origins for CORS. | No — `http://localhost:5173` matches Vite's default dev port. |
| `PREDICTOR` | Which ML predictor to use. `spectral` = the real Spectral Ridge model, `stub` = a simpler deterministic stub. | No. `spectral` is recommended. Use `stub` if you want faster startup without real ML. |
| `CIS_API_KEY` | API key for external Congestion Impact Score service. | No. Leave empty — the system uses synthetic/fallback scores. |
| `CIS_TOP_K` | How many top cells get CIS enrichment. | No. |
| `MAPPLS_CLIENT_ID` | MapmyIndia API credentials (for geocoding). | No. Leave empty — location names will be null but everything else works. |
| `MAPPLS_CLIENT_SECRET` | MapmyIndia API secret. | No. Same as above. |
| `GEOCODE_DATA_PATH` | Path to a pre-fetched reverse-geocode JSON file for cell location names. | No. If the file doesn't exist, the backend logs a warning and continues — cells just won't have location names. |

### 2.3 Start the backend

```bash
# Make sure the venv is activated
uvicorn app.main:app --reload --port 8000
```

You should see output like:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Database initialized at sqlite:///./data/gridlock.db
```

### 2.4 Verify

Open a new terminal and run:

```bash
curl http://localhost:8000/api/model/status
```

Expected response:

```json
{"status":"idle","last_trained_at":null,"dataset_count":0,"total_rows":0}
```

`"idle"` means the backend is running but no training data has been uploaded yet. This is correct.

---

## 3. Frontend setup

Open a **second terminal** (keep the backend running in the first).

### 3.1 Install dependencies

```bash
cd frontend
npm ci
```

### 3.2 Configure environment variables

The frontend ships with a `.env` file already at `frontend/.env`:

```env
VITE_API_BASE_URL=/api
VITE_MAPBOX_TOKEN=
VITE_USE_MOCKS=false
```

| Variable | What it does | Do you need to change it? |
|---|---|---|
| `VITE_API_BASE_URL` | Base path for API calls. | No. `/api` is correct — Vite's dev server proxies `/api/*` to the backend at `localhost:8000` automatically. |
| `VITE_MAPBOX_TOKEN` | Mapbox GL JS access token for the map. | **Optional.** If empty, the app uses Leaflet + OpenStreetMap as a free fallback. If you have a Mapbox account, paste your token here for nicer map tiles. |
| `VITE_USE_MOCKS` | Use static mock data instead of the live backend. | Set to `true` if you want to run the frontend **without** the backend (design/UI work). Set to `false` (default) for full-stack. |

### 3.3 Start the frontend

```bash
npm run dev
```

Output:

```
  VITE v5.x.x  ready in Xms

  ➜  Local:   http://localhost:5173/
```

### 3.4 Open the app

Go to **http://localhost:5173** in your browser.

---

## 4. Using the app (end-to-end test)

With both backend and frontend running:

1. **Navigate to Data Management** (top nav bar).
2. **Upload a CSV** — drag-and-drop or click to select a `.csv` file. The CSV should have columns for `timestamp`, `latitude`, `longitude`, and optionally `violation` (type) and `severity`. Example row:
   ```
   timestamp,latitude,longitude,violation,severity
   2024-03-31T08:15:00,12.9716,77.5946,Signal Jumping,high
   ```
3. **Watch the status bar** — it transitions from **Idle** → **Training…** → **Ready** (takes a few seconds).
4. **Go to Dashboard** — predictions load for the forecast date (day after the last timestamp in your CSV).
5. The map shows colored grid cells and the side panel shows ranked hotspots.

---

## 5. Frontend-only mode (no backend)

If you only want to work on the frontend UI without running the backend:

1. Edit `frontend/.env`:
   ```env
   VITE_USE_MOCKS=true
   ```
2. Run `npm run dev` as usual.
3. The app loads static mock data from `frontend/src/api/mocks/` — no network calls to the backend.

---

## 6. Mapbox token (optional, for better maps)

The app works without a Mapbox token (falls back to Leaflet + OpenStreetMap). For the Mapbox experience:

1. Create a free account at [mapbox.com](https://www.mapbox.com/).
2. Copy your **default public token** from the account dashboard.
3. Paste it in `frontend/.env`:
   ```env
   VITE_MAPBOX_TOKEN=pk.eyJ1Ij...your_token_here
   ```
4. Restart the frontend dev server (`Ctrl+C` then `npm run dev`).

---

## 7. Quick reference

### Start everything (two terminals)

**Terminal 1 — Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

**Open:** http://localhost:5173

### Other useful commands

| Command | Where | What |
|---|---|---|
| `npm run build` | `frontend/` | Production build → `dist/` |
| `npm run lint` | `frontend/` | ESLint check |
| `npm run typecheck` | `frontend/` | TypeScript type check |
| `python -m pytest tests/ -v` | `backend/` (venv active) | Run backend tests |

---

## Troubleshooting

**Backend won't start / import errors**
→ Make sure the venv is activated (`source venv/bin/activate`) and you ran `pip install -r requirements.txt`.

**Frontend shows "Failed to fetch predictions" / network errors**
→ The backend isn't running, or it's on a different port. Ensure the backend is up at `localhost:8000` and `VITE_USE_MOCKS=false` in `frontend/.env`.

**Map is blank / no tiles loading**
→ If `VITE_MAPBOX_TOKEN` is empty, the app should auto-fallback to Leaflet. If both fail, check your network connection. OpenStreetMap tiles require internet access.

**"No model trained yet" on Dashboard**
→ Expected when first starting. Go to Data Management and upload a CSV. Once the model trains, predictions appear.

**Port 5173 or 8000 already in use**
→ Kill the existing process or change the port. For the backend: `uvicorn app.main:app --reload --port 8001` (and update `CORS_ORIGINS` in `backend/.env` and the proxy target in `frontend/vite.config.ts`). For the frontend: `npx vite --port 3000`.
