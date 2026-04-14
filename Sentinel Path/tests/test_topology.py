"""Tests for topology analysis module."""

import pytest

from core.errors import CycleError, GraphTopologyError
from core.topology import build_project_graph, critical_path_nodes, run_cpm
from models.schemas import Dependency, Task


def test_cpm_forward_backward_pass_with_lag() -> None:
    """CPM must compute ES/EF/LS/LF/TF correctly with lag."""
    tasks = [
        Task(id="A", duration=5, optimistic_duration=4, pessimistic_duration=7),
        Task(id="B", duration=3, optimistic_duration=2, pessimistic_duration=4),
        Task(id="C", duration=4, optimistic_duration=3, pessimistic_duration=6),
    ]
    dependencies = [
        Dependency(from_id="A", to_id="C", lag=1.0),
        Dependency(from_id="B", to_id="C", lag=0.0),
    ]

    graph = build_project_graph(tasks, dependencies)
    timing, duration = run_cpm(graph)

    assert duration == pytest.approx(10.0)
    assert timing["A"].es == pytest.approx(0.0)
    assert timing["A"].ef == pytest.approx(5.0)
    assert timing["A"].ls == pytest.approx(0.0)
    assert timing["A"].lf == pytest.approx(5.0)
    assert timing["A"].tf == pytest.approx(0.0)

    assert timing["B"].es == pytest.approx(0.0)
    assert timing["B"].ef == pytest.approx(3.0)
    assert timing["B"].ls == pytest.approx(3.0)
    assert timing["B"].lf == pytest.approx(6.0)
    assert timing["B"].tf == pytest.approx(3.0)

    assert timing["C"].es == pytest.approx(6.0)
    assert timing["C"].ef == pytest.approx(10.0)
    assert timing["C"].ls == pytest.approx(6.0)
    assert timing["C"].lf == pytest.approx(10.0)
    assert timing["C"].tf == pytest.approx(0.0)

    assert critical_path_nodes(timing) == ["A", "C"]


def test_cycle_detection_raises() -> None:
    """Graph builder must reject cyclic dependencies."""
    tasks = [
        Task(id="A", duration=1, optimistic_duration=1, pessimistic_duration=1.5),
        Task(id="B", duration=1, optimistic_duration=0.8, pessimistic_duration=1.2),
    ]
    dependencies = [
        Dependency(from_id="A", to_id="B"),
        Dependency(from_id="B", to_id="A"),
    ]

    with pytest.raises(CycleError):
        build_project_graph(tasks, dependencies)


def test_isolated_nodes_raise_error() -> None:
    """Builder must reject isolated nodes for multi-node projects."""
    tasks = [
        Task(id="A", duration=1, optimistic_duration=0.8, pessimistic_duration=1.2),
        Task(id="B", duration=2, optimistic_duration=1.0, pessimistic_duration=3.0),
    ]

    with pytest.raises(GraphTopologyError):
        build_project_graph(tasks, [])
