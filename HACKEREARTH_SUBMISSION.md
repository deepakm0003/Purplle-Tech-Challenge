# HackerEarth submission — copy/paste guide

Use this when filling **Create Submission** on HackerEarth.

---

## Title

```
Store Intelligence — CCTV to Real-Time Retail Analytics API & Dashboard
```

---

## Description

```markdown
## Problem
Offline retail stores lack the session-level analytics that e-commerce has. This project turns anonymised in-store CCTV into structured behavioural events and serves real-time store intelligence through a production-style API and React dashboard.

## Solution
1. **Detection pipeline** — YOLOv8 + ByteTrack on Store 1 & Store 2 footage; zone mapping; staff heuristics; emits JSONL events (`ENTRY`, `ZONE_DWELL`, billing queue events, etc.).
2. **Intelligence API** — FastAPI with ingest, metrics, conversion funnel, zone heatmap, anomaly detection, and health checks. Docker Compose (Postgres + Redis + API).
3. **Dashboard** — Multi-store UI with POS analytics, CCTV viewer with track overlay, and live visitor metrics.

## North-star metric
Offline conversion rate = purchasers ÷ unique visitors (staff excluded), correlated with POS in a 5-minute billing window.

## Repo highlights
- Pre-committed pipeline output: `store-intelligence/data/bootstrap/` and `output/submission_events.jsonl`
- `DESIGN.md` and `CHOICES.md` document architecture and AI-assisted decisions
- pytest suite for metrics, funnel, heatmap, anomalies

## Links
- GitHub: https://github.com/deepakm0003/Purplle-Tech-Challenge
```

---

## Theme

Select: **Purplle Tech Challenge 2026 — Round 2 Problem Statement**

---

## Demo Link *

```
http://localhost:5173
```

**Note for reviewers:** This is a **local** demo. After following *Instructions to Run*, open the dashboard at port 5173 and API docs at `http://localhost:8000/api/docs`. (Remote hosted URL not required by the challenge.)

---

## Repository URL *

```
https://github.com/deepakm0003/Purplle-Tech-Challenge.git
```

---

## Video URL

Leave **empty** unless you recorded a optional walkthrough. Follow-up Q&A videos are requested **by email after** submission, not on this form.

---

## Instructions to Run *

```markdown
### Prerequisites
- Docker Desktop (Windows/Mac) OR Python 3.11+ and Node 18+
- Git

### 1. Clone
git clone https://github.com/deepakm0003/Purplle-Tech-Challenge.git
cd Purplle-Tech-Challenge/store-intelligence

Important: run Docker from the `store-intelligence` folder (where docker-compose.yml lives).

### 2. Start API (Docker)
docker compose up -d --build
docker compose ps
curl http://localhost:8000/health

Swagger UI: http://localhost:8000/api/docs
Try: GET /api/analytics/stores/ST1008/metrics
Try: GET /api/analytics/stores/ST2002/metrics

### 3. Start dashboard (new terminal)
cd ../store-intelligence-dashboard
npm ci
npm run dev
Open: http://localhost:5173
Switch Store 1 (ST1008) / Store 2 (ST2002) in the header.

### 4. Pipeline output (already in repo)
- Per-camera events: store-intelligence/output/store-1/events/, output/store-2/events/
- Merged API ingest file: store-intelligence/output/submission_events.jsonl
- Reviewer copy: store-intelligence/data/bootstrap/

### 5. Re-run pipeline (optional, requires local MP4s — not in git)
Place Store 1/, Store 2/, POS CSV next to repo parent folder.
cd store-intelligence
pip install -r requirements.txt
python scripts/process_stores.py --export-tracks
python scripts/backfill_entry_events.py
python scripts/build_submission_events.py

### 6. Tests
cd store-intelligence
pytest tests/unit -q
```

---

## Snapshots (upload images)

Upload from `docs/screenshots/` after you capture:

1. `02-dashboard-overview.png` — Overview page
2. `06-api-swagger.png` — Swagger with metrics response
3. `07-docker-compose.png` — `docker compose ps` healthy

---

## Source Code zip

**Optional** — reviewers use GitHub. Only upload zip if HackerEarth requires it; exclude `Store 1/`, `Store 2/`, `*.mp4`, `.venv`, `node_modules`.

---

## Private repo access

Settings → Collaborators → invite: `purplletechchallenge2026@hackerearth.com`
