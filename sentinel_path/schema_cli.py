"""CLI utility to export Sentinel Path JSON schema."""

from __future__ import annotations

import argparse

from sentinel_path.contracts import write_report_json_schema


def main() -> None:
    """Export SentinelReport JSON schema to disk."""
    parser = argparse.ArgumentParser(description="Export SentinelReport JSON Schema.")
    parser.add_argument(
        "--output",
        default="schemas/sentinel_report.schema.json",
        help="Output schema file path.",
    )
    args = parser.parse_args()
    out = write_report_json_schema(args.output)
    print(f"Schema exported: {out}")


if __name__ == "__main__":
    main()
