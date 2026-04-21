---
title: Part 1 MCQ Metrics
---

# Part 1 - Metric Evidence

```sql mcq_metrics
select *
from datathon_warehouse.mart_part1_mcq_metrics
order by metric_key
```

<DataTable data={mcq_metrics} rows=10 />

## Notes

- This page provides reproducible metrics backing the Part 1 questions.
- It does not auto-select options A/B/C/D; answer mapping should be validated in notebook/report context.
