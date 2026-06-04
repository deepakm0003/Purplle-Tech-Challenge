# Purplle Tech Challenge 2026 — Store Intelligence

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-Vite-646cff.svg)](https://react.dev/)
[![License](https://img.shields.io/badge/license-Hackathon--submission-lightgrey.svg)]()

**Author:** [deepakm0003](https://github.com/deepakm0003) — individual submission, no co-authors.

End-to-end **offline store intelligence**: raw anonymised CCTV → structured behavioural events → real-time analytics API → live React dashboard. Built for the Purplle Tech Challenge 2026 Round 2 take-home.

---

## Table of contents

1. [What this repo delivers](#what-this-repo-delivers)
2. [Architecture](#architecture)
3. [Repository layout](#repository-layout)
4. [Screenshots](#screenshots)
5. [Prerequisites](#prerequisites)
6. [Quick start (reviewer — 5 commands)](#quick-start-reviewer--5-commands)
7. [Full local setup (with CCTV videos)](#full-local-setup-with-cctv-videos)
8. [Detection pipeline](#detection-pipeline)
9. [API reference](#api-reference)
10. [Dashboard](#dashboard)
11. [Docker](#docker)
12. [Stores: Store 1 vs Store 2](#stores-store-1-vs-store-2)
13. [Submission checklist](#submission-checklist)
14. [Do I submit the CCTV videos?](#do-i-submit-the-cctv-videos)
15. [Documentation](#documentation)

---

## What this repo delivers

| Layer | Implementation | Output |
|-------|----------------|--------|
| **Detection** | YOLOv8 + ByteTrack, zone polygons, staff heuristics | JSONL events (`ENTRY`, `ZONE_*`, `BILLING_*`, …) |
| **Intelligence API** | FastAPI, in-memory + optional Postgres, POS correlation | `/events/ingest`, `/stores/{id}/metrics`, funnel, heatmap, anomalies, `/health` |
| **Dashboard** | React + Vite + TanStack Query | Store selector, overview, sales/CCTV, live metrics |
| **Production** | Docker Compose, structured logs, pytest (>70% target) | `docker compose up` |

North-star metric: **offline conversion rate** = purchasers ÷ unique visitors (staff excluded).

---

## Architecture

```text
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌──────────────┐
│ Store 1/2   │     │ detector/        │     │ api/ + analytics│     │ Dashboard    │
│ *.mp4       │────▶│ process_video.py │────▶│ FastAPI         │────▶│ localhost:   │
│ (local only)│     │ YOLO + tracker   │     │ metrics/funnel  │     │ 5173         │
└─────────────┘     └──────────────────┘     └─────────────────┘     └──────────────┘
                              │                        ▲
                              ▼                        │
                    output/ + data/bootstrap/   POST /events/ingest
                    *.jsonl events              GET  /stores/{id}/…
```

**Committed without videos:** `store-intelligence/data/bootstrap/{store}/events/*.jsonl` so reviewers see live metrics immediately after `docker compose up`.

---

## Repository layout

```text
Purplle-Tech-Challenge/                    ← Git root (this repo)
├── README.md                            ← You are here
├── docs/screenshots/                    ← Add PNGs for README gallery
├── store-intelligence/                  ← Backend + CV pipeline
│   ├── api/
│   │   ├── main.py                      FastAPI app, static mounts for video/tracks
│   │   ├── bootstrap_data.py            Load JSONL + POS on startup
│   │   ├── routes/
│   │   │   ├── analytics.py             Challenge endpoints + ingest
│   │   │   └── stores.py                Multi-store dashboard, cameras, POS
│   │   └── services/
│   │       ├── store_catalog.py         Store 1 / Store 2 config
│   │       └── store_service.py         POS aggregation per store
│   ├── detector/
│   │   ├── process_video.py             CLI: one MP4 → one JSONL
│   │   ├── event_generator.py           ENTRY, ZONE_*, queue events
│   │   ├── entry_backfill.py            Fix missing ENTRY rows for metrics
│   │   └── detection_filters.py         Blur/mirror false-positive filters
│   ├── analytics/                       metrics, funnel, heatmap, anomalies
│   ├── config/
│   │   ├── stores.json                  ST1008 / ST2002 cameras & paths
│   │   ├── zones.json                   Store 1 zone polygons
│   │   └── store-2-zones.json           Store 2 zone polygons
│   ├── data/bootstrap/                  Committed pipeline events (no MP4)
│   ├── scripts/
│   │   ├── process_stores.py            Batch all cameras both stores
│   │   ├── backfill_entry_events.py     ENTRY backfill for footfall
│   │   └── sync_bootstrap_events.py     Copy output → data/bootstrap
│   ├── tests/                           pytest unit + integration
│   ├── docker-compose.yml               Postgres + Redis + API
│   ├── DESIGN.md                        Architecture + AI-assisted decisions
│   ├── CHOICES.md                       Model, schema, API trade-offs
│   └── requirements.txt
│
└── store-intelligence-dashboard/        ← Frontend
    ├── src/
    │   ├── context/StoreContext.tsx     Store 1 / Store 2 switch
    │   ├── pages/
    │   │   ├── BrigadeOverview.tsx      Overview metrics
    │   │   ├── POSAnalytics.tsx         Sales & intelligence
    │   │   └── StoreCCTV.tsx            CCTV + track overlay
    │   └── services/apiClient.ts        API base URL + store header
    └── package.json
```

### Local-only paths (never commit)

Place these **next to** the `Purplle-Tech-Challenge` folder (parent directory on your machine):

```text
Purple Tech Hiring Challenge/          ← parent folder on disk
├── Store 1/                         CAM 3 entry, CAM 1/2 zone, CAM 5 billing
├── Store 2/                         entry 1/2, zone, billing_area
├── POS - sample transactionsb1e826f.csv
├── sample_eventsbe42122.jsonl
└── Purplle-Tech-Challenge/          ← git clone root
```

---

## Screenshots

Add your captures under [`docs/screenshots/`](docs/screenshots/README.md). Below: placeholders (images appear once files exist).

### GitHub repository

![GitHub repository](docs/screenshots/01-github-repository.png)

### Dashboard — store overview

![Dashboard overview](docs/screenshots/02-dashboard-overview.png)

### Sales & intelligence

![Sales and intelligence](docs/screenshots/03-sales-intelligence.png)

### CCTV with detection overlay

![CCTV tracking](docs/screenshots/04-store-cctv-tracks.png)

### Store map / heatmap

![Store heatmap](docs/screenshots/05-store-map-heatmap.png)

### API (Swagger / metrics)

![API documentation](docs/screenshots/06-api-swagger.png)

### Docker Compose running

![Docker Compose](docs/screenshots/07-docker-compose.png)

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| Docker Desktop | optional, for `docker compose` |
| GPU | optional; CPU works with YOLO `nano` |

---

## Quick start (reviewer — 5 commands)

```bash
git clone https://github.com/deepakm0003/Purplle-Tech-Challenge.git
cd Purplle-Tech-Challenge/store-intelligence
pip install -r requirements.txt
docker compose up -d --build
cd ../store-intelligence-dashboard && npm ci && npm run dev
```

| Service | URL |
|---------|-----|
| API | http://localhost:8000/docs |
| Health | http://localhost:8000/health |
| Dashboard | http://localhost:5173 |

Bootstrap events load automatically from `data/bootstrap/` — no videos required for metrics.

---

## Full local setup (with CCTV videos)

```powershell
# 1. Clone and install
git clone https://github.com/deepakm0003/Purplle-Tech-Challenge.git
cd Purplle-Tech-Challenge\store-intelligence
pip install -r requirements.txt

# 2. Put Store 1/, Store 2/, POS CSV in parent folder (see layout above)

# 3. Run detection on all cameras (~20 min per clip; use GPU if available)
python scripts/process_stores.py --export-tracks
python scripts/backfill_entry_events.py
python scripts/sync_bootstrap_events.py

# 4. API + dashboard
python -m uvicorn api.main:app --reload --port 8000
# new terminal:
cd ..\store-intelligence-dashboard
npm install && npm run dev
```

**Restart API** after pipeline or backfill so bootstrap reloads.

---

## Detection pipeline

| Script | Purpose |
|--------|---------|
| `python scripts/process_stores.py` | Process Store 1 + Store 2 (all cameras) |
| `python scripts/process_stores.py --store ST2002` | Single store |
| `python scripts/backfill_entry_events.py` | Add `ENTRY` events when only `ZONE_DWELL` exists |
| `python scripts/sync_bootstrap_events.py` | Copy `output/` → `data/bootstrap/` for git |
| `python scripts/build_submission_events.py` | Merge → `output/submission_events.jsonl` |

Single camera:

```bash
python -m detector.process_video \
  -v "../Store 1/CAM 3 - entry.mp4" \
  -o output/store-1/events/CAM_3_-_entry_events.jsonl \
  --store-id ST1008 --camera-id CAM-ENTRY --camera-role entry \
  --layout config/zones.json --sample-rate 5 --confidence 0.45 --min-hits 5
```

---

## API reference

Challenge-aligned routes (also under `/api/analytics`):

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/events/ingest` | Batch ingest (idempotent by `event_id`) |
| `GET` | `/stores/{id}/metrics` | Visitors, conversion, dwell, queue |
| `GET` | `/stores/{id}/funnel` | Entry → zone → billing → purchase |
| `GET` | `/stores/{id}/heatmap` | Zone frequency + dwell (0–100) |
| `GET` | `/stores/{id}/anomalies` | Queue spike, conversion drop, dead zone |
| `GET` | `/health` | Service + stale-feed warnings |

App-specific:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/stores` | List stores |
| `GET` | `/api/stores/{id}/dashboard` | POS + summary for dashboard |
| `GET` | `/api/stores/{id}/cameras` | Camera list + pipeline status |

Ingest example:

```bash
curl -X POST http://localhost:8000/events/ingest \
  -H "Content-Type: application/json" \
  -d @store-intelligence/data/bootstrap/store-2/events/entry_1_events.jsonl
```

---

## Dashboard

| Page | Route | Content |
|------|-------|---------|
| Overview | `/` | Revenue, orders, CCTV visitors |
| Store map | `/store` | Floorplan / zones |
| Sales & intelligence | `/sales` | POS + funnel-style metrics |
| CCTV | `/cctv` | Video + bounding boxes |

Switch **Store 1** (`ST1008`) / **Store 2** (`ST2002`) in the header.

Environment (optional): `store-intelligence-dashboard/.env`

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_STORE_ID=ST1008
```

---

## Docker

```bash
cd store-intelligence
docker compose up -d --build
docker compose ps
curl http://localhost:8000/health
```

Services: **api** (8000), **postgres** (5432), **redis** (6379).

---

## Stores: Store 1 vs Store 2

| | Store 1 (`ST1008`) | Store 2 (`ST2002`) |
|---|-------------------|-------------------|
| POS in sample CSV | Yes (`ST1008`) | No rows → revenue shows **₹0** |
| CCTV / visitors | Yes | Yes (bootstrap + pipeline) |
| Cameras | 4 (entry, 2× zone, billing) | 4 (2× entry, zone, billing) |

Store 2 shows CCTV footfall and heatmaps; zero POS is expected with the provided CSV.

---

## Submission checklist

- [x] GitHub: https://github.com/deepakm0003/Purplle-Tech-Challenge
- [ ] Private repo → invite `purplletechchallenge2026@hackerearth.com`
- [x] `DESIGN.md` + `CHOICES.md` in `store-intelligence/`
- [x] `docker compose up` documented
- [x] No `*.mp4` / `Store 1` / `Store 2` in git
- [x] Bootstrap JSONL for offline metrics
- [ ] Add remaining screenshots under `docs/screenshots/`

---

## Do I submit the CCTV videos?

**No — do not upload CCTV footage to GitHub** (challenge licence + repo rules).

| What | Submit? |
|------|---------|
| Git repo (code + docs + bootstrap JSONL) | **Yes** |
| `DESIGN.md` + `CHOICES.md` | **Yes** |
| Raw MP4 / dataset ZIP | **No** (keep local; describe paths in README) |
| Follow-up **video answers** (5 questions, ~30 min async) | **Later** — email after submission; you record yourself explaining **your** code (not the CCTV files) |

Optional **Part E bonus**: demo dashboard updating live (terminal or this web UI) — still no need to submit source videos.

---

## Documentation

| Document | Location |
|----------|----------|
| Architecture & AI decisions | [`store-intelligence/DESIGN.md`](store-intelligence/DESIGN.md) |
| Engineering choices | [`store-intelligence/CHOICES.md`](store-intelligence/CHOICES.md) |
| API deep-dive | [`store-intelligence/README.md`](store-intelligence/README.md) |
| Data placement | [`store-intelligence/data/README.md`](store-intelligence/data/README.md) |
| Screenshot filenames | [`docs/screenshots/README.md`](docs/screenshots/README.md) |

---

**Repository:** https://github.com/deepakm0003/Purplle-Tech-Challenge  
**Contributor:** deepakm0003 only.
