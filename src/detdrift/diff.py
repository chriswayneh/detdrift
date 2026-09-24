"""Compare before/after schemas to Sigma rules and report impact."""

from __future__ import annotations

import fnmatch
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from detdrift.fields import extract_fields_from_rule, load_rule
from detdrift.schema import schema_from_path

# JSON report contract version (see docs/json-report.md).
REPORT_SCHEMA_VERSION = 1

# Directory names skipped by default during recursive rules discovery.
DEFAULT_IGNORE_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".github",
        "vendor",
        "tests",
        "test",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
    }
)

_SEVERITY_RANK = {
    "informational": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


@dataclass
class RuleImpact:
    """One rule's outcome under a schema change."""

    rule: str
    title: str
    status: str  # "IMPACTED" | "SAFE" | "UNKNOWN"
    referenced_fields: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    # Fields the rule references that were never in `before` (informational)
    never_in_before: list[str] = field(default_factory=list)
    level: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DiffReport:
    """Full impact report across a rules directory."""

    before_fields: list[str]
    after_fields: list[str]
    removed_fields: list[str]
    impacts: list[RuleImpact]
    rules_scanned: int = 0
    schema_version: int = REPORT_SCHEMA_VERSION

    @property
    def impacted(self) -> list[RuleImpact]:
        return [i for i in self.impacts if i.status == "IMPACTED"]

    @property
    def safe(self) -> list[RuleImpact]:
        return [i for i in self.impacts if i.status == "SAFE"]

    @property
    def has_impacts(self) -> bool:
        return bool(self.impacted)

    def matching_impacts(
        self,
        *,
        fail_on_severity: Iterable[str] | None = None,
        fail_on_tags: Iterable[str] | None = None,
    ) -> list[RuleImpact]:
        """IMPACTED rules that match optional severity / tag fail filters.

        If no filters are set, returns all IMPACTED rules.
        Severity match: rule level rank >= minimum of the requested severities
        (so ``high,critical`` fails on high or critical).
        Tag match: any requested token is a substring of any rule tag
        (case-insensitive).
        When both filters are set, a rule must match severity AND tag.
        """
        impacted = self.impacted
        sev_list = [s.strip().lower() for s in (fail_on_severity or []) if s and s.strip()]
        tag_list = [t.strip().lower() for t in (fail_on_tags or []) if t and t.strip()]

        if not sev_list and not tag_list:
            return list(impacted)

        min_rank: int | None = None
        if sev_list:
            ranks = [_SEVERITY_RANK[s] for s in sev_list if s in _SEVERITY_RANK]
            if not ranks:
                # Unknown severity names: treat as no severity match possible.
                min_rank = 999
            else:
                min_rank = min(ranks)

        out: list[RuleImpact] = []
        for item in impacted:
            ok_sev = True
            ok_tag = True
            if min_rank is not None:
                level = (item.level or "").strip().lower()
                rank = _SEVERITY_RANK.get(level, -1)
                ok_sev = rank >= min_rank
            if tag_list:
                rule_tags = [t.lower() for t in item.tags]
                ok_tag = any(
                    any(needle in hay for hay in rule_tags) for needle in tag_list
                )
            if ok_sev and ok_tag:
                out.append(item)
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "before_fields": self.before_fields,
            "after_fields": self.after_fields,
            "removed_fields": self.removed_fields,
            "rules_scanned": self.rules_scanned,
            "impacted_count": len(self.impacted),
            "safe_count": len(self.safe),
            "impacts": [i.to_dict() for i in self.impacts],
        }


def _should_ignore(path: Path, root: Path, ignore_dirs: set[str], ignore_globs: list[str]) -> bool:
    """Return True if this file (or a parent under root) should be skipped."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path

    for part in rel.parts[:-1]:
        if part in ignore_dirs:
            return True

    rel_str = rel.as_posix()
    name = path.name
    for pattern in ignore_globs:
        if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel_str, pattern):
            return True
    return False


def discover_rules(
    rules_dir: Path | str,
    *,
    ignore: Iterable[str] | None = None,
    ignore_dirs: Iterable[str] | None = None,
) -> list[Path]:
    """Recursively find Sigma YAML rule files under a directory.

    Skips directories named in ``ignore_dirs`` (defaults to
    ``DEFAULT_IGNORE_DIRS``: ``.git``, ``.github``, ``vendor``, ``tests``,
    and similar). Extra ``ignore`` entries are treated as fnmatch globs
    matched against the relative path or basename (for example
    ``*_test.yml`` or ``fixtures/**``).
    """
    root = Path(rules_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Rules directory not found: {root}")

    skip_dirs = set(DEFAULT_IGNORE_DIRS)
    if ignore_dirs is not None:
        skip_dirs = set(ignore_dirs)

    globs = [g for g in (ignore or []) if g]

    seen: set[Path] = set()
    out: list[Path] = []
    for pattern in ("**/*.yml", "**/*.yaml"):
        for f in sorted(root.glob(pattern)):
            if not f.is_file():
                continue
            if _should_ignore(f, root, skip_dirs, globs):
                continue
            resolved = f.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            out.append(f)
    return out


def _rule_level(rule: dict[str, Any]) -> str:
    raw = rule.get("level") or rule.get("severity") or ""
    return str(raw).strip().lower()


def _rule_tags(rule: dict[str, Any]) -> list[str]:
    tags = rule.get("tags") or []
    if isinstance(tags, str):
        return [tags]
    if isinstance(tags, list):
        return [str(t) for t in tags]
    return []


def analyze_rule(
    rule_path: Path,
    before: set[str],
    after: set[str],
    *,
    relative_to: Path | None = None,
) -> RuleImpact:
    """Classify a single rule as IMPACTED / SAFE / UNKNOWN."""
    rule = load_rule(rule_path)
    refs = extract_fields_from_rule(rule)
    title = str(rule.get("title") or rule_path.stem)
    level = _rule_level(rule)
    tags = _rule_tags(rule)

    if relative_to is not None:
        try:
            display = str(rule_path.relative_to(relative_to))
        except ValueError:
            display = str(rule_path)
    else:
        display = str(rule_path)

    if not refs:
        return RuleImpact(
            rule=display,
            title=title,
            status="UNKNOWN",
            referenced_fields=[],
            missing_fields=[],
            never_in_before=[],
            level=level,
            tags=tags,
        )

    # Fields the rule needs that existed before but vanished after → silence risk
    missing = sorted(f for f in refs if f in before and f not in after)
    never = sorted(f for f in refs if f not in before)
    referenced = sorted(refs)

    status = "IMPACTED" if missing else "SAFE"
    return RuleImpact(
        rule=display,
        title=title,
        status=status,
        referenced_fields=referenced,
        missing_fields=missing,
        never_in_before=never,
        level=level,
        tags=tags,
    )


def diff_rules(
    before_path: Path | str,
    after_path: Path | str,
    rules_dir: Path | str,
    *,
    ignore: Iterable[str] | None = None,
) -> DiffReport:
    """Compare before/after schemas and flag rules that would go silent."""
    before = schema_from_path(before_path)
    after = schema_from_path(after_path)
    removed = sorted(before - after)

    rules_root = Path(rules_dir)
    rule_files = discover_rules(rules_root, ignore=ignore)
    impacts = [
        analyze_rule(rp, before, after, relative_to=rules_root)
        for rp in rule_files
    ]

    return DiffReport(
        before_fields=sorted(before),
        after_fields=sorted(after),
        removed_fields=removed,
        impacts=impacts,
        rules_scanned=len(rule_files),
        schema_version=REPORT_SCHEMA_VERSION,
    )


def format_report_human(
    report: DiffReport,
    *,
    fail_matches: list[RuleImpact] | None = None,
    fail_on_severity: list[str] | None = None,
    fail_on_tags: list[str] | None = None,
) -> str:
    """Render a human-readable impact report."""
    lines: list[str] = []
    lines.append("detdrift: schema change vs Sigma rules")
    lines.append("=" * 48)
    lines.append(f"Rules scanned:    {report.rules_scanned}")
    lines.append(f"Before fields:    {len(report.before_fields)}")
    lines.append(f"After fields:     {len(report.after_fields)}")
    lines.append(
        f"Removed fields:   {', '.join(report.removed_fields) if report.removed_fields else '(none)'}"
    )
    lines.append("")

    impacted = report.impacted
    safe = report.safe

    if impacted:
        lines.append(f"IMPACTED ({len(impacted)}): rules that would go quiet")
        for item in impacted:
            miss = ", ".join(item.missing_fields)
            lines.append(f"  x {item.rule}")
            lines.append(f"      title:   {item.title}")
            if item.level:
                lines.append(f"      level:   {item.level}")
            if item.tags:
                lines.append(f"      tags:    {', '.join(item.tags)}")
            lines.append(f"      missing: {miss}")
            lines.append(f"      refs:    {', '.join(item.referenced_fields)}")
        lines.append("")
    else:
        lines.append("IMPACTED (0): no rules lose fields from the before schema.")
        lines.append("")

    if safe:
        lines.append(f"SAFE ({len(safe)}): referenced fields still present")
        for item in safe:
            lines.append(f"  ✓ {item.rule}  ({', '.join(item.referenced_fields)})")
        lines.append("")

    unknown = [i for i in report.impacts if i.status == "UNKNOWN"]
    if unknown:
        lines.append(f"UNKNOWN ({len(unknown)}): no field references extracted")
        for item in unknown:
            lines.append(f"  ? {item.rule}")
        lines.append("")

    filters_active = bool(fail_on_severity or fail_on_tags)
    if filters_active:
        matches = fail_matches if fail_matches is not None else []
        sev = ",".join(fail_on_severity or []) or "(none)"
        tags = ",".join(fail_on_tags or []) or "(none)"
        lines.append(f"Fail filter: severity={sev}  tags={tags}")
        lines.append(f"Fail matches: {len(matches)}")
        for item in matches:
            lines.append(f"  ! {item.rule} (level={item.level or '-'})")
        lines.append("")
        if matches:
            lines.append("Result: FAIL (filtered IMPACTED rules matched --fail-on)")
        else:
            lines.append(
                "Result: PASS (IMPACTED rules exist but none matched --fail-on)"
            )
    elif report.has_impacts:
        lines.append("Result: FAIL (detection coverage at risk)")
    else:
        lines.append("Result: PASS (no rules lose fields from this schema change)")
    return "\n".join(lines)
