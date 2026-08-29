"""Event folder creation and discovery."""

import re
from datetime import datetime
from pathlib import Path

from expedite.config import data_dir
from expedite.models import Event
from expedite.storage.sqlite_store import get_event_metadata, list_event_metadata, save_event


def _slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value.strip()).strip("_").lower()
    return slug or "event"


def _unique_folder(base_dir: Path, name: str, start_date: str) -> Path:
    stem = f"{_slugify(name)}_{start_date}"
    candidate = base_dir / stem
    suffix = 2
    while candidate.exists():
        candidate = base_dir / f"{stem}_{suffix}"
        suffix += 1
    return candidate


def ensure_data_dir() -> Path:
    root = data_dir()
    root.mkdir(parents=True, exist_ok=True)
    return root


def create_event(name: str, start_date: str | None = None) -> Event:
    event_name = name.strip() or "Untitled Event"
    event_date = start_date or datetime.now().astimezone().date().isoformat()
    root = ensure_data_dir()
    path = _unique_folder(root, event_name, event_date)
    (path / "labels").mkdir(parents=True)

    event = Event(
        name=event_name,
        start_date=event_date,
        path=path,
        created_at=datetime.now().astimezone(),
    )
    save_event(event)
    return event


def _ensure_event_folder(event: Event) -> Event:
    """Recreate derived event directories after a database-only restore."""
    (event.path / "labels").mkdir(parents=True, exist_ok=True)
    return event


def list_events() -> list[Event]:
    ensure_data_dir()
    return [_ensure_event_folder(event) for event in list_event_metadata()]


def get_event(folder_name: str) -> Event | None:
    root = ensure_data_dir().resolve()
    candidate = (root / folder_name).resolve()
    if root not in candidate.parents and candidate != root:
        return None
    event = get_event_metadata(candidate)
    return _ensure_event_folder(event) if event is not None else None
