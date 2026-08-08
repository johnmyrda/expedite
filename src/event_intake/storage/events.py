"""Event folder creation and discovery."""

import json
import re
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from event_intake.config import data_dir
from event_intake.models import Event

METADATA_FILE = "event.json"


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


def _metadata_path(event: Event) -> Path:
    return event.path / METADATA_FILE


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
    _metadata_path(event).write_text(
        event.model_dump_json(indent=2, exclude={"path"}),
        encoding="utf-8",
    )
    return event


def _event_from_folder(path: Path) -> Event | None:
    try:
        metadata = json.loads((path / METADATA_FILE).read_text(encoding="utf-8"))
        metadata["path"] = path
        return Event.model_validate(metadata)
    except (OSError, json.JSONDecodeError, ValidationError):
        return None


def list_events() -> list[Event]:
    root = ensure_data_dir()
    events = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        event = _event_from_folder(child)
        if event is not None:
            events.append(event)
    return sorted(events, key=lambda event: event.created_at, reverse=True)


def get_event(folder_name: str) -> Event | None:
    root = ensure_data_dir().resolve()
    candidate = (root / folder_name).resolve()
    if root not in candidate.parents and candidate != root:
        return None
    if not candidate.is_dir():
        return None
    return _event_from_folder(candidate)
