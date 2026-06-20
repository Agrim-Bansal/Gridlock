# Deploying Gridlock to AWS Lightsail

Single VM: Nginx serves the frontend static build and reverse-proxies `/api/*` to the backend on `:8000`.

## 1. Build the frontend (local machine)

```bash
cd frontend
npm ci && npm run build
```

This produces `frontend/dist/`.

## 2. Provision the VM

- Ubuntu 22.04+ Lightsail instance (1 GB RAM minimum)
- Open ports 80 (and 443 if using HTTPS)

## 3. Copy files to the VM

```bash
VM=<your-vm-ip>

# Frontend
scp -r frontend/dist/ ubuntu@$VM:/var/www/gridlock/dist/

# Backend
rsync -av --exclude='data/' --exclude='__pycache__/' --exclude='.env' \
  backend/ ubuntu@$VM:/opt/gridlock/backend/
```

## 4. Set up the backend

```bash
ssh ubuntu@$VM

cd /opt/gridlock/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: set CORS_ORIGINS to your domain, adjust RETRAIN_DELAY_S if needed

# Create data directory
mkdir -p data
```

## 5. Install the systemd service

```bash
sudo cp /opt/gridlock/backend/deploy/gridlock-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gridlock-backend
sudo systemctl start gridlock-backend

# Verify
sudo systemctl status gridlock-backend
curl http://127.0.0.1:8000/api/model/status
```

## 6. Configure Nginx

```bash
sudo apt install -y nginx
sudo cp /opt/gridlock/backend/deploy/nginx-gridlock.conf /etc/nginx/sites-available/gridlock
sudo ln -sf /etc/nginx/sites-available/gridlock /etc/nginx/sites-enabled/gridlock
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

## 7. Optional: HTTPS with Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

## Updating

```bash
# Frontend: rebuild locally, scp dist/
# Backend: rsync, then:
sudo systemctl restart gridlock-backend
```
