# Norway Unfiltered — SSB Report Generator Skill

**Date:** 2026-04-19
**Status:** Approved design, awaiting spec review
**Supersedes:** `2026-04-18-nl-ssb-dashboard-design.md`
**Replaces in repo:** Existing `app.py` + `data/*.json` + `render.yaml`

## Problem

The user wants to ask natural-language questions about Norwegian society ("hvor mange bor i Oslo?", "arbeidsledighet per fylke siste år", "import av frukt fra Spania") inside Claude Code and have Claude produce a polished, viewable artifact — either a self-contained HTML report or an interactive Streamlit dashboard — without writing code by hand each time. The existing app is a static, hand-curated Plotly dashboard that requires code edits to add a new statistic; that workflow does not scale and does not capture the user's actual flow (asking questions in Claude Code).

## Goal

A repo-local Claude Code skill (`ssb-report-generator`) that, when triggered by an SSB-question intent in this repo, runs an end-to-end workflow:

1. Use the existing `ssb-api` skill + SSB MCP to find a table, fetch metadata, propose a query
2. Confirm the proposal with the user in chat (single yes/no — Claude Code IS the UI)
3. Fetch data via SSB MCP, save raw JSON-stat2 + a Parquet conversion to `output/data/`
4. Decide whether the answer is best served as an HTML report (single chart, summary) or a Streamlit dashboard (multi-dimensional, exploratory)
5. Render the artifact from a Jinja2 template using SSB's official dataviz palette + typography
6. Update a markdown index of all generated artifacts
7. Tell the user where the artifact lives and how to view it

Everything runs locally. Nothing is hosted. The user interface is Claude Code in this repo. The user must be in this repo for the skill to auto-trigger.

## Non-goals

- Hosting (no Render, Vercel, or any deploy target)
- Multi-user, accounts, auth
- Anthropic API usage (Claude Code subscription powers the agent)
- Streamlit prompt-bar UI (the prompt bar is Claude Code itself)
- PDF export
- Cross-machine sync, history-per-user
- Automatic re-fetch / scheduled refresh
- Browser automation tests

## Architecture

The deliverable is a **skill definition + templates + a small generator helper**, plus convention for where artifacts and cached data live. There is no long-running process, no server, no API integration of our own.

```
norway-unfiltered/
├── .claude/skills/
│   ├── ssb-report-generator/
│   │   ├── SKILL.md                       ← workflow, decision rules, naming, links to ssb-api/ssb-dataviz
│   │   ├── templates/
│   │   │   ├── report.html.j2             ← standalone HTML (Plotly via CDN, SSB palette)
│   │   │   ├── dashboard_app.py.j2        ← Streamlit scaffold
│   │   │   └── dashboard_readme.md.j2     ← per-dashboard run instructions
│   │   ├── scripts/
│   │   │   └── generate.py                ← slugify, hash, render templates, append index
│   │   └── references/
│   │       └── palette.md                 ← SSB palette + typography (mirror of ssb-dataviz)
│   └── bearingpoint-brand/
│       └── SKILL.md                       ← optional alternative palette
├── output/
│   ├── INDEX.md                           ← auto-updated catalog
│   ├── reports/<slug>.html
│   ├── dashboards/<slug>/{app.py, README.md}
│   └── data/<table_id>__<filter_hash>.{parquet,json}
├── scripts/install-ssb-skills.sh
├── CLAUDE.md
├── requirements.txt                       ← jinja2, pandas, plotly, streamlit, pyarrow
├── .gitignore                             ← adds output/data/
└── docs/superpowers/specs/...
```

Claude Code discovers skills under `.claude/skills/` automatically when running in this repo. The `ssb-api` and `ssb-dataviz` skills (already user-level installed) provide the underlying SSB knowledge; `ssb-report-generator` orchestrates them.

### Why a skill vs ad-hoc scripts

A skill is the smallest unit of repeatable Claude behavior. Putting the workflow in `SKILL.md` means:
- Claude Code auto-triggers it on relevant phrasing (description-matched)
- Steps are deterministic — same workflow every time, not re-improvised
- Versioned in repo, reviewable, diffable
- New machines / sessions inherit the workflow with zero re-explanation

Ad-hoc scripts would require the user to remember and request the right script every time and would not auto-trigger.

## Workflow (skill execution)

```
User in Claude Code (in this repo): "lag rapport om befolkningsutvikling i Oslo siste 10 år"
   ↓
ssb-api skill auto-triggers (Norwegian stats question detected)
   ↓
Claude:
   1. ssb_search("title:folkemengde")
   2. ssb_table_metadata("07459")
   3. Proposes query in chat:
      "Tabell 07459 (Folkemengde). Region=0301 (Oslo), Tid=top(10).
       Generere som HTML-rapport. OK?"
User: "ja"
   ↓
ssb-report-generator skill activates
   ↓
Claude:
   4. ssb_get_data(07459, [Region=0301, Tid=top(10)])
   5. Save raw JSON-stat2 → output/data/07459__a3f8b1c2.json
      Convert → DataFrame → output/data/07459__a3f8b1c2.parquet
   6. Decide artifact type (rules below) — HTML
   7. Slugify question → "befolkningsutvikling-i-oslo-siste-10-ar"
   8. Pick chart type (per ssb-dataviz: time series → line)
   9. Build chart spec, render template:
      output/reports/befolkningsutvikling-i-oslo-siste-10-ar.html
  10. Append row to output/INDEX.md
  11. Reply: "Generert: open output/reports/befolkningsutvikling-i-oslo-siste-10-ar.html"
```

### Decision rule — HTML report vs Streamlit dashboard

Claude evaluates in order; first match wins.

1. **Explicit user override** — phrases "lag rapport"/"make a report"/"oppsummering" → HTML; "lag dashboard"/"make a dashboard"/"interaktiv"/"explore" → Streamlit
2. **Single-chart answer** (one primary chart conveys the whole insight, e.g. KPI, simple trend, one bar chart) → HTML
3. **Multi-dimensional data** (≥2 dimensions where filtering would be valuable, e.g. region × time × age) → Streamlit
4. **≥3 distinct charts** required to tell the story → Streamlit
5. **Default fallback** → HTML (lighter to generate, easier to share)

Claude states the chosen type in the proposal step so the user can override before generation.

## Slug + cache key conventions

**Slug** (artifact filename, deterministic):
- Source: the user's NL question
- Lowercase, kebab-case, ASCII-normalized (`æ`→`ae`, `ø`→`oe`, `å`→`aa`, strip other non-ASCII)
- Strip stop words: "lag", "vis", "make", "show", "for", "om", "the", "a"
- Max 60 chars; truncate at word boundary
- Conflict policy: append `-2`, `-3`, …

**Cache key** (parquet filename):
- `<table_id>__<sha8(canonical_filters)>.{parquet,json}`
- Canonical filters: `json.dumps(filters, sort_keys=True, separators=(",",":"))` after sorting each `valueCodes` list and sorting `filters` by `variableCode`
- `sha8` = first 8 hex chars of `sha256(canonical_filters)`
- Re-runs check cache before re-fetching; user says "refresh" → bypass cache

## Index

`output/INDEX.md` is a single markdown table appended to on each generation. Format:

```markdown
# Norway Unfiltered — Generated Artifacts

| Generated | Title | Type | SSB Table | Path |
|---|---|---|---|---|
| 2026-04-19 | Befolkningsutvikling i Oslo siste 10 år | HTML | 07459 | reports/befolkningsutvikling-i-oslo-siste-10-ar.html |
| 2026-04-19 | Arbeidsledighet per fylke | Dashboard | 13772 | dashboards/arbeidsledighet-per-fylke/ |
```

Idempotent: if a row with the same path exists, update its date instead of duplicating.

## Templates

### `report.html.j2` — standalone HTML

- Single file, no build step
- Plotly via CDN (`<script src="https://cdn.plot.ly/plotly-2.x.min.js"></script>`)
- SSB palette + Roboto Condensed/Open Sans (fonts via Google Fonts CDN)
- Sections: title, declarative sub-line, KPI scorecard (optional), chart `<div>`, source footer ("Kilde: SSB, tabell {id}. Sist oppdatert: {date}.")
- Self-contained: opens directly in browser, no server

### `dashboard_app.py.j2` — Streamlit scaffold

- Uses `streamlit`, `pandas`, `plotly` only
- Layout: title, optional sidebar filters (one selectbox per filterable dimension from the SSB query), main chart area, KPI row, source footer
- Loads cached parquet via `pd.read_parquet(...)` — no live SSB calls (data is captured at generation time; user "refreshes" by re-running the skill)
- Uses SSB palette via inline CSS

### `dashboard_readme.md.j2` — per-dashboard README

- One paragraph: question that produced it, SSB table, when generated
- Run command: `streamlit run output/dashboards/<slug>/app.py`
- Refresh instruction: "Ask Claude in this repo: `refresh dashboard <slug>`"

## Styling (defers to `ssb-dataviz`)

Both templates apply, without re-deciding per generation:

- **Categorical palette (rank order):** `#1A9D49`, `#1D9DE2`, `#C78800`, `#C775A7`, `#075745`, `#0F2080`, `#A3136C`, `#471F00`, `#909090`
- **Max 6 categories** per chart (rest grouped as "Andre" in `#909090`)
- **Title font:** Roboto Condensed 20px bold, color `#274247`
- **Body/axis font:** Open Sans 12–14px, color `#274247`
- **Bars start at y=0**; no 3D, no dual axes, no pie (use donut)
- **Source footer required:** `Kilde: SSB, tabell {table_id}. Sist oppdatert: {date}.` in `#909090`
- **Number format:** Norwegian (space as thousands separator)
- **Declarative title** (insight, not description) — Claude generates per question

## Generator helper (`scripts/generate.py`)

Single Python file, ~150 LOC. Exposes one CLI:

```
python .claude/skills/ssb-report-generator/scripts/generate.py \
    --question "..." \
    --table-id 07459 \
    --filters '{"Region":["0301"],"Tid":["top(10)"]}' \
    --type html|dashboard \
    --data-file output/data/07459__a3f8b1c2.parquet \
    --chart-spec '{"chart_type":"line","x":"Tid","y":"value","title":"..."}'
```

Responsibilities:
- Slugify the question (deterministic)
- Resolve slug conflicts (`-2`, `-3`)
- Render the chosen Jinja template
- Write artifact to `output/reports/` or `output/dashboards/<slug>/`
- Append/update `output/INDEX.md`

Pure function. No SSB calls, no Anthropic calls. Claude invokes it via Bash after collecting all inputs through the SSB MCP. Keeping it single-purpose means it's easy to test and easy for Claude to drive.

## Error handling (skill-level guidance)

The skill markdown instructs Claude how to handle the foreseeable failure modes (no separate runtime error handler is needed beyond what the SSB MCP and Jinja already raise):

- **No matching SSB table** → tell user, suggest reformulation; do not generate empty artifact
- **Empty result set** → warn user, suggest broadening filters; do not generate
- **MCP unavailable** → fall back to manual Statbank link (per `ssb-api` skill's existing fallback)
- **Slug collision after `-9`** → ask user for explicit slug
- **Generator script error** → surface stderr, do not partially write the artifact (`generate.py` writes to a temp file then atomic rename)
- **Cached parquet schema mismatch** (rare, after SSB schema change) → bypass cache, re-fetch

## Testing

- **Unit (`tests/test_generate.py`):**
  - `slugify` — Norwegian chars, length cap, stop-word strip, idempotent
  - cache-key hash — equivalent filter orderings produce identical hash
  - INDEX.md append — idempotent on repeat path, sorted by date desc
  - template render — produces non-empty HTML/Streamlit with required tokens (title, source, palette colors)
- **Manual E2E (3 representative questions):**
  - HTML happy path: "lag rapport om befolkningsutvikling i Oslo siste 10 år" → expect single-line chart, valid HTML opens in browser
  - Streamlit happy path: "lag interaktivt dashboard for arbeidsledighet per fylke" → expect Streamlit scaffold, runs via `streamlit run ...`
  - Refresh: re-run first question with "refresh" keyword → expect cache bypass, parquet rewritten, HTML re-rendered with same slug
- **Skill activation check:** open Claude Code in repo, ask a Norwegian-stats question, verify ssb-report-generator skill is auto-invoked

No browser automation; opening HTML in a real browser + running Streamlit dev server are manual verification steps.

## File changes

**Deleted:**
- `app.py`
- `data/*.json` (all seven existing files)
- `render.yaml`

**Created:**
- `.claude/skills/ssb-report-generator/SKILL.md`
- `.claude/skills/ssb-report-generator/templates/report.html.j2`
- `.claude/skills/ssb-report-generator/templates/dashboard_app.py.j2`
- `.claude/skills/ssb-report-generator/templates/dashboard_readme.md.j2`
- `.claude/skills/ssb-report-generator/scripts/generate.py`
- `.claude/skills/ssb-report-generator/references/palette.md`
- `.claude/skills/bearingpoint-brand/SKILL.md` *(already created in this session)*
- `output/.gitkeep`, `output/INDEX.md`
- `tests/test_generate.py`

**Updated:**
- `requirements.txt` — replace pydeck with: `jinja2`, `pyarrow`, `requests` (keep `streamlit`, `pandas`, `plotly`)
- `.gitignore` — `output/data/` already added (cache only, generated artifacts ARE committed so the user can browse history without regenerating)
- `CLAUDE.md` — add a section pointing at `.claude/skills/ssb-report-generator/SKILL.md` and the `output/INDEX.md` catalog

**Untouched:**
- `scripts/install-ssb-skills.sh`
- `.claude/skills/bearingpoint-brand/SKILL.md` (already in place)

## Open questions

None. All decisions locked:

- Skill-driven (a), repo-local
- Hybrid HTML/Streamlit per question (c), with rule-based selection + user override
- Existing app fully deleted
- No Anthropic API; Claude Code subscription powers the agent
- SSB MCP at runtime (not direct PxWebApi); already configured for this repo
- Generated artifacts committed to repo; only `output/data/` cache is gitignored
- Norwegian as default chat/output language (with English titles also accepted)

## Risks

- **Skill prompt drift** — if SKILL.md is vague, two runs of the same question produce different artifacts. Mitigation: SKILL.md must be detailed and include 2–3 worked examples. Treat the skill itself as the primary deliverable, not an afterthought.
- **Slug collisions** mid-question phrasing — two genuinely different questions could slugify to the same string. Numeric suffix policy handles it; `-9` cap forces explicit naming.
- **Streamlit dashboards rot** when the user hand-edits — generated code is overwritten on regen. Each dashboard's README documents this; if user wants to keep edits, they rename the dashboard folder before regenerating.
- **SSB table deprecation** — cached parquet for a discontinued table still works; `ssb-api` already warns on `(avslutta serie)` tables at search time.
- **Norwegian font availability** — Roboto Condensed + Open Sans on Google Fonts; HTML uses CDN, Streamlit uses inline `<style>`. Aptos (BearingPoint) not on Google Fonts — falls back to Calibri/system.
- **MCP HTTP key in URL** — the personal SSB MCP key is in `claude mcp list` config, not in repo. Not a leak risk for the skill itself, but the user should know not to commit `.claude.json` (it's in user's home dir, not repo, so safe by default).
