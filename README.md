# Datathon Round 1 — Analytics & Forecasting

End-to-end analytics and forecasting pipeline for daily revenue and COGS.

**Stack:** uv · dbt + DuckDB · Evidence · Rich CLI · LightGBM · XGBoost · CatBoost · Seaborn

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

# 5. Tune all models, merge configs, compare, and generate submission
uv run datathon tune --model-type lightgbm --patience 5
uv run datathon tune --model-type xgboost --patience 5
uv run datathon tune --model-type catboost --patience 5

# Merge individual delta configs into one file for compare-models
uv run python -c "
import yaml, glob, pathlib
base = yaml.safe_load(open('configs/modeling.yaml'))
for p in sorted(glob.glob('configs/tuned/*.yaml')):
    delta = yaml.safe_load(open(p))
    for k, v in (delta.get('models') or {}).items():
        base.setdefault('models', {})[k] = v
pathlib.Path('configs/tuned/all_models.yaml').write_text(yaml.dump(base, sort_keys=False, allow_unicode=True))
"

uv run datathon compare-models --config configs/tuned/all_models.yaml
uv run datathon submit-kaggle --dry-run --file data/submissions/best_submission.csv
```

---

## Project Structure

```
├── configs/                  # YAML configs
│   ├── modeling.yaml         # Base config (source of truth)
│   └── tuned/                # Delta configs from Optuna tuning
├── dbt/
│   ├── models/
│   │   ├── staging/          # Source-aligned cleaned views
│   │   ├── intermediate/     # Enriched order lines, inventory signals
│   │   └── marts/            # Business-domain marts (finance, operations,
│   │                         #   marketing, customer, product, executive)
│   └── tests/                # Custom dbt tests
├── notebooks/                # Exploratory notebooks
├── reports/
│   ├── evidence/             # Evidence.dev analytics site
│   └── shap/                 # SHAP plots output (auto-generated)
├── src/datathon/
│   ├── cli.py                # Entry point
│   ├── commands/             # CLI commands
│   ├── modeling/             # Forecasters, CV, trainer, tuner, SHAP explainer
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
| `datathon tune --model-type catboost --n-trials 30 --patience 5` | Optuna hyperparameter search with early stopping |
| `datathon train --mode evaluate --model-type lightgbm` | Expanding-window CV vs seasonal naive |
| `datathon train --mode train-final --model-type lightgbm --config configs/tuned/lightgbm.yaml` | Train final model with tuned params |
| `datathon predict --model-type lightgbm` | Generate submission from saved model |
| `datathon compare-models --config configs/tuned/all_models.yaml` | CV all models + ensemble, pick true winner, train finals, submit |
| `datathon ensemble --model-types lightgbm,xgboost --weights 0.5,0.5` | Weighted ensemble from trained models |
| `datathon explain --model-type lightgbm` | Generate SHAP summary & bar plots |
| `datathon baseline --mode evaluate` | Seasonal-naive baseline benchmark |
| `datathon baseline --mode submit` | Generate naive submission |
| `datathon submit-kaggle --dry-run --file <path>` | Validate submission schema |
| `datathon submit-kaggle --file <path> --message "desc"` | Submit to Kaggle |

### Config Management

Base config lives in `configs/modeling.yaml` (source of truth):

```yaml
cogs_target: absolute          # "absolute" or "ratio"
residual_target: true          # predict residual vs YoY baseline instead of raw values
models:
  ...
```

Tuning writes **delta configs** (only the tuned model's hyperparameters) to `configs/tuned/<model>.yaml`:

```yaml
# configs/tuned/catboost.yaml
models:
  catboost:
    learning_rate: 0.0789
    depth: 5
    iterations: 487   # best iteration from early stopping (injected automatically)
    ...
```

Use `--config <path>` to overlay a delta on top of the base config:

```bash
uv run datathon train --mode train-final --model-type catboost --config configs/tuned/catboost.yaml
```

Merge multiple deltas into a single file for `compare-models`:

```bash
# Merge individual tuned configs into one file
uv run python -c "
import yaml, glob, pathlib
base = yaml.safe_load(open('configs/modeling.yaml'))
for p in sorted(glob.glob('configs/tuned/*.yaml')):
    delta = yaml.safe_load(open(p))
    for k, v in (delta.get('models') or {}).items():
        base.setdefault('models', {})[k] = v
pathlib.Path('configs/tuned/all_models.yaml').write_text(yaml.dump(base, sort_keys=False, allow_unicode=True))
"

uv run datathon compare-models --config configs/tuned/all_models.yaml
```

> **Why merge?** `compare-models` only accepts a single `--config`. Each `tune` run emits a delta for one model. Merging them ensures every model uses its own tuned params during the comparison.

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
    def fit(self, X, y_rev, y_cogs, eval_set=None): ...
    def predict(self, X) -> (rev_pred, cogs_pred): ...
    def save(self, path): ...
    @classmethod
    def load(cls, path): ...

# Register
FORECASTERS["my_model"] = MyForecaster
```

### Registered Models

| Model | Config Key |
|---|---|
| `lightgbm` | `models.lightgbm` |
| `xgboost` | `models.xgboost` |
| `catboost` | `models.catboost` |

Hyperparameters are **injected from YAML** — no hardcode in Python. Early stopping rounds, n_estimators ceiling, and parallel jobs are defined once in the base config.

### Recursive Multi-Step Forecast

`recursive_forecast` recomputes target-derived lags and rolling statistics at each step. Exogenous features are forward-filled; calendar features are computed from the date. This guarantees **no data leakage**.

### Cross-Validation

`ExpandingWindowCV` produces time-series-aware splits:

```
Fold 1: [train==========|val===]
Fold 2: [train===============|val===]
Fold 3: [train======================|val===]
```

`compare-models` evaluates every registered model **and** an unweighted ensemble on the same CV folds, then picks the true winner (individual model or ensemble) by lowest total MAE.

### Two-Stage COGS

When `cogs_target: ratio` is set in the config, the COGS model predicts `cogs / revenue` instead of absolute COGS. The ratio is clamped to `[0, 2]` and converted back to absolute values (`revenue * ratio`) during recursive forecast. This leverages the strong revenue-COGS correlation (≈0.976) while allowing negative-margin scenarios.

### Residual Modeling

When `residual_target: true` is set (recommended), models predict **deviations from the YoY baseline** instead of raw values:
- `revenue_residual = revenue - lag_365d_revenue`
- `cogs_residual = cogs - lag_365d_cogs`

Recursive forecast reconstructs: `revenue = lag_365d_revenue + predicted_residual`.

This is especially effective for long horizons (548 days) because the YoY baseline already captures ~70-80% of variance; the model only learns the "delta" from last year, which is easier to predict accurately.

---

## DBT Marts

Marts are organised by business domain:

- **finance** — `mart_forecast_daily_base`, `mart_forecast_daily_features`, `mart_submission_scaffold`
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
make tune-catboost      # datathon tune --model-type catboost --n-trials 30 --patience 5
make compare-models     # datathon compare-models --config configs/tuned/all_models.yaml
make ensemble           # datathon ensemble --model-types lightgbm,xgboost,catboost
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
  meta.json           # {model_type, feature_columns, cogs_column}
  cv_results.json
```

Tuning studies are persisted to `optuna_studies/<model>.db` (SQLite) for resume on interrupt.

---

## Conventions

See [`CONVENTIONS.md`](CONVENTIONS.md) for detailed naming rules covering:
- dbt model prefixes (`stg_`, `int_`, `mart_`)
- Feature naming (`lag_7d_revenue`, `roll_mean_28d_sessions`)
- Notebook naming (`01_shap_explainability.ipynb`)
- Visualisation preference (seaborn over matplotlib)
- Command naming and warehouse schema layers
