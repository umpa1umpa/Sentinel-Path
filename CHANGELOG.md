# Changelog

## 0.3.0 - 2026-04-20
### Added
- Техническая документация `DOCS.md` с детальным описанием архитектуры и потоков данных (Data Flow).
- Подробные аннотации (docstrings) для ключевых методов класса `SentinelEngine`.
- Секция Roadmap в документации с планом развития проекта на версию 0.4.0.
- Таблица компонентов системы в `README.md` для упрощения онбординга.
### Changed
- Проведен полный рефакторинг `README.md`: улучшена навигация и добавлены перекрестные ссылки на технические разделы.
- Оптимизированы комментарии в модулях парсинга: теперь они описывают бизнес-логику (Why-logic), а не просто действие кода.
### Fixed
- Улучшена обработка путей с кодировкой UTF-8 для корректной работы в кроссплатформенных средах.
- Описаны и учтены краевые случаи (edge cases) при работе с путями в ОС Windows и Linux.


## 0.2.0 - 2026-04-14

- Add modular package entrypoint `sentinel_path` with facade and submodule exports.
- Add CLI command `sentinel-path` and module execution `python -m sentinel_path`.
- Add sensitivity analytics (`sensitivity_spearman`, `tornado_impact`) and chart export.
- Add reproducibility control with `ProjectConfig.rng_seed`.
- Add benchmark runner and persisted benchmark reports.
- Add JSON Schema contract export helpers and `sentinel-path-schema` CLI command.
- Add CI workflow for tests and CLI smoke validation.

## 0.1.0 - 2026-04-14

- Initial Sentinel Path MVP:
  - DAG validation and CPM (`ES/EF/LS/LF/TF`) with lag support.
  - Fragility point detection with PCI scoring.
  - Monte Carlo simulation with Beta-PERT and Cruciality Index.
  - `SentinelEngine` orchestration and base report schema.
