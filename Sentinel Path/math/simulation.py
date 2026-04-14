"""Monte Carlo simulation with Beta-PERT distributions."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np

from core.errors import GraphTopologyError
from models.schemas import Task


@dataclass(frozen=True)
class SimulationResult:
    """Result of stochastic schedule simulation."""

    cruciality_metrics: dict[str, float]
    project_confidence: float


def run_monte_carlo(
    graph: nx.DiGraph,
    tasks: list[Task],
    mc_iterations: int,
    baseline_duration: float,
    rng_seed: int | None = 42,
) -> SimulationResult:
    """Run Monte Carlo simulation and compute cruciality index per task."""
    if mc_iterations < 1:
        raise GraphTopologyError("mc_iterations must be >= 1.")

    task_by_id = {task.id: task for task in tasks}
    topo_order = list(nx.topological_sort(graph))
    if not topo_order:
        raise GraphTopologyError("Cannot simulate an empty graph.")

    durations = _sample_pert_durations(task_by_id, topo_order, mc_iterations, rng_seed)
    total_float, project_durations = _compute_total_float_matrix(graph, topo_order, durations)

    critical_hits = np.isclose(total_float, 0.0, atol=1e-8).sum(axis=0)
    cruciality = {
        node: round(float(critical_hits[idx] * 100.0 / mc_iterations), 2)
        for idx, node in enumerate(topo_order)
    }
    project_confidence = round(
        float((project_durations <= baseline_duration).sum() * 100.0 / mc_iterations), 2
    )
    return SimulationResult(
        cruciality_metrics=cruciality,
        project_confidence=project_confidence,
    )


def _sample_pert_durations(
    task_by_id: dict[str, Task],
    topo_order: list[str],
    mc_iterations: int,
    rng_seed: int | None,
) -> np.ndarray:
    """Sample task durations using Beta-PERT for all iterations."""
    rng = np.random.default_rng(rng_seed)
    samples = np.zeros((mc_iterations, len(topo_order)), dtype=np.float64)

    for idx, task_id in enumerate(topo_order):
        task = task_by_id[task_id]
        low = task.optimistic_duration
        mode = task.duration
        high = task.pessimistic_duration

        if np.isclose(low, high):
            samples[:, idx] = low
            continue

        alpha = 1.0 + 4.0 * (mode - low) / (high - low)
        beta = 1.0 + 4.0 * (high - mode) / (high - low)
        beta_samples = rng.beta(alpha, beta, size=mc_iterations)
        samples[:, idx] = low + beta_samples * (high - low)

    return samples


def _compute_total_float_matrix(
    graph: nx.DiGraph, topo_order: list[str], durations: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Compute total float matrix for each iteration and node."""
    node_to_idx = {node: idx for idx, node in enumerate(topo_order)}
    es = np.zeros_like(durations)
    ef = np.zeros_like(durations)

    for node in topo_order:
        idx = node_to_idx[node]
        preds = list(graph.predecessors(node))
        if preds:
            candidates = [
                ef[:, node_to_idx[pred]] + float(graph.edges[pred, node].get("lag", 0.0))
                for pred in preds
            ]
            es[:, idx] = np.maximum.reduce(candidates)
        ef[:, idx] = es[:, idx] + durations[:, idx]

    project_duration = np.max(ef, axis=1)
    ls = np.zeros_like(durations)
    lf = np.zeros_like(durations)

    for node in reversed(topo_order):
        idx = node_to_idx[node]
        succs = list(graph.successors(node))
        if succs:
            candidates = [
                ls[:, node_to_idx[succ]] - float(graph.edges[node, succ].get("lag", 0.0))
                for succ in succs
            ]
            lf[:, idx] = np.minimum.reduce(candidates)
        else:
            lf[:, idx] = project_duration
        ls[:, idx] = lf[:, idx] - durations[:, idx]

    total_float = ls - es
    return total_float, project_duration
