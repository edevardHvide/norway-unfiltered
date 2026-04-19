---
name: bearingpoint-brand
description: Apply BearingPoint's official brand colors and typography to any artifact in this repo (HTML reports, Streamlit dashboards, slides, plots). Use when generating visual outputs that should follow BearingPoint design — alternative to SSB's official styling for non-public-stats deliverables.
---

# BearingPoint Brand Styling

Use this skill when producing artifacts (HTML reports, Streamlit dashboards, plots, slides) that should follow BearingPoint's official brand identity.

## When to apply

- **Default for this repo's generated artifacts** — all `output/reports/` and `output/dashboards/` use BP brand. Data attribution still names SSB; visual identity is BearingPoint.
- Internal BearingPoint-branded deliverables, slides, client decks
- When the user explicitly asks for "BearingPoint styling" or "BP brand"

For chart-type **selection** (line vs bar vs donut etc.) and statistical-integrity rules, defer to `ssb-dataviz`. This skill controls the **visual layer** (palette, fonts, spacing) — `ssb-dataviz` informs **chart choice**.

## Colors

### Text & background

| Token | Hex | Role |
|---|---|---|
| Dark 1 | `#000000` | Primary text; dark backgrounds |
| Light 1 | `#FFFFFF` | Light backgrounds; text on dark |
| Dark 2 | `#421799` | Purple brand color |
| Light 2 | `#FAF8F7` | Warm light background |

### Accents

| Token | Hex | Role |
|---|---|---|
| Accent 1 | `#99171D` | Deep red — primary accent |
| Accent 2 | `#FF787A` | Coral |
| Accent 3 | `#FFB1B5` | Soft pink |
| Accent 4 | `#806659` | Warm brown |
| Accent 5 | `#B2A59F` | Taupe / gray |

### Links

| State | Hex |
|---|---|
| Hyperlink | `#A070FF` |
| Followed | `#421799` |

## Typography

- **Headings**: Aptos Display (fallback: Calibri, then `sans-serif`)
- **Body**: Aptos (fallback: Calibri, then `sans-serif`)

## CSS variables (drop-in)

```css
:root {
  --bp-dark-1: #000000;
  --bp-light-1: #FFFFFF;
  --bp-dark-2: #421799;
  --bp-light-2: #FAF8F7;
  --bp-accent-1: #99171D;
  --bp-accent-2: #FF787A;
  --bp-accent-3: #FFB1B5;
  --bp-accent-4: #806659;
  --bp-accent-5: #B2A59F;
  --bp-link: #A070FF;
  --bp-link-visited: #421799;
  --bp-font-heading: 'Aptos Display', Calibri, sans-serif;
  --bp-font-body: 'Aptos', Calibri, sans-serif;
}
```

## Application rules

- **Categorical chart palette order**: Accent 1 → Accent 2 → Dark 2 → Accent 4 → Accent 5 → Accent 3
- **Single-series highlight color**: Accent 1 (`#99171D`) on Light 2 background, or Light 1 on Dark 2 background
- **Maximum 6 categories** per chart; group rest as "Other" in Accent 5 (taupe)
- **Headings**: Aptos Display, weight 700 for primary, 600 for secondary
- **Body text on light**: Dark 1 on Light 2; minimum 14px
- **Body text on dark**: Light 1 on Dark 2; minimum 14px
- **Links**: underline on hover, no underline at rest, `--bp-link` color
- **Aptos font** is not on Google Fonts; for web embed use Microsoft's CDN or fall back to Calibri/system sans

## Do not

- Mix BearingPoint palette with SSB palette in the same artifact (pick one)
- Use Accent 1 (red) and Accent 2 (coral) on adjacent series — they read as a single hue at distance
- Drop the SSB source attribution from charts that use SSB data — visual styling is BP, but data provenance must remain SSB
