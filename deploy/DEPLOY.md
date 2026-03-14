# GB Golf Optimizer — VPS Deployment Guide

Target: Hostinger KVM 2 VPS
URL after deployment: `http://gameblazers.silverreyes.net/golf`

---

## Prerequisites

1. Python >= 3.10 installed on the VPS:
   ```bash
   python3 --version
   ```
2. `git` and `pip` are installed:
   ```bash
   git --version && pip3 --version
   ```
3. Nginx is installed and running (Open Claw is already using it — this config coexists via a separate server block).

---

## Step-by-Step Deployment

### 1. Get the project onto the VPS

**Option A — git clone:**
```bash
git clone https://github.com/YOUR_USER/GBGolfOptimizer.git /path/to/GBGolfOptimizer
```

**Option B — scp from local machine:**
```bash
scp -r /local/path/to/GBGolfOptimizer user@VPS_IP:/path/to/GBGolfOptimizer
```

Replace `/path/to/GBGolfOptimizer` with the actual absolute path you want on the server (e.g. `/home/silver/GBGolfOptimizer`).

### 2. Create a virtual environment and install dependencies

```bash
cd /path/to/GBGolfOptimizer
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

This installs `gbgolf` as an editable package plus all dependencies (Flask, PuLP, etc.) declared in `pyproject.toml`.

### 3. Edit the systemd service file

Open `deploy/gbgolf.service` and replace every placeholder:

| Placeholder | Replace with |
|---|---|
| `<deploy_user>` | Your VPS Linux username (e.g. `silver`) |
| `/path/to/GBGolfOptimizer` | Absolute path from Step 1 (all four occurrences) |

Example after editing:
```ini
User=silver
WorkingDirectory=/home/silver/GBGolfOptimizer
Environment="PATH=/home/silver/GBGolfOptimizer/venv/bin"
Environment="SCRIPT_NAME=/golf"
ExecStart=/home/silver/GBGolfOptimizer/venv/bin/gunicorn \
    --workers 2 \
    --bind unix:/home/silver/GBGolfOptimizer/gbgolf.sock \
    --umask 007 \
    wsgi:app
```

Note on worker count: 2 workers match the 2 vCPUs on the Hostinger KVM 2. Each worker handles one request at a time; 2 avoids core contention while allowing concurrent requests.

### 4. Install and start the systemd service

```bash
sudo cp deploy/gbgolf.service /etc/systemd/system/gbgolf.service
sudo systemctl daemon-reload
sudo systemctl enable gbgolf
sudo systemctl start gbgolf
```

### 5. Verify the service is running

```bash
sudo systemctl status gbgolf
```

Look for `active (running)`. If it shows `failed`, check the logs:
```bash
sudo journalctl -u gbgolf -n 50
```

### 6. Confirm the socket was created

```bash
ls -la /path/to/GBGolfOptimizer/gbgolf.sock
```

You should see the socket file with group `www-data` permissions (mode `srwxrwx---` or similar).

### 7. Edit the Nginx config file

Open `deploy/gameblazers.silverreyes.net.nginx` and replace the single placeholder:

| Placeholder | Replace with |
|---|---|
| `/path/to/GBGolfOptimizer` | Absolute path from Step 1 |

### 8. Check for conflicts before deploying Nginx config

Confirm no existing server block already uses `gameblazers.silverreyes.net`:
```bash
sudo nginx -T | grep server_name
```

Confirm no port conflict (Nginx should already own port 80):
```bash
ss -tlnp | grep :80
```

### 9. Deploy the Nginx config

```bash
sudo cp deploy/gameblazers.silverreyes.net.nginx /etc/nginx/sites-available/gameblazers.silverreyes.net
sudo ln -s /etc/nginx/sites-available/gameblazers.silverreyes.net /etc/nginx/sites-enabled/
```

### 10. Test and reload Nginx

```bash
sudo nginx -t
```

If the test passes (no errors):
```bash
sudo systemctl reload nginx
```

### 11. Smoke test

```bash
curl -s -o /dev/null -w "%{http_code}" http://gameblazers.silverreyes.net/golf/
```

Expected: `200`

If you get `502 Bad Gateway`, the Gunicorn socket is not reachable — check Step 6 and `journalctl -u gbgolf`.
If you get `404`, Nginx is running but the location block is not matching — verify Step 9 and `sudo nginx -T`.

---

## Optional: DNS Setup

If `gameblazers.silverreyes.net` is not yet pointing to the VPS, add an A record in your DNS provider:

- **Type:** A
- **Name:** `gameblazers`
- **Value:** VPS public IP address
- **TTL:** 300 (or your provider's default)

## Optional: HTTPS with Let's Encrypt

After DNS propagates and the smoke test passes on HTTP:

```bash
sudo certbot --nginx -d gameblazers.silverreyes.net
```

Certbot will obtain a certificate and automatically update the Nginx config to redirect HTTP to HTTPS.

---

## Open Claw Coexistence

This deployment uses a dedicated `server_name gameblazers.silverreyes.net` block. It does **not** modify any existing server block used by Open Claw. Run `sudo nginx -T` before and after deploying to confirm no existing blocks are changed.

---

## Quick Reference: Service Commands

```bash
# Status
sudo systemctl status gbgolf

# Restart after code update
sudo systemctl restart gbgolf

# View logs (last 100 lines)
sudo journalctl -u gbgolf -n 100

# Stop
sudo systemctl stop gbgolf
```
