"""Simple offline KQL field-reference extraction.

Not a KQL engine: collects field-like identifiers from common operators
(``where`` / ``project`` / ``summarize … by`` / ``sort by``). Ignores
condition evaluation, joins, and let-statements.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# Dotted field path: Image, Process.CommandLine, winlog.event_data.CommandLine
_FIELD = r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*"

_COMPARISON_OPS = (
    r"(?:==|!=|=~|!~|<=|>=|<|>|"
    r"contains|startswith|endswith|has|!has|has_any|has_all|in|!in)"
)

# where Field op … / and Field op … / or Field op …
_WHERE_FIELD = re.compile(
    rf"(?i)\b(?:where|and|or)\s+({_FIELD})\s+{_COMPARISON_OPS}\b"
)

# project / project-away / project-keep / project-rename clause body
_PROJECT_CLAUSE = re.compile(
    r"(?i)\bproject(?:-away|-keep|-rename)?\s+([^|;]+)"
)

# summarize … by Field1, Field2  (also distinct-by style)
_BY_CLAUSE = re.compile(
    rf"(?i)\bby\s+({_FIELD}(?:\s*,\s*{_FIELD})*)"
)

# sort by Field [asc|desc] / order by Field
_SORT_BY = re.compile(
    rf"(?i)\b(?:sort|order)\s+by\s+({_FIELD})\b"
)

# Bare identifier token (for project lists)
_BARE_FIELD = re.compile(rf"^({_FIELD})$")

# Skip KQL keywords mistaken for fields in project lists
_KQL_KEYWORDS = frozenset(
    {
        "and",
        "or",
        "not",
        "where",
        "project",
        "extend",
        "summarize",
        "sort",
        "order",
        "by",
        "asc",
        "desc",
        "null",
        "true",
        "false",
        "let",
        "join",
        "on",
        "kind",
        "inner",
        "outer",
        "leftouter",
        "rightouter",
        "fullouter",
        "anti",
        "semi",
        "union",
        "between",
        "ago",
        "now",
        "datetime",
        "timespan",
        "tostring",
        "toint",
        "tolong",
        "todouble",
        "tobool",
        "count",
        "dcount",
        "sum",
        "avg",
        "min",
        "max",
        "take",
        "limit",
        "distinct",
        "mv-expand",
        "mv-apply",
        "parse",
        "evaluate",
    }
)


def _is_field_name(name: str) -> bool:
    if not name or name.lower() in _KQL_KEYWORDS:
        return False
    return bool(_BARE_FIELD.match(name))


def _fields_from_project_body(body: str) -> set[str]:
    """Parse a project* clause: bare fields and ``Alias = Field`` RHS when bare."""
    out: set[str] = set()
    for raw in body.split(","):
        part = raw.strip()
        if not part:
            continue
        # Alias = Expression
        if "=" in part:
            _lhs, rhs = part.split("=", 1)
            rhs = rhs.strip()
            # Only collect when RHS is a bare field path (not a function call).
            if _is_field_name(rhs):
                out.add(rhs)
            continue
        # Drop sort suffixes accidentally included
        token = part.split()[0] if part.split() else part
        if _is_field_name(token):
            out.add(token)
    return out


def extract_fields_from_kql(text: str) -> set[str]:
    """Return field paths referenced by simple KQL operators in ``text``."""
    fields: set[str] = set()
    if not text or not text.strip():
        return fields

    for m in _WHERE_FIELD.finditer(text):
        name = m.group(1)
        if _is_field_name(name):
            fields.add(name)

    for m in _PROJECT_CLAUSE.finditer(text):
        fields |= _fields_from_project_body(m.group(1))

    for m in _BY_CLAUSE.finditer(text):
        for part in m.group(1).split(","):
            name = part.strip()
            if _is_field_name(name):
                fields.add(name)

    for m in _SORT_BY.finditer(text):
        name = m.group(1)
        if _is_field_name(name):
            fields.add(name)

    return fields


def extract_fields_from_file(path: Path | str) -> set[str]:
    """Load a ``.kql`` text file and extract field references."""
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig")
    return extract_fields_from_kql(text)


def load_rule_meta(path: Path | str) -> dict[str, Any]:
    """Metadata for a KQL rule file (title from first comment or stem)."""
    path = Path(path)
    title = path.stem
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        text = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("//"):
            comment = stripped[2:].strip()
            if comment:
                title = comment
                break
        if stripped.startswith("/*"):
            continue
        if stripped:
            break
    return {
        "title": title,
        "level": "",
        "tags": [],
        "rule": None,
    }
