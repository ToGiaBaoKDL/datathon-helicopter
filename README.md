# Datathon Round 1 — Revenue & COGS Forecasting

End-to-end analytics and forecasting pipeline.
**Stack:** uv · dbt + DuckDB · LightGBM · XGBoost · CatBoost · Evidence · MLflow

**Deep dive dashboard**: [https://datathon-helicopter.vercel.app](https://datathon-helicopter.vercel.app)

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
| Build raw | `make build-raw` | DuckDB warehouse (`datathon.duckdb`) — single-file analytical DB |
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

## ML Pipeline

End-to-end forecasting for Revenue + COGS. Supports LightGBM, XGBoost, and CatBoost with residual targets, ratio-mode COGS, long-horizon restart strategy, and inverse-MAE weighted ensembles.

### Quick Commands

```bash
# 1. Evaluate a single model (2-fold sliding-window CV, 548d horizon)
uv run datathon train --mode evaluate --model-type lightgbm

# 2. Tune hyperparameters with Optuna (50 trials, early stopping + pruning)
uv run datathon tune --model-type lightgbm

# 3. Train final model on full history & save artifacts
uv run datathon train --mode train-final --model-type lightgbm

# 4. Generate Kaggle submission from a saved model
uv run datathon predict --model-type lightgbm \
  --output-path data/submissions/lightgbm_submission.csv

# 5. Compare all models + weighted ensemble, auto-generate submission
uv run datathon compare-models

# 6. Manual ensemble from trained models
uv run datathon ensemble --model-types lightgbm,xgboost,catboost \
  --output-path data/submissions/ensemble_submission.csv

# 7. SHAP explainability
uv run datathon explain --model-type lightgbm
```

### Optimal Config (`configs/modeling.yaml`)

Key settings that give the best CV scores:

| Setting | Value | Why |
|---|---|---|
| `target_transform` | `residual` | Model predicts `revenue - seasonal_baseline`; smaller range, easier to learn |
| `cogs_target` | `ratio` | COGS = `revenue * predicted_ratio`; leverages 0.98 revenue-COGS correlation |
| `train_start_date` | `2019-01-01` | Ignores pre-2019 regime (revenue dropped ~40%) |
| `restart_horizon` | `365` | Refresh recursive history every 365 days to curb error accumulation over the 548-day horizon |
| `sample_weight` | `True` (CLI default) | Exponential decay by recency; recent data matters more |
| `n_estimators` | `5000` ceiling | Early stopping in CV finds the real best iteration; `train_final` auto-clips to the CV best iteration |

### How It Works

1. **Feature mart** — dbt tạo tất cả features leakage-safe trong SQL: calendar cyclicals, seasonal baselines (dow + month), promo profiles, lags, rolling stats, và residual targets (`revenue - baseline`).
2. **Recursive forecast** — sau mỗi bước dự báo, Python cập nhật incrementally các target-derived features (lags, rolling, EMA, trends, residuals) trong O(window).
3. **Restart strategy** — horizon 548 ngày được chia thành chunk 365 ngày. Sau mỗi chunk, predictions được append vào history để chunk tiếp theo dùng real predictions thay vì stale seeds, giảm error accumulation.
4. **CV best-iteration clipping** — `train_final` auto-clips `n_estimators` về `max(best_iteration)` từ CV folds, tránh train full 5,000 trees khi early stopping đã tìm được vòng tối ưu nhỏ hơn nhiều.
5. **Ensemble** — `compare-models` tính inverse-MAE weights per fold. Ensemble CV được so sánh với từng model; winner (individual hoặc ensemble) tạo submission.

### MLflow Tracking (Optional)

Disabled by default. Enable by editing `configs/tracking.yaml` or overriding via env var:

```bash
# SQLite backend (recommended — avoids deprecated filesystem backend)
export MLFLOW_TRACKING_URI="sqlite:///mlflow/datathon.db"
uv run datathon tune --model-type lightgbm
uv run mlflow ui --backend-store-uri sqlite:///mlflow/datathon.db
```

Set `tracking_uri: null` in `configs/tracking.yaml` to disable. Pipeline runs unchanged when tracking is off.

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
