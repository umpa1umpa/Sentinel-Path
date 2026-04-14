# Sentinel Path

`Sentinel Path` - библиотека анализа структурной хрупкости сетевых графиков проекта.
Она объединяет CPM, анализ сходимости путей и Монте-Карло на Beta-PERT.

## Возможности

- Расчет `ES/EF/LS/LF/TF` с поддержкой `FS`-зависимостей и `lag`.
- Поиск точек хрупкости через `PCI` (узлы, где сходятся околокритические пути).
- Монте-Карло с `Cruciality Index` по задачам.
- Анализ чувствительности:
  - `sensitivity_spearman` - коэффициент Спирмена между длительностью задачи и сроком проекта.
  - `tornado_impact` - оценка влияния `+1 дня` в задаче на итоговую длительность.
- Воспроизводимость моделирования через `config.rng_seed`.
- Экспорт графиков через `SentinelEngine.export_charts()`:
  - `finish_date_histogram.png`
  - `s_curve.png`
  - `tornado.png`

## Установка

Рекомендуемый способ (uv):

```bash
uv sync
```

Запуск тестов через uv:

```bash
uv run pytest -v
```

Альтернатива через pip:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

Для разработки:

```bash
pip install -e ".[dev]"
```

## Быстрый старт

```python
from sentinel_path import SentinelEngine

tasks = [
    {"id": "A", "duration": 6, "optimistic_duration": 4, "pessimistic_duration": 9},
    {"id": "B", "duration": 7, "optimistic_duration": 5, "pessimistic_duration": 11},
    {"id": "C", "duration": 5, "optimistic_duration": 3, "pessimistic_duration": 8},
    {"id": "D", "duration": 4, "optimistic_duration": 3, "pessimistic_duration": 7},
    {"id": "E", "duration": 3, "optimistic_duration": 2, "pessimistic_duration": 5},
]

dependencies = [
    {"from_id": "A", "to_id": "D", "type": "FS", "lag": 0.0},
    {"from_id": "B", "to_id": "D", "type": "FS", "lag": 0.0},
    {"from_id": "C", "to_id": "D", "type": "FS", "lag": 0.0},
    {"from_id": "D", "to_id": "E", "type": "FS", "lag": 0.0},
]

engine = SentinelEngine()
report = engine.analyze(
    tasks_raw=tasks,
    dependencies_raw=dependencies,
    config_raw={"mc_iterations": 3000, "convergence_threshold_pct": 0.1, "rng_seed": 42},
)

print(report.project_duration_base)
print(report.project_confidence)
print(report.cruciality_metrics)
print(report.sensitivity_spearman)
print(report.tornado_impact)

charts = engine.export_charts("artifacts/charts")
print(charts)
```

## Модульность и запуск

- Единый фасад: `from sentinel_path import SentinelEngine`
- Отдельные модули:
  - `sentinel_path.schemas`
  - `sentinel_path.topology`
  - `sentinel_path.fragility`
  - `sentinel_path.simulation`
- CLI запуск:

```bash
python -m sentinel_path --tasks tasks.json --dependencies deps.json --config config.json --output report.json --charts-dir artifacts/charts
```

## Контракт API (JSON Schema)

Экспорт JSON Schema для `SentinelReport`:

```bash
sentinel-path-schema --output schemas/sentinel_report.schema.json
```

или программно:

```python
from sentinel_path import write_report_json_schema

write_report_json_schema("schemas/sentinel_report.schema.json")
```

## Сценарий ценности: критический узел из 5 задач

Если в один узел сходятся несколько задач, классический CPM обычно покажет только один критический путь.
`Sentinel Path` показывает полную картину:

1. `PCI` фиксирует узел с высокой уязвимостью.
2. `Cruciality Index` выявляет задачи, которые чаще всего "перехватывают" критичность в стохастике.
3. `sensitivity_spearman` и `tornado_impact` дают ответ менеджеру:
   какая задача действительно двигает дату финиша, и на сколько дней.

Итог: можно приоритизировать буферы и управленческое внимание по реальному риску, а не только по базовому критическому пути.

## Benchmark

Скрипт замера производительности:

```bash
python scripts/benchmark.py
```

Он прогоняет матрицу:
- графы: `10`, `100`, `500` узлов;
- итерации: `100`, `1000`, `10000`.

Результаты сохраняются в:
- `benchmarks/latest.csv`
- `benchmarks/latest.md`

## Тесты

```bash
uv run pytest -v
```