# Norway Unfiltered — Natural-Language SSB Dashboard

**Date:** 2026-04-18
**Status:** ⚠️ SUPERSEDED by `2026-04-19-ssb-report-generator-design.md`
**Reason for supersession:** Architecture changed from "Streamlit app + Anthropic API agent" to "repo-local Claude Code skill that generates HTML reports / Streamlit dashboards on demand using Claude Code subscription + SSB MCP." This spec is preserved for context only.
**Replaces:** Current static JSON dashboard (`app.py` + `data/*.json`)

## Problem

The existing Norway Unfiltered dashboard renders a fixed set of pre-baked statistics (roadkill, crime, alcohol, divorces, food spending, time use) from JSON files in `data/`. Adding a new statistic requires hand-curating JSON and writing a new Plotly block. The user wants a self-service UX: type a natural-language question, have an agent pick the right SSB table and query, approve it, and get a chart — on demand, without code changes.

## Goal

Replace the current app with a single-page Streamlit app that:

1. Accepts a natural-language question in a prompt bar
2. Uses Claude Haiku 4.5 (via Anthropic API) with tool-use to find a suitable SSB table, draft a query, and propose a chart type
3. Shows the proposal inline for user approval (accept / discard)
4. On accept, fetches data from SSB's PxWebApi, caches it locally, and renders a Plotly chart styled per SSB's official dataviz guidelines
5. Keeps a session-only history of answered questions

## Non-goals

- Multi-user auth, accounts, or access control
- Cross-session persistence (SQLite/DB)
- Editing the proposed query in-place (discard and rephrase instead)
- Code generation for charts (spec-driven rendering only)
- Data sources beyond SSB
- Deployment to Render (app is local-first; Render config retained but unused until API key wired in)

## Architecture

Single Streamlit process. Python imports `anthropic` SDK and runs a tool-use loop against Haiku 4.5. The agent has four tools that wrap SSB's public PxWebApi v2-beta endpoints over HTTP (no MCP subprocess at runtime). Fetched data is cached as Parquet on disk, keyed on a stable hash of `(table_id, filter_json)`. Chart rendering is a deterministic function from `(DataFrame, chart_spec) → plotly.Figure`, where the chart spec is a small JSON object the agent emits.

Runtime dependencies are minimal: `streamlit`, `anthropic`, `requests`, `pandas`, `pyarrow`, `plotly`, `python-dotenv`.

### Why direct PxWebApi, not the SSB MCP

This repo's Claude Code session uses TRY's hosted SSB MCP server (email-gated personal URL). That's right for interactive Claude Code work. For the Streamlit runtime it's the wrong boundary: it adds a third-party dependency, requires a per-user key, and only exposes a subset of PxWebApi. Calling `https://data.ssb.no/api/pxwebapi/v2-beta/...` directly gives us the same data, zero third-party hops, no auth, and full API surface. The tool-use loop in Haiku mirrors the MCP tool names (`search_tables`, `get_metadata`, `fetch_data`) so the prompt semantics stay identical.

### Component boundaries

```
┌─────────────────────────────────────────────────────────────┐
│ app.py  —  Streamlit UI                                     │
│   - Prompt bar, proposal card, Accept/Discard, history      │
│   - Orchestrates: agent.ask → cache → render                │
└─────────────┬────────────────────────┬──────────────────────┘
              │                        │
       ┌──────▼──────┐          ┌──────▼──────┐
       │  agent.py   │          │  cache.py   │
       │  Haiku loop │          │  parquet IO │
       │  tool defs  │          │  hash keys  │
       └──────┬──────┘          └─────────────┘
              │
       ┌──────▼──────┐
       │ ssb_tools.py│
       │  4 tool fns │   ──►  https://data.ssb.no/api/pxwebapi/v2-beta
       └─────────────┘
                                  ┌─────────────┐
                                  │ renderer.py │
                                  │ spec → fig  │
                                  │ SSB styling │
                                  └─────────────┘
                                  ┌─────────────┐
                                  │ config.py   │
                                  │ env, const  │
                                  └─────────────┘
```

Each module is independently testable and has one clear job:

- **`app.py`** — UI glue. No business logic beyond state transitions (idle → proposing → awaiting-approval → fetching → rendered).
- **`agent.py`** — `ask(question: str) → Proposal` runs the Haiku tool-use loop and returns a structured proposal. Holds the system prompt.
- **`ssb_tools.py`** — `search_tables`, `get_metadata`, `fetch_data`, `build_share_url`. Pure functions over HTTP. No Streamlit or Anthropic imports.
- **`cache.py`** — `load(key) → DataFrame | None`, `save(key, df)`. Parquet files under `data/cache/`. Cache key is `sha256(table_id + "|" + canonical_filters)` where `canonical_filters` is `json.dumps(filters, sort_keys=True, separators=(",", ":"))` after sorting each Selection's `valueCodes` list and sorting the outer `filters` list by `variableCode`. This makes equivalent filter orderings produce identical keys.
- **`renderer.py`** — `render(df, spec) → plotly.graph_objects.Figure`. SSB-styled. No IO.
- **`config.py`** — env loading, API base URLs, cache dir, model constants.

## Data flow

```
1. User enters question in prompt bar → app.py sets state=proposing
2. app.py calls agent.ask(question)
   └─ Haiku loop (max ~6 turns):
       - search_tables(query) → [candidate tables]
       - get_metadata(table_id) → variables + codes
       - (optional) get_metadata on a second candidate for comparison
       - Final message: JSON with { table_id, table_title, filters, chart_spec, rationale }
3. app.py renders proposal card with rationale + Accept/Discard buttons
4. On Accept:
   - compute cache_key = sha256(table_id + canonical(filters))
   - cache.load(cache_key) — hit? use. Miss? ssb_tools.fetch_data(table_id, filters) → DataFrame → cache.save
   - renderer.render(df, chart_spec) → figure
   - st.plotly_chart(figure)
   - append { question, proposal, cache_key } to st.session_state.history
5. On Discard: clear proposal, return to idle. History not appended.
```

## Chart spec schema

A small JSON object the agent emits as part of its final structured message. Three required fields (`chart_type`, `x`, `title`); four optional (`y`, `color`, `aggregation`, `subtitle`). The renderer validates and applies defaults: `y` defaults to the first numeric column not equal to `x`; `color` defaults to `null` (single series); `aggregation` defaults to `"none"`; `subtitle` is auto-generated from `(table_id, last_updated, period)` if omitted.

```json
{
  "chart_type": "line | bar | horizontal_bar | donut | area | map | table | scorecard",  // required
  "x": "column_name",                                                                     // required
  "y": "column_name",                                                                     // optional
  "color": "column_name | null",                                                          // optional
  "aggregation": "sum | mean | none",                                                     // optional
  "title": "Deklarativ innsikt, ikke beskrivelse",                                        // required
  "subtitle": "Kilde: SSB, tabell {id}. Periode: {range}."                                // optional
}
```

Chart-type selection rules (baked into system prompt, per `ssb-dataviz` skill):

- Time series (x is year/month) → `line`
- Ranking/comparison across categories → `horizontal_bar` (sorted)
- Part-of-whole, ≤5 segments → `donut`
- Geographic (x is kommune/fylke, many rows) → `map`
- Single KPI → `scorecard`
- Fallback → `table`

## Agent prompt and tool contract

System prompt gives Haiku:

1. Role: "You are a Norwegian public-statistics agent. Find SSB tables matching the user's question. Always respect SSB API patterns (filter on Tid first, narrow Region, pick ContentsCode)."
2. Tool descriptions (4 tools, JSON Schema).
3. Output contract: after tool calls complete, reply with exactly one JSON block conforming to the `Proposal` schema. No prose outside the block.
4. Style rules condensed from `ssb-dataviz` skill (declarative title, chart-type selection matrix, color/axis conventions applied by the renderer — the agent just picks `chart_type`).

Tools exposed to Haiku during the proposal phase (only two):

```
search_tables(query: str, include_discontinued: bool = False) → list[TableSummary]
get_metadata(table_id: str) → TableMetadata
```

Functions called by `app.py` post-accept (NOT exposed to Haiku — this enforces the accept-gate at the schema level rather than relying on prompt instructions):

```
fetch_data(table_id: str, filters: list[Selection]) → dict (JSON-stat2)
build_share_url(table_id: str, filters: list[Selection]) → str
```

`Proposal` schema (the JSON block Haiku emits as its terminal message):

```json
{
  "table_id": "07459",                       // SSB table identifier
  "table_title": "Folkemengde, etter ...",   // human-readable, from get_metadata
  "filters": [                               // list of Selection objects passed to fetch_data
    { "variableCode": "Region", "valueCodes": ["0301"] },
    { "variableCode": "Tid", "valueCodes": ["top(5)"] }
  ],
  "chart_spec": { ... },                     // see Chart spec schema above
  "rationale": "1–3 sentence Norwegian explanation of why this table + filters answer the question"
}
```

**Loop bounds:**

- Max **6 turns** (1 turn = one Anthropic API request, possibly with multiple tool calls). Tool loop exits when Haiku returns a message with a `Proposal` JSON block instead of tool calls, or when 6 turns elapse (then show "agent could not find a match, try rephrasing").
- **30s timeout per individual API call** to Haiku (not the whole loop). Implemented via the Anthropic SDK's request timeout. A loop hitting all 6 turns can take up to ~3 minutes worst case; surface a non-blocking spinner with elapsed time so the user can refresh out if needed.

## SSB styling (per `ssb-dataviz` skill)

Applied in `renderer.py`, not via agent prompt. Ensures visual consistency regardless of agent output:

- **Palette (categorical, rank order):** `#1A9D49`, `#1D9DE2`, `#C78800`, `#C775A7`, `#075745`, `#0F2080`, `#A3136C`, `#471F00`, `#909090`
- **Max 6 categories** per chart; others rolled to "Andre" in SSB Grå
- **Typography:** Roboto Condensed for titles (20px bold), Open Sans for body (12–14px), `#274247` for text
- **Bars start at y=0**, no 3D, no dual axes, no pie charts (use donut)
- **Source footer** auto-injected: `Kilde: SSB, tabell {table_id}. Sist oppdatert: {date}.`
- **Number format:** norsk — space as thousands separator
- **Dark-mode Streamlit base** retained from existing app (`#08090c`) with SSB palette applied to data layers

## State machine (Streamlit session_state)

```
idle ──[submit]──► proposing ──[agent returns]──► awaiting_approval
                     │                                    │
                     │                                    ├──[accept]──► fetching ──[done]──► rendered
                     │                                    └──[discard]──► idle
                     └──[error/timeout]──► idle (with error banner)
```

Keys held in `st.session_state`: `mode`, `question`, `proposal`, `current_df`, `current_fig`, `history` (list of past renders), `error`.

## Error handling

- **Missing `ANTHROPIC_API_KEY`** → app renders a setup card on boot instead of the prompt bar, with link to `.env.example`. Prompt bar disabled.
- **Agent timeout (>30s on a single Haiku call)** → cancel, show "Agent didn't respond in time, try again or rephrase". Loop-level timeout is the 6-turn cap, not a wall clock.
- **Agent could not find table (6-turn limit hit)** → friendly message + suggestion to rephrase. History not appended.
- **PxWebApi 400 (invalid filter)** → show the filter JSON and the SSB error message; offer "Discard and retry" button.
- **PxWebApi 5xx or network** → 3 retries with exponential backoff (1s, 2s, 4s); if still failing, show error banner.
- **Empty result set** → warn user; suggest broadening filters via rephrase.
- **Cache corruption** → treat as miss, overwrite on next fetch.

All errors are non-fatal — the app returns to `idle` so the user can try again without reload.

## Testing

- **Unit**
  - `ssb_tools`: mock `requests`, assert correct URL construction for `search_tables` / `get_metadata` / `fetch_data`; assert JSON-stat2 → DataFrame parsing on fixture data
  - `cache`: hash stability across equivalent filter orderings (canonical JSON); round-trip save/load
  - `renderer`: for each `chart_type`, assert figure has correct trace type, correct palette, title set, source footer present
- **Smoke**
  - `agent.ask(question)` with a mocked Anthropic client returning a canned tool-use transcript for "hvor mange bor i Oslo?" → assert `Proposal` parses and has `table_id == "07459"`
- **Manual E2E**
  - Happy path: "hvor mange bor i Oslo siste 5 år" → expect line chart, table 07459
  - Ranking: "arbeidsledighet per fylke siste måned" → expect horizontal_bar, fylke codelist
  - Donut: "andel av befolkningen over 67 år" → expect donut, max 5 segments
  - Error: disconnect network mid-fetch → expect retry banner, then error message
  - Empty: "eksport av varer til Mars" → expect "no match" message

No browser automation needed for MVP; manual E2E plus unit/smoke is sufficient.

## File changes

**Deleted:**
- `app.py` (body; file recreated with new content)
- `data/*.json` (all seven files)

**Rewritten:**
- `app.py` — new UI
- `requirements.txt` — add `anthropic`, `requests`, `pyarrow`, `python-dotenv`

**Created:**
- `agent.py`, `ssb_tools.py`, `cache.py`, `renderer.py`, `config.py`
- `.env.example` — documents `ANTHROPIC_API_KEY`
- `.gitignore` — `.env`, `data/cache/`, `__pycache__/`, `*.pyc`
- `tests/test_ssb_tools.py`, `tests/test_cache.py`, `tests/test_renderer.py`, `tests/test_agent_smoke.py`
- `data/cache/.gitkeep`

**Unchanged:**
- `CLAUDE.md` (setup instructions)
- `scripts/install-ssb-skills.sh`
- `render.yaml` (kept; Render deploy blocked until `ANTHROPIC_API_KEY` added as secret — out of scope for this spec)

## Open questions

None blocking — all design decisions locked:

- Backend: Claude Haiku 4.5 via Anthropic API (pay-as-you-go, ~$0.01/query)
- HITL: accept-gate on proposal
- Chart: spec-driven, rendered from fixed palette/typography
- History: session-only
- Data source: SSB PxWebApi v2-beta direct (not via MCP at runtime)
- Existing dashboards: fully replaced

## Risks

- **Agent picks wrong table** — mitigated by accept-gate; worst case the user clicks Discard and rephrases. Monitor with manual E2E variety.
- **SSB PxWebApi v2-beta stability** — v2 is in beta per SSB. If endpoints change, `ssb_tools.py` is the single point of update. Fallback to v1 API is one-file change.
- **Haiku tool-use quality at edge queries** — Haiku 4.5 is strong at tool use but smaller than Sonnet/Opus. If accuracy is unacceptable, swap `MODEL` constant in `config.py` to Sonnet 4.6 (~5x cost, still < $0.05/query).
- **PxWebApi rate limits** — SSB publishes a soft limit (~30 req/s). Cache + accept-gate make rate pressure unlikely at single-user scale.
- **Deployment cost surprise** — Render config exists but deploy requires `ANTHROPIC_API_KEY` as secret; user should review API cost expectations before flipping it on.
