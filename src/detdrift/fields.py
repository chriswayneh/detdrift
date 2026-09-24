"""Extract field references from Sigma detection YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Selection / filter group names that are not field paths.
_GROUP_KEYS = frozenset(
    {
        "condition",
        "timeframe",
        "keywords",
    }
)


def strip_modifier(key: str) -> str:
    """Strip Sigma modifiers after ``|`` (e.g. ``CommandLine|contains`` -> ``CommandLine``)."""
    return key.split("|", 1)[0].strip()


def _is_scalar(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool)) or value is None


def _is_scalar_list(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    for x in value:
        if _is_scalar(x):
            continue
        if isinstance(x, list) and _is_scalar_list(x):
            continue
        return False
    return True


def _looks_like_field_path(key: str) -> bool:
    """True if a key looks like a Sigma field path rather than a selection group name."""
    if not key or key in _GROUP_KEYS:
        return False
    base = strip_modifier(key)
    if not base or " " in base:
        return False
    # Common group prefixes: selection, filter, sel_, filt_
    lower = base.lower()
    if lower in {"selection", "filter", "filters"}:
        return False
    if lower.startswith(("selection_", "filter_", "sel_", "filt_")):
        return False
    # Field paths are typically alnum / underscore / dot / hyphen
    return all(c.isalnum() or c in "._-" for c in base)


def _walk_detection(node: Any, fields: set[str], *, parent_path: str | None = None) -> None:
    """Recursively collect field names from a Sigma detection structure.

    Handles:
    - Flat field maps under selection / filter groups
    - Lists of maps under selections (OR of field maps)
    - Nested dicts whose keys look like field paths (optionally dotted under parent)
    - ``|modifier`` stripping on every collected key
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if key in {"condition", "timeframe"}:
                continue

            key_str = str(key)
            base = strip_modifier(key_str)

            if isinstance(value, dict):
                # Nested group or nested field container.
                # If this key looks like a field path, recurse with dotted parent
                # so children become parent.child (common nested Sigma paths).
                if _looks_like_field_path(key_str):
                    dotted = f"{parent_path}.{base}" if parent_path else base
                    # Record the container key itself (schema often has the parent too).
                    fields.add(dotted if parent_path else base)
                    _walk_detection(value, fields, parent_path=dotted if parent_path else base)
                else:
                    # Selection / filter group name: walk children without prefixing.
                    _walk_detection(value, fields, parent_path=parent_path)
            elif isinstance(value, list):
                if _is_scalar_list(value):
                    # Field with a list of scalar values (or keyword-ish list).
                    if key_str.lower() == "keywords" or not _looks_like_field_path(key_str):
                        # Keyword-only lists under non-field keys: skip.
                        continue
                    dotted = f"{parent_path}.{base}" if parent_path else base
                    fields.add(dotted)
                else:
                    # List of maps (or mixed): walk structured items.
                    # Do not treat the group key as a field.
                    _walk_detection(value, fields, parent_path=parent_path)
            else:
                # key -> scalar => key is a field (if it looks like one).
                if not _looks_like_field_path(key_str):
                    continue
                dotted = f"{parent_path}.{base}" if parent_path else base
                fields.add(dotted)

    elif isinstance(node, list):
        for item in node:
            if isinstance(item, dict):
                # List-of-maps under a selection: each map is a field map.
                _walk_map_or_group(item, fields, parent_path=parent_path)
            elif isinstance(item, list):
                _walk_detection(item, fields, parent_path=parent_path)
            # bare strings in keyword searches are not field names


def _walk_map_or_group(node: dict, fields: set[str], *, parent_path: str | None = None) -> None:
    """Walk a dict that is either a field map or a nested group."""
    # Prefer treating as a field map when values are scalars / scalar lists.
    if _looks_like_flat_field_map(node):
        for key, value in node.items():
            if key in {"condition", "timeframe"}:
                continue
            key_str = str(key)
            if not _looks_like_field_path(key_str):
                # Unusual meta inside a map; recurse just in case.
                if isinstance(value, (dict, list)):
                    _walk_detection(value, fields, parent_path=parent_path)
                continue
            base = strip_modifier(key_str)
            dotted = f"{parent_path}.{base}" if parent_path else base
            fields.add(dotted)
            if isinstance(value, dict):
                _walk_detection(value, fields, parent_path=dotted)
            elif isinstance(value, list) and not _is_scalar_list(value):
                _walk_detection(value, fields, parent_path=parent_path)
    else:
        _walk_detection(node, fields, parent_path=parent_path)


def _looks_like_flat_field_map(d: dict) -> bool:
    """True if dict values are scalars or lists of scalars (a field map)."""
    if not d:
        return False
    for v in d.values():
        if isinstance(v, dict):
            return False
        if isinstance(v, list) and not _is_scalar_list(v):
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
