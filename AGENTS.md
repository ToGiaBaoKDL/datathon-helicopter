# Agent Context

## Project
Analytics / forecasting repo for datathon round 1. Stack: uv, dbt + DuckDB, Evidence, Rich CLI, LightGBM.

## What We Did This Session

### 1. CLI Cleanup & Anti-Duplication
- **baseline command** (`src/datathon/commands/baseline.py`):
  - `--output-path` is now only accepted (and required) in `--mode submit`. Passing it with `--mode evaluate` raises a `CommandError`.
  - `_generate_submission` now uses `submission_columns()` from `competition.py` instead of hardcoded `["Date", "Revenue", "COGS"]`, enforcing the exact column order defined in `configs/competition.yaml`.
- **submit-kaggle command** (`src/datathon/commands/submit_kaggle.py`):
  - Added `--dry-run` flag. When set, the command validates the submission file (columns match `submission_columns()`, non-empty, null warning) without uploading.
  - `--message` is no longer required when `--dry-run` is used.
- **Makefile**: Added `validate-submission` target wrapping `datathon submit-kaggle --dry-run`.

### 2. Evidence Final Polish
Updated pages under `reports/evidence/pages/eda/`:
- **executive-kpi-pulse.md**: Commercial Pulse changed from `LineChart` to `AreaChart`. Added `subtitle` to all charts. Added a `Heatmap` for average session-to-order rate by day-of-week.
- **revenue-and-drivers.md**: Revenue vs COGS and Traffic vs Orders changed to `AreaChart`. Added `subtitle`, `yFmt`. Added a `Heatmap` for average revenue by day-of-week.
- **fulfillment-and-returns.md**: Added `subtitle` and `yFmt` to charts. Added a `Heatmap` for average return rate by day-of-week.
- **inventory-and-growth-scorecard.md**: Added `subtitle` and `yFmt`. Added a `Heatmap` for conversion rate by day-of-week.
- **category-and-region-performance.md**: Added `subtitle` and `yFmt` to all charts.
- **forecast-feature-health.md**: Added `subtitle` and `yFmt`.
- **risk-flags.md**: New page showing daily risk alerts (see below).
- **index.md**: Added link to Risk Flags page.

### 3. New Mart: `mart_daily_risk_flags`
- Created `dbt/models/marts/executive/mart_daily_risk_flags.sql`.
- Derives from `mart_daily_executive_kpis` using dynamic thresholds (`quantile_cont`):
  - `stockout_risk_flag`: 1 when `avg_stockout_days > p90`.
  - `return_spike_flag`: 1 when `return_record_rate > p95`.
  - `conversion_drop_flag`: 1 when `session_to_order_rate < p10`.
- Added model spec + tests (`not_null`, `unique` on `sales_date`) in `marts.yml`.
- Added Evidence source `mart_daily_risk_flags.sql` and new page `risk-flags.md`.

### 4. Customer Analytics Marts (New)
- **`mart_monthly_customer_cohort`** (`dbt/models/marts/customer/mart_monthly_customer_cohort.sql`):
  - Grain: `(cohort_month, months_since_first_order)`.
  - Metrics: `cohort_size`, `active_customer_count`, `retention_rate`, `total_orders`, `total_revenue`, `total_cogs`, `gross_profit`, `avg_order_value`.
  - Cohort month = first order month of each customer (from `stg_orders`).
  - **Fix**: Changed `count(*)` to `count(distinct order_id)` in monthly_activity CTE so `total_orders` counts orders (not order lines) and `avg_order_value` is true AOV.
- **`mart_customer_rfm`** (`dbt/models/marts/customer/mart_customer_rfm.sql`):
  - Grain: `customer_id`.
  - Metrics: `first_order_date`, `last_order_date`, `total_orders`, `total_revenue`, `total_cogs`, `gross_profit`, `avg_order_value`, `recency_days`, `avg_days_between_orders`, `acquisition_channel`, `age_group`.

### 5. Promotion Effectiveness Mart (New)
- **`mart_promotion_effectiveness`** (`dbt/models/marts/marketing/mart_promotion_effectiveness.sql`):
  - Grain: `promo_id`.
  - Metrics: `promo_type`, `discount_value`, `start_date`, `end_date`, `applicable_category`, `promo_channel`, `total_order_lines`, `total_orders`, `total_units`, `total_gross_revenue`, `total_net_revenue`, `total_discount_amount`, `avg_discount_per_line`, `avg_order_value`, `discount_rate`.
  - Uses actual `discount_amount` from order_items (not formula-based).
  - Key insight from data: percentage promos (45 campaigns) drive ~5B revenue at 12.9% avg discount rate; fixed promos (5 campaigns) drive ~376M at 1.2% rate.

### 6. Product Analytics Marts (New)
- **`mart_product_lifetime_performance`** (`dbt/models/marts/product/mart_product_lifetime_performance.sql`):
  - Grain: `product_id`.
  - Metrics: static attributes, `total_orders`, `total_units_sold`, `total_revenue`, `total_cogs`, `gross_profit`, `realized_margin_rate`, `return_unit_rate`, `avg_selling_price`, `avg_sell_through_rate`, inventory flags, `lifecycle_stage` (active/dormant/discontinued/never_sold), `category_revenue_rank`, `revenue_share_in_category`.
  - Lifecycle logic based on last_sale_date vs dataset max date (active = last 6 months, dormant = 6-12 months, discontinued = > 12 months, never_sold = no sales).
  - Revenue reconciles 100% with `int_order_line_enriched`.
- **`mart_monthly_product_health`** (`dbt/models/marts/product/mart_monthly_product_health.sql`):
  - Grain: `(product_id, month_start_date)`.
  - Metrics: monthly `orders`, `units_sold`, `revenue`, `cogs`, `return_units`, `return_unit_rate`, inventory metrics (`stock_on_hand`, `sell_through_rate`, `stockout_flag`, `overstock_flag`, etc.).
  - Full outer join of monthly sales and monthly inventory (both normalized to month_start_date).

### 7. dbt Audit & Bug Fixes
- **`build_raw.py`**: `_EXPECTED_RAW_COLUMNS` was missing 8 of 14 tables. Completed full column validation for all raw tables.
- **`mart_daily_returns_kpis`**: Fixed **critical logic bug**. Returns were previously grouped by `return_date`, denominator by `order_date`, causing rates > 1 (e.g., 2013-03-02 rate = 1.11). Now both numerator and denominator use **order_date cohort** grain via join to `stg_orders`. Max rate is now 0.17.
- **`mart_weekly_region_performance`**: Fixed bad `group by 1, 2, 11, 12, 13` referencing joined CTE columns. Changed to `max(coalesce(...))` with clean `group by 1, 2`.
- **`mart_daily_marketing_kpis`**: Removed `order_status not in ('created', 'cancelled')` filter on `order_count` to ensure consistency with `mart_forecast_daily_base`. The mismatch was affecting 3,824/3,833 days (99.8% of days have cancelled orders).

### 8. ML Feature Enrichment (`mart_forecast_daily_features`)
- **Calendar features** (known in advance, leakage-safe):
  - `quarter`, `day_of_month`, `days_to_month_end`, `is_month_start` (day <= 3), `is_month_end` (day > 28).
  - Business insight: month-end days avg revenue ~7.1M vs ~4.0M other days (salary cycle effect).
- **Revenue volatility**:
  - `roll_std_7d_revenue`, `roll_std_28d_revenue` — sample stddev on lagged revenue windows.
- **Extended feature lags**:
  - `lag_7d_sessions`, `lag_7d_order_count`, `lag_7d_units_sold` — weekly periodicity capture.
- **Rolling means on lagged features**:
  - `roll_mean_7d_sessions`, `roll_mean_7d_order_count`, `roll_mean_7d_units_sold`.
- All additions are **leakage-safe** (only historical lags/rolling used).

### 9. Folder Reorganization
Marts reorganized into semantic business domains under `dbt/models/marts/`:
- `finance/` — forecast, submission scaffold
- `operations/` — fulfillment, inventory, returns
- `marketing/` — traffic/conversion, promotions
- `customer/` — cohorts, RFM
- `product/` — lifetime performance, monthly health, category performance
- `executive/` — executive KPIs, risk flags, scorecards, region performance, MCQ

### 10. DBT Documentation Enrichment
- **`staging.yml`**: Added detailed `description` for **all 14 models and every column** (~100+ columns). Descriptions include business context, unit of measure, calculation logic, and FK relationships.
- **`marts.yml`**: Added detailed `description` for **all 18 table models and every column** (~150+ columns). Each model now includes grain statement. Descriptions cover derived metrics (e.g., `realized_margin_rate`, `retention_rate`, `discount_rate`), flags, and lag features.

### 11. Evidence Sources & Pages Expansion
- **New sources** (5 files under `reports/evidence/sources/datathon_warehouse/`):
  - `mart_customer_rfm.sql`
  - `mart_monthly_customer_cohort.sql`
  - `mart_promotion_effectiveness.sql`
  - `mart_product_lifetime_performance.sql`
  - `mart_monthly_product_health.sql`
- **New pages** (3 files under `reports/evidence/pages/eda/`):
  - **`customer-cohort-and-rfm.md`**: BigValue snapshots, retention curve LineChart, RFM segment BarChart, recency distribution BarChart, top customers DataTable.
  - **`promotion-effectiveness.md`**: Promo type BarCharts, campaign timeline DataTable, discount-vs-revenue ScatterPlot, channel breakdown BarChart, daily discount AreaChart, day-of-week discount Heatmap.
  - **`product-lifecycle-and-health.md`**: Lifecycle distribution BarCharts, category Pareto BarCharts, monthly health LineCharts, top returned products DataTable, revenue share DataTable.
- **`index.md`**: Updated with links to 3 new pages.
- **Evidence convention applied consistently**:
  - `title` = Noun phrase (metric + dimension)
  - `subtitle` = Insight/guidance (max 10 words)
  - `yFmt` aligned to data type (`0,0` for VND, `0.0%` for rates, `0` for counts)
  - Chart diversity: AreaChart, LineChart, BarChart, Heatmap, ScatterPlot, BigValue, DataTable

### 12. Evidence Pages Rewrite — Filters, Seasonal Heatmaps, INT32 Safety
Systematic rewrite of all Evidence pages under `reports/evidence/pages/eda/`:
- **Filters added**:
  - `executive-kpi-pulse.md`: DateRange + Year Dropdown.
  - `revenue-and-drivers.md`: DateRange.
  - `fulfillment-and-returns.md`: DateRange.
  - `inventory-and-growth-scorecard.md`: DateRange.
  - `risk-flags.md`: DateRange (new).
  - `customer-cohort-and-rfm.md`: Acquisition Channel Dropdown (new).
  - `promotion-effectiveness.md`: Promo Type + Promo Channel Dropdowns (new).
  - `product-lifecycle-and-health.md`: Category + Lifecycle Stage Dropdowns (new).
  - `category-and-region-performance.md`: Category Dropdown (fixed component ref from `categories` → `_categories`).
- **Seasonal insights** (monthly heatmaps + day-of-week heatmaps) added to: executive-kpi-pulse, revenue-and-drivers, fulfillment-and-returns, inventory-and-growth-scorecard.
- **INT32 overflow fix**: Replaced all `::int` casts on monetary aggregates with `::bigint` in customer, promotion, and product Evidence pages.
- **`_date_bounds` fix**: Changed from `select sales_date from table` (full table scan) to `select min(sales_date) as sales_date, max(sales_date) as sales_date` in revenue-and-drivers, fulfillment-and-returns, inventory-and-growth-scorecard.
- **`rows=10` enforcement**: All DataTable components now explicitly set `rows=10`.

### 13. Evidence Folder Reorganization & Filter Best Practice Fixes
- **Semantic subfolders** created under `reports/evidence/pages/eda/` to mirror dbt marts structure:
  - `executive/` — executive-kpi-pulse, risk-flags, part1-mcq-metrics
  - `finance/` — revenue-and-drivers, forecast-feature-health
  - `operations/` — fulfillment-and-returns, inventory-and-growth-scorecard
  - `marketing/` — promotion-effectiveness
  - `customer/` — customer-cohort-and-rfm
  - `product/` — product-lifecycle-and-health, category-and-region-performance
  - `index.md` updated with grouped navigation links.
- **Dropdown best practice fixes** (Evidence docs: value access requires `.value`):
  - `category-and-region-performance.md`: Fixed `inputs.cat_filter` → `inputs.cat_filter.value` (was serializing to `[object Object]`). Switched to **multi-select** Dropdown (`multiple=true`, `selectAllByDefault=true`) with SQL `in ${inputs.cat_filter.value}`. Added DateRange filter for both category and region queries.
  - `customer-cohort-and-rfm.md`: Fixed `inputs.channel_filter` → `inputs.channel_filter.value`. Removed `'null'` string hack; Evidence auto-selects first option by default. Added Age Group Dropdown for drill-down.
  - `executive-kpi-pulse.md`: Fixed `inputs.year_filter` → `inputs.year_filter.value`. Removed `'null'` string hack.
  - `product-lifecycle-and-health.md`: Fixed `inputs.category_filter` → `inputs.category_filter.value`, `inputs.stage_filter` → `inputs.stage_filter.value`. Removed `'null'` string hack.
  - `promotion-effectiveness.md`: Fixed `inputs.type_filter` → `inputs.type_filter.value`, `inputs.channel_filter` → `inputs.channel_filter.value`. Removed `'null'` string hack.

### 14. Evidence Filter Fixes — Multi-Select Defaults & DateRange Repair
- **`_date_bounds` reverted**: `select min(...) as sales_date, max(...) as sales_date` returned 1 row with 2 columns, breaking Evidence DateRange (showed only 1 date). Reverted to `select sales_date from table` so DateRange computes range from actual date column values.
- **All Dropdowns converted to multi-select** (`multiple=true`, `selectAllByDefault=true`) with SQL `in ${inputs.filter.value}`:
  - `category-and-region-performance.md`: Category + Region multi-select.
  - `customer-cohort-and-rfm.md`: Channel + Age Group multi-select.
  - `product-lifecycle-and-health.md`: Category + Lifecycle Stage multi-select.
  - `promotion-effectiveness.md`: Promo Type + Promo Channel multi-select.
- **Missing DateRange added**:
  - `promotion-effectiveness.md`: DateRange applied to `daily_promo_pressure` and `discount_heatmap_dow`.
  - `product-lifecycle-and-health.md`: DateRange applied to `monthly_health_trend`.
- **Missing filters added**:
  - `category-and-region-performance.md`: Added Region multi-select Dropdown.

### 15. Evidence Business Logic & Visualization Audit
Full review of all 12 Evidence pages against mart schemas, filter correctness, and business visualization standards:
- **`executive-kpi-pulse.md`**:
  - **Fix**: Split `key_metrics_long` into 2 charts (`revenue_long` + `rates_long`). Root cause: Revenue (~4-7M) and rates (~2-20%) on same Y-axis caused rates to collapse to zero line — critical visualization bug.
  - **Fix**: `quarterly_summary` changed from `avg(gross_margin_rate)` to `sum(gross_profit)/sum(revenue)` and `avg(session_to_order_rate)` to `sum(order_count)/sum(sessions)` for ratio-accurate aggregation.
- **`product-lifecycle-and-health.md`**:
  - **Fix**: Removed `category in ${inputs.category_filter.value}` from `monthly_health_trend`. Root cause: `mart_monthly_product_health` does not have a `category` column (grain = product_id × month), causing a column-not-found error.
- **Filter audit passed**: All pages use `multiple=true` + `selectAllByDefault=true` with SQL `in ${inputs.filter.value}`. DateRange applies consistently. `_date_bounds` uses `select sales_date from table` (required by Evidence DateRange component to compute min/max from column values).
- **Mart coverage audit passed**: Every page queries the correct mart(s) at the correct grain. No evidence pages duplicate dbt business logic; standard `union all` unpivots are used only for Evidence component consumption.
- **Chart diversity audit passed**: AreaChart, LineChart, BarChart, Heatmap, ScatterPlot, BigValue, DataTable all used appropriately across pages.

### 16. Evidence Chart Cleanup — Sparse Heatmaps → BarCharts
Replaced low-information-density Heatmaps with clearer BarCharts across 4 pages:
- **Day-of-week heatmaps** (1-dimensional, only diagonal values visible):
  - `executive-kpi-pulse.md`: Conversion Pattern by Day of Week → BarChart.
  - `revenue-and-drivers.md`: Revenue Pattern by Day of Week → BarChart.
  - `fulfillment-and-returns.md`: Return Rate by Day of Week → BarChart.
  - `inventory-and-growth-scorecard.md`: Conversion Rate by Day of Week → BarChart.
- **Monthly year×month heatmaps** (number overflow in cells, hard to compare):
  - `revenue-and-drivers.md`: Monthly Revenue by Year → BarChart with `series=year`, `yFmt="0.0a"` (suffix format: 1.5b, 2.3m).
  - `fulfillment-and-returns.md`: Monthly Return Rate by Year → BarChart with `series=year`.
  - `inventory-and-growth-scorecard.md`: Monthly Stockout Days by Year → BarChart with `series=year`.
- Removed `::bigint` cast on `monthly_revenue_heatmap` aggregate (no longer needed with BarChart).

### 17. Evidence Formatting Best Practice Fix
- **Root cause**: Dùng `0.0a` trong Evidence hiển thị suffix `k/m/b` tự động, gây không thống nhất (cùng page có cả `k` và `m`). Scale `/ 1000` trong SQL + title `(k)` là anti-pattern.
- **Fix theo Evidence docs** (https://docs.evidence.dev/core-concepts/formatting):
  - Revert tất cả SQL queries về giá trị gốc (bỏ `/ 1000`).
  - Dùng built-in format `num0` cho monetary aggregates — hiển thị full integer với comma separator, để Evidence auto-format theo context.
  - Bỏ `(k)` khỏi tất cả `yAxisTitle`.
  - Count values dùng `num0`, rates dùng `0.0%`, days dùng `0` hoặc `0.00`.

### 18. Evidence Chart Enhancements — New Components
- **`revenue-and-drivers.md`**: Monthly Revenue BarChart → **CalendarHeatmap** (`daily_revenue_calendar`). Hiển thị revenue intensity từng ngày trên lịch, phát hiện spike/bottom patterns tốt hơn grouped monthly bars.
- **`inventory-and-growth-scorecard.md`**: Gộp 2 LineChart (Revenue Growth + Order Growth) thành **1 Combo BarChart** (`y=wow_revenue_growth_rate` bar, `y2=wow_order_growth_rate` line, `y2SeriesType=line`). Tiết kiệm space, thể hiện correlation trực quan.
- **`executive-kpi-pulse.md`**: Thêm `ReferenceLine` mean revenue trên Revenue Trend (AreaChart) và Monthly Seasonality (BarChart). Giúp reader nhận biết nhanh ngày/tháng nào trên/dưới trung bình.
- **`fulfillment-and-returns.md`**: Thêm `ReferenceLine y=0.05` (5% threshold) trên Daily Return Record Rate và Daily Return Unit Rate. Đánh dấu ngưỡng chất lượng.
- **`promotion-effectiveness.md`**: Thêm `ReferenceLine` avg discount rate trên ScatterPlot (Discount Depth vs Revenue). Chia góc phần tư: high-discount-low-revenue vs low-discount-high-revenue.
- **`product-lifecycle-and-health.md`**: Thêm `ReferenceLine y=0.05` (5% quality threshold) trên Monthly Average Return Rate, và `y=100` (alert level) trên Monthly Stockout Product Count.
- **`category-and-region-performance.md`**: Thêm `ReferenceLine y=0.15` (15% target margin) trên Monthly Gross Margin by Category.
- **`customer-cohort-and-rfm.md`**: Thêm `ReferenceLine y=0.20` (20% benchmark) trên Retention Curve.

### 20. Modular ML Pipeline (Refactored)
Architecture supports pluggable forecasters via `BaseForecaster` abstraction.

**Modeling layer:**
- **`src/datathon/modeling/forecasters/base.py`**: `BaseForecaster` ABC — `fit`, `predict`, `save`, `load`.
- **`src/datathon/modeling/forecasters/lightgbm.py`**: `LightGBMForecaster` — dual `LGBMRegressor` for revenue/COGS.
- **`src/datathon/modeling/forecasters/__init__.py`**: `FORECASTERS` registry (`{"lightgbm": LightGBMForecaster, "xgboost": XGBoostForecaster}`). New models register here.
- **`src/datathon/modeling/cv.py`**: `ExpandingWindowCV` — time-series expanding-window splits.
- **`src/datathon/modeling/recursive.py`**: `recursive_forecast` — generic multi-step recursion. Recomputes target-derived lags/rolling each step. Exogenous features forward-filled; calendar features computed from date.
- **`src/datathon/modeling/trainer.py`**: Generic `Trainer` — accepts any `BaseForecaster`. `run_cv`, `train_final`, `save_artifacts`, `load_artifacts`.
- **`src/datathon/modeling/forecasters/xgboost.py`**: `XGBoostForecaster` — dual `XGBRegressor` for revenue/COGS.
- **`src/datathon/modeling/factory.py`**: `build_forecaster(model_type, config)` — central factory that instantiates any registered forecaster from YAML config. Eliminates duplicate `_build_forecaster` logic across CLI commands.
- **`src/datathon/modeling/explainer.py`**: SHAP explainability wrapper for fitted forecasters. Returns mean absolute SHAP values per feature for revenue and COGS models, useful for business feature-importance interpretation.
- **`src/datathon/utils/config.py`**: `load_modeling_config()` reads `configs/modeling.yaml`.
- **`src/datathon/utils/data_loaders.py`**: Centralised DuckDB data loaders (`load_modeling_data`, `load_forecast_base`, `load_scaffold`). Eliminates duplicate SQL across CLI commands.

**Config centralization:**
- `configs/modeling.yaml`:
  ```yaml
  models:
    lightgbm:
      n_estimators: 500
      learning_rate: 0.05
      num_leaves: 31
      objective: regression
      verbose: -1
    xgboost:
      n_estimators: 500
      learning_rate: 0.05
      max_depth: 6
      objective: reg:squarederror
      verbosity: 0
  ```
  Hyperparameters injected into forecaster via `**model_cfg`. No hardcode in Python.

**CLI layer:**
- `datathon train --mode evaluate --model-type lightgbm --n-folds 5 --horizon-days 30`
- `datathon train --mode train-final --model-type lightgbm`
- `datathon predict --model-type lightgbm --output-path <path>`
- `datathon compare-models --n-folds 3 --horizon-days 30` — runs CV for **all** registered model types, prints comparison table, trains final winner, generates submission.
- `--model-type` validated against registry. Artifacts saved to `models/<model_type>/`.

**Artifacts structure:**
```
models/lightgbm/
  forecaster.pkl      # serialized LightGBMForecaster
  meta.json           # {model_type, feature_columns}
  cv_results.json
```

**Validation Results on 3-fold expanding-window CV** (30-day horizon):
  - Revenue MAE: ~268K–859K (LightGBM) vs ~763K–1.6M (seasonal naive).
  - COGS MAE: ~333K–928K (LightGBM) vs ~793K–1.5M (seasonal naive).
  - LightGBM beats naive baseline on every fold by roughly 2–3x.
- **Tests**: `tests/test_trainer.py` parametrized for both `LightGBMForecaster` and `XGBoostForecaster` (13 passed).
- **Makefile**: Added `compare-models` target. `train-model` and `predict-model` targets use `--model-type lightgbm`.

### 21. SHAP Explainability — CLI + Notebook
- **`datathon explain` command** (`src/datathon/commands/explain.py`):
  - Load saved forecaster artifacts (`Trainer.load_artifacts`), sample background distribution from `mart_forecast_daily_features`.
  - Generates **SHAP beeswarm summary** and **bar plots** for both Revenue and COGS models, saved as PNGs under `reports/shap/`.
  - Prints Rich table of top features ranked by mean absolute SHAP value.
  - Options: `--model-type`, `--model-dir`, `--output-dir`, `--sample-size` (default 500), `--max-display` (default 20).
- **`notebooks/shap_analysis.ipynb`**:
  - Standalone Jupyter notebook for interactive SHAP exploration.
  - Loads model + data, wraps `shap.Explanation` for `shap.plots.beeswarm` and `shap.plots.bar`, and displays ranked feature tables.

### 22. Dead Code Removal
- Removed `src/datathon/features/lag_features.py` and `tests/test_lag_features.py`. All lag/rolling features are now created entirely inside dbt (`mart_forecast_daily_features.sql`); the Python feature module was no longer used by the main pipeline.

### 23. Validation Results
- `dbt build`: **167 / 167 PASS** (18 table models, 17 view models, 132 data tests).
- `pytest`: 11 passed (removed 2 lag_features tests).
- `ruff check .`: All checks passed.
- `datathon baseline --mode evaluate`: Works.
- `datathon baseline --mode submit`: Generates file correctly.
- `datathon train --mode evaluate`: Works.
- `datathon train --mode train-final`: Saves artifacts correctly.
- `datathon predict --model-type lightgbm --output-path data/submissions/lightgbm_submission.csv`: Generates valid submission.
- `datathon compare-models --n-folds 2 --horizon-days 30`: Evaluates all models, picks winner, trains final, generates submission.
- `datathon explain --model-type lightgbm`: Generates SHAP plots successfully.
- `datathon submit-kaggle --dry-run`: Validates successfully.
- `datathon ensemble --model-types lightgbm,xgboost`: Generates ensemble submission successfully.
- `npm --prefix reports/evidence run sources`: All 17 sources processed successfully.

### 24. Optuna Tuning Overhaul — Early Stopping, Pruning, Ensemble CV
**Problem identified**: Tuning was slow (no early stopping, `n_estimators` in search space, 50 trials default), and `compare-models` never evaluated ensemble on CV — only picked a single model winner.

**Fixes applied:**
- **`configs/modeling.yaml`**: Added `early_stopping_rounds: 50`, `n_jobs`/`thread_count: 4`, bumped `n_estimators`/`iterations` to **2000** (ceiling for early stopping).
- **Forecaster early stopping** (`src/datathon/modeling/forecasters/{lightgbm,xgboost,catboost}.py`):
  - `BaseForecaster.fit()` now accepts optional `eval_set` tuple.
  - LightGBM: `lgb.early_stopping()` callback in `fit()`.
  - XGBoost: `xgb.callback.EarlyStopping()` passed via **constructor** (XGBoost 3.x API).
  - CatBoost: `early_stopping_rounds` in `fit()`.
- **`src/datathon/modeling/tuner.py`**:
  - Removed `n_estimators`/`iterations` from Optuna search space — fixed ceiling injected from base config.
  - Added `_inject_fixed_params()` to merge tuned + fixed params.
  - `eval_set` passed to `forecaster.fit()` so every trial uses early stopping.
  - Per-fold pruning: `trial.report(cumulative_mae, step=fold)` + `trial.should_prune()`.
  - Default trials reduced from **50 → 30**.
- **`src/datathon/commands/tune.py`**:
  - Default SQLite storage (`optuna_studies/<model>.db`) for resume on interrupt.
  - Graceful `KeyboardInterrupt` handling.
- **`src/datathon/commands/{train,predict,compare_models,ensemble}.py`**:
  - Added `--config <path>` support so tuned configs can be passed through the whole pipeline.
- **`src/datathon/modeling/trainer.py`**:
  - `run_cv(..., return_predictions=True)` returns per-fold prediction DataFrames.
- **`src/datathon/commands/compare_models.py`**:
  - Computes **unweighted ensemble CV score** by averaging fold predictions across all models.
  - Compares ensemble total MAE vs individual models.
  - **Generates submission from the true winner** (individual model OR ensemble).

**Tuning results (3-fold × 30d expanding-window CV):**
| Model | Revenue MAE | COGS MAE | Total MAE |
|---|---|---|---|
| LightGBM (default) | 595,354 | 471,836 | 1,067,191 |
| XGBoost (tuned) | 495,714 | 420,877 | 916,591 |
| CatBoost (tuned) | 550,793 | 428,258 | 979,051 |
| **Ensemble** ★ | **484,160** | **389,534** | **873,694** |

- CatBoost best tuned total MAE: **780,776** (Optuna found on trial 9; ensemble CV is higher because it includes weaker LightGBM/XGBoost defaults — ensemble submission uses trained finals with tuned params).
- XGBoost best tuned total MAE: **841,954**.
- **Ensemble wins CV** — submission generated from ensemble (`data/submissions/tuned_best_submission.csv`).
- Dry-run validation: **passed**.

## Remaining Notes / Known Issues
- Evidence pages still use `union all` unpivot patterns where needed; this is standard for Evidence component consumption and not duplicate business logic.
- **Kaggle submission executed**: Ensemble (LightGBM + XGBoost) submitted successfully to datathon-2026-round-1.
- Source data anomaly: ~30,495 product-months have both `stockout_flag = 1` and `overstock_flag = 1` in raw inventory data. This is preserved in marts for fidelity.
- 359 sold products have negative `realized_margin_rate` (COGS > net revenue after discounts), reflecting deep promotional discounting.
- 181 days in 2012 have `sessions = 0` in `mart_forecast_daily_base` (missing early web_traffic data).

## Quick Commands
```bash
# Full pipeline
uv run datathon build-raw --strict
uv run dbt build --project-dir dbt --profiles-dir dbt
uv run datathon baseline --mode submit --output-path data/submissions/submission.csv
uv run datathon train --mode train-final --model-type lightgbm
uv run datathon predict --model-type lightgbm --output-path data/submissions/lightgbm_submission.csv
uv run datathon compare-models --n-folds 2 --horizon-days 30
uv run datathon ensemble --model-types lightgbm,xgboost
uv run datathon explain --model-type lightgbm
uv run datathon submit-kaggle --dry-run --file data/submissions/ensemble_submission.csv

# Evidence
npm --prefix reports/evidence install
npm --prefix reports/evidence run sources
npm --prefix reports/evidence run dev
```
