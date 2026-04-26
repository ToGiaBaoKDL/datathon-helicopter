# Datathon Round 1 — Revenue & COGS Forecasting

End-to-end analytics and forecasting pipeline.
**Stack:** uv · dbt + DuckDB · LightGBM · XGBoost · CatBoost · Evidence · MLflow

---

## Prerequisites

- **Python** 3.10–3.12
- **uv** — [install guide](https://docs.astral.sh/uv/getting-started/installation/)
- **Node.js** 18+ — [install guide](https://nodejs.org/)
- **Make** — usually pre-installed on Linux/macOS; Windows users can use [WSL](https://learn.microsoft.com/windows/wsl/) or [install via Chocolatey](https://community.chocolatey.org/packages/make)

---

## Quick Start

```bash
# 1. Install dependencies
make install

# 2. Download raw data
make download-data

# 3. Build DuckDB warehouse
make build-raw

# 4. Run dbt pipeline (models + tests)
make dbt-build

# 5. Start Evidence dashboard
make evidence-install
make evidence-sources
make evidence-dev
```

---

## Project Structure

```
.
├── configs/
│   ├── modeling.yaml          # Base modeling config (hyperparameters, target transform)
│   ├── competition.yaml       # Kaggle submission metadata
│   ├── tracking.yaml          # MLflow on/off switch
│   └── tuned/                 # Optuna delta configs
├── dbt/
│   ├── models/
│   │   ├── staging/           # Cleaned sources
│   │   ├── intermediate/      # Enriched order lines, inventory signals
│   │   └── marts/             # Business-domain aggregates (finance, ops, marketing, customer, product, executive)
│   └── seeds/                 # Tet dates, holidays
├── src/datathon/
│   ├── commands/              # CLI commands (train, tune, predict, compare, ensemble, explain)
│   ├── modeling/              # Forecasters, CV, trainer, tuner, explainer
│   └── utils/                 # Config loaders, DuckDB I/O
├── notebooks/                 # SHAP analysis
├── reports/
│   ├── evidence/              # Evidence.dev analytics site
│   └── shap/                  # Auto-generated SHAP plots
├── tests/
├── Makefile
└── README.md
```

---

## Pipeline Overview

| Step | Command | Output |
|---|---|---|
| Download | `make download-data` | Raw CSVs in `data/raw/` |
| Build raw | `make build-raw` | DuckDB warehouse (`datathon.duckdb`) |
| dbt transform | `make dbt-build` | Staging → intermediate → marts |
| Evidence | `make evidence-dev` | Analytics dashboard |

---

## dbt Data Pipeline

All feature engineering lives in dbt models (DuckDB backend). Three layers:

| Layer | Prefix | Purpose |
|---|---|---|
| **Staging** | `stg_` | Cleaned, typed sources |
| **Intermediate** | `int_` | Enriched order lines, inventory signals |
| **Marts** | `mart_` | Business-domain aggregates: finance, operations, marketing, customer, product, executive |

Key marts for forecasting:
- `mart_forecast_daily_base` — daily revenue + COGS
- `mart_forecast_daily_features` — engineered features (lags, rolling, calendar, residuals)
- `mart_submission_scaffold` — forecast date grid

---

## ML Pipeline (Optional)

The modeling layer is fully modular. Use it only if you want to train custom forecasters.

**Workflow:**
1. `datathon tune --model-type lightgbm` — Optuna HPO with early stopping
2. `datathon compare-models` — CV all models, pick winner, train final, generate submission
3. `datathon predict --model-type lightgbm` — Generate submission from saved model

**MLflow:** Optional tracking. Enable via `configs/tracking.yaml` or `MLFLOW_TRACKING_URI`. Pipeline runs unchanged when disabled.

---

## Makefile Shortcuts

```bash
make install        # uv sync --extra dev
make download-data  # datathon download-data
make build-raw      # datathon build-raw --strict
make dbt-build      # dbt build
make dbt-test       # dbt test
make test           # pytest -q
make lint           # ruff check .

# Evidence
make evidence-install    # npm install
make evidence-sources    # refresh DuckDB sources
make evidence-dev        # local dev server
make evidence-build      # production build
make evidence-deploy     # deploy to Netlify
```

---

## Validation

| Check | Command |
|---|---|
| dbt build | `make dbt-build` |
| dbt tests | `make dbt-test` |
| pytest | `make test` |
| ruff | `make lint` |

---

## Evidence Dashboard

Pages: executive KPIs, risk flags, revenue drivers, fulfillment, inventory, marketing, customer cohorts, product health, category performance.

See [`CONVENTIONS.md`](CONVENTIONS.md) and [`AGENTS.md`](AGENTS.md) for detailed architecture and session history.