"""Facade orchestrator for Sentinel Path analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import importlib.util
import sys

from core.fragility import find_fragility_points
from core.topology import build_project_graph, critical_path_nodes, run_cpm
from models.schemas import Dependency, ProjectConfig, SentinelReport, Task


def _load_simulation_module() -> Any:
    """Load simulation module from math/simulation.py safely."""
    module_path = Path(__file__).parent / "math" / "simulation.py"
    spec = importlib.util.spec_from_file_location("sentinel_simulation", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("Failed to load simulation module.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SentinelEngine:
    """Facade for topology, fragility and stochastic analysis."""

    def analyze(
        self,
        tasks_raw: list[dict[str, Any]],
        dependencies_raw: list[dict[str, Any]],
        config_raw: dict[str, Any] | None = None,
    ) -> SentinelReport:
        """Validate input and produce final Sentinel report."""
        tasks = [Task.model_validate(task) for task in tasks_raw]
        dependencies = [
            Dependency.model_validate(dependency) for dependency in dependencies_raw
        ]
        config = ProjectConfig.model_validate(config_raw or {})

        graph = build_project_graph(tasks, dependencies)
        timing, project_duration = run_cpm(graph)
        critical_path = critical_path_nodes(timing)

        tf_by_node = {node: metrics.tf for node, metrics in timing.items()}
        predecessors = {node: list(graph.predecessors(node)) for node in graph.nodes}
        fragility = find_fragility_points(
            timing_by_node=tf_by_node,
            project_duration=project_duration,
            convergence_threshold_pct=config.convergence_threshold_pct,
            predecessors_by_node=predecessors,
        )

        simulation_module = _load_simulation_module()
        simulation_result = simulation_module.run_monte_carlo(
            graph=graph,
            tasks=tasks,
            mc_iterations=config.mc_iterations,
            baseline_duration=project_duration,
        )

        return SentinelReport(
            project_duration_base=round(project_duration, 2),
            critical_path_base=critical_path,
            fragility_points=fragility,
            cruciality_metrics=simulation_result.cruciality_metrics,
            project_confidence=simulation_result.project_confidence,
        )
