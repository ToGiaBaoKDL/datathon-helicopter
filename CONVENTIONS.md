# Naming and Modeling Conventions

This project uses strict naming to keep SQL, EDA, and ML aligned.

## General

- Use lowercase snake_case for files, columns, models, and scripts.
- Use explicit semantic prefixes for dbt models and marts.
- Keep one model per file.
- Keep each model at a single grain and document that grain.

## dbt Model Prefixes

- `stg_`: source-aligned cleaned tables, minimal business logic
- `int_`: intermediate logic and joins, business-ready but not final
- `mart_`: analysis and ML consumption tables

Examples:

- `stg_orders`
- `int_order_line_enriched`
- `mart_forecast_daily_base`

## Feature Naming

- Prefix lagged features with `lag_` and include unit and window.
- Prefix rolling aggregates with `roll_` and include statistic and window.
- Include business domain in feature name.

Examples:

- `lag_7d_revenue`
- `roll_mean_28d_sessions`
- `lag_1m_stock_on_hand_total`

## Date and Time

- Use `_date` suffix for date columns.
- Use `_ts` suffix for timestamps.
- Use `snapshot_date` for periodic snapshots.
- Use `as_of_date` for point-in-time feature materialization.

## Paths and Artifacts

- Raw downloaded files: `data/raw/`
- Model-ready data and outputs: `data/processed/`
- Kaggle submissions: `data/submissions/`
- DuckDB warehouse file: `warehouse/datathon.duckdb`
- Static artifacts and exam docs: `assets/`
- Exploratory notebooks: `notebooks/`

## Warehouse Schema Layers

Use warehouse schemas aligned with transformation stages:

- `raw`: ingestion/landing tables from source CSV files
- `staging`: cleaned source-aligned dbt models
- `intermediate`: reusable join/business logic models
- `marts`: analytics and modeling-ready outputs

This maps naturally to landing/curated/analytics concepts while preserving dbt-native naming.

Avoid creating extra physical dataset layers (e.g. `data/interim/`) unless a workflow explicitly
needs persisted artifacts outside dbt.

## Command Naming

Use verb-first command names:

- `download-data`
- `build-raw`
- `baseline`
- `export-model-data`

Execution pattern:

- Use `uv run datathon <command>` as the single entrypoint.
- Keep implementation in `src/datathon/commands/*` and orchestration in `src/datathon/cli.py`.

Submission artifact:

- Final upload file name should be `data/submissions/submission.csv`.
- Use `datathon submit-kaggle --message "..."` for CLI-based submission.

## Evidence Query Naming

- Use domain + metric + grain pattern.
- Keep markdown query names short and scoped to each page.

Examples:

- `daily_revenue_kpi`
- `returns_by_reason_monthly`
