# Palette + Chart Selection Reference (BP brand applied to SSB data)

Self-contained reference for the report generator. Mirrors `bearingpoint-brand` (visual layer) and `ssb-dataviz` (chart selection); the report-generator skill points here so Claude has one place to look during artifact generation.

## Categorical palette (rank order — use in this order)

| Rank | Token | Hex |
|---|---|---|
| 1 | Accent 1 (Deep red) | `#99171D` |
| 2 | Accent 2 (Coral) | `#FF787A` |
| 3 | Dark 2 (Purple) | `#421799` |
| 4 | Accent 4 (Brown) | `#806659` |
| 5 | Accent 5 (Taupe) | `#B2A59F` |
| 6 | Accent 3 (Soft pink) | `#FFB1B5` |

**Rules:**
- Max 6 categories. Group the rest as "Andre" in Accent 5 (`#B2A59F`).
- Never put Accent 1 + Accent 2 on adjacent series (they read as one hue at distance — interleave with Dark 2 or Accent 4).
- Single-series highlight: Accent 1 (`#99171D`).

## Backgrounds + text

- Page background: Light 2 (`#FAF8F7`)
- Primary text: Dark 1 (`#000000`)
- Source/footnote text: Accent 5 (`#B2A59F`)
- Dark mode (optional): Dark 2 (`#421799`) bg + Light 1 (`#FFFFFF`) text

## Typography

- Headings: Aptos Display, fallback Calibri, then `sans-serif`
- Body: Aptos, fallback Calibri, then `sans-serif`

## Chart-type selection

| Goal | Chart | Avoid |
|---|---|---|
| Trend over time | `line` | bar w/ many periods, pie |
| Compare categories | `horizontal_bar` (sorted) | unsorted bars, pie |
| Part of whole (≤5) | `donut` | pie, donut w/ >5 segments |
| Ranking | `horizontal_bar` (sorted desc) | unsorted |
| Geographic | `map` (choropleth) | bar w/ 400 kommune names |
| Single KPI | `scorecard` | chart for one number |
| Fallback | `table` | — |

**Always avoid:** 3D effects, dual y-axes, pie charts (use donut), truncated y-axis on bars, heavy gridlines.

**Statistical integrity (per ssb-dataviz):**
- Y-axis on bars starts at 0
- Time series have even intervals
- Always show units + measurement period
- Source attribution required: `Kilde: SSB, tabell {table_id}. Sist oppdatert: {date}.`
