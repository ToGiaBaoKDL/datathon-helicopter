# Evidence App

This Evidence app is the BI-as-code layer for EDA storytelling and metric evidence.

## Start

From repository root:

```bash
npm --prefix reports/evidence install
npm --prefix reports/evidence run sources
npm --prefix reports/evidence run dev
```

## Data Source

The app uses DuckDB source `datathon_warehouse` at:

`warehouse/datathon.duckdb`

This database is built by:

1. `uv run datathon build-raw --strict`
2. `uv run dbt build --project-dir dbt --profiles-dir dbt`
