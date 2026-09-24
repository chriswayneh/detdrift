"""Build field-path sets from NDJSON / JSONL telemetry samples."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _paths_from_event(event: dict[str, Any], *, nested: bool = True) -> set[str]:
    """Collect top-level keys and optionally one-level dotted nested paths."""
    paths: set[str] = set()
    for key, value in event.items():
        paths.add(str(key))
        if nested and isinstance(value, dict):
            for child in value:
                paths.add(f"{key}.{child}")
    return paths


def schema_from_events(events: list[dict[str, Any]], *, nested: bool = True) -> set[str]:
    """Union of field paths across a list of events."""
    schema: set[str] = set()
    for event in events:
        if isinstance(event, dict):
            schema |= _paths_from_event(event, nested=nested)
    return schema


def schema_from_ndjson(path: Path | str, *, nested: bool = True) -> set[str]:
    """Build a field set from an NDJSON/JSONL file (one JSON object per line).

    Uses ``utf-8-sig`` so files with a UTF-8 BOM (common from Windows editors
    and PowerShell ``Set-Content -Encoding utf8``) still parse.
    """
    path = Path(path)
    schema: set[str] = set()
    with path.open(encoding="utf-8-sig") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {lineno} of {path}: {exc}") from exc
            if isinstance(obj, dict):
                schema |= _paths_from_event(obj, nested=nested)
    return schema


def schema_from_path(path: Path | str, *, nested: bool = True) -> set[str]:
    """Build a field set from a file or directory of NDJSON samples.

    - File: parse as NDJSON
    - Directory: union schemas from all ``*.jsonl`` / ``*.ndjson`` / ``*.json`` files
    """
    path = Path(path)
    if path.is_file():
        return schema_from_ndjson(path, nested=nested)
    if path.is_dir():
        schema: set[str] = set()
        patterns = ("*.jsonl", "*.ndjson", "*.json")
        files: list[Path] = []
        for pattern in patterns:
            files.extend(sorted(path.glob(pattern)))
        # de-dupe while preserving order
        seen: set[Path] = set()
        unique: list[Path] = []
        for f in files:
            if f not in seen and f.is_file():
                seen.add(f)
                unique.append(f)
        if not unique:
            raise FileNotFoundError(f"No NDJSON/JSON sample files found in {path}")
        for f in unique:
            schema |= schema_from_ndjson(f, nested=nested)
        return schema
    raise FileNotFoundError(f"Schema path not found: {path}")
