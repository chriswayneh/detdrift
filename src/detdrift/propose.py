"""Propose mapping notes or draft rule patches after a schema change.

Offline helper for Phase 2 Assist. Never edits rules in place. Never commits.
Heuristic renames when the mapping is obvious; otherwise mapping notes only.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from detdrift.diff import DiffReport, diff_rules
from detdrift.schema import schema_from_path

# Well-known field aliases seen in Windows / ECS / OCSF-ish telemetry.
_KNOWN_ALIASES: dict[str, frozenset[str]] = {
    "CommandLine": frozenset({"cmd", "command_line", "CommandLine", "process.command_line"}),
    "cmd": frozenset({"CommandLine", "command_line", "process.command_line"}),
    "command_line": frozenset({"CommandLine", "cmd", "process.command_line"}),
    "Image": frozenset({"image", "ImagePath", "process.executable", "NewProcessName"}),
    "ParentImage": frozenset({"parent_image", "ParentImagePath", "process.parent.executable"}),
    "User": frozenset({"user", "UserName", "user.name", "SubjectUserName"}),
    "ProcessId": frozenset({"pid", "ProcessID", "process.pid"}),
    "ParentProcessId": frozenset({"ppid", "ParentProcessID", "process.parent.pid"}),
    "OriginalFileName": frozenset({"original_file_name", "OriginalFilename"}),
}


def _normalize(name: str) -> str:
    """Lowercase and strip underscores/dots/hyphens for fuzzy compare."""
    return re.sub(r"[_\.\-]", "", name).lower()


def _alias_candidates(removed: str) -> set[str]:
    """Return known alias spellings for a removed field name."""
    out: set[str] = set()
    if removed in _KNOWN_ALIASES:
        out |= set(_KNOWN_ALIASES[removed])
    norm = _normalize(removed)
    for key, aliases in _KNOWN_ALIASES.items():
        if _normalize(key) == norm:
            out |= set(aliases)
            out.add(key)
        for a in aliases:
            if _normalize(a) == norm:
                out |= set(aliases)
                out.add(key)
    out.discard(removed)
    return out


def infer_renames(
    before: set[str],
    after: set[str],
) -> dict[str, str | None]:
    """Map each removed field to a suggested after-field, or None if unclear.

    Heuristics (in order):
    1. Known alias table hit present in ``after``.
    2. Fuzzy match against a single obvious added field (e.g. CommandLine to cmd).
    3. Otherwise ``None`` (notes-only for that field).
    """
    removed = sorted(before - after)
    added = sorted(after - before)
    added_set = set(added)
    mapping: dict[str, str | None] = {}
    used_targets: set[str] = set()

    for field_name in removed:
        candidates = [
            c for c in _alias_candidates(field_name) if c in added_set and c not in used_targets
        ]
        if len(candidates) == 1:
            mapping[field_name] = candidates[0]
            used_targets.add(candidates[0])
            continue
        if len(candidates) > 1:
            pick = sorted(candidates, key=lambda s: (len(s), s))[0]
            mapping[field_name] = pick
            used_targets.add(pick)
            continue

        norm_removed = _normalize(field_name)
        fuzzy: list[str] = []
        for a in added:
            if a in used_targets:
                continue
            na = _normalize(a)
            if not na or not norm_removed:
                continue
            if na == norm_removed:
                fuzzy.append(a)
            elif na in norm_removed or norm_removed in na:
                shorter = na if len(na) <= len(norm_removed) else norm_removed
                if len(shorter) >= 3:
                    fuzzy.append(a)

        if len(fuzzy) == 1:
            mapping[field_name] = fuzzy[0]
            used_targets.add(fuzzy[0])
        elif len(fuzzy) > 1 and len(added) == 1:
            mapping[field_name] = added[0]
            used_targets.add(added[0])
        else:
            mapping[field_name] = None

    return mapping


@dataclass
class ProposeResult:
    """Draft assist output for a schema change."""

    report: DiffReport
    renames: dict[str, str | None]
    added_fields: list[str] = field(default_factory=list)
    removed_fields: list[str] = field(default_factory=list)

    @property
    def confident_renames(self) -> dict[str, str]:
        return {k: v for k, v in self.renames.items() if v is not None}

    @property
    def unclear(self) -> list[str]:
        return [k for k, v in self.renames.items() if v is None]


def propose_from_paths(
    before_path: Path | str,
    after_path: Path | str,
    rules_dir: Path | str,
    *,
    ignore: Iterable[str] | None = None,
) -> ProposeResult:
    """Run diff + rename heuristics for the given paths."""
    before = schema_from_path(before_path)
    after = schema_from_path(after_path)
    report = diff_rules(before_path, after_path, rules_dir, ignore=ignore)
    renames = infer_renames(before, after)
    return ProposeResult(
        report=report,
        renames=renames,
        added_fields=sorted(after - before),
        removed_fields=sorted(before - after),
    )


def format_notes(result: ProposeResult) -> str:
    """Human-readable mapping notes (default propose-patch format)."""
    lines: list[str] = []
    lines.append("detdrift propose-patch: mapping notes")
    lines.append("=" * 48)
    lines.append(f"Rules scanned:     {result.report.rules_scanned}")
    lines.append(f"IMPACTED rules:    {len(result.report.impacted)}")
    lines.append(
        f"Removed fields:    {', '.join(result.removed_fields) if result.removed_fields else '(none)'}"
    )
    lines.append(
        f"Added fields:      {', '.join(result.added_fields) if result.added_fields else '(none)'}"
    )
    lines.append("")

    if not result.removed_fields:
        lines.append("No fields were removed. Nothing to propose.")
        lines.append("")
        lines.append("Review these notes yourself. detdrift does not edit rules or commit.")
        return "\n".join(lines)

    lines.append("Suggested renames (heuristic):")
    if result.confident_renames:
        for old, new in sorted(result.confident_renames.items()):
            lines.append(f"  {old}  ->  {new}")
    else:
        lines.append("  (none confident enough to auto-suggest)")
    lines.append("")

    if result.unclear:
        lines.append("Unclear removals (review the after schema by hand):")
        for name in result.unclear:
            lines.append(f"  {name}  ->  ?")
        if result.added_fields:
            lines.append(f"  Candidates in after: {', '.join(result.added_fields)}")
        lines.append("")

    impacted = result.report.impacted
    if impacted:
        lines.append("IMPACTED rules and what to change:")
        for item in impacted:
            lines.append(f"  - {item.rule}  ({item.title})")
            for miss in item.missing_fields:
                target = result.renames.get(miss)
                if target:
                    lines.append(
                        f"      replace field key `{miss}` with `{target}` (keep |modifiers)"
                    )
                else:
                    lines.append(
                        f"      field `{miss}` gone; map manually (no confident rename)"
                    )
        lines.append("")

    lines.append("These are drafts for human review.")
    lines.append(
        "detdrift does not edit rule files, does not auto-commit, and needs no network."
    )
    return "\n".join(lines)


def _replace_field_keys_in_text(text: str, renames: dict[str, str]) -> str:
    """Replace Sigma field keys (with optional |modifiers) using confident renames.

    Only rewrites keys that look like YAML map keys: ``FieldName:`` or
    ``FieldName|modifier:``. Does not touch bare string values.
    """
    if not renames:
        return text

    ordered = sorted(renames.keys(), key=len, reverse=True)

    def replacer(match: re.Match[str]) -> str:
        indent = match.group(1)
        bare = match.group(2)
        mods = match.group(3) or ""
        rest = match.group(4)
        if bare in renames:
            return f"{indent}{renames[bare]}{mods}{rest}"
        return match.group(0)

    pattern = re.compile(
        r"^([ \t]*)("
        + "|".join(re.escape(k) for k in ordered)
        + r")((?:\|[A-Za-z0-9_]+)*)(:)",
        re.MULTILINE,
    )
    return pattern.sub(replacer, text)


def format_patch(result: ProposeResult, rules_dir: Path | str) -> str:
    """Emit a unified-diff style patch for IMPACTED rules with confident renames.

    Rules without a confident rename for every missing field are skipped with
    a comment in the patch header. Nothing is written to disk.
    """
    rules_root = Path(rules_dir)
    renames = result.confident_renames
    lines: list[str] = []
    lines.append("# detdrift propose-patch --format patch")
    lines.append("# Draft only. Review before applying. No files were modified.")
    if not renames:
        lines.append("# No confident renames inferred; empty patch.")
        lines.append("# Use --format notes for mapping guidance.")
        return "\n".join(lines)

    lines.append(
        "# Suggested renames: "
        + ", ".join(f"{k}->{v}" for k, v in sorted(renames.items()))
    )
    lines.append("")

    patched_any = False
    for item in result.report.impacted:
        if not item.missing_fields:
            continue
        if any(m not in renames for m in item.missing_fields):
            lines.append(f"# skip {item.rule}: missing field(s) without confident rename")
            continue

        rule_path = rules_root / item.rule
        if not rule_path.is_file():
            rule_path = Path(item.rule)
        if not rule_path.is_file():
            lines.append(f"# skip {item.rule}: file not found")
            continue

        original = rule_path.read_text(encoding="utf-8")
        updated = _replace_field_keys_in_text(original, renames)
        if updated == original:
            lines.append(f"# skip {item.rule}: no textual key replacements applied")
            continue

        patched_any = True
        display = item.rule.replace("\\", "/")
        old_lines = original.splitlines(keepends=True)
        new_lines = updated.splitlines(keepends=True)
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{display}",
            tofile=f"b/{display}",
            lineterm="\n",
        )
        diff_text = "".join(diff)
        if not diff_text.endswith("\n"):
            diff_text += "\n"
        lines.append(diff_text.rstrip("\n"))
        lines.append("")

    if not patched_any:
        lines.append("# No rule patches generated.")

    return "\n".join(lines).rstrip() + "\n"


def format_propose(result: ProposeResult, rules_dir: Path | str, fmt: str) -> str:
    """Dispatch notes vs patch formatting."""
    fmt = (fmt or "notes").strip().lower()
    if fmt == "notes":
        return format_notes(result)
    if fmt == "patch":
        return format_patch(result, rules_dir)
    raise ValueError(f"Unknown propose-patch format: {fmt!r} (use notes or patch)")
