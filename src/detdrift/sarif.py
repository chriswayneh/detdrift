"""Emit SARIF 2.1.0 from a DiffReport for CI / PR annotations."""

from __future__ import annotations

import json
from typing import Any

from detdrift import __version__
from detdrift.diff import DiffReport, RuleImpact

SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
RULE_ID = "detdrift-field-missing"


def _level_for_impact(item: RuleImpact) -> str:
    """Map Sigma level to SARIF result level."""
    level = (item.level or "").strip().lower()
    if level in {"critical", "high"}:
        return "error"
    return "warning"


def report_to_sarif(report: DiffReport) -> dict[str, Any]:
    """Build a SARIF 2.1.0 document from IMPACTED rules (and sample warnings)."""
    results: list[dict[str, Any]] = []

    for msg in report.warnings:
        results.append(
            {
                "ruleId": "detdrift-sample-warning",
                "level": "warning",
                "message": {"text": msg},
            }
        )

    for item in report.impacted:
        missing = ", ".join(item.missing_fields) or "(unknown)"
        text = (
            f"Rule may go quiet after schema change: missing field(s) {missing}. "
            f"Title: {item.title}."
        )
        results.append(
            {
                "ruleId": RULE_ID,
                "level": _level_for_impact(item),
                "message": {"text": text},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": item.rule.replace("\\", "/"),
                            }
                        }
                    }
                ],
                "properties": {
                    "missing_fields": item.missing_fields,
                    "referenced_fields": item.referenced_fields,
                    "sigma_level": item.level,
                    "tags": item.tags,
                },
            }
        )

    return {
        "$schema": SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "detdrift",
                        "version": __version__,
                        "informationUri": "https://github.com/chriswayneh/detdrift",
                        "rules": [
                            {
                                "id": RULE_ID,
                                "name": "FieldMissingAfterSchemaChange",
                                "shortDescription": {
                                    "text": "Sigma rule references a field present before and missing after"
                                },
                                "fullDescription": {
                                    "text": (
                                        "A telemetry schema change removed one or more fields that this "
                                        "Sigma rule still references. The rule may stop matching until "
                                        "the mapping or rule is updated."
                                    )
                                },
                                "defaultConfiguration": {"level": "warning"},
                                "helpUri": "https://github.com/chriswayneh/detdrift#readme",
                            },
                            {
                                "id": "detdrift-sample-warning",
                                "name": "SampleIncompleteOrEmpty",
                                "shortDescription": {
                                    "text": "After sample looks empty or incomplete"
                                },
                                "fullDescription": {
                                    "text": (
                                        "The after sample had zero events or far fewer fields than before. "
                                        "An empty file is not the same as nothing removed."
                                    )
                                },
                                "defaultConfiguration": {"level": "warning"},
                            },
                        ],
                    }
                },
                "results": results,
            }
        ],
    }


def format_sarif(report: DiffReport) -> str:
    """Serialize DiffReport as indented SARIF JSON."""
    return json.dumps(report_to_sarif(report), indent=2)

