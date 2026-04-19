"""CLI entry point for Sentinel Path."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from sentinel_path.engine import SentinelEngine
from sentinel_path.path_handler import clean_path, validate_access


def _load_json(path: Path) -> object:
    """
    Safely loads and parses a JSON file from a validated path.
    
    Why: Using UTF-8 ensures consistency across platforms and handles special characters
    in task names or descriptions.
    
    Business result: Provides a clean data structure for the engine to analyze.
    """
    # Using clean_path to normalize input path string to handle cross-platform differences
    normalized_path = clean_path(path)
    
    # We check access early to fail fast if the file is not readable, improving UX.
    if not validate_access(normalized_path, os.R_OK):
        print(f"Error: Path '{normalized_path}' is not accessible for reading.")
        sys.exit(1)
        
    return json.loads(normalized_path.read_text(encoding="utf-8"))


def main() -> None:
    """
    Main CLI entry point for project fragility and risk analysis.
    
    Why: Orchestrates the loading of tasks, dependencies, and configuration to produce
    a comprehensive report on project schedule risks.
    
    Business result: Enables users to run analysis from the terminal or automate it
    via CI/CD pipelines.
    """
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

    # The engine is our primary facade that hides the complexity of topology and stochastic logic.
    engine = SentinelEngine()
    
    # We load each component separately to isolate potential parsing errors.
    report = engine.analyze(
        tasks_raw=_load_json(args.tasks),
        dependencies_raw=_load_json(args.dependencies),
        config_raw=_load_json(args.config) if args.config else None,
    )

    # Chart generation is optional to save time in high-frequency automated runs.
    if args.charts_dir:
        charts_path = clean_path(args.charts_dir)
        # We ensure the directory exists before attempting to write images.
        charts_path.mkdir(parents=True, exist_ok=True)
        engine.export_charts(charts_path)

    payload = report.model_dump()
    if args.output:
        output_path = clean_path(args.output)
        # We write with ensure_ascii=False to support non-Latin characters in reports.
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
