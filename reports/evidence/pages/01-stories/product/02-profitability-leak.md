---
title: The Profitability Leak
---

<Alert status="warning">
<b>The question:</b> <Value data={negative_margin_count} column=negative_margin_products fmt=0/> sold products have negative realized margin — meaning every sale destroys value. 
Which categories are bleeding the most? How much revenue is at risk?
</Alert>

```sql negative_margin_count
select count(*) as negative_margin_products
from datathon_warehouse.mart_product_lifetime_performance
where realized_margin_rate < 0
  and lifecycle_stage != 'never_sold'
```

```sql negative_margin_by_category
select
    category,
    count(*) as negative_skus,
    round(sum(total_revenue), 0) as at_risk_revenue,
    round(avg(realized_margin_rate), 4) as avg_margin_rate
from datathon_warehouse.mart_product_lifetime_performance
where realized_margin_rate < 0
  and lifecycle_stage != 'never_sold'
group by 1
order by negative_skus desc
```

```sql category_margin_overview
select
    category,
    round(avg(realized_margin_rate), 4) as avg_margin_rate,
    count(*) as total_skus
from datathon_warehouse.mart_product_lifetime_performance
where lifecycle_stage != 'never_sold'
group by 1
order by avg_margin_rate desc
```

```sql negative_margin_lifecycle
select
    lifecycle_stage,
    category,
    count(*) as negative_skus,
    round(sum(total_revenue), 0) as at_risk_revenue
from datathon_warehouse.mart_product_lifetime_performance
where realized_margin_rate < 0
  and lifecycle_stage != 'never_sold'
group by 1, 2
order by at_risk_revenue desc
```

```sql total_at_risk_revenue
select
    round(sum(total_revenue), 0) as total_at_risk_revenue
from datathon_warehouse.mart_product_lifetime_performance
where realized_margin_rate < 0
  and lifecycle_stage != 'never_sold'
```

```sql negative_margin_pct
select
    round(
        count(*)::double
        / (select count(*) from datathon_warehouse.mart_product_lifetime_performance where lifecycle_stage != 'never_sold'),
        4
    ) as pct
from datathon_warehouse.mart_product_lifetime_performance
where realized_margin_rate < 0
  and lifecycle_stage != 'never_sold'
```

```sql active_negative_count
select count(*) as active_negative_skus
from datathon_warehouse.mart_product_lifetime_performance
where realized_margin_rate < 0
  and lifecycle_stage = 'active'
```

```sql margin_revenue_scatter
select
    product_name,
    category,
    round(total_revenue, 0) as total_revenue,
    round(realized_margin_rate, 4) as realized_margin_rate,
    total_units_sold
from datathon_warehouse.mart_product_lifetime_performance
where lifecycle_stage != 'never_sold'
  and total_revenue > 0
order by total_revenue desc
limit 100
```

```sql what_if_delist
with active_negative as (
    select
        sum(total_revenue) as revenue_lost,
        round(sum(total_revenue * realized_margin_rate), 0) as gross_profit_lost
    from datathon_warehouse.mart_product_lifetime_performance
    where realized_margin_rate < 0
      and lifecycle_stage = 'active'
),
total_revenue as (
    select sum(total_revenue) as all_revenue
    from datathon_warehouse.mart_product_lifetime_performance
    where lifecycle_stage != 'never_sold'
)
select
    revenue_lost,
    gross_profit_lost,
    -gross_profit_lost as loss_prevented,
    round(gross_profit_lost::double / nullif(revenue_lost, 0), 4) as avg_loss_rate,
    round(revenue_lost::double / nullif(all_revenue, 0), 4) as pct_of_total_revenue
from active_negative, total_revenue
```

## 1. The Count: Hundreds of Loss-Making SKUs

<Alert status="info">
<Value data={negative_margin_count} column=negative_margin_products fmt=0/> products sell below cost. 
Every transaction on these SKUs deepens the loss. 
<Value data={active_negative_count} column=active_negative_skus fmt=0/> of them are still labeled <b>active</b> — meaning they are actively replenished and promoted.
</Alert>

<Grid cols=2>
    <BigValue
        data={negative_margin_count}
        value=negative_margin_products
        title="Negative-Margin Products"
        fmt="0"
    />
    <BigValue
        data={negative_margin_pct}
        value=pct
        title="Share of Total SKU Base"
        fmt="pct2"
    />
</Grid>

## 2. Category Breakdown: Where the Bleeding Is Concentrated

<Alert status="info">
Negative-margin products are not evenly distributed. Some categories have a structural pricing or COGS problem. 
The chart below shows which categories host the most loss-making SKUs.
</Alert>

<BarChart
    data={negative_margin_by_category}
    x=category
    y=negative_skus
    title="Negative-Margin SKU Count by Category"
    subtitle="Loss-making SKU count by category"
    yAxisTitle="SKUs"
    yFmt="0"
/>

<BarChart
    data={negative_margin_by_category}
    x=category
    y=at_risk_revenue
    title="At-Risk Revenue by Category"
    subtitle="At-risk revenue from negative-margin SKUs by category"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
/>

## 3. Category Margin: Benchmark Against 15% Target

<Alert status="info">
The healthy target for realized margin is <b>15%</b> (industry benchmark). Most categories fall below this. 
The category with the most negative-margin SKUs may not be the lowest-margin category overall — it may simply be the largest.
</Alert>

<BarChart
    data={category_margin_overview}
    x=category
    y=avg_margin_rate
    title="Average Realized Margin Rate by Category"
    subtitle="Negative values = category average is loss-making"
    yAxisTitle="Margin Rate"
    yFmt="pct2"
>
    <ReferenceLine y=0.15 label="15% Target" hideValue=true color=positive lineType=dashed/>
    <ReferenceLine y=0 label="Break-even" hideValue=true color=negative/>
</BarChart>

<Alert status="info">
The bubble chart below maps every non-never_sold product. 
X-axis = realized margin rate; Y-axis = total revenue; bubble size = units sold; color = category.
The danger zone is bottom-right: high revenue but negative margin — these are the portfolio killers.
</Alert>

<BubbleChart
    data={margin_revenue_scatter}
    x=realized_margin_rate
    y=total_revenue
    series=category
    size=total_units_sold
    title="Product Margin vs Revenue"
    subtitle="High-revenue + negative-margin = portfolio killers. Top-left = efficient winners."
    xAxisTitle="Realized Margin Rate"
    yAxisTitle="Total Revenue"
    xFmt="pct2"
    yFmt="num0"
>
    <ReferenceLine y=0 label="Break-even" hideValue=true color=negative/>
    <ReferenceLine x=0.15 label="15% Target" hideValue=true color=positive lineType=dashed/>
</BubbleChart>

## 4. Lifecycle × Category: Active + Negative = Immediate Delist Candidates

<Alert status="info">
<Value data={total_at_risk_revenue} column=total_at_risk_revenue fmt=num0/> VND in lifetime revenue comes from negative-margin SKUs.
Active products in this list should be delisted immediately — they destroy value on every sale.
</Alert>

<DataTable
    data={negative_margin_lifecycle}
    rows=10
>
    <Column id=lifecycle_stage title="Lifecycle"/>
    <Column id=category title="Category"/>
    <Column id=negative_skus title="Loss SKUs" fmt=0/>
    <Column id=at_risk_revenue title="At-Risk Revenue" fmt=num0/>
</DataTable>

## 5. What-If: Delist All Active + Negative SKUs

<Alert status="info">
Delisting <Value data={active_negative_count} column=active_negative_skus fmt=0/> active+negative SKUs would sacrifice
<Value data={what_if_delist} column=revenue_lost fmt=num0/> VND in revenue.
However, those SKUs currently lose <Value data={what_if_delist} column=gross_profit_lost fmt=num0/> VND in gross profit —
so delisting <b>saves <Value data={what_if_delist} column=loss_prevented fmt=num0/> VND</b> in destroyed value.
That revenue represents only <Value data={what_if_delist} column=pct_of_total_revenue fmt=pct2/> of total lifetime revenue.
</Alert>

<Grid cols=3>
    <BigValue
        data={what_if_delist}
        value=revenue_lost
        title="Revenue Sacrificed"
        fmt="num0"
    />
    <BigValue
        data={what_if_delist}
        value=loss_prevented
        title="Loss Prevented"
        fmt="num0"
    />
    <BigValue
        data={what_if_delist}
        value=pct_of_total_revenue
        title="% of Total Revenue"
        fmt="pct2"
    />
</Grid>

## The Verdict

<Alert status="positive">
<b>Action:</b> Immediate delist for <Value data={active_negative_count} column=active_negative_skus fmt=0/> active+negative margin SKUs. 
Review pricing strategy for categories with structural margin deficits. 
<Value data={total_at_risk_revenue} column=total_at_risk_revenue fmt=num0/> VND in at-risk revenue must be turned around or written off.
</Alert>

## Deep Dive

- [Product Lifecycle And Health](/02-eda/product/01-product-lifecycle-and-health)
- [Reviews And Quality](/02-eda/product/03-reviews-and-quality)

