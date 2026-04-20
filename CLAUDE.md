# Project setup

This repo uses the SSB (Statistics Norway) MCP server and two companion skills
from TRY. On first session in this repo, please ensure they are installed.

## Required setup

1. **Check if SSB skills are installed.** Look for these directories:
   - `~/.claude/skills/ssb-api/SKILL.md`
   - `~/.claude/skills/ssb-dataviz/SKILL.md`
   - `~/.claude/skills/developing-with-streamlit/SKILL.md` (Streamlit's official agent-skills — required for dashboard work)

   If the first two are missing, run `./scripts/install-ssb-skills.sh` from the repo root.
   If the Streamlit skill is missing: `git clone --depth 1 https://github.com/streamlit/agent-skills.git /tmp/agent-skills && cp -r /tmp/agent-skills/developing-with-streamlit ~/.claude/skills/`.

2. **Check if the SSB MCP server is configured.** Run `claude mcp list` and
   look for a server named `ssb`. If missing, the user needs to get a personal
   MCP URL from https://tools.try.no/ssb-mcp (email-gated) and then run:

       claude mcp add --transport http ssb <URL-from-email>

   Do NOT ask the user for credentials or try to fetch the URL yourself —
   this requires their email signup.

3. Once both are in place, confirm to the user and proceed.

## Generating reports + dashboards

This repo includes a local skill `ssb-report-generator` (at `.claude/skills/ssb-report-generator/`) that turns Norwegian-statistics questions into either HTML reports or Streamlit dashboards using the SSB MCP. Visual identity is BearingPoint (palette in `.claude/skills/bearingpoint-brand/SKILL.md`).

- Catalog of generated artifacts: `output/INDEX.md`
- HTML reports: `output/reports/*.html`
- Streamlit dashboards: `output/dashboards/<slug>/app.py`
- Cached SSB data: `output/data/*.parquet` (gitignored)

Just ask: "lag rapport om …" or "lag dashboard for …".

## Gotchas

- **Use `python3`, not `python`**: on this machine `python` is not on PATH. Launch Streamlit as `python3 -m streamlit run <path> --server.headless true --server.port 8501` (the `streamlit` CLI shim is also not on PATH even though the package is installed).
- **Dashboards must exceed the scaffold.** The `ssb-report-generator` render template produces a single-chart app; for real deliverables, overwrite `output/dashboards/<slug>/app.py` with a hand-composed layout that uses KPI cards (`st.metric(border=True, chart_data=…)`), an Altair ranking chart with top-N highlighted, an Altair time-series with a `mark_rule` for the selected year, and a YoY-change table. Prefer Altair over Plotly (bundled, cleaner). Keep the slug + INDEX row unchanged.
- **Run the dashboard yourself after generating.** Launch in the background with `run_in_background: true`, then `curl -s -o /dev/null -w "%{http_code}" http://localhost:8501/` to confirm HTTP 200 before reporting done.
- **SSB table for "arbeidsledighet per fylke":** use `13563` with codelist `agg_KommFylker`, HovArbStyrkStatus=`A.09`, Alder=`15-74`, InnvandrKat=`A-G`, ContentsCode=`Bosatte`. The `ssb-report-generator` SKILL.md example cites 13772 / `agg_Fylker2024` — both are wrong (13772 is about kjøretid til fødested). The KOSTRA table 11818 is too sparse post-2020, and all older NAV-based ledighetstabeller (10540, 04471, 11021) are `avslutta serie` since 2020.
- **Filter Svalbard-style regions** (`F-21`, `F-22`, `F-23`) from 13563 output — they are null-series under `agg_KommFylker` but still returned. Fylke labels have multilingual suffixes ("Oslo - Oslove", "Nordland - Nordlánnda"); split on `" - "` and keep the first token.
