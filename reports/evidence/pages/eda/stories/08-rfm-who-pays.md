---
title: RFM — Who Pays the Bills?
---

# RFM — Who Pays the Bills?

<Alert status="warning">
<b>The question:</b> What share of revenue does the top 10% of customers generate? 
Are "At Risk" customers worth saving? RFM segmentation reveals who really drives the business.
</Alert>

```sql revenue_pareto
with customer_deciles as (
    select
        customer_id,
        total_revenue,
        ntile(10) over (order by total_revenue desc) as decile
    from datathon_warehouse.mart_customer_rfm
)
select
    decile,
    round(sum(total_revenue), 0) as decile_revenue,
    count(*) as customers
from customer_deciles
group by 1
order by 1
```

```sql top_10_pct
select
    round(sum(case when decile = 1 then decile_revenue else 0 end)::double / sum(decile_revenue), 4) as top_10_pct
from ${revenue_pareto}
```

```sql top_20_pct
select
    round(sum(case when decile <= 2 then decile_revenue else 0 end)::double / sum(decile_revenue), 4) as top_20_pct
from ${revenue_pareto}
```

```sql rfm_segment_summary
select
    rfm_segment,
    count(*) as customer_count,
    round(sum(total_revenue), 0) as segment_revenue,
    round(avg(total_revenue), 0) as avg_revenue,
    round(avg(total_orders), 1) as avg_orders,
    round(avg(recency_days), 0) as avg_recency
from datathon_warehouse.mart_rfm_segments
group by 1
order by segment_revenue desc
```

```sql clv_tiers
with customer_quartiles as (
    select
        customer_id,
        total_revenue,
        ntile(4) over (order by total_revenue desc) as revenue_quartile
    from datathon_warehouse.mart_customer_rfm
)
select
    case
        when revenue_quartile = 1 then 'Platinum'
        when revenue_quartile = 2 then 'Gold'
        when revenue_quartile = 3 then 'Silver'
        else 'Bronze'
    end as tier,
    round(sum(total_revenue), 0) as tier_revenue,
    count(*) as customers
from customer_quartiles
group by revenue_quartile
order by revenue_quartile
```

```sql at_risk_value
select
    count(*) as at_risk_customers,
    round(sum(total_revenue), 0) as at_risk_revenue,
    round(avg(total_revenue), 0) as avg_at_risk_revenue
from datathon_warehouse.mart_rfm_segments
where rfm_segment = 'At Risk'
```

```sql channel_champions
select
    acquisition_channel,
    count(*) as customer_count
from datathon_warehouse.mart_rfm_segments
where rfm_segment = 'Champions'
group by 1
order by customer_count desc
```

```sql channel_hibernating
select
    acquisition_channel,
    count(*) as customer_count
from datathon_warehouse.mart_rfm_segments
where rfm_segment = 'Hibernating'
group by 1
order by customer_count desc
```

## 1. The Pareto: Top 10% Revenue Concentration

<Alert status="info">
The top decile of customers generates <b><Value data={top_10_pct} column=top_10_pct fmt=pct2/></b> of total revenue.
    The top 20% generates <b><Value data={top_20_pct} column=top_20_pct fmt=pct2/></b>.
Pareto holds strongly — a small base drives the majority of the business.
</Alert>

<BarChart
    data={revenue_pareto}
    x=decile
    y=decile_revenue
    title="Revenue by Customer Decile"
    subtitle="Decile 1 = top 10%. Sharp Pareto concentration"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
/>

## 2. CLV Tiers: Equal Count, Unequal Value

<Alert status="info">
Quartile-based tiers (Platinum/Gold/Silver/Bronze) have equal customer counts but vastly unequal revenue. 
Platinum customers contribute the largest share despite being only 25% of the base.
</Alert>

<BarChart
    data={clv_tiers}
    x=tier
    y=tier_revenue
    title="Revenue Share by CLV Tier"
    subtitle="Platinum (top quartile) dominates total revenue"
    yAxisTitle="Revenue (VND)"
    yFmt="num0"
/>

## 3. RFM Segments: Where the Customers Live

<Alert status="info">
Champions and Loyal customers are the core. At Risk and Hibernating represent sleeping value. 
"Cannot Lose Them" are high-value but inactive — the highest-urgency win-back target.
</Alert>

<BarChart
    data={rfm_segment_summary}
    x=rfm_segment
    y=customer_count
    title="Customer Count by RFM Segment"
    subtitle="Champions and Hibernating are the largest segments"
    yAxisTitle="Customers"
    yFmt="0"
/>

<BarChart
    data={rfm_segment_summary}
    x=rfm_segment
    y=avg_revenue
    title="Average Revenue per Segment"
    subtitle="Cannot Lose Them and Champions have the highest per-customer value"
    yAxisTitle="Avg Revenue (VND)"
    yFmt="num0"
/>

## 4. At Risk: Substantial Sleeping Value

<Alert status="info">
<Value data={at_risk_value} column=at_risk_customers fmt=0/> customers are "At Risk". 
They generated <Value data={at_risk_value} column=at_risk_revenue fmt=num0/> VND in lifetime revenue — 
an average of <Value data={at_risk_value} column=avg_at_risk_revenue fmt=num0/> VND each. 
Win-back campaigns here have high expected ROI.
</Alert>

<Grid cols=3>
    <BigValue
        data={at_risk_value}
        value=at_risk_customers
        title="At Risk Customers"
        fmt="0"
    />
    <BigValue
        data={at_risk_value}
        value=at_risk_revenue
        title="At Risk Lifetime Revenue"
        fmt="num0"
    />
    <BigValue
        data={at_risk_value}
        value=avg_at_risk_revenue
        title="Avg Revenue per At Risk"
        fmt="num0"
    />
</Grid>

## 5. Channel of Champions vs Hibernating

<Alert status="info">
Where do Champions come from? Where do Hibernating customers come from? 
If Champions cluster in one channel, that channel deserves more budget.
</Alert>

<BarChart
    data={channel_champions}
    x=acquisition_channel
    y=customer_count
    title="Champions by Acquisition Channel"
    subtitle="Organic search is the top source for Champions"
    yAxisTitle="Champions"
    yFmt="0"
/>

<BarChart
    data={channel_hibernating}
    x=acquisition_channel
    y=customer_count
    title="Hibernating by Acquisition Channel"
    subtitle="Organic search also produces the most Hibernating customers"
    yAxisTitle="Hibernating"
    yFmt="0"
/>

## The Verdict

<Alert status="positive">
<b>Action:</b> The top 10% of customers generate <Value data={top_10_pct} column=top_10_pct fmt=pct2/> of revenue. 
Deploy a VIP program for Champions. Launch targeted win-back offers for At Risk (<Value data={at_risk_value} column=at_risk_customers fmt=0/> customers, <Value data={at_risk_value} column=at_risk_revenue fmt=num0/> VND at stake). 
Nurture Potential Loyalists with loyalty-point incentives. Shift acquisition budget toward channels that produce Champions.
</Alert>
