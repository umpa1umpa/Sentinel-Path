"""Fragility and path convergence analysis."""

from __future__ import annotations

from models.schemas import FragilityPoint


def find_fragility_points(
    timing_by_node: dict[str, float],
    project_duration: float,
    convergence_threshold_pct: float,
    predecessors_by_node: dict[str, list[str]],
) -> list[FragilityPoint]:
    """
    Identifies 'fragility points' where multiple near-critical paths converge.
    
    Why: Points where several paths meet are high-risk nodes. A delay in any
    one of those paths can delay the entire project. This is known as path convergence.
    
    Business result: Highlights the most vulnerable tasks in the project graph
    that need extra management attention.
    """
    # Threshold for what we consider 'near-critical' based on a percentage of project duration.
    threshold = project_duration * convergence_threshold_pct
    points: list[FragilityPoint] = []

    for node, predecessors in predecessors_by_node.items():
        # A fragility point must have at least two incoming paths.
        if len(predecessors) < 2:
            continue
            
        near_critical_paths = 0
        for predecessor in predecessors:
            # We count how many of the incoming paths are near the critical path.
            if timing_by_node[predecessor] <= threshold:
                near_critical_paths += 1

        # If multiple paths are near-critical, we flag this node.
        if near_critical_paths < 2:
            continue

        # PCI (Path Convergence Index) score represents the proportion of 
        # near-critical incoming paths.
        pci_score = near_critical_paths / len(predecessors)
        points.append(
            FragilityPoint(
                node_id=node,
                incoming_critical_paths=near_critical_paths,
                pci_score=round(pci_score, 4),
            )
        )

    # We sort the points by their PCI score to show the most fragile nodes first.
    return sorted(points, key=lambda p: (-p.pci_score, p.node_id))
