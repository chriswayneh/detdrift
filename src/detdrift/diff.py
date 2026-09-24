"""Compare before/after schemas to Sigma rules and report impact."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from detdrift.fields import extract_fields_from_rule, load_rule
from detdrift.schema import schema_from_path


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

    @property
    def impacted(self) -> list[RuleImpact]:
        return [i for i in self.impacts if i.status == "IMPACTED"]

    @property
    def safe(self) -> list[RuleImpact]:
        return [i for i in self.impacts if i.status == "SAFE"]

    @property
    def has_impacts(self) -> bool:
        return bool(self.impacted)

    def to_dict(self) -> dict[str, Any]:
        return {
            "before_fields": self.before_fields,
            "after_fields": self.after_fields,
            "removed_fields": self.removed_fields,
            "rules_scanned": self.rules_scanned,
            "impacted_count": len(self.impacted),
            "safe_count": len(self.safe),
            "impacts": [i.to_dict() for i in self.impacts],
        }


def discover_rules(rules_dir: Path | str) -> list[Path]:
    """Find Sigma YAML rule files under a directory (non-recursive + one level)."""
    root = Path(rules_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Rules directory not found: {root}")
    files = sorted(root.glob("*.yml")) + sorted(root.glob("*.yaml"))
    # also one level of subdirs (common layout: rules/windows/*.yml)
    files += sorted(root.glob("*/*.yml")) + sorted(root.glob("*/*.yaml"))
    # de-dupe
    seen: set[Path] = set()
    out: list[Path] = []
    for f in files:
        resolved = f.resolve()
        if resolved not in seen and f.is_file():
            seen.add(resolved)
            out.append(f)
    return out


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
    )


def diff_rules(
    before_path: Path | str,
    after_path: Path | str,
    rules_dir: Path | str,
) -> DiffReport:
    """Compare before/after schemas and flag rules that would go silent."""
    before = schema_from_path(before_path)
    after = schema_from_path(after_path)
    removed = sorted(before - after)

    rules_root = Path(rules_dir)
    rule_files = discover_rules(rules_root)
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
    )


def format_report_human(report: DiffReport) -> str:
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

    if report.has_impacts:
        lines.append("Result: FAIL (detection coverage at risk)")
    else:
        lines.append("Result: PASS (no rules lose fields from this schema change)")
    return "\n".join(lines)
