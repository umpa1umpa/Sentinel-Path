"""Tests for package-level Sentinel Path API."""

from sentinel_path import SentinelEngine
from sentinel_path.schemas import Task


def test_package_imports_work() -> None:
    """Package imports should expose the expected public API."""
    task = Task(
        id="A",
        duration=1.0,
        optimistic_duration=0.8,
        pessimistic_duration=1.4,
    )
    assert task.id == "A"

    engine = SentinelEngine()
    report = engine.analyze(
        tasks_raw=[
            {
                "id": "A",
                "duration": 2.0,
                "optimistic_duration": 1.0,
                "pessimistic_duration": 3.0,
            }
        ],
        dependencies_raw=[],
        config_raw={"mc_iterations": 50},
    )
    assert report.project_duration_base > 0
