"""
Store catalog — Store 1 / Store 2 video folders, cameras, and output paths.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "stores.json"


@dataclass(frozen=True)
class CameraSpec:
    id: str
    file: str
    role: str
    label: str

    @property
    def file_slug(self) -> str:
        return self.file.replace(" ", "_").replace(".mp4", "")


@dataclass(frozen=True)
class StoreSpec:
    id: str
    name: str
    slug: str
    folder: str
    layout_file: str
    pos_store_ids: list[str]
    cameras: list[CameraSpec]

    @property
    def root(self) -> Path:
        return PROJECT_ROOT / self.folder

    @property
    def events_dir(self) -> Path:
        return PROJECT_ROOT / "output" / self.slug / "events"

    @property
    def tracks_dir(self) -> Path:
        return PROJECT_ROOT / "output" / self.slug / "tracks"

    def media_url(self, filename: str) -> str:
        return f"/store-media/{self.slug}/{filename}"

    def layout_url(self) -> str | None:
        path = self.root / self.layout_file
        if path.is_file():
            return self.media_url(self.layout_file)
        return None


def _load_config() -> dict[str, Any]:
    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(f"Store config not found: {CONFIG_PATH}")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def get_catalog_config() -> dict[str, Any]:
    return _load_config()


def list_stores() -> list[StoreSpec]:
    cfg = get_catalog_config()
    stores: list[StoreSpec] = []
    for raw in cfg.get("stores", []):
        cameras = [
            CameraSpec(
                id=c["id"],
                file=c["file"],
                role=c.get("role", "zone"),
                label=c.get("label", c["id"]),
            )
            for c in raw.get("cameras", [])
        ]
        stores.append(
            StoreSpec(
                id=raw["id"],
                name=raw["name"],
                slug=raw["slug"],
                folder=raw["folder"],
                layout_file=raw.get("layout_file", ""),
                pos_store_ids=list(raw.get("pos_store_ids", [raw["id"]])),
                cameras=cameras,
            )
        )
    return stores


def get_store(store_id: str) -> StoreSpec | None:
    for s in list_stores():
        if s.id == store_id:
            return s
    return None


def get_store_by_slug(slug: str) -> StoreSpec | None:
    for s in list_stores():
        if s.slug == slug:
            return s
    return None


def sample_events_path() -> Path:
    name = get_catalog_config().get("sample_events_file", "sample_eventsbe42122.jsonl")
    return PROJECT_ROOT / name


def pos_csv_path() -> Path:
    name = get_catalog_config().get("pos_file", "POS - sample transactionsb1e826f.csv")
    return PROJECT_ROOT / name


def sample_events_store_map() -> dict[str, str]:
    return dict(get_catalog_config().get("sample_events_store_map", {}))


def bootstrap_events_dir(store: StoreSpec) -> Path:
    """Committed demo events (no videos) for reviewers / Docker."""
    return PROJECT_ROOT / "data" / "bootstrap" / store.slug / "events"


def iter_event_jsonl_paths(store: StoreSpec) -> Iterator[Path]:
    """All JSONL files for a store (pipeline output, then committed bootstrap)."""
    seen: set[Path] = set()
    events_dir = store.events_dir
    if events_dir.is_dir():
        for path in sorted(events_dir.glob("*.jsonl")):
            if path not in seen:
                seen.add(path)
                yield path

    boot = bootstrap_events_dir(store)
    if boot.is_dir():
        for path in sorted(boot.glob("*.jsonl")):
            if path not in seen:
                seen.add(path)
                yield path
    legacy = PROJECT_ROOT / "output" / "events"
    if legacy.is_dir():
        for cam in store.cameras:
            slug = Path(cam.file).stem.replace(" ", "_")
            for candidate in (
                legacy / f"{slug}_events.jsonl",
                legacy / f"{Path(cam.file).stem}_events.jsonl",
            ):
                if candidate.is_file() and candidate not in seen:
                    seen.add(candidate)
                    yield candidate


def camera_events_path(store: StoreSpec, camera: CameraSpec) -> Path:
    slug = Path(camera.file).stem.replace(" ", "_")
    return store.events_dir / f"{slug}_events.jsonl"


def camera_tracks_path(store: StoreSpec, camera: CameraSpec) -> Path:
    slug = Path(camera.file).stem.replace(" ", "_")
    return store.tracks_dir / f"{slug}_tracks.json"


def camera_tracks_url(store: StoreSpec, camera: CameraSpec) -> str | None:
    """URL path must match StaticFiles mount: output/ → /cctv-tracks/…"""
    path = camera_tracks_path(store, camera)
    if path.is_file() and path.stat().st_size > 50:
        return f"/cctv-tracks/{store.slug}/tracks/{path.name}"
    return None
