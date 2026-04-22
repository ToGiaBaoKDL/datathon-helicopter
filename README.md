# Datathon Round 1 — Analytics & Forecasting

End-to-end analytics and forecasting pipeline for daily revenue and COGS.

**Stack:** uv · dbt + DuckDB · Evidence · Rich CLI · LightGBM · XGBoost · Seaborn

---

## Prerequisites

- **Python** 3.10–3.12
- **uv** — fast Python package manager  
  Install: [https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)
- **Node.js** 18+ (for Evidence dashboard only)
- **Kaggle API credentials** (for data download & submission)

### OS Notes

| OS | Notes |
|---|---|
| Linux / macOS | Fully supported. Use `make` commands as-is. |
| Windows | Use Git Bash or WSL for `make`. Alternatively run `uv run datathon <command>` directly. |

---

## Quick Start

```bash
# 1. Clone and install dependencies
uv sync --extra dev

# 2. Configure Kaggle credentials
cp .env.example .env
# Edit .env with your Kaggle username and API token

# 3. Download & build raw data
uv run datathon download-data
uv run datathon build-raw --strict

# 4. Run dbt pipeline
uv run dbt build --project-dir dbt --profiles-dir dbt

# 5. Train, compare models, and generate submission
uv run datathon compare-models --n-folds 3 --horizon-days 30
uv run datathon submit-kaggle --dry-run --file data/submissions/best_submission.csv
```

---

## Project Structure

```
├── configs/                  # YAML configs (competition, modeling, raw tables)
├── dbt/
│   ├── models/
│   │   ├── staging/          # Source-aligned cleaned views
│   │   ├── intermediate/     # Enriched order lines, inventory signals
│   │   └── marts/            # Business-domain marts (finance, operations,
│   │                         #   marketing, customer, product, executive)
│   └── tests/                # Custom dbt tests
├── notebooks/                # Exploratory notebooks (numbered prefix convention)
│   └── 01_shap_explainability.ipynb
├── reports/
│   ├── evidence/             # Evidence.dev analytics site
│   └── shap/                 # SHAP plots output (auto-generated)
├── src/datathon/
│   ├── cli.py                # Entry point
│   ├── commands/             # CLI commands (rich output)
│   ├── modeling/             # Forecasters, CV, trainer, SHAP explainer
│   └── utils/                # Config, data loaders, DuckDB I/O
├── tests/                    # pytest suite
├── Makefile                  # Common tasks
└── CONVENTIONS.md            # Naming & modeling conventions
```

---

## CLI Commands

| Command | Purpose |
|---|---|
| `datathon build-raw --strict` | Load CSVs into DuckDB raw schema |
| `datathon train --mode evaluate --model-type lightgbm` | Expanding-window CV vs seasonal naive |
| `datathon train --mode train-final --model-type lightgbm` | Train final model & save artifacts |
| `datathon predict --model-type lightgbm` | Generate submission from saved model |
| `datathon compare-models` | CV all registered models, pick winner, train final, submit |
| `datathon ensemble --model-types lightgbm,xgboost` | Average predictions from trained models |
| `datathon explain --model-type lightgbm` | Generate SHAP summary & bar plots |
| `datathon baseline --mode evaluate` | Seasonal-naive baseline benchmark |
| `datathon baseline --mode submit` | Generate naive submission |
| `datathon submit-kaggle --dry-run --file <path>` | Validate submission schema |

---

## Notebooks

All notebooks live in `notebooks/` and follow the `NN_descriptive_name.ipynb` convention.

| Notebook | Purpose |
|---|---|
| `01_shap_explainability.ipynb` | Interactive SHAP analysis for trained Revenue & COGS models |

Run with:
```bash
uv run jupyter lab notebooks/
```

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

Run: `make dbt-build` to build models and run tests.

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
make ensemble           # datathon ensemble --model-types lightgbm,xgboost
make explain            # datathon explain --model-type lightgbm
make test               # pytest -q
make lint               # ruff check .
```

---

## Tests

```bash
make test   # run pytest suite
make lint   # run ruff linter
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

---

## Conventions

See [`CONVENTIONS.md`](CONVENTIONS.md) for detailed naming rules covering:
- dbt model prefixes (`stg_`, `int_`, `mart_`)
- Feature naming (`lag_7d_revenue`, `roll_mean_28d_sessions`)
- Notebook naming (`01_shap_explainability.ipynb`)
- Visualisation preference (seaborn over matplotlib)
- Command naming and warehouse schema layers
