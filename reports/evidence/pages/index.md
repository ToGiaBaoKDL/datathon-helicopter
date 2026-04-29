---
title: EDA Hub
---

This Evidence app is connected to the same DuckDB warehouse used by dbt and ML scripts.

## Navigation

### Executive
- [01 Executive Summary](./eda/executive/01-executive-summary)
- [02 Executive KPI Pulse](./eda/executive/02-executive-kpi-pulse)
- [03 Risk Flags](./eda/executive/03-risk-flags)

### Finance
- [01 Revenue and Business Drivers](./eda/finance/01-revenue-and-drivers)
- [02 Payment and Checkout](./eda/finance/02-payment-and-checkout)
- [03 Seasonal Decomposition](./eda/finance/03-seasonal-decomposition)

### Operations
- [01 Fulfillment and Returns](./eda/operations/01-fulfillment-and-returns)
- [02 Geographic Fulfillment](./eda/operations/02-geographic-fulfillment)
- [03 Inventory and Growth Scorecard](./eda/operations/03-inventory-and-growth-scorecard)

### Marketing
- [01 Conversion Funnel](./eda/marketing/01-conversion-funnel)
- [02 Promotion Effectiveness](./eda/marketing/02-promotion-effectiveness)

### Customer
- [01 Customer Cohort and RFM](./eda/customer/01-customer-cohort-and-rfm)

### Product
- [01 Product Lifecycle and Health](./eda/product/01-product-lifecycle-and-health)
- [02 Category and Region Performance](./eda/product/02-category-and-region-performance)
- [03 Reviews and Quality](./eda/product/03-reviews-and-quality)

### Business Stories — Marketing
- [01 The Demand Capture Crisis](./stories/marketing/01-demand-capture-crisis)
- [02 The Promo Paradox](./stories/marketing/02-promo-paradox)
- [03 The Cannibalization Test](./stories/marketing/03-cannibalization-test)
- [04 The Seasonality Paradox](./stories/marketing/04-seasonality-paradox)
- [05 The Discount Calendar Ritual](./stories/marketing/05-discount-calendar-ritual)
- [06 The Device Blind Spot](./stories/marketing/06-device-blind-spot)

### Business Stories — Customer
- [01 The Retention Trap](./stories/customer/01-retention-trap)
- [02 RFM — Who Pays the Bills?](./stories/customer/02-rfm-who-pays)
- [03 The Unit Economics Map](./stories/customer/03-unit-economics-map)

### Business Stories — Product
- [01 The Inventory Capital Trap](./stories/product/01-inventory-capital-trap)
- [02 The Profitability Leak](./stories/product/02-profitability-leak)
- [03 Quality Before Growth](./stories/product/03-quality-before-growth)
- [04 The Portfolio Drift](./stories/product/04-portfolio-drift)

### Business Stories — Operations
- [01 The Geographic Cost Puzzle](./stories/operations/01-geographic-cost-puzzle)
- [02 The COD Tax](./stories/operations/02-cod-tax)
- [03 The Risk Flag Convergence](./stories/operations/03-risk-flag-convergence)
- [04 The Shipment Blind Spot](./stories/operations/04-shipment-blind-spot)

### Business Stories — Finance
- [01 The Revenue Anatomy](./stories/finance/01-revenue-anatomy)
- [02 The Capital Lock-Up](./stories/finance/02-capital-lock-up)

### Appendix
- [01 Forecast Feature Health](./eda/appendix/01-forecast-feature-health)
- [02 MCQ Metrics](./eda/appendix/02-mcq-metrics)

## Data Build Order

Run these commands from repository root before opening this app:

```bash
uv run datathon build-raw --strict
uv run dbt build --project-dir dbt --profiles-dir dbt
npm --prefix reports/evidence run sources
```
