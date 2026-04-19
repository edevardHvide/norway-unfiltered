---
name: ssb-report-generator
description: Generate a HTML report or Streamlit dashboard from Norwegian public statistics (SSB) in this repo. Use when the user asks for a report, dashboard, visualization, or analysis of SSB data — phrases like "lag rapport om", "make a report on", "vis stats om", "lag dashboard for", "visualiser", "interaktiv". Triggers in this repo only; orchestrates ssb-api + bearingpoint-brand skills and writes artifacts to output/.
---

# SSB Report Generator

Generate a HTML report or Streamlit dashboard from Norwegian public statistics, using the SSB MCP for data and BearingPoint brand for visual identity.

## When to invoke

Auto-trigger on Norwegian-statistics questions in this repo where the user wants a viewable artifact. Phrases that activate:

- "lag rapport om …" / "make a report on …"
- "lag dashboard for …" / "make a dashboard for …"
- "vis statistikk for …" / "show stats on …"
- "visualiser …" / "interaktiv visning av …"
- Bare data questions ("hvor mange bor i Oslo siste 10 år") where presenting a figure makes sense

If the user only wants a number in chat (no artifact), defer to `ssb-api` and skip this skill.

## Workflow

### 1. Query SSB (delegate to ssb-api skill)

Follow `ssb-api` exactly:
- `ssb_search` to find candidate tables
- `ssb_table_metadata` to inspect variables
- Propose a query in chat: tabell ID, filters, declarative title in Norwegian

### 2. Confirm + decide artifact type

In a single chat message, present:
- The proposed query (table, filters, period)
- The chosen artifact type (HTML report or Streamlit dashboard) with one-line rationale
- A clear yes/no prompt

Decision rule (first match wins):
1. Explicit user phrasing — "rapport"/"report" → HTML; "dashboard"/"interaktiv"/"explore" → Streamlit
2. Single chart conveys the whole answer (KPI, simple trend, one bar chart) → HTML
3. ≥2 dimensions worth filtering OR ≥3 distinct charts → Streamlit
4. Default → HTML

### 3. Fetch data

`ssb_get_data` with the confirmed filters. Save the raw JSON-stat2 response to `output/data/{table_id}__{filter_hash}.json` for debuggability, then convert to a DataFrame and save to `output/data/{table_id}__{filter_hash}.parquet`.

Use `python .claude/skills/ssb-report-generator/scripts/generate.py hash --filters '<json>'` to compute the filter hash. Re-runs check the parquet first; if the user's question includes "refresh"/"oppdater", bypass the cache.

### 4. Compose chart spec

Per `references/palette.md` chart-type matrix:
- Time series (x is year/month) → `line`
- Ranking → `horizontal_bar` (sorted)
- Part-of-whole, ≤5 segments → `donut`
- Many regions → `map`
- Single KPI → `scorecard`
- Fallback → `table`

Title is **declarative** (the insight, not "X over time"). Keep ≤6 categories; group rest as "Andre".

### 5. Generate artifact

```bash
python .claude/skills/ssb-report-generator/scripts/generate.py render \
    --question "<user's NL question>" \
    --table-id <id> \
    --table-title "<title from metadata>" \
    --filters '<canonical-json>' \
    --type html|dashboard \
    --data-file output/data/<id>__<hash>.parquet \
    --chart-spec '<json>' \
    --rationale "<1–3 Norwegian sentences>"
```

`generate.py` produces a slug, renders the right template, writes the artifact, and updates INDEX.md.

**For refresh requests** ("refresh dashboard <slug>", "oppdater rapport <slug>"): look up the original question + filters in `output/INDEX.md` (and the existing artifact for the chart spec if needed), bypass the parquet cache when calling `ssb_get_data`, and pass `--overwrite` to `generate.py render` so the existing slug is reused (no `-2` suffix) and the INDEX row's date advances in place.

### 6. Reply to user

State exactly: artifact path, how to view (open file or `streamlit run …`), and where to find the catalog (`output/INDEX.md`).

## Examples

### "lag rapport om befolkningsutvikling i Oslo siste 10 år"

→ Tabell 07459, Region=0301, Tid=top(10). HTML report. Chart: line. Slug: `befolkningsutvikling-i-oslo-siste-10-ar`.

### "lag interaktivt dashboard for arbeidsledighet per fylke"

→ Tabell 13772, codelist `agg_Fylker2024`, Tid=top(12). Streamlit dashboard. Default chart: horizontal_bar with sidebar period selector. Slug: `arbeidsledighet-per-fylke`.

### "refresh dashboard arbeidsledighet-per-fylke"

→ Look up slug in `output/INDEX.md` to recover original question + filters; bypass cache; re-fetch; re-render same slug.

## Failure modes

- No matching SSB table → tell user, suggest reformulation. Do not generate an empty artifact.
- Empty result set → warn user, suggest broadening filters. Do not generate.
- MCP unavailable → fall back to https://www.ssb.no/statbank link (per `ssb-api` fallback).
- Slug collision after `-9` → ask user for an explicit slug.
- Generator script error → surface stderr; the script writes to a temp file then atomic-renames, so partial artifacts cannot exist.

## Files this skill writes

- `output/data/<table_id>__<hash>.{json,parquet}` — cached SSB data (gitignored)
- `output/reports/<slug>.html` — HTML report (committed)
- `output/dashboards/<slug>/{app.py,README.md}` — Streamlit dashboard (committed)
- `output/INDEX.md` — catalog (committed)

## Related skills

- `ssb-api` — query workflow + filter syntax + common tables (auto-triggered upstream)
- `ssb-dataviz` — chart-type selection + statistical-integrity rules (informational reference)
- `bearingpoint-brand` — visual identity (palette, typography); applied in templates
