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

### Finance
- [Revenue and Business Drivers](./eda/finance/revenue-and-drivers)
- [Payment and Checkout](./eda/finance/payment-and-checkout)
- [Seasonal Decomposition](./eda/finance/seasonal-decomposition)

### Operations
- [Fulfillment and Returns](./eda/operations/fulfillment-and-returns)
- [Inventory and Growth Scorecard](./eda/operations/inventory-and-growth-scorecard)
- [Geographic Fulfillment](./eda/operations/geographic-fulfillment)

### Marketing
- [Promotion Effectiveness](./eda/marketing/promotion-effectiveness)
- [Conversion Funnel](./eda/marketing/conversion-funnel)

### Customer
- [Customer Cohort and RFM](./eda/customer/customer-cohort-and-rfm)

### Product
- [Product Lifecycle and Health](./eda/product/product-lifecycle-and-health)
- [Category and Region Performance](./eda/product/category-and-region-performance)
- [Reviews and Quality](./eda/product/reviews-and-quality)

### Business Stories (Narratives)
- [The Demand Capture Crisis](./eda/stories/01-demand-capture-crisis)
- [The Retention Trap](./eda/stories/02-retention-trap)
- [The Promo Paradox](./eda/stories/03-promo-paradox)
- [The Inventory Capital Trap](./eda/stories/04-inventory-capital-trap)
- [The Profitability Leak](./eda/stories/05-profitability-leak)
- [Quality Before Growth](./eda/stories/06-quality-before-growth)
- [The Cannibalization Test](./eda/stories/07-cannibalization-test)
- [RFM — Who Pays the Bills?](./eda/stories/08-rfm-who-pays)
- [The Geographic Cost Puzzle](./eda/stories/09-geographic-cost-puzzle)
- [The COD Tax](./eda/stories/10-cod-tax)
- [The Seasonality Paradox](./eda/stories/11-seasonality-paradox)
- [The Portfolio Drift](./eda/stories/12-portfolio-drift)
- [The Risk Flag Convergence](./eda/stories/13-risk-flag-convergence)
- [The Mobile Conversion Gap](./eda/stories/14-mobile-conversion-gap)

### Appendix
- [Analytical Questions & Findings](./eda/appendix/analytical-questions)
- [Part 1 MCQ Metrics](./eda/appendix/part1-mcq-metrics)
- [Forecast Feature Health](./eda/appendix/forecast-feature-health)

## Data Build Order

Run these commands from repository root before opening this app:

```bash
uv run datathon build-raw --strict
uv run dbt build --project-dir dbt --profiles-dir dbt
npm --prefix reports/evidence run sources
```
