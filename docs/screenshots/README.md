# Screenshot guide

Add PNG files here for the root README gallery. Recommended width: **1400–1600px**.

## Files

| File | Capture |
|------|---------|
| `01-github-repository.png` | GitHub repo root |
| `02-dashboard-overview.png` | http://localhost:5173 — Overview |
| `03-sales-intelligence.png` | `/sales` |
| `04-store-cctv-tracks.png` | `/cctv` with track overlay |
| `05-store-map-heatmap.png` | `/store` |
| `06-api-swagger.png` | See steps below |
| `07-docker-compose.png` | `docker compose ps` — all healthy |

## Swagger screenshot (06)

1. `cd store-intelligence && docker compose up -d --build`
2. Open http://localhost:8000/api/docs
3. Expand `GET /api/analytics/stores/{store_id}/metrics`
4. Try it out → `store_id` = `ST2002` → Execute
5. `Win + Shift + S` → save as `06-api-swagger.png`

## Docker screenshot (07)

```powershell
docker compose ps
```

Screenshot terminal with api, postgres, redis running.

## Commit

```powershell
git add docs/screenshots/*.png
git commit -m "Add README screenshots"
git push origin main
```

Use a normal terminal for `git commit` if you want to avoid extra co-author trailers from IDE hooks.
