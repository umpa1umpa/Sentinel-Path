"""Facade orchestrator for Sentinel Path analysis."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from core.fragility import find_fragility_points
from core.errors import GraphTopologyError
from core.topology import build_project_graph, critical_path_nodes, run_cpm
from models.schemas import Dependency, ProjectConfig, SentinelReport, Task
from stochastic.simulation import run_monte_carlo


@dataclass(frozen=True)
class _AnalysisSnapshot:
    """In-memory simulation outputs for post-analysis visualization."""

    project_durations: np.ndarray
    sensitivity_spearman: dict[str, float]
    tornado_impact: dict[str, float]


class SentinelEngine:
    """
    Facade for topology, fragility and stochastic analysis.
    
    This class orchestrates the entire analysis pipeline, from graph building
    to Monte Carlo simulations and chart generation.
    
    Business result: Provides a high-level API for project managers and analysts
     to assess project schedule risks and identify critical paths.
    """

    def __init__(self) -> None:
        self._last_snapshot: _AnalysisSnapshot | None = None

    def analyze(
        self,
        tasks_raw: list[dict[str, Any]],
        dependencies_raw: list[dict[str, Any]],
        config_raw: dict[str, Any] | None = None,
    ) -> SentinelReport:
        """
        Validates input data and produces a comprehensive Sentinel report.
        
        Why: We separate the raw dictionary input from the internal Pydantic models
        to ensure data integrity and catch schema errors early.
        
        Business result: A structured report containing project duration, critical paths,
        and fragility metrics for risk management.
        """
        # We validate the models here so that the engine works with clean, typed objects.
        tasks = [Task.model_validate(task) for task in tasks_raw]
        dependencies = [
            Dependency.model_validate(dependency) for dependency in dependencies_raw
        ]
        config = ProjectConfig.model_validate(config_raw or {})

        # 1. Build the project graph - this is the backbone of all further analysis.
        graph = build_project_graph(tasks, dependencies)
        
        # 2. Run Critical Path Method (CPM) to find baseline project duration.
        timing, project_duration = run_cpm(graph)
        critical_path = critical_path_nodes(timing)

        # 3. Identify fragility points where paths converge and risks are high.
        tf_by_node = {node: metrics.tf for node, metrics in timing.items()}
        predecessors = {node: list(graph.predecessors(node)) for node in graph.nodes}
        fragility = find_fragility_points(
            timing_by_node=tf_by_node,
            project_duration=project_duration,
            convergence_threshold_pct=config.convergence_threshold_pct,
            predecessors_by_node=predecessors,
        )

        # 4. Run Monte Carlo simulation for stochastic risk assessment.
        simulation_result = run_monte_carlo(
            graph=graph,
            tasks=tasks,
            mc_iterations=config.mc_iterations,
            baseline_duration=project_duration,
            rng_seed=config.rng_seed,
        )
        
        # We save the simulation snapshot for future chart generation to avoid re-running MC.
        self._last_snapshot = _AnalysisSnapshot(
            project_durations=simulation_result.project_durations,
            sensitivity_spearman=simulation_result.sensitivity_spearman,
            tornado_impact=simulation_result.tornado_impact,
        )

        return SentinelReport(
            project_duration_base=round(project_duration, 2),
            critical_path_base=critical_path,
            fragility_points=fragility,
            cruciality_metrics=simulation_result.cruciality_metrics,
            project_confidence=simulation_result.project_confidence,
            sensitivity_spearman=simulation_result.sensitivity_spearman,
            tornado_impact=simulation_result.tornado_impact,
        )

    def export_charts(
        self, output_dir: str | Path, top_n_tornado: int = 10
    ) -> dict[str, str]:
        """
        Generates and saves visual analysis charts to the specified directory.
        
        Why: Visualizing risk distributions and tornado impacts makes the analytical
        results more accessible to stakeholders than raw numbers.
        
        Business result: Three PNG files providing a visual overview of project risks.
        """
        if self._last_snapshot is None:
            # We enforce a strict order of operations: analyze first, then visualize.
            raise GraphTopologyError("Run analyze() before export_charts().")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        project_durations = self._last_snapshot.project_durations

        histogram_path = output_path / "finish_date_histogram.png"
        plt.figure(figsize=(8, 5))
        plt.hist(project_durations, bins=25, density=True, alpha=0.75, color="#2C7FB8")
        plt.title("Project Finish Duration Distribution")
        plt.xlabel("Duration (days)")
        plt.ylabel("Density")
        plt.tight_layout()
        plt.savefig(histogram_path, dpi=120)
        plt.close()

        s_curve_path = output_path / "s_curve.png"
        sorted_durations = np.sort(project_durations)
        cumulative_prob = np.arange(1, len(sorted_durations) + 1) / len(sorted_durations)
        plt.figure(figsize=(8, 5))
        plt.plot(sorted_durations, cumulative_prob, color="#1A9641", linewidth=2.0)
        plt.title("S-Curve (Completion Probability by Date)")
        plt.xlabel("Duration (days)")
        plt.ylabel("Probability")
        plt.ylim(0.0, 1.0)
        plt.grid(alpha=0.25)
        plt.tight_layout()
        plt.savefig(s_curve_path, dpi=120)
        plt.close()

        tornado_path = output_path / "tornado.png"
        sorted_impacts = sorted(
            self._last_snapshot.tornado_impact.items(),
            key=lambda item: abs(item[1]),
            reverse=True,
        )[:top_n_tornado]
        labels = [item[0] for item in sorted_impacts]
        impacts = [item[1] for item in sorted_impacts]
        plt.figure(figsize=(9, max(4, len(labels) * 0.45)))
        plt.barh(labels[::-1], impacts[::-1], color="#F46D43")
        plt.title("Tornado Impact (+1 day in task duration)")
        plt.xlabel("Project delay (days)")
        plt.tight_layout()
        plt.savefig(tornado_path, dpi=120)
        plt.close()

        return {
            "finish_date_histogram": str(histogram_path),
            "s_curve": str(s_curve_path),
            "tornado": str(tornado_path),
        }
