# Data layout (not in Git)

Place hackathon files next to `store-intelligence/` (repo root parent):

```
Purple Tech Hiring Challenge/
├── Store 1/                    # MP4s — do NOT commit
├── Store 2/                    # MP4s — do NOT commit
├── POS - sample transactionsb1e826f.csv
├── sample_eventsbe42122.jsonl
└── store-intelligence/
    └── data/bootstrap/         # committed pipeline JSONL (no video)
```

**Reviewers / Docker:** API loads `data/bootstrap/{store}/events/*.jsonl` when present, then `output/` after you run the pipeline locally.

**Refresh bootstrap after re-processing:**

```bash
python scripts/process_stores.py --export-tracks
python scripts/backfill_entry_events.py
python scripts/sync_bootstrap_events.py
```
