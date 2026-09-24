"""Build field-path sets from NDJSON / JSONL telemetry samples."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SchemaSample:
    """Field set plus light load stats for empty/incomplete checks."""

    fields: set[str]
    event_count: int
    file_count: int
    path: str


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


def _schema_from_ndjson_file(path: Path, *, nested: bool = True) -> tuple[set[str], int]:
    """Parse one NDJSON/JSONL file. Returns (fields, event_count)."""
    schema: set[str] = set()
    count = 0
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
                count += 1
    return schema, count


def schema_from_ndjson(path: Path | str, *, nested: bool = True) -> set[str]:
    """Build a field set from an NDJSON/JSONL file (one JSON object per line).

    Uses ``utf-8-sig`` so files with a UTF-8 BOM (common from Windows editors
    and PowerShell ``Set-Content -Encoding utf8``) still parse.
    """
    fields, _ = _schema_from_ndjson_file(Path(path), nested=nested)
    return fields


def load_schema_sample(path: Path | str, *, nested: bool = True) -> SchemaSample:
    """Load a schema sample with event/file counts for warning checks.

    - File: parse as NDJSON
    - Directory: union schemas from all ``*.jsonl`` / ``*.ndjson`` / ``*.json`` files
    """
    path = Path(path)
    if path.is_file():
        fields, events = _schema_from_ndjson_file(path, nested=nested)
        return SchemaSample(
            fields=fields,
            event_count=events,
            file_count=1,
            path=str(path),
        )
    if path.is_dir():
        schema: set[str] = set()
        patterns = ("*.jsonl", "*.ndjson", "*.json")
        files: list[Path] = []
        for pattern in patterns:
            files.extend(sorted(path.glob(pattern)))
        seen: set[Path] = set()
        unique: list[Path] = []
        for f in files:
            if f not in seen and f.is_file():
                seen.add(f)
                unique.append(f)
        if not unique:
            raise FileNotFoundError(f"No NDJSON/JSON sample files found in {path}")
        total_events = 0
        for f in unique:
            fields, events = _schema_from_ndjson_file(f, nested=nested)
            schema |= fields
            total_events += events
        return SchemaSample(
            fields=schema,
            event_count=total_events,
            file_count=len(unique),
            path=str(path),
        )
    raise FileNotFoundError(f"Schema path not found: {path}")


def schema_from_path(path: Path | str, *, nested: bool = True) -> set[str]:
    """Build a field set from a file or directory of NDJSON samples."""
    return load_schema_sample(path, nested=nested).fields


def sample_warnings(
    before: SchemaSample,
    after: SchemaSample,
    *,
    incomplete_ratio: float = 0.2,
    min_before_fields: int = 5,
) -> list[str]:
    """Warn when the after sample is empty or looks clearly incomplete.

    An empty after file is not the same as "nothing removed". Callers should
    surface these warnings so CI does not treat a bad sample as a clean pass
    or as a huge false IMPACTED blast.
    """
    warnings: list[str] = []
    after_label = after.path or "after"

    if after.event_count == 0:
        warnings.append(
            f"After sample is empty (0 events in {after_label}). "
            "An empty file is not the same as 'nothing removed'; "
            "impact results may be misleading."
        )
    elif not after.fields and before.fields:
        warnings.append(
            f"After sample has events but no fields ({after.event_count} event(s) in "
            f"{after_label}). Check that the file is NDJSON with object keys."
        )
    elif (
        before.fields
        and len(before.fields) >= min_before_fields
        and after.fields
        and len(after.fields) / len(before.fields) < incomplete_ratio
    ):
        warnings.append(
            f"After sample looks incomplete: {len(after.fields)} field(s) vs "
            f"{len(before.fields)} before (under {int(incomplete_ratio * 100)}% of before). "
            f"Confirm {after_label} is a full representative sample, not a stub."
        )

    return warnings
