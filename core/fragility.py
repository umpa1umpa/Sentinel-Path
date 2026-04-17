"""Fragility and path convergence analysis."""

from __future__ import annotations

from models.schemas import FragilityPoint


def find_fragility_points(
    timing_by_node: dict[str, float],
    project_duration: float,
    convergence_threshold_pct: float,
    predecessors_by_node: dict[str, list[str]],
) -> list[FragilityPoint]:
    """Compute fragility points and PCI scores for convergence nodes."""
    # Threshold is derived from project duration to make "near critical" scale with
    # project size instead of using a fixed day-based constant.
    threshold = project_duration * convergence_threshold_pct
    points: list[FragilityPoint] = []

    for node, predecessors in predecessors_by_node.items():
        if len(predecessors) < 2:
            # Convergence risk exists only where multiple incoming paths compete.
            continue
        near_critical_paths = 0
        for predecessor in predecessors:
            if timing_by_node[predecessor] <= threshold:
                near_critical_paths += 1

        if near_critical_paths < 2:
            # A single near-critical predecessor is not enough to classify a node as
            # structurally fragile; we require at least two competing risky branches.
            continue

        # Normalizing by total predecessors keeps PCI comparable across nodes with
        # different fan-in degrees.
        pci_score = near_critical_paths / len(predecessors)
        points.append(
            FragilityPoint(
                node_id=node,
                incoming_critical_paths=near_critical_paths,
                pci_score=round(pci_score, 4),
            )
        )

    return sorted(points, key=lambda p: (-p.pci_score, p.node_id))
