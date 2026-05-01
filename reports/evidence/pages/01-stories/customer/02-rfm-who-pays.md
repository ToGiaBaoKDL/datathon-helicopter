---
title: RFM — Who Pays the Bills?
---

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

```sql recency_distribution
select
    case
        when recency_days <= 30 then '0-30 days'
        when recency_days <= 90 then '31-90 days'
        when recency_days <= 180 then '91-180 days'
        when recency_days <= 365 then '181-365 days'
        else '365+ days'
    end as recency_bucket,
    count(*) as customers,
    round(avg(total_revenue), 0) as avg_revenue
from datathon_warehouse.mart_customer_rfm
group by 1
order by 1
```

```sql platinum_bronze
with quartiles as (
    select
        customer_id,
        total_revenue,
        ntile(4) over (order by total_revenue desc) as quartile
    from datathon_warehouse.mart_customer_rfm
)
select
    round(sum(case when quartile = 1 then total_revenue else 0 end)::double / sum(total_revenue), 4) as platinum_share,
    round(sum(case when quartile = 4 then total_revenue else 0 end)::double / sum(total_revenue), 4) as bronze_share,
    count(case when quartile = 1 then 1 end) as platinum_customers,
    count(case when quartile = 4 then 1 end) as bronze_customers
from quartiles
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

### Platinum vs Bronze: Revenue Concentration

<Alert status="info">
Platinum (top quartile, <Value data={platinum_bronze} column=platinum_customers fmt=0/> customers) generates <Value data={platinum_bronze} column=platinum_share fmt=pct2/> of total revenue.
Bronze (bottom quartile, <Value data={platinum_bronze} column=bronze_customers fmt=0/> customers) contributes only <Value data={platinum_bronze} column=bronze_share fmt=pct2/>.
The gap is massive — a few customers carry most of the business.
</Alert>

<Grid cols=2>
    <BigValue
        data={platinum_bronze}
        value=platinum_share
        title="Platinum Revenue Share"
        fmt="pct2"
    />
    <BigValue
        data={platinum_bronze}
        value=bronze_share
        title="Bronze Revenue Share"
        fmt="pct2"
    />
</Grid>

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

## 2.5. CLV Tier Distribution

<Alert status="info">
CLV tiers follow a classic Pareto pattern. Platinum (top 25%) generates the majority of revenue
while Bronze (bottom 25%) contributes minimally. The donut visualises this concentration.
</Alert>

<ECharts config={
    {
        title: {
            text: 'CLV Tier Revenue Share',
            subtext: 'Platinum dominates — classic Pareto concentration',
            left: 'center'
        },
        tooltip: {
            formatter: '{b}: {c} ({d}%)'
        },
        series: [
            {
                type: 'pie',
                radius: ['40%', '70%'],
                data: [...clv_donut],
            }
        ]
    }
}/>

## 3. RFM Segments: Where the Customers Live

<Alert status="info">
Champions and Loyal customers are the core. At Risk and Hibernating represent sleeping value. 
"Cannot Lose Them" are high-value but inactive — the highest-urgency win-back target.
</Alert>

<BarChart
    data={rfm_segment_summary}
    x=rfm_segment
    y=customer_count
    swapXY=true
    title="Customer Count by RFM Segment"
    subtitle="Champions and Hibernating are the largest segments"
    yAxisTitle="Customers"
    yFmt="0"
/>

<BarChart
    data={rfm_segment_summary}
    x=rfm_segment
    y=avg_revenue
    swapXY=true
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

## 4.5. Churn Risk Segments

<Alert status="info">
<Value data={churn_risk_total} column=churned_customers fmt=0/> customers are "Churned" — no order in 2× their normal gap.
<Value data={churn_risk_total} column=single_order_customers fmt=0/> are "Single Order" — never returned after first purchase.
These are distinct problems requiring different tactics.
</Alert>

<Grid cols=4>
    <BigValue
        data={churn_risk_total}
        value=active_customers
        title="Active Customers"
        fmt="0"
    />
    <BigValue
        data={churn_risk_total}
        value=at_risk_customers
        title="At Risk Customers"
        fmt="0"
    />
    <BigValue
        data={churn_risk_total}
        value=churned_customers
        title="Churned Customers"
        fmt="0"
    />
    <BigValue
        data={churn_risk_total}
        value=single_order_customers
        title="Single-Order Customers"
        fmt="0"
    />
</Grid>

<BarChart
    data={churn_risk}
    x=churn_risk
    y=customers
    swapXY=true
    title="Customer Count by Churn Risk"
    subtitle="Based on recency vs historical ordering gap"
    yAxisTitle="Customers"
    yFmt="0"
/>

<BarChart
    data={churn_risk}
    x=churn_risk
    y=avg_revenue
    swapXY=true
    title="Average Lifetime Revenue by Churn Risk"
    subtitle="Revenue at stake in each segment"
    yAxisTitle="Avg Revenue (VND)"
    yFmt="num0"
/>

## 4.6. Top Customers by Revenue

<Alert status="info">
The highest-value customers deserve VIP treatment. Monitor their recency and purchase frequency
to prevent churn at the top of the revenue pyramid.
</Alert>

<DataTable data={top_customers} rows=10>
    <Column id=customer_id title="Customer"/>
    <Column id=acquisition_channel title="Channel"/>
    <Column id=age_group title="Age"/>
    <Column id=total_orders title="Orders" fmt=0/>
    <Column id=total_revenue title="Revenue" fmt=num0/>
    <Column id=recency_days title="Recency" fmt=0/>
    <Column id=avg_gap title="Avg Gap" fmt=0/>
</DataTable>

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

```sql rfm_channel_matrix
select
    rfm_segment,
    acquisition_channel,
    count(*) as customer_count
from datathon_warehouse.mart_rfm_segments
group by 1, 2
order by 1, 2
```

```sql clv_donut
select
    tier as name,
    round(tier_revenue::double / sum(tier_revenue) over (), 4) as value
from ${clv_tiers}
```

```sql churn_risk_total
select
    sum(case when recency_days > 2 * avg_days_between_orders then 1 else 0 end) as churned_customers,
    sum(case when avg_days_between_orders is null then 1 else 0 end) as single_order_customers,
    sum(case when recency_days <= avg_days_between_orders then 1 else 0 end) as active_customers,
    sum(case when avg_days_between_orders is not null and recency_days > avg_days_between_orders and recency_days <= 2 * avg_days_between_orders then 1 else 0 end) as at_risk_customers,
    count(*) as total_customers
from datathon_warehouse.mart_customer_rfm
```

```sql churn_risk
select
    case
        when avg_days_between_orders is null then 'Single Order'
        when recency_days <= avg_days_between_orders then 'Active'
        when recency_days <= 2 * avg_days_between_orders then 'At Risk'
        else 'Churned'
    end as churn_risk,
    count(*) as customers,
    avg(total_revenue) as avg_revenue,
    avg(recency_days) as avg_recency
from datathon_warehouse.mart_customer_rfm
group by churn_risk
order by avg_recency
```

```sql top_customers
select
    customer_id,
    acquisition_channel,
    age_group,
    total_orders,
    total_revenue,
    recency_days,
    avg_days_between_orders as avg_gap
from datathon_warehouse.mart_customer_rfm
order by total_revenue desc
limit 10
```

## 6. Recency: How Recently Did They Buy?

<Alert status="info">
Recency reveals how active the customer base is. A concentration in "365+ days" means most customers are dormant.
A concentration in "0-30 days" indicates a healthy, recently engaged base.
</Alert>

<BarChart
    data={recency_distribution}
    x=recency_bucket
    y=customers
    title="Customer Recency Distribution"
    subtitle="How recently customers placed their last order — recency is the strongest churn predictor"
    yAxisTitle="Customers"
    yFmt="num0"
/>

<BarChart
    data={recency_distribution}
    x=recency_bucket
    y=avg_revenue
    title="Average Revenue by Recency Bucket"
    subtitle="Do dormant customers have different value profiles?"
    yAxisTitle="Avg Revenue (VND)"
    yFmt="num0"
/>

<Alert status="info">
The matrix below maps every RFM segment against every acquisition channel.
Dark cells reveal where each segment concentrates. 
The Organic Paradox is visible: organic search produces both Champions (high-value, active) and Hibernating (low-value, inactive) in large numbers.
</Alert>

<Heatmap
    data={rfm_channel_matrix}
    x=acquisition_channel
    y=rfm_segment
    value=customer_count
    title="RFM Segment by Acquisition Channel"
    subtitle="Customer count heatmap — reveals channel-quality patterns"
    valueFmt="0"
/>

## 6. What-If: Win Back 10% of At-Risk Customers

<Alert status="info">
At Risk customers generated <b><Value data={at_risk_value} column=at_risk_revenue fmt=num0/></b> VND in lifetime revenue
(<Value data={at_risk_value} column=at_risk_customers fmt=0/> customers).
If a win-back campaign recovers 10% of them,
that is <b><Value data={what_if_winback} column=recovered_customers fmt=0/></b> customers recovered
and <b><Value data={what_if_winback} column=recovered_revenue fmt=num0/></b> VND in lifetime value protected.
</Alert>

```sql what_if_winback
select
    round(count(*) * 0.10, 0) as recovered_customers,
    round(avg(total_revenue) * count(*) * 0.10, 0) as recovered_revenue
from datathon_warehouse.mart_customer_rfm
where recency_days > avg_days_between_orders
  and recency_days <= 2 * avg_days_between_orders
```

<Grid cols=2>
    <BigValue
        data={what_if_winback}
        value=recovered_customers
        title="Recovered Customers (10%)"
        fmt="0"
    />
    <BigValue
        data={what_if_winback}
        value=recovered_revenue
        title="Recovered Revenue"
        fmt="num0"
    />
</Grid>

## The Verdict

<Alert status="positive">
<b>Action:</b> The top 10% of customers generate <Value data={top_10_pct} column=top_10_pct fmt=pct2/> of revenue. 
Deploy a VIP program for Champions. Launch targeted win-back offers for At Risk (<Value data={at_risk_value} column=at_risk_customers fmt=0/> customers, <Value data={at_risk_value} column=at_risk_revenue fmt=num0/> VND at stake). 
Nurture Potential Loyalists with loyalty-point incentives. Shift acquisition budget toward channels that produce Champions.
</Alert>

## Deep Dive

- [Customer Cohort And Rfm](/02-eda/customer/01-customer-cohort-and-rfm)

