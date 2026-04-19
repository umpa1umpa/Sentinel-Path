"""Topology analysis utilities for Sentinel Path."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import networkx as nx

from core.errors import CycleError, GraphTopologyError
from models.schemas import Dependency, Task


@dataclass(frozen=True)
class NodeTiming:
    """Timing metrics for a project task."""

    es: float
    ef: float
    ls: float
    lf: float
    tf: float


def build_project_graph(tasks: list[Task], dependencies: list[Dependency]) -> nx.DiGraph:
    """
    Builds and validates a directed acyclic graph (DAG) from tasks and dependencies.
    
    Why: A project schedule is naturally a DAG. If there are cycles, the CPM
    algorithm will fail as it cannot determine which task comes first.
    
    Business result: Ensures the logical consistency of the project plan before
    starting any calculations.
    """
    if not tasks:
        raise GraphTopologyError("At least one task is required.")

    graph = nx.DiGraph()
    task_ids = set()
    for task in tasks:
        # Each task must have a unique ID to be correctly mapped in the graph.
        if task.id in task_ids:
            raise GraphTopologyError(f"Duplicate task id '{task.id}'.")
        task_ids.add(task.id)
        graph.add_node(task.id, task=task)

    for dep in dependencies:
        # We ensure that dependencies only point to existing tasks.
        if dep.from_id not in task_ids or dep.to_id not in task_ids:
            raise GraphTopologyError(
                f"Dependency references unknown tasks: {dep.from_id} -> {dep.to_id}."
            )
        graph.add_edge(dep.from_id, dep.to_id, lag=dep.lag, type=dep.type)

    # A project plan must not have circular dependencies.
    if not nx.is_directed_acyclic_graph(graph):
        raise CycleError("Project dependencies contain a cycle.")

    # We check for disconnected components to ensure the project has a single root/sink structure.
    isolates = list(nx.isolates(graph))
    if isolates and len(graph.nodes) > 1:
        raise GraphTopologyError(f"Isolated tasks detected: {isolates}.")

    return graph


def run_cpm(
    graph: nx.DiGraph,
    durations: Mapping[str, float] | None = None,
) -> tuple[dict[str, NodeTiming], float]:
    """
    Runs forward and backward CPM passes to calculate early/late start and finish times.
    
    Why: Critical Path Method is the standard for determining project duration
    and identifying tasks that cannot be delayed without delaying the entire project.
    
    Business result: Calculates the baseline project schedule and total float for each task.
    """
    topo_order = list(nx.topological_sort(graph))
    if not topo_order:
        raise GraphTopologyError("Cannot run CPM on an empty graph.")

    effective_durations = _resolve_durations(graph, durations)
    es: dict[str, float] = {}
    ef: dict[str, float] = {}

    # Forward pass: calculate Early Start (ES) and Early Finish (EF)
    for node in topo_order:
        preds = list(graph.predecessors(node))
        if preds:
            # ES is the latest EF of all predecessors plus their lag.
            es[node] = max(
                ef[pred] + float(graph.edges[pred, node].get("lag", 0.0))
                for pred in preds
            )
        else:
            # For root nodes, ES is zero.
            es[node] = 0.0
        ef[node] = es[node] + effective_durations[node]

    # The project duration is determined by the task that finishes last.
    project_duration = max(ef.values())
    ls: dict[str, float] = {}
    lf: dict[str, float] = {}

    # Backward pass: calculate Late Finish (LF) and Late Start (LS)
    for node in reversed(topo_order):
        succs = list(graph.successors(node))
        if succs:
            # LF is the earliest LS of all successors minus the lag.
            lf[node] = min(
                ls[succ] - float(graph.edges[node, succ].get("lag", 0.0))
                for succ in succs
            )
        else:
            # For sink nodes, LF is equal to the project duration.
            lf[node] = project_duration
        ls[node] = lf[node] - effective_durations[node]

    # Combine results into NodeTiming objects for easy access.
    timing = {
        node: NodeTiming(
            es=es[node],
            ef=ef[node],
            ls=ls[node],
            lf=lf[node],
            tf=ls[node] - es[node],
        )
        for node in topo_order
    }
    return timing, project_duration


def critical_path_nodes(timing: Mapping[str, NodeTiming], eps: float = 1e-9) -> list[str]:
    """Return deterministic critical path nodes ordered by ES."""
    critical = [node for node, metrics in timing.items() if abs(metrics.tf) <= eps]
    return sorted(critical, key=lambda node: (timing[node].es, node))


def _resolve_durations(
    graph: nx.DiGraph, durations: Mapping[str, float] | None
) -> dict[str, float]:
    """Resolve effective task durations for CPM run."""
    resolved: dict[str, float] = {}
    for node, payload in graph.nodes(data=True):
        if durations is not None:
            if node not in durations:
                raise GraphTopologyError(f"Missing duration override for task '{node}'.")
            duration = float(durations[node])
        else:
            duration = float(payload["task"].duration)
        if duration <= 0:
            raise GraphTopologyError(f"Duration for task '{node}' must be > 0.")
        resolved[node] = duration
    return resolved
