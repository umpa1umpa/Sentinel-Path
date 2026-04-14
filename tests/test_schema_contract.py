"""Tests for JSON schema contract export."""

from sentinel_path.contracts import get_report_json_schema, write_report_json_schema


def test_report_schema_contains_core_fields(tmp_path) -> None:
    """Exported schema should contain required report contract properties."""
    schema = get_report_json_schema()
    assert schema["type"] == "object"
    assert "project_duration_base" in schema["properties"]
    assert "critical_path_base" in schema["properties"]
    assert "project_confidence" in schema["properties"]

    out = write_report_json_schema(tmp_path / "sentinel_report.schema.json")
    assert out.exists()
