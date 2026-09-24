"""Tests for NDJSON schema extraction."""

from pathlib import Path

from detdrift.schema import schema_from_events, schema_from_ndjson, schema_from_path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_top_level_keys():
    events = [
        {"Image": "a.exe", "CommandLine": "a", "User": "u"},
        {"Image": "b.exe", "CommandLine": "b"},
    ]
    schema = schema_from_events(events)
    assert schema == {"Image", "CommandLine", "User"}


def test_one_level_nested():
    events = [{"process": {"name": "cmd.exe", "pid": 1}, "User": "alice"}]
    schema = schema_from_events(events, nested=True)
    assert "process" in schema
    assert "process.name" in schema
    assert "process.pid" in schema
    assert "User" in schema


def test_before_fixture():
    schema = schema_from_path(FIXTURES / "before")
    assert schema == {"Image", "CommandLine", "User"}


def test_after_fixture():
    schema = schema_from_path(FIXTURES / "after")
    assert schema == {"Image", "cmd", "User"}
    assert "CommandLine" not in schema


def test_ndjson_file_directly():
    schema = schema_from_ndjson(FIXTURES / "before" / "process.jsonl")
    assert "CommandLine" in schema


def test_utf8_bom_ndjson(tmp_path):
    """PowerShell Set-Content -Encoding utf8 writes a BOM; parsing must still work."""
    line = '{"Image": "cmd.exe", "CommandLine": "whoami", "User": "alice"}\n'
    bom_file = tmp_path / "bom.jsonl"
    bom_file.write_bytes(b"\xef\xbb\xbf" + line.encode("utf-8"))

    schema = schema_from_ndjson(bom_file)
    assert schema == {"Image", "CommandLine", "User"}

    schema_via_path = schema_from_path(bom_file)
    assert schema_via_path == {"Image", "CommandLine", "User"}
