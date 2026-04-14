# Changelog

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
