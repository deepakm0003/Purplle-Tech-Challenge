#!/usr/bin/env python3
"""POST all JSONL events from output/events/ to the Intelligence API."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "output" / "events"
BATCH = 500


def load_events(events_dir: Path, store_id: str | None) -> list[dict]:
    events: list[dict] = []
    for path in sorted(events_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            ev = json.loads(line)
            if store_id and ev.get("store_id") != store_id:
                continue
            events.append(ev)
    return events


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest CCTV JSONL into Store Intelligence API")
    parser.add_argument("--api", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR, help="Events directory")
    parser.add_argument("--store-id", default="ST1008", help="Filter by store_id")
    args = parser.parse_args()

    events = load_events(args.dir, args.store_id)
    if not events:
        print(f"No events in {args.dir}")
        return 1

    url = f"{args.api.rstrip('/')}/events/ingest"
    alt = f"{args.api.rstrip('/')}/api/analytics/events/ingest"

    ingested = 0
    with httpx.Client(timeout=120.0) as client:
        for i in range(0, len(events), BATCH):
            batch = events[i : i + BATCH]
            payload = {"events": batch}
            for endpoint in (url, alt):
                try:
                    r = client.post(endpoint, json=payload)
                    if r.status_code in (200, 202):
                        body = r.json()
                        ingested += body.get("ingested", len(batch))
                        print(f"Batch {i // BATCH + 1}: {body.get('message', r.status_code)}")
                        break
                    print(f"{endpoint} -> {r.status_code}: {r.text[:200]}")
                except httpx.RequestError as exc:
                    print(f"Request failed ({endpoint}): {exc}")
                    return 1
            else:
                return 1

    print(f"Done — ingested ~{ingested} events from {len(events)} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
