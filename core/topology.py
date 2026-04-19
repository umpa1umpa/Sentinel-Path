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
    """Строит и валидирует DAG из задач и связей."""
    if not tasks:
        raise GraphTopologyError("At least one task is required.")

    graph = nx.DiGraph()
    task_ids = set()
    for task in tasks:
        # Дубликаты ID здесь особенно опасны: граф "молча" перезапишет вершину,
        # и дальше метрики будут выглядеть корректно, но по факту неверны.
        if task.id in task_ids:
            raise GraphTopologyError(f"Duplicate task id '{task.id}'.")
        task_ids.add(task.id)
        graph.add_node(task.id, task=task)

    for dep in dependencies:
        # Проверяем ссылки заранее, чтобы не получать размытые ошибки на этапе CPM.
        if dep.from_id not in task_ids or dep.to_id not in task_ids:
            raise GraphTopologyError(
                f"Dependency references unknown tasks: {dep.from_id} -> {dep.to_id}."
            )
        graph.add_edge(dep.from_id, dep.to_id, lag=dep.lag, type=dep.type)

    # Цикл ломает смысл расписания: у такой сети нет корректного топологического порядка.
    if not nx.is_directed_acyclic_graph(graph):
        raise CycleError("Project dependencies contain a cycle.")

    # Для MVP считаем изолированные задачи ошибкой:
    # иначе отчет по рискам вводит в заблуждение (часть плана не участвует в анализе).
    isolates = list(nx.isolates(graph))
    if isolates and len(graph.nodes) > 1:
        raise GraphTopologyError(f"Isolated tasks detected: {isolates}.")

    return graph


def run_cpm(
    graph: nx.DiGraph,
    durations: Mapping[str, float] | None = None,
) -> tuple[dict[str, NodeTiming], float]:
    """Выполняет прямой и обратный проход CPM."""
    topo_order = list(nx.topological_sort(graph))
    if not topo_order:
        raise GraphTopologyError("Cannot run CPM on an empty graph.")

    effective_durations = _resolve_durations(graph, durations)
    es: dict[str, float] = {}
    ef: dict[str, float] = {}

    # Прямой проход отвечает на вопрос "как рано можем стартовать".
    for node in topo_order:
        preds = list(graph.predecessors(node))
        if preds:
            # Берем максимум по предшественникам: узел можно стартовать только когда
            # завершился самый поздний входящий путь (с учетом лагов).
            es[node] = max(
                ef[pred] + float(graph.edges[pred, node].get("lag", 0.0))
                for pred in preds
            )
        else:
            # Корневые задачи стартуют с нуля по определению сетевого графика.
            es[node] = 0.0
        ef[node] = es[node] + effective_durations[node]

    # Общая длительность — это самый поздний EF среди всех вершин.
    project_duration = max(ef.values())
    ls: dict[str, float] = {}
    lf: dict[str, float] = {}

    # Обратный проход отвечает на "насколько можем сдвинуть без срыва дедлайна".
    for node in reversed(topo_order):
        succs = list(graph.successors(node))
        if succs:
            # Идем от наследников: не хотим сдвинуть задачу позже самого раннего LS
            # среди исходящих путей.
            lf[node] = min(
                ls[succ] - float(graph.edges[node, succ].get("lag", 0.0))
                for succ in succs
            )
        else:
            # Финишные вершины ограничены только общим дедлайном проекта.
            lf[node] = project_duration
        ls[node] = lf[node] - effective_durations[node]

    # Собираем в отдельную структуру, чтобы явно разделить расчет и представление.
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
