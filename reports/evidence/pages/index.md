---
title: EDA Hub
---

# EDA Hub

This Evidence app is connected to the same DuckDB warehouse used by dbt and ML scripts.

## Navigation

### Executive
- [Executive Summary](./eda/executive/executive-summary)
- [Executive KPI Pulse](./eda/executive/executive-kpi-pulse)
- [Risk Flags](./eda/executive/risk-flags)
- [Part 1 MCQ Metrics](./eda/executive/part1-mcq-metrics)

### Finance
- [Revenue and Business Drivers](./eda/finance/revenue-and-drivers)
- [Forecast Feature Health](./eda/finance/forecast-feature-health)

### Operations
- [Fulfillment and Returns](./eda/operations/fulfillment-and-returns)
- [Inventory and Growth Scorecard](./eda/operations/inventory-and-growth-scorecard)

### Marketing
- [Promotion Effectiveness](./eda/marketing/promotion-effectiveness)

### Customer
- [Customer Cohort and RFM](./eda/customer/customer-cohort-and-rfm)

### Product
- [Product Lifecycle and Health](./eda/product/product-lifecycle-and-health)
- [Category and Region Performance](./eda/product/category-and-region-performance)

## Data Build Order

Run these commands from repository root before opening this app:

```bash
uv run datathon build-raw --strict
uv run dbt build --project-dir dbt --profiles-dir dbt
npm --prefix reports/evidence run sources
```
