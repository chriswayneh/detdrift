"""Extract field references from Sigma detection YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def strip_modifier(key: str) -> str:
    """Strip Sigma modifiers after ``|`` (e.g. ``CommandLine|contains`` → ``CommandLine``)."""
    return key.split("|", 1)[0].strip()


def _walk_detection(node: Any, fields: set[str]) -> None:
    """Recursively collect field names from a Sigma detection structure.

    Sigma selections are typically dicts whose keys are field names (optionally
    with modifiers). Condition strings and keyword-only lists are skipped.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            # Meta keys used by Sigma detection blocks
            if key in {"condition", "timeframe"}:
                continue
            # Nested selection groups (selection_*, filter_*, etc.)
            if isinstance(value, (dict, list)):
                # If the key itself looks like a field (has no spaces / isn't a
                # selection-group name with nested field dicts), still walk value.
                # Selection group names are walked into; field keys are collected.
                if isinstance(value, dict):
                    # Heuristic: if all children look like field→value pairs
                    # (values are scalars/lists of scalars), treat keys as fields.
                    # If children are nested dicts/lists-of-dicts, treat as groups.
                    if _looks_like_field_map(value):
                        for field_key, field_val in value.items():
                            fields.add(strip_modifier(str(field_key)))
                            _walk_detection(field_val, fields)
                    else:
                        _walk_detection(value, fields)
                else:
                    # list value under a selection-group name, or a field with list values
                    # If key is not a known meta and value is list of scalars → field
                    if _is_scalar_list(value) or _is_scalar(value):
                        fields.add(strip_modifier(str(key)))
                    else:
                        _walk_detection(value, fields)
            else:
                # key → scalar value ⇒ key is a field
                fields.add(strip_modifier(str(key)))
    elif isinstance(node, list):
        for item in node:
            if isinstance(item, (dict, list)):
                _walk_detection(item, fields)
            # bare strings in keyword searches are not field names


def _is_scalar(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool)) or value is None


def _is_scalar_list(value: Any) -> bool:
    return isinstance(value, list) and all(_is_scalar(x) or (isinstance(x, list) and _is_scalar_list(x)) for x in value)


def _looks_like_field_map(d: dict) -> bool:
    """True if dict values are scalars or lists of scalars (a field map)."""
    if not d:
        return False
    for v in d.values():
        if isinstance(v, dict):
            return False
        if isinstance(v, list) and not _is_scalar_list(v):
            # list of dicts → nested structure, not a flat field map
            if any(isinstance(x, dict) for x in v):
                return False
    return True


def extract_fields_from_detection(detection: Any) -> set[str]:
    """Return the set of field paths referenced in a Sigma ``detection`` block."""
    fields: set[str] = set()
    if detection is None:
        return fields
    _walk_detection(detection, fields)
    return fields


def extract_fields_from_rule(rule: dict[str, Any]) -> set[str]:
    """Extract field references from a parsed Sigma rule dict."""
    return extract_fields_from_detection(rule.get("detection"))


def load_rule(path: Path | str) -> dict[str, Any]:
    """Load a Sigma YAML rule file. Raises ValueError on empty/invalid content."""
    path = Path(path)
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Rule is not a YAML mapping: {path}")
    return data


def extract_fields_from_file(path: Path | str) -> set[str]:
    """Load a rule file and return its referenced field set."""
    return extract_fields_from_rule(load_rule(path))
