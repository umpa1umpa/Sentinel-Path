"""Schema contract utilities for Sentinel Path reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.schemas import SentinelReport


def get_report_json_schema() -> dict[str, Any]:
    """Return JSON Schema for the public Sentinel report contract."""
    return SentinelReport.model_json_schema()


def write_report_json_schema(path: str | Path) -> Path:
    """Persist SentinelReport JSON Schema to a file path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = get_report_json_schema()
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
