"""Tests for Sigma field extraction."""

from pathlib import Path

from detdrift.fields import (
    extract_fields_from_detection,
    extract_fields_from_file,
    extract_fields_from_rule,
    strip_modifier,
)

RULES = Path(__file__).resolve().parents[1] / "rules"


def test_strip_modifier():
    assert strip_modifier("CommandLine|contains") == "CommandLine"
    assert strip_modifier("Image|endswith") == "Image"
    assert strip_modifier("User") == "User"
    assert strip_modifier("Event.Data|re") == "Event.Data"


def test_extract_with_modifiers():
    detection = {
        "selection": {
            "Image|endswith": ["\\whoami.exe"],
            "CommandLine|contains": "whoami",
        },
        "condition": "selection",
    }
    fields = extract_fields_from_detection(detection)
    assert fields == {"Image", "CommandLine"}


def test_extract_nested_and_filter():
    detection = {
        "selection": {
            "EventID": 1,
            "ParentImage|endswith": "\\explorer.exe",
        },
        "filter": {
            "User|contains": "SYSTEM",
        },
        "condition": "selection and not filter",
    }
    fields = extract_fields_from_detection(detection)
    assert fields == {"EventID", "ParentImage", "User"}


def test_extract_dotted_field():
    detection = {
        "selection": {
            "winlog.event_data.CommandLine|contains": "whoami",
        },
        "condition": "selection",
    }
    fields = extract_fields_from_detection(detection)
    assert "winlog.event_data.CommandLine" in fields


def test_list_of_maps_under_selection():
    """Common Sigma pattern: selection is a list of field maps (OR)."""
    detection = {
        "selection": [
            {"Image|endswith": "\\whoami.exe"},
            {"CommandLine|contains": "whoami"},
            {"OriginalFileName|endswith": "whoami.exe"},
        ],
        "condition": "selection",
    }
    fields = extract_fields_from_detection(detection)
    assert fields == {"Image", "CommandLine", "OriginalFileName"}


def test_nested_dict_field_paths():
    """Nested dict under a field-like key yields dotted paths."""
    detection = {
        "selection": {
            "EventData": {
                "CommandLine|contains": "whoami",
                "Image|endswith": "\\cmd.exe",
            }
        },
        "condition": "selection",
    }
    fields = extract_fields_from_detection(detection)
    assert "EventData" in fields
    assert "EventData.CommandLine" in fields
    assert "EventData.Image" in fields


def test_list_of_maps_with_modifiers_mixed():
    detection = {
        "selection_cmd": [
            {
                "Image|endswith": ["\\cmd.exe", "/bin/bash"],
                "CommandLine|contains|all": ["whoami", "/all"],
            },
            {"ParentImage|endswith": "\\explorer.exe"},
        ],
        "condition": "selection_cmd",
    }
    fields = extract_fields_from_detection(detection)
    assert fields == {"Image", "CommandLine", "ParentImage"}


def test_sample_rule_file():
    fields = extract_fields_from_file(RULES / "proc_whoami.yml")
    assert fields == {"Image", "CommandLine"}


def test_condition_not_treated_as_field():
    rule = {
        "title": "t",
        "detection": {
            "selection": {"Image": "x"},
            "condition": "selection",
        },
    }
    fields = extract_fields_from_rule(rule)
    assert "condition" not in fields
    assert fields == {"Image"}


def test_keyword_only_no_fields():
    detection = {
        "keywords": ["mimikatz", "sekurlsa"],
        "condition": "keywords",
    }
    fields = extract_fields_from_detection(detection)
    assert "mimikatz" not in fields
    assert "sekurlsa" not in fields
    assert "keywords" not in fields
