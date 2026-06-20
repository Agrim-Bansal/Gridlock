# Gridlock — Project Status & Deployment Guide

## What's Done

### Frontend (complete)
- Full React SPA with Vite + TypeScript + Tailwind CSS
- Dashboard page: Mapbox/Leaflet map with GeoJSON hotspot cells, severity coloring, click popups
- Ranking panel: two tabs (by violations, by congestion impact), peak-hour chips, click-to-fly
- Data management page: drag-and-drop CSV upload with 5-row preview, dataset table, delete
- API seam: `api/types.ts` (raw) → `api/mappers.ts` (conversion) → `types/index.ts` (domain)
- Three Zustand stores: predictions, datasets, model status
- Mock mode (`VITE_USE_MOCKS=true`) with static JSON — works with no backend
- Dark/light theme auto-switching
- Status bar with model state pill, last trained timestamp, dataset count
- Error banners, empty states, loading spinners
- Builds cleanly (`npm run build` produces `dist/`)

### Backend (complete)
- FastAPI service honoring API_CONTRACT.md exactly (all 5 endpoints)
- SQLite persistence (datasets + violation rows) + raw CSVs on disk
- CSV ingest with flexible column aliases (lat/latitude, lon/lng/longitude, etc.)
- Predictor seam: `Predictor` Protocol with `StubPredictor` behind a registry
- Stub predictor: date-seeded randomness, 30 Bengaluru landmarks, data-biased after training, only "No Parking" violations
- Percentile-based severity assignment in service layer
- Background retrain with configurable delay (observable `idle → training → ready`)
- Structured error responses (`{error, message}`) for all non-2xx codes
- CORS configured for frontend origin
- 18 tests passing (grid math + contract shape validation)
- Deploy artifacts: systemd unit, nginx config, step-by-step guide

### Shared
- Grid math parity: `backend/app/grid.py` and `frontend/src/lib/grid.ts` use identical constants
- API contract documented in `API_CONTRACT.md`

---

## What's Left

### Must-do (demo-blocking)

1. **End-to-end integration test** — Run frontend + backend together locally and verify the full flow: upload CSV → model trains → fetch predictions → map renders cells → ranking rows match → click interactions work. Currently only tested in isolation (frontend against mocks, backend against test client).

2. **Sample CSV** — Create a realistic sample CSV file (`sample_data/bengaluru_violations.csv`) with ~500-1000 rows covering Bengaluru coordinates, timestamps across different hours/days, and "No Parking" violations. This is needed for the demo and for anyone testing the app.

3. **Provision the Lightsail VM** — Create the instance, open ports 80/443, SSH in. Not yet done.

4. **Deploy** — Follow the deployment steps below.

### Should-do (polish)

5. **Frontend `VITE_USE_MOCKS=false`** — Flip mock mode off and test against the live backend. Verify the API seam handles real responses correctly (timestamps, null location names, empty peak hours, etc.).

6. **CORS origin for production** — Update `CORS_ORIGINS` in the backend `.env` to match the actual domain or Lightsail public IP.

7. **Frontend env for production** — Set `VITE_API_BASE_URL=/api` (already the default) and optionally add a Mapbox token for better map tiles.

8. **Retrain delay tuning** — The default `RETRAIN_DELAY_S=2.0` is meant to make the `training` state observable in the UI. Adjust if the frontend polls too fast or too slow.

### Nice-to-have (not demo-blocking)

9. **Real ML model** — Drop in a `RealPredictor` implementing the `Predictor` protocol in `backend/app/ml/real.py`, add it to the registry, set `PREDICTOR=real` in `.env`. Zero router/service changes needed.

10. **HTTPS** — Run `certbot --nginx -d yourdomain.com` on the VM if a domain is available. Not needed for HTTP demo.

11. **More violation types** — The stub currently only generates "No Parking". If the demo needs variety, update `StubPredictor._make_violation_types()` in `backend/app/ml/stub.py`.

12. **Monitoring/logs** — `journalctl -u gridlock-backend -f` works for systemd. No structured logging beyond FastAPI's defaults.

---

## How to Deploy

Single AWS Lightsail VM. Nginx serves the static frontend and reverse-proxies `/api/*` to the backend on port 8000.

```
Internet ──80──▶ Nginx ┬── /        → /var/www/gridlock/dist/  (SPA, fallback to index.html)
                       └── /api/*   → http://127.0.0.1:8000    (FastAPI via uvicorn)
```

### Step 1: Build the frontend (on your local machine)

```bash
cd frontend
npm ci
npm run build
# produces frontend/dist/
```

### Step 2: Provision the VM

- Create an Ubuntu 22.04+ Lightsail instance (1 GB RAM minimum)
- Open port 80 in the networking tab (and 443 if using HTTPS later)
- Note the public IP

### Step 3: Copy files to the VM

```bash
VM=<your-lightsail-ip>

# Frontend static build
scp -r frontend/dist/ ubuntu@$VM:/var/www/gridlock/dist/

# Backend code (excluding runtime data and venv)
rsync -av \
  --exclude='data/' \
  --exclude='venv/' \
  --exclude='__pycache__/' \
  --exclude='.env' \
  --exclude='.pytest_cache/' \
  backend/ ubuntu@$VM:/opt/gridlock/backend/
```

### Step 4: Set up the backend on the VM

```bash
ssh ubuntu@$VM

# Create directories
sudo mkdir -p /var/www/gridlock/dist
sudo mkdir -p /opt/gridlock/backend

# Python environment
cd /opt/gridlock/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env
# Set CORS_ORIGINS=["http://<your-lightsail-ip>"]
# Leave other defaults as-is

# Create data directory
mkdir -p data

# Quick test — should return {"status":"idle",...}
uvicorn app.main:app --port 8000 &
curl http://127.0.0.1:8000/api/model/status
kill %1
```

### Step 5: Install the systemd service

```bash
sudo cp /opt/gridlock/backend/deploy/gridlock-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gridlock-backend
sudo systemctl start gridlock-backend

# Verify it's running
sudo systemctl status gridlock-backend
curl http://127.0.0.1:8000/api/model/status
```

### Step 6: Configure Nginx

```bash
sudo apt update && sudo apt install -y nginx
sudo cp /opt/gridlock/backend/deploy/nginx-gridlock.conf /etc/nginx/sites-available/gridlock
sudo ln -sf /etc/nginx/sites-available/gridlock /etc/nginx/sites-enabled/gridlock
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

The app is now live at `http://<your-lightsail-ip>/`.

### Step 7 (optional): HTTPS

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### Updating after changes

```bash
# Frontend: rebuild locally, then:
scp -r frontend/dist/ ubuntu@$VM:/var/www/gridlock/dist/

# Backend: rsync code, then:
ssh ubuntu@$VM "sudo systemctl restart gridlock-backend"
```

### Troubleshooting

| Symptom | Check |
|---|---|
| 502 Bad Gateway | `sudo systemctl status gridlock-backend` — is uvicorn running? |
| CORS errors in browser | Does `CORS_ORIGINS` in `.env` match the URL in the browser address bar? |
| "No model trained" (409) | Upload a CSV on the Data Management page first. |
| Map shows no tiles | Set `VITE_MAPBOX_TOKEN` in `frontend/.env` and rebuild, or use without (Leaflet/OSM fallback). |
| Predictions don't change after upload | Wait 2-3 seconds for retrain, then re-fetch. Check model status pill shows "Ready". |
| Backend logs | `journalctl -u gridlock-backend -f` |
| Nginx logs | `/var/log/nginx/error.log` |
