# Datathon Round 1 — Revenue & COGS Forecasting

End-to-end forecasting pipeline for daily revenue and COGS (548-day horizon).  
**Stack:** uv · dbt + DuckDB · LightGBM · XGBoost · CatBoost · Evidence · MLflow

---

## Prerequisites

- **Python** 3.10–3.12
- **uv** — [install guide](https://docs.astral.sh/uv/getting-started/installation/)
- **Node.js** 18+ (for Evidence dashboard only)
- **Kaggle API credentials** — place in `~/.kaggle/kaggle.json`

---

## Quick Start

```bash
# 1. Install dependencies
uv sync --extra dev

# 2. Download raw data from Kaggle (skip if you already have CSVs)
uv run datathon download-data

# 3. Build DuckDB warehouse from raw CSVs
uv run datathon build-raw --strict

# 4. Run dbt pipeline (models + tests)
uv run dbt build --project-dir dbt --profiles-dir dbt

# 5. Tune all models → merge configs → compare & submit
uv run datathon tune --model-type lightgbm --n-trials 50
uv run datathon tune --model-type xgboost   --n-trials 50
uv run datathon tune --model-type catboost  --n-trials 50

# Merge delta configs into one file
uv run python -c "
import yaml, glob, pathlib
base = yaml.safe_load(open('configs/modeling.yaml'))
for p in sorted(glob.glob('configs/tuned/*.yaml')):
    d = yaml.safe_load(open(p))
    for k, v in (d.get('models') or {}).items():
        base.setdefault('models', {})[k] = v
pathlib.Path('configs/tuned/all_models.yaml').write_text(
    yaml.dump(base, sort_keys=False, allow_unicode=True))
"

# Run CV comparison, train winner, generate submission
uv run datathon compare-models --config configs/tuned/all_models.yaml

# Validate submission before uploading
uv run datathon submit-kaggle --dry-run --file data/submissions/best_submission.csv
```

---

## Project Structure

```
├── configs/
│   ├── modeling.yaml           # Base config (all hyperparameters)
│   ├── competition.yaml        # Kaggle slug & submission columns
│   ├── tracking.yaml           # MLflow on/off switch
│   └── tuned/                  # Delta configs from Optuna
├── dbt/
│   ├── models/
│   │   ├── staging/            # 14 cleaned sources
│   │   ├── intermediate/       # Enriched order lines
│   │   └── marts/              # 18+ business-domain marts
│   └── seeds/                  # Tet dates, holidays
├── audit/                      # Data-quality & feature-audit package
├── notebooks/                  # SHAP analysis
├── reports/
│   ├── evidence/               # Evidence.dev analytics site
│   └── shap/                   # Auto-generated SHAP plots
├── src/datathon/
│   ├── commands/               # CLI commands (train, tune, predict, ...)
│   ├── modeling/               # Forecasters, CV, trainer, tuner, explainer
│   └── utils/                  # Config loaders, DuckDB I/O
└── tests/                      # 78 pytest tests
```

---

## dbt Data Pipeline

All feature engineering lives in dbt models (DuckDB backend). The pipeline has 3 layers:

| Layer | Prefix | Purpose |
|---|---|---|
| **Staging** | `stg_` | Cleaned, typed sources (14 tables) |
| **Intermediate** | `int_` | Enriched order lines, inventory signals |
| **Marts** | `mart_` | Business-domain aggregates: finance, operations, marketing, customer, product, executive |

Key marts for forecasting:
- `mart_forecast_daily_base` — daily revenue + COGS
- `mart_forecast_daily_features` — 76 engineered features (lags, rolling, calendar, residuals)
- `mart_submission_scaffold` — 548-day forecast date grid

Build everything + run data tests:

```bash
uv run dbt build --project-dir dbt --profiles-dir dbt
```

---

## Key CLI Commands

| Command | Purpose |
|---|---|
| `datathon build-raw --strict` | Load CSVs into DuckDB raw schema |
| `datathon tune --model-type lightgbm --n-trials 50` | Optuna HPO with early stopping |
| `datathon train --mode evaluate --model-type lightgbm` | Expanding-window CV |
| `datathon train --mode train-final --model-type lightgbm` | Train on full history |
| `datathon predict --model-type lightgbm` | Generate submission CSV |
| `datathon compare-models --config <path>` | CV all models + ensemble, pick winner, submit |
| `datathon ensemble --model-types lgb,xgb,cb` | Weighted ensemble from saved models |
| `datathon explain --model-type lightgbm` | SHAP beeswarm + bar plots |
| `datathon submit-kaggle --dry-run --file <path>` | Validate submission schema |

All commands accept `--config <path>` to overlay tuned hyperparameters on top of `configs/modeling.yaml`.

---

## Modeling Approach

**Target:** Predict daily `revenue` and `cogs` for 2023-01-01 → 2024-07-01 (548 days).

**Feature engineering** (dbt → `mart_forecast_daily_features`):
- Calendar features: day-of-year/week/month, Tet proximity, holidays, structural-break era
- Lag features: `lag_1d/2d/3d/7d/14d/28d/365d` for revenue, COGS, and residuals
- Rolling stats: mean/median/std on 7d/28d/365d windows
- Growth ratios: WoW, MoM, YoY + acceleration (momentum of momentum)
- Residual baseline: `lag_365d_revenue` (naive YoY forecast)

**Modeling modes** (switch in `configs/modeling.yaml`):
- `residual_target: true` — models predict deviation from YoY baseline; recursive forecast reconstructs `baseline + residual`. Default.
- `cogs_target: absolute` — predict absolute COGS directly (alternatively `ratio`).

**Architecture:**
- Pluggable forecasters via `BaseForecaster` ABC — registered in `src/datathon/modeling/forecasters/__init__.py`
- Recursive multi-step forecast: target-derived lags recomputed each step; calendar from date; exogenous forward-filled
- Expanding-window CV: 2 folds × 548-day horizon (matches real forecast length)
- Ensemble: inverse-MAE weighted average across all models; compared on same CV folds

**Registered models:** LightGBM, XGBoost, CatBoost.

---

## Validation & Quality

| Check | Status |
|---|---|
| dbt build | **172 / 172 PASS** (models + tests) |
| pytest | **78 passed** |
| ruff | **All passed** |
| Mart ↔ Recursive sync | `python -m audit` confirms 76 columns classified correctly |
| Data leakage | Lags look backward only; rolling on `[:idx]`; no future info |

---

## Evidence Dashboard

```bash
make evidence-install    # npm install
make evidence-sources    # refresh DuckDB sources
make evidence-dev        # local dev server
```

Pages: executive KPIs, risk flags, revenue drivers, fulfillment, inventory, marketing, customer cohorts, product health, category performance.

---

## Optional: MLflow Tracking

Edit `configs/tracking.yaml` or set env var:

```bash
export MLFLOW_TRACKING_URI=file:./mlruns
uv run datathon tune --model-type lightgbm
uv run mlflow ui --backend-store-uri file:./mlruns
```

Disabled by default — pipeline runs unchanged without a server.

---

## Makefile Shortcuts

```bash
make install        # uv sync --extra dev
make build-raw      # datathon build-raw --strict
make dbt-build      # dbt build
make test           # pytest -q
make lint           # ruff check .
make compare-models # datathon compare-models
```

---

## Conventions

See [`CONVENTIONS.md`](CONVENTIONS.md) for naming rules (dbt prefixes, feature names, notebook naming).

See [`AGENTS.md`](AGENTS.md) for detailed session history, bug fixes, and architecture decisions.
