"""Benchmark Sentinel Path performance across graph sizes and iterations."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import SentinelEngine


@dataclass(frozen=True)
class BenchmarkCase:
    """Single benchmark setup."""

    nodes: int
    iterations: int


def _build_chain_with_convergence(node_count: int) -> tuple[list[dict], list[dict]]:
    """Build a DAG with linear chain and periodic convergence points."""
    tasks = []
    dependencies = []
    for idx in range(node_count):
        task_id = f"task_{idx:03d}"
        base = 2.0 + (idx % 7) * 0.35
        tasks.append(
            {
                "id": task_id,
                "duration": base,
                "optimistic_duration": max(0.5, base * 0.7),
                "pessimistic_duration": base * 1.6,
            }
        )
        if idx > 0:
            dependencies.append(
                {
                    "from_id": f"task_{idx-1:03d}",
                    "to_id": task_id,
                    "type": "FS",
                    "lag": 0.0,
                }
            )
        if idx > 2 and idx % 5 == 0:
            dependencies.append(
                {
                    "from_id": f"task_{idx-3:03d}",
                    "to_id": task_id,
                    "type": "FS",
                    "lag": 0.0,
                }
            )
    return tasks, dependencies


def run_benchmark() -> None:
    """Run benchmark matrix and store csv + markdown report."""
    matrix = [
        BenchmarkCase(nodes=10, iterations=100),
        BenchmarkCase(nodes=10, iterations=1000),
        BenchmarkCase(nodes=10, iterations=10000),
        BenchmarkCase(nodes=100, iterations=100),
        BenchmarkCase(nodes=100, iterations=1000),
        BenchmarkCase(nodes=100, iterations=10000),
        BenchmarkCase(nodes=500, iterations=100),
        BenchmarkCase(nodes=500, iterations=1000),
        BenchmarkCase(nodes=500, iterations=10000),
    ]

    benchmarks_dir = Path("benchmarks")
    benchmarks_dir.mkdir(parents=True, exist_ok=True)
    csv_path = benchmarks_dir / "latest.csv"
    md_path = benchmarks_dir / "latest.md"

    rows: list[dict[str, float | int]] = []
    engine = SentinelEngine()

    for case in matrix:
        tasks, dependencies = _build_chain_with_convergence(case.nodes)
        start = time.perf_counter()
        report = engine.analyze(
            tasks_raw=tasks,
            dependencies_raw=dependencies,
            config_raw={"mc_iterations": case.iterations},
        )
        elapsed = time.perf_counter() - start
        rows.append(
            {
                "nodes": case.nodes,
                "iterations": case.iterations,
                "seconds": round(elapsed, 4),
                "ms_per_iteration": round((elapsed * 1000.0) / case.iterations, 6),
                "confidence": report.project_confidence,
            }
        )

    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["nodes", "iterations", "seconds", "ms_per_iteration", "confidence"],
        )
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Sentinel Path benchmark",
        "",
        "| Nodes | Iterations | Seconds | ms/iter | Confidence |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['nodes']} | {row['iterations']} | {row['seconds']} | "
            f"{row['ms_per_iteration']} | {row['confidence']} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Saved benchmark CSV: {csv_path}")
    print(f"Saved benchmark report: {md_path}")


if __name__ == "__main__":
    run_benchmark()
