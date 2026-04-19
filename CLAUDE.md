# Project setup

This repo uses the SSB (Statistics Norway) MCP server and two companion skills
from TRY. On first session in this repo, please ensure they are installed.

## Required setup

1. **Check if SSB skills are installed.** Look for these directories:
   - `~/.claude/skills/ssb-api/SKILL.md`
   - `~/.claude/skills/ssb-dataviz/SKILL.md`

   If either is missing, run `./scripts/install-ssb-skills.sh` from the repo root.

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
