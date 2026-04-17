"""CLI entry point for Sentinel Path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sentinel_path.engine import SentinelEngine


def _load_json(path: Path) -> object:
    # Centralized UTF-8 loading keeps CLI behavior stable across Windows/Linux shells.
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Sentinel Path analysis.")
    parser.add_argument("--tasks", type=Path, required=True, help="Path to tasks JSON file")
    parser.add_argument(
        "--dependencies",
        type=Path,
        required=True,
        help="Path to dependencies JSON file",
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=False,
        help="Path to optional config JSON file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=False,
        help="Path to output report JSON file (defaults to stdout)",
    )
    parser.add_argument(
        "--charts-dir",
        type=Path,
        required=False,
        help="Optional directory to export charts",
    )
    args = parser.parse_args()

    engine = SentinelEngine()
    report = engine.analyze(
        tasks_raw=_load_json(args.tasks),
        dependencies_raw=_load_json(args.dependencies),
        config_raw=_load_json(args.config) if args.config else None,
    )

    if args.charts_dir:
        engine.export_charts(args.charts_dir)

    payload = report.model_dump()
    # TODO: Add optional JSON Schema validation for input files before analyze() to
    # surface malformed payloads with clearer CLI diagnostics.
    if args.output:
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
