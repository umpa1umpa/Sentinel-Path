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
    """Читает JSON с диска. Да, это тонкая обертка, но она держит IO в одном месте."""
    # FIXME: argparse уже дает Path, но мы все равно прогоняем через clean_path.
    # Это работает, но выглядит как "двойная броня". Когда-нибудь надо упростить.
    normalized_path = clean_path(path)

    # Падаем рано: лучше сразу, чем после половины пайплайна.
    if not validate_access(normalized_path, os.R_OK):
        print(f"Error: Path '{normalized_path}' is not accessible for reading.")
        sys.exit(1)

    # Внимание: пустой файл или `{}` без нужных полей — это разные истории.
    # Пустой файл уронит json.loads, а `{}` для tasks — уже ValidationError внутри engine.
    # TODO: нормальная валидация "пустой config = дефолты" пока не сделана.
    return json.loads(normalized_path.read_text(encoding="utf-8"))


def main() -> None:
    """CLI: собрать вход, прогнать engine, опционально сохранить картинки."""
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

    # Грузим кусками: так проще понять, какой именно JSON больной.
    report = engine.analyze(
        tasks_raw=_load_json(args.tasks),
        dependencies_raw=_load_json(args.dependencies),
        config_raw=_load_json(args.config) if args.config else None,
    )

    if args.charts_dir:
        charts_path = clean_path(args.charts_dir)
        # TODO: проверить writable, а не только mkdir. Сейчас mkdir "успокаивает", но не гарантирует.
        charts_path.mkdir(parents=True, exist_ok=True)
        engine.export_charts(charts_path)

    payload = report.model_dump()
    if args.output:
        output_path = clean_path(args.output)
        # UTF-8 + ensure_ascii=False: кириллица в id задач не должна превращаться в \\uXXXX в отчете.
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
