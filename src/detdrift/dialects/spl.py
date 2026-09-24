"""Simple offline SPL field-reference extraction.

Not an SPL engine: collects field-like identifiers from common operators
(``Field=``, ``stats ... by``, ``table``, ``rex field=``). Ignores
condition evaluation, subsearches, and macros.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# Dotted field path: Image, Process.CommandLine, winlog.event_data.CommandLine
_FIELD = r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*"

# Field=value / Field!= (search and where). Avoid bare <> so rex
# named groups like (?<whoami_args>...) are not treated as fields.
_EQ_FIELD = re.compile(
    rf"(?<![A-Za-z0-9_.])({_FIELD})\s*(?:=|!=)"
)

# stats / chart / timechart ... by Field1, Field2
_BY_CLAUSE = re.compile(
    rf"(?i)\bby\s+({_FIELD}(?:\s*,\s*{_FIELD})*)"
)

# table Field1, Field2[, ...]
_TABLE_CLAUSE = re.compile(
    r"(?i)\btable\s+([^|;]+)"
)

# rex field=Field
_REX_FIELD = re.compile(
    rf"(?i)\brex\s+field\s*=\s*({_FIELD})\b"
)

# Bare identifier token (for table lists)
_BARE_FIELD = re.compile(rf"^({_FIELD})$")

# Skip SPL keywords mistaken for fields
_SPL_KEYWORDS = frozenset(
    {
        "and",
        "or",
        "not",
        "where",
        "eval",
        "stats",
        "chart",
        "timechart",
        "table",
        "rex",
        "fields",
        "rename",
        "sort",
        "dedup",
        "head",
        "tail",
        "limit",
        "search",
        "by",
        "as",
        "over",
        "span",
        "true",
        "false",
        "null",
        "avg",
        "sum",
        "count",
        "min",
        "max",
        "values",
        "list",
        "dc",
        "distinct_count",
        "earliest",
        "latest",
        "first",
        "last",
        "mode",
        "range",
        "field",
        "top",
        "rare",
        "join",
        "append",
        "union",
        "lookup",
        "inputlookup",
        "outputlookup",
        "makemv",
        "mvexpand",
        "nomv",
        "spath",
        "extract",
        "bin",
        "bucket",
        "eventstats",
        "streamstats",
        "transaction",
        "fillnull",
        "filldown",
        "convert",
        "replace",
        "selfjoin",
        "multisearch",
        "tstats",
        "sitop",
        "sistats",
        "sichart",
        "sitimechart",
        "sirare",
        "case",
        "if",
        "like",
        "match",
        "in",
        "isnull",
        "isnotnull",
        "tonumber",
        "tostring",
        "coalesce",
        "now",
        "time",
        "strftime",
        "strptime",
        "typeof",
        "len",
        "lower",
        "upper",
        "trim",
        "substr",
        "split",
        "mvcount",
        "mvindex",
        "mvfilter",
        "mvjoin",
        "round",
        "abs",
        "ceil",
        "floor",
    }
)


def _is_field_name(name: str) -> bool:
    if not name or name.lower() in _SPL_KEYWORDS:
        return False
    return bool(_BARE_FIELD.match(name))


def _fields_from_list_body(body: str) -> set[str]:
    """Parse a comma-separated field list (table / fields)."""
    out: set[str] = set()
    for raw in body.split(","):
        part = raw.strip()
        if not part:
            continue
        # Drop leading +/- from ``fields +Foo, -Bar``
        if part[0] in "+-":
            part = part[1:].strip()
        token = part.split()[0] if part.split() else part
        if _is_field_name(token):
            out.add(token)
    return out


def extract_fields_from_spl(text: str) -> set[str]:
    """Return field paths referenced by simple SPL operators in ``text``."""
    fields: set[str] = set()
    if not text or not text.strip():
        return fields

    for m in _EQ_FIELD.finditer(text):
        name = m.group(1)
        if _is_field_name(name):
            fields.add(name)

    for m in _BY_CLAUSE.finditer(text):
        for part in m.group(1).split(","):
            name = part.strip()
            if _is_field_name(name):
                fields.add(name)

    for m in _TABLE_CLAUSE.finditer(text):
        fields |= _fields_from_list_body(m.group(1))

    for m in _REX_FIELD.finditer(text):
        name = m.group(1)
        if _is_field_name(name):
            fields.add(name)

    return fields


def extract_fields_from_file(path: Path | str) -> set[str]:
    """Load a ``.spl`` text file and extract field references."""
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig")
    return extract_fields_from_spl(text)


def load_rule_meta(path: Path | str) -> dict[str, Any]:
    """Metadata for an SPL rule file (title from first comment or stem)."""
    path = Path(path)
    title = path.stem
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        text = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            continue
        if stripped.startswith("//") or stripped.startswith("#"):
            comment = stripped.lstrip("/#").strip()
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
