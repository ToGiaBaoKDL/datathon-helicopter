# Datathon Round 1 — Analytics & Forecasting

End-to-end analytics and forecasting pipeline for daily revenue and COGS.

**Stack:** uv · dbt + DuckDB · Evidence · Rich CLI · LightGBM · XGBoost

---

## Quick Start

```bash
# 1. Install
uv sync --extra dev

# 2. Download & build raw data
uv run datathon download-data
uv run datathon build-raw --strict

# 3. Run dbt pipeline
uv run dbt build --project-dir dbt --profiles-dir dbt

# 4. Train, compare, and submit
uv run datathon compare-models --n-folds 3 --horizon-days 30
uv run datathon submit-kaggle --dry-run --file data/submissions/best_submission.csv
```

---

## Project Structure

```
├── configs/                  # YAML configs (competition, modeling, raw tables)
├── dbt/
│   ├── models/
│   │   ├── staging/          # 14 staging views
│   │   ├── intermediate/     # Enriched order lines, inventory signals
│   │   └── marts/            # Business-domain marts (finance, operations,
│   │                         #   marketing, customer, product, executive)
│   └── tests/                # Custom dbt tests
├── reports/evidence/         # Evidence.dev analytics site
├── src/datathon/
│   ├── cli.py                # Entry point
│   ├── commands/             # CLI commands (rich output)
│   ├── modeling/             # Forecasters, CV, trainer, SHAP explainer
│   └── utils/                # Config, data loaders, DuckDB I/O
├── tests/                    # pytest suite
└── Makefile                  # Common tasks
```

---

## CLI Commands

All commands use **Rich** for clean tables and progress output.

| Command | Purpose |
|---|---|
| `datathon build-raw --strict` | Load CSVs into DuckDB raw schema |
| `datathon train --mode evaluate --model-type lightgbm` | Expanding-window CV vs seasonal naive |
| `datathon train --mode train-final --model-type lightgbm` | Train final model & save artifacts |
| `datathon predict --model-type lightgbm` | Generate submission from saved model |
| `datathon compare-models` | CV all registered models, pick winner, train final, submit |
| `datathon baseline --mode evaluate` | Seasonal-naive baseline benchmark |
| `datathon baseline --mode submit` | Generate naive submission |
| `datathon submit-kaggle --dry-run --file <path>` | Validate submission schema |

---

## Modeling

### Pluggable Forecasters

Any model implementing `BaseForecaster` can be registered:

```python
# src/datathon/modeling/forecasters/my_model.py
class MyForecaster(BaseForecaster):
    def fit(self, X, y_rev, y_cogs): ...
    def predict(self, X) -> (rev_pred, cogs_pred): ...
    def save(self, path): ...
    @classmethod
    def load(cls, path): ...

# Register
FORECASTERS["my_model"] = MyForecaster
```

### Registered Models

| Model | Config Location |
|---|---|
| `lightgbm` | `configs/modeling.yaml` → `models.lightgbm` |
| `xgboost` | `configs/modeling.yaml` → `models.xgboost` |

Hyperparameters are **injected from YAML** — no hardcode in Python.

### Recursive Multi-Step Forecast

`recursive_forecast` recomputes target-derived lags and rolling statistics at each step. Exogenous features are forward-filled; calendar features are computed from the date. This guarantees **no data leakage**.

### Cross-Validation

`ExpandingWindowCV` produces time-series-aware splits:

```
Fold 1: [train==========|val===]
Fold 2: [train===============|val===]
Fold 3: [train======================|val===]
```

---

## DBT Marts

Marts are organised by business domain:

- **finance** — `mart_forecast_daily_base`, `mart_forecast_daily_modeling`, `mart_submission_scaffold`
- **operations** — fulfillment, inventory, returns KPIs
- **marketing** — traffic/conversion, promotion effectiveness
- **customer** — cohorts, RFM
- **product** — lifetime performance, monthly health, category performance
- **executive** — daily KPIs, risk flags, scorecards, region performance

Run: `make dbt-build` (167 tests, all passing).

---

## Evidence Dashboard

```bash
make evidence-install
make evidence-sources   # Refresh sources from DuckDB
make evidence-dev       # Local dev server
```

Pages: executive pulse, risk flags, revenue drivers, fulfillment, inventory, marketing, customer cohorts, product health, category performance, forecast feature health.

---

## Makefile Targets

```bash
make install            # uv sync --extra dev
make build-raw          # datathon build-raw --strict
make dbt-build          # dbt build
make train-model        # datathon train --mode train-final --model-type lightgbm
make predict-model      # datathon predict --model-type lightgbm
make compare-models     # datathon compare-models --n-folds 2 --horizon-days 30
make test               # pytest -q
make lint               # ruff check .
```

---

## Tests

```bash
make test   # 13 passed
make lint   # All checks passed
```

---

## Artifacts

Saved to `models/<model_type>/`:

```
models/lightgbm/
  forecaster.pkl      # fitted forecaster
  meta.json           # {model_type, feature_columns}
  cv_results.json
```
