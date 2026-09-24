"""Pluggable rule dialects for field-reference extraction.

Sigma remains the default. Optional dialects (KQL, SPL) are simple
offline extractors — not query engines or matchers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from detdrift.dialects import kql as kql_mod
from detdrift.dialects import sigma as sigma_mod
from detdrift.dialects import spl as spl_mod

DialectName = str  # "sigma" | "kql" | "spl" | "auto"

SUPPORTED_DIALECTS: tuple[str, ...] = ("sigma", "kql", "spl", "auto")

# Extension → dialect (used when dialect=auto or when discovering rules).
EXTENSION_DIALECT: dict[str, str] = {
    ".yml": "sigma",
    ".yaml": "sigma",
    ".kql": "kql",
    ".spl": "spl",
}

_EXTRACTORS: dict[str, Callable[[Path], set[str]]] = {
    "sigma": sigma_mod.extract_fields_from_file,
    "kql": kql_mod.extract_fields_from_file,
    "spl": spl_mod.extract_fields_from_file,
}


def normalize_dialect(name: str | None) -> str:
    """Return a supported dialect name; default sigma when unset/blank."""
    if name is None or not str(name).strip():
        return "sigma"
    d = str(name).strip().lower()
    if d not in SUPPORTED_DIALECTS:
        raise ValueError(
            f"Unknown dialect {name!r}; use one of: {', '.join(SUPPORTED_DIALECTS)}"
        )
    return d


def detect_dialect(path: Path | str) -> str:
    """Guess dialect from file extension; default sigma for unknown extensions."""
    ext = Path(path).suffix.lower()
    return EXTENSION_DIALECT.get(ext, "sigma")


def resolve_dialect(path: Path | str, dialect: str | None) -> str:
    """Resolve effective dialect for a single file."""
    d = normalize_dialect(dialect)
    if d == "auto":
        return detect_dialect(path)
    return d


def rule_globs_for_dialect(dialect: str | None) -> tuple[str, ...]:
    """Glob patterns under --rules for the given dialect setting."""
    d = normalize_dialect(dialect)
    if d == "sigma":
        return ("**/*.yml", "**/*.yaml")
    if d == "kql":
        return ("**/*.kql",)
    if d == "spl":
        return ("**/*.spl",)
    # auto: all known
    return ("**/*.yml", "**/*.yaml", "**/*.kql", "**/*.spl")


def extract_fields_from_file(path: Path | str, *, dialect: str | None = None) -> set[str]:
    """Extract field references from a rule file using the chosen dialect."""
    path = Path(path)
    effective = resolve_dialect(path, dialect)
    extractor = _EXTRACTORS.get(effective)
    if extractor is None:
        raise ValueError(f"No extractor for dialect {effective!r}")
    return extractor(path)


def load_rule_meta(path: Path | str, *, dialect: str | None = None) -> dict:
    """Lightweight metadata for impact reports (title, level, tags)."""
    path = Path(path)
    effective = resolve_dialect(path, dialect)
    if effective == "sigma":
        return sigma_mod.load_rule_meta(path)
    if effective == "kql":
        return kql_mod.load_rule_meta(path)
    if effective == "spl":
        return spl_mod.load_rule_meta(path)
    raise ValueError(f"No metadata loader for dialect {effective!r}")
