"""Integration tests for SentinelEngine facade."""

from pathlib import Path

from pydantic import ValidationError
import pytest

from engine import SentinelEngine
from models.schemas import Task


def test_task_validation_bounds() -> None:
    """Task validation rejects optimistic duration above base."""
    with pytest.raises(ValidationError):
        Task(
            id="A",
            duration=5.0,
            optimistic_duration=6.0,
            pessimistic_duration=7.0,
        )


def test_engine_pipeline_output_shape() -> None:
    """Engine must return complete report structure."""
    engine = SentinelEngine()
    report = engine.analyze(
        tasks_raw=[
            {
                "id": "task_1",
                "duration": 5.0,
                "optimistic_duration": 4.0,
                "pessimistic_duration": 8.0,
            },
            {
                "id": "task_2",
                "duration": 5.0,
                "optimistic_duration": 4.5,
                "pessimistic_duration": 6.5,
            },
            {
                "id": "task_3",
                "duration": 2.0,
                "optimistic_duration": 1.0,
                "pessimistic_duration": 3.0,
            },
        ],
        dependencies_raw=[
            {"from_id": "task_1", "to_id": "task_3", "type": "FS", "lag": 0.0},
            {"from_id": "task_2", "to_id": "task_3", "type": "FS", "lag": 0.0},
        ],
        config_raw={"mc_iterations": 200, "convergence_threshold_pct": 0.2},
    )

    assert report.project_duration_base > 0
    assert set(report.critical_path_base).issubset({"task_1", "task_2", "task_3"})
    assert len(report.fragility_points) == 1
    assert report.fragility_points[0].node_id == "task_3"
    assert report.fragility_points[0].incoming_critical_paths == 2
    assert set(report.cruciality_metrics.keys()) == {"task_1", "task_2", "task_3"}
    assert set(report.sensitivity_spearman.keys()) == {"task_1", "task_2", "task_3"}
    assert set(report.tornado_impact.keys()) == {"task_1", "task_2", "task_3"}
    for metric in report.cruciality_metrics.values():
        assert 0.0 <= metric <= 100.0
    for rho in report.sensitivity_spearman.values():
        assert -1.0 <= rho <= 1.0
    assert 0.0 <= report.project_confidence <= 100.0


def test_export_charts_creates_expected_files(tmp_path) -> None:
    """Engine should export histogram, s-curve and tornado charts."""
    engine = SentinelEngine()
    engine.analyze(
        tasks_raw=[
            {
                "id": "task_1",
                "duration": 5.0,
                "optimistic_duration": 4.0,
                "pessimistic_duration": 8.0,
            },
            {
                "id": "task_2",
                "duration": 5.0,
                "optimistic_duration": 4.5,
                "pessimistic_duration": 6.5,
            },
            {
                "id": "task_3",
                "duration": 2.0,
                "optimistic_duration": 1.0,
                "pessimistic_duration": 3.0,
            },
        ],
        dependencies_raw=[
            {"from_id": "task_1", "to_id": "task_3", "type": "FS", "lag": 0.0},
            {"from_id": "task_2", "to_id": "task_3", "type": "FS", "lag": 0.0},
        ],
        config_raw={"mc_iterations": 150},
    )
    exported = engine.export_charts(tmp_path)

    for key in ("finish_date_histogram", "s_curve", "tornado"):
        assert key in exported
        assert (tmp_path / Path(exported[key]).name).exists()
