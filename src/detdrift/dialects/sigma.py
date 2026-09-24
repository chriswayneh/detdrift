"""Sigma dialect: field extraction from detection YAML (default)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from detdrift.fields import (
    extract_fields_from_file as _extract_fields_from_file,
    extract_fields_from_rule,
    load_rule,
)


def extract_fields_from_file(path: Path | str) -> set[str]:
    return _extract_fields_from_file(path)


def load_rule_meta(path: Path | str) -> dict[str, Any]:
    """Return title / level / tags from a Sigma rule file."""
    rule = load_rule(path)
    tags = rule.get("tags") or []
    if isinstance(tags, str):
        tag_list = [tags]
    elif isinstance(tags, list):
        tag_list = [str(t) for t in tags]
    else:
        tag_list = []
    level = rule.get("level") or rule.get("severity") or ""
    return {
        "title": str(rule.get("title") or Path(path).stem),
        "level": str(level).strip().lower(),
        "tags": tag_list,
        "rule": rule,
    }


__all__ = [
    "extract_fields_from_file",
    "extract_fields_from_rule",
    "load_rule",
    "load_rule_meta",
]
