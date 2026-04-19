"""Monte Carlo simulation with Beta-PERT distributions."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np
from scipy.stats import spearmanr

from core.errors import GraphTopologyError
from models.schemas import Task


@dataclass(frozen=True)
class SimulationResult:
    """Result of stochastic schedule simulation."""

    cruciality_metrics: dict[str, float]
    project_confidence: float
    sensitivity_spearman: dict[str, float]
    tornado_impact: dict[str, float]
    project_durations: np.ndarray
    sampled_durations: np.ndarray
    topo_order: list[str]


def run_monte_carlo(
    graph: nx.DiGraph,
    tasks: list[Task],
    mc_iterations: int,
    baseline_duration: float,
    rng_seed: int | None = 42,
) -> SimulationResult:
    """
    Performs Monte Carlo simulation to assess project schedule risks.
    
    Why: Deterministic CPM doesn't account for uncertainty in task durations.
    Monte Carlo provides a range of possible outcomes and their probabilities.
    
    Business result: Calculates project confidence level (probability of finishing on time)
    and identifies 'crucial' tasks that frequently appear on the critical path.
    """
    if mc_iterations < 1:
        raise GraphTopologyError("mc_iterations must be >= 1.")

    task_by_id = {task.id: task for task in tasks}
    topo_order = list(nx.topological_sort(graph))
    if not topo_order:
        raise GraphTopologyError("Cannot simulate an empty graph.")

    # 1. Sample durations using Beta-PERT distribution for all iterations at once.
    durations = _sample_pert_durations(task_by_id, topo_order, mc_iterations, rng_seed)
    
    # 2. Vectorized CPM pass for all simulation iterations.
    total_float, project_durations = _compute_total_float_matrix(graph, topo_order, durations)

    # 3. Calculate metrics based on simulation results.
    # TODO: Optimize memory usage for very large mc_iterations (e.g., > 100,000) by using chunking.
    critical_hits = np.isclose(total_float, 0.0, atol=1e-8).sum(axis=0)
    cruciality = {
        node: round(float(critical_hits[idx] * 100.0 / mc_iterations), 2)
        for idx, node in enumerate(topo_order)
    }
    project_confidence = round(
        float((project_durations <= baseline_duration).sum() * 100.0 / mc_iterations), 2
    )
    
    # 4. Compute advanced sensitivity metrics like Spearman correlation and Tornado impact.
    # TODO: Parallelize sensitivity metric calculation for large graphs using multiprocessing.
    sensitivity_spearman, tornado_impact = _compute_sensitivity_metrics(
        durations=durations,
        project_durations=project_durations,
        topo_order=topo_order,
    )
    return SimulationResult(
        cruciality_metrics=cruciality,
        project_confidence=project_confidence,
        sensitivity_spearman=sensitivity_spearman,
        tornado_impact=tornado_impact,
        project_durations=project_durations,
        sampled_durations=durations,
        topo_order=topo_order,
    )


def _sample_pert_durations(
    task_by_id: dict[str, Task],
    topo_order: list[str],
    mc_iterations: int,
    rng_seed: int | None,
) -> np.ndarray:
    """
    Samples task durations using the Beta-PERT distribution.
    
    Why: Beta-PERT is preferred in project management as it emphasizes the 'most likely'
    duration while still accounting for optimistic and pessimistic scenarios.
    
    Business result: Generates a realistic distribution of possible task durations.
    """
    rng = np.random.default_rng(rng_seed)
    # We pre-allocate the matrix for efficiency.
    samples = np.zeros((mc_iterations, len(topo_order)), dtype=np.float64)

    for idx, task_id in enumerate(topo_order):
        task = task_by_id[task_id]
        low = task.optimistic_duration
        mode = task.duration
        high = task.pessimistic_duration

        # If there's no uncertainty, we use the constant duration.
        if np.isclose(low, high):
            samples[:, idx] = low
            continue

        # Convert PERT parameters (low, mode, high) to Beta distribution parameters (alpha, beta).
        alpha = 1.0 + 4.0 * (mode - low) / (high - low)
        beta = 1.0 + 4.0 * (high - mode) / (high - low)
        beta_samples = rng.beta(alpha, beta, size=mc_iterations)
        samples[:, idx] = low + beta_samples * (high - low)

    return samples


def _compute_total_float_matrix(
    graph: nx.DiGraph, topo_order: list[str], durations: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """
    Vectorized calculation of total float for all simulation iterations.
    
    Why: Using NumPy vectorization instead of a loop over mc_iterations 
    improves performance by orders of magnitude.
    
    Business result: Enables high-speed simulation of complex project graphs.
    """
    node_to_idx = {node: idx for idx, node in enumerate(topo_order)}
    es = np.zeros_like(durations)
    ef = np.zeros_like(durations)

    # Forward pass: calculate ES and EF for all iterations.
    # TODO: Consider using a sparse matrix approach or specialized graph library if nodes > 10,000.
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


def _compute_sensitivity_metrics(
    durations: np.ndarray,
    project_durations: np.ndarray,
    topo_order: list[str],
) -> tuple[dict[str, float], dict[str, float]]:
    """Compute Spearman rank correlation and linear impact slope per task."""
    sensitivity_spearman: dict[str, float] = {}
    tornado_impact: dict[str, float] = {}

    for idx, task_id in enumerate(topo_order):
        task_samples = durations[:, idx]
        rho, _ = spearmanr(task_samples, project_durations)
        if np.isnan(rho):
            rho = 0.0

        centered_x = task_samples - float(np.mean(task_samples))
        centered_y = project_durations - float(np.mean(project_durations))
        denominator = float(np.sum(centered_x**2))
        slope = (
            0.0
            if np.isclose(denominator, 0.0)
            else float(np.sum(centered_x * centered_y) / denominator)
        )

        sensitivity_spearman[task_id] = round(float(rho), 4)
        tornado_impact[task_id] = round(slope, 4)

    return sensitivity_spearman, tornado_impact
