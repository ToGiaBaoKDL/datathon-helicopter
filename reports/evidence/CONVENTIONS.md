# Evidence Dashboard Conventions

## SQL Placement
- All sql blocks must appear before the first section header (## ) on the page.
- Keep SQL at the top; filters (DateRange, Dropdown) immediately after the last SQL block and before the first ## heading.

## Percent Format (CRITICAL)
- Always use fmt=pct2 for percentage values (2 decimal places, e.g. 12.90%).
- Never use fmt=pct1, fmt=pct, fmt=pct0, fmt=0.0%, fmt=0.00%, yFmt=0.0%, etc.
- SQL must NOT multiply by 100. Store ratios as 0..1 in SQL; let pct2 handle the rendering.
  - Good: round(sum(x)::double / nullif(sum(y), 0), 4) + fmt=pct2
  - Bad:  round(sum(x) * 100.0 / sum(y), 1) + fmt=num1/>%

## Multiply / Ratio Format
- Use fmt=0.0x for ratios like 2.0x, 11.7x.
- Do NOT add an extra x after the </Value> tag. The x suffix is already built into the format.
  - Good: <Value data={roi} column=ratio fmt=0.0x/>
  - Bad:  <Value data={roi} column=ratio fmt=0.0x/>x

## HTML Tag Safety
- Do not use raw > or < in plain text outside of HTML/XML tags.
  - Good: discount above 10%, more than 2x credit card
  - Bad:  discount >10%, >2x credit card

## Subtitles — Insight-Driven
- Subtitles must contain a clear insight or data point, not just a generic chart description.
  - Good: Retention drops to ~3.5% by month 1 then flatlines
  - Good: Fixed: 1.2% avg discount vs 12.9% for percentage
  - Bad:  Revenue by promotion type
  - Bad:  Retention rate by cohort age
- Use hardcoded numbers when the insight is verified and subtitle cannot accept <Value> tags.
- Keep subtitle under 12 words if possible.

## Dynamic Values — Zero Hardcode in Insight Text
- Every number in Alert text and body paragraphs must use <Value data={query} column=col fmt=.../>.
- No hardcoded statistics in Alert paragraphs.

## Story Page Rules
- No filters (DateRange, Dropdown) inside story pages. Narratives are fixed.
- Structure: Hook (Alert warning) -> Evidence (3-5 charts) -> Insight (Alert info) -> Action (Alert positive).

## ECharts
- Use inline config={{...}} object directly on the <ECharts/> tag.
- Do not use <script> const x = {...} </script> + <ECharts config={x}/> -- this fails in Evidence.

## DataTable
- Always set rows=10 explicitly on <DataTable>.

## General
- title = Noun phrase (metric + dimension)
- subtitle = Short insight with a data point (max 12 words)
- yAxisTitle / xAxisTitle = Clear unit labels
