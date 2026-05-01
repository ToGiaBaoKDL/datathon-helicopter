---
title: EDA Hub
---

This Evidence app is connected to the same DuckDB warehouse used by dbt and ML scripts.

## Navigation

### Business Stories — Executive
- [00 The State of the Business](./01-stories/00-the-state-of-the-business)
- [The 2019 Cliff](./01-stories/the-2019-cliff)

### Business Stories — Marketing
- [01 The Demand Capture Crisis](./01-stories/marketing/01-demand-capture-crisis)
- [02 The Promo Paradox](./01-stories/marketing/02-promo-paradox)
- [03 The Cannibalization Test](./01-stories/marketing/03-cannibalization-test)
- [04 The Seasonality Paradox](./01-stories/marketing/04-seasonality-paradox)
- [05 The Discount Calendar Ritual](./01-stories/marketing/05-discount-calendar-ritual)
- [06 The Device Blind Spot](./01-stories/marketing/06-device-blind-spot)

### Business Stories — Customer
- [01 The Retention Trap](./01-stories/customer/01-retention-trap)
- [02 RFM — Who Pays the Bills?](./01-stories/customer/02-rfm-who-pays)
- [03 The Unit Economics Map](./01-stories/customer/03-unit-economics-map)

### Business Stories — Product
- [01 The Inventory Capital Trap](./01-stories/product/01-inventory-capital-trap)
- [02 The Profitability Leak](./01-stories/product/02-profitability-leak)
- [03 Quality Before Growth](./01-stories/product/03-quality-before-growth)
- [04 The Portfolio Drift](./01-stories/product/04-portfolio-drift)

### Business Stories — Operations
- [01 The Geographic Cost Puzzle](./01-stories/operations/01-geographic-cost-puzzle)
- [02 The COD Tax](./01-stories/operations/02-cod-tax)
- [03 The Risk Flag Convergence](./01-stories/operations/03-risk-flag-convergence)
- [04 The Shipment Blind Spot](./01-stories/operations/04-shipment-blind-spot)

### Business Stories — Finance
- [01 The Revenue Anatomy](./01-stories/finance/01-revenue-anatomy)

### EDA — Executive
- [01 Executive KPI Pulse](./02-eda/executive/02-executive-kpi-pulse)
- [02 Risk Flags](./02-eda/executive/03-risk-flags)

### EDA — Finance
- [01 Revenue and Business Drivers](./02-eda/finance/01-revenue-and-drivers)
- [02 Payment and Checkout](./02-eda/finance/02-payment-and-checkout)
- [03 Seasonal Decomposition](./02-eda/finance/03-seasonal-decomposition)

### EDA — Operations
- [01 Fulfillment and Returns](./02-eda/operations/01-fulfillment-and-returns)
- [02 Geographic Fulfillment](./02-eda/operations/02-geographic-fulfillment)
- [03 Inventory and Growth Scorecard](./02-eda/operations/03-inventory-and-growth-scorecard)

### EDA — Marketing
- [01 Conversion Funnel](./02-eda/marketing/01-conversion-funnel)
- [02 Promotion Effectiveness](./02-eda/marketing/02-promotion-effectiveness)

### EDA — Customer
- [01 Customer Cohort and RFM](./02-eda/customer/01-customer-cohort-and-rfm)

### EDA — Product
- [01 Product Lifecycle and Health](./02-eda/product/01-product-lifecycle-and-health)
- [02 Category and Region Performance](./02-eda/product/02-category-and-region-performance)
- [03 Reviews and Quality](./02-eda/product/03-reviews-and-quality)

### Appendix
- [01 Forecast Feature Health](./02-eda/appendix/01-forecast-feature-health)
- [02 MCQ Metrics](./02-eda/appendix/02-mcq-metrics)

## Data Build Order

Run these commands from repository root before opening this app:

```bash
uv run datathon build-raw --strict
uv run dbt build --project-dir dbt --profiles-dir dbt
npm --prefix reports/evidence run sources
```
