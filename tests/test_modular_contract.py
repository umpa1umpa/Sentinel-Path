"""Contract tests for modular and facade behavior."""

from core.fragility import find_fragility_points
from core.topology import build_project_graph, critical_path_nodes, run_cpm
from models.schemas import Dependency, ProjectConfig, Task
from sentinel_path import SentinelEngine
from stochastic.simulation import run_monte_carlo


def test_facade_matches_modular_pipeline() -> None:
    """Facade output should match direct module pipeline output."""
    tasks_raw = [
        {"id": "A", "duration": 4.0, "optimistic_duration": 3.0, "pessimistic_duration": 6.0},
        {"id": "B", "duration": 5.0, "optimistic_duration": 4.0, "pessimistic_duration": 7.0},
        {"id": "C", "duration": 3.0, "optimistic_duration": 2.0, "pessimistic_duration": 4.0},
    ]
    dependencies_raw = [
        {"from_id": "A", "to_id": "C", "type": "FS", "lag": 0.0},
        {"from_id": "B", "to_id": "C", "type": "FS", "lag": 0.0},
    ]
    config_raw = {"mc_iterations": 200, "convergence_threshold_pct": 0.1, "rng_seed": 7}

    engine = SentinelEngine()
    report = engine.analyze(tasks_raw, dependencies_raw, config_raw)

    tasks = [Task.model_validate(item) for item in tasks_raw]
    dependencies = [Dependency.model_validate(item) for item in dependencies_raw]
    config = ProjectConfig.model_validate(config_raw)

    graph = build_project_graph(tasks, dependencies)
    timing, project_duration = run_cpm(graph)
    fragility = find_fragility_points(
        timing_by_node={node: metrics.tf for node, metrics in timing.items()},
        project_duration=project_duration,
        convergence_threshold_pct=config.convergence_threshold_pct,
        predecessors_by_node={node: list(graph.predecessors(node)) for node in graph.nodes},
    )
    simulation = run_monte_carlo(
        graph=graph,
        tasks=tasks,
        mc_iterations=config.mc_iterations,
        baseline_duration=project_duration,
        rng_seed=config.rng_seed,
    )

    assert report.project_duration_base == round(project_duration, 2)
    assert report.critical_path_base == critical_path_nodes(timing)
    assert report.fragility_points == fragility
    assert report.cruciality_metrics == simulation.cruciality_metrics
    assert report.project_confidence == simulation.project_confidence
    assert report.sensitivity_spearman == simulation.sensitivity_spearman
    assert report.tornado_impact == simulation.tornado_impact
