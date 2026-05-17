# Forecast — riktom.com

Research-weighted 24-hour hunt + fish activity forecast. Lives at `forecast.riktom.com`.

## Stack
- **Backend:** Python 3.12 + FastAPI + httpx, served by uvicorn on `127.0.0.1:8004`, systemd unit `forecast-api.service`
- **Frontend:** Static HTML/CSS/vanilla-JS — no build step
- **Data source:** Open-Meteo (free, no API key)

## Algorithm

Two scoring profiles (`fish` and `hunt`) over the same data inputs. Both use 8 weighted factors that score 0–10 per hour. Composite is weighted average → scaled 0–100.

**Fish profile** is ported from [Tnijem/hahirafish](https://github.com/Tnijem/hahirafish). Weights are research-justified: water temperature (22%), front passage (20%), time of day (18%), wind/dissolved-oxygen proxy (14%), solunar (10%), pressure trend (9%), moon phase (4%), cloud cover (3%).

**Hunt profile** is whitetail-tuned: dawn/dusk window (25%), front passage (20%), temperature drop (15%), wind/scent (12%), pressure trend (10%), moon phase (8%), solunar (7%), cloud cover (3%).

The differentiator vs commercial apps: weights reflect peer-reviewed evidence rather than tradition. Barometric pressure is intentionally underweighted; dissolved-oxygen and front-passage signals are weighted more heavily.

## Repo layout

```
backend/
  app/
    main.py        FastAPI routes (/api/health, /api/profiles, /api/forecast)
    scoring.py     scoring engine — assembles factor scores into composite
    profiles.py    fish + hunt profiles (weights + per-factor scoring functions)
    weather.py     Open-Meteo client with 30-min in-process cache
    solunar.py     Meeus astronomical algorithms — moon phase + transit times
  requirements.txt
frontend/
  index.html       Species toggle, lat/lon input, geolocation
  app.js           Renders bars + factor breakdown
  style.css
```

## API

- `GET /api/health` — `{ok: true}`
- `GET /api/profiles` — list of `fish` / `hunt` profiles with weights
- `GET /api/forecast?lat=&lon=&species=fish|hunt` — 24h forecast JSON

## Deploy (VPS)

Mirrors the existing `firewatcher` deployment pattern.

```bash
cd /opt && git clone https://github.com/riktom-com/forecast.git
cd /opt/forecast/backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# systemd unit (see forecast-api.service in repo root)
cp /opt/forecast/forecast-api.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now forecast-api

# nginx site at /etc/nginx/sites-available/forecast.riktom.com (template in repo)
ln -s /etc/nginx/sites-available/forecast.riktom.com /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# SSL
certbot --nginx -d forecast.riktom.com
```

## DNS

Requires `A forecast.riktom.com → 72.62.83.12` at Squarespace, OR a wildcard `A * → 72.62.83.12`.

## Roadmap

- Per-species hunt profiles (turkey, hog) alongside whitetail
- Saved locations
- Push notifications for top windows
- Historical accuracy tracking


## Standardized Nav (rk-nav)

This app uses the shared riktom.com nav block (scoped `.rk-*` classes, self-contained CSS) that is identical across all 11 riktom.com properties. The block is enclosed by marker comments:

```
<!-- rk-nav:start -->
... nav HTML + scoped style ...
<!-- rk-nav:end -->
```

**To update the nav site-wide** (add a new app, change a link, restyle):
1. Edit `/tmp/patch_navs.py` on the VPS (or `/tmp/sync/patch_local.py` for local repos) with the new HTML.
2. Re-run the patcher — it finds the markers and replaces the block in place. The replace is idempotent.
3. For repos with React/Vite builds (e.g. fire-watcher), re-patch after rebuild since `dist/index.html` is regenerated.

Nav contents: Logo · About · Blog · Apps ▾ (11 apps) · 💡 Suggest · 🏠 Home (top-right white pill).
