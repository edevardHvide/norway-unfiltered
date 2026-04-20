# Cloud Deployment Plan — Managed Agents + Agent Skills

**Date:** 2026-04-20
**Status:** Forward-looking architecture; not yet implemented
**Relation:** Extends `docs/superpowers/specs/2026-04-19-ssb-report-generator-design.md` by porting the Claude Code skill to a cloud-hosted deployment so end users can use the agent from a web browser without terminal access.

## Problem

The SSB Report Generator currently runs inside a Claude Code terminal session. The user types questions, Claude Code auto-triggers the `ssb-report-generator` skill, the SSB MCP fetches data, and an artifact lands in `output/`. This works for one developer in terminal.

Target: an internal BearingPoint analyst portal (and eventually a client-facing surface) where end users interact through a web browser, not a terminal. The agent loop, SSB MCP access, skill knowledge, and BearingPoint brand styling must all be available server-side — without asking users to install Claude Code, obtain a personal SSB MCP key, or learn slash commands.

## Goal

Reproduce the Claude Code experience in a hosted web app with three architectural pieces composed server-side:

1. **Agent Skills** (Anthropic API feature) — upload the existing `SKILL.md` files to the Anthropic API once; they load on-demand per request with the same progressive-disclosure behavior as in Claude Code
2. **MCP Connector** (`mcp_servers` + `mcp_toolset` parameters) — Anthropic proxies tool calls to the SSB MCP server-side; the model sees SSB tools as native
3. **Managed Agents** — Anthropic runs the tool-use loop; the backend posts a question, gets back a final artifact plus optional chat response

Together these three compose into "Claude Code in the cloud" for this specific workflow.

## Non-goals

- Replacing Claude Code for developer workflows — Claude Code remains the authoring environment for skills and local iteration
- Supporting Claude Code-specific features that have no API equivalent: slash commands, hooks, `/compact`, status line, `Skill` tool auto-invocation pattern (nearest equivalent is skill-metadata auto-discovery — described below)
- Subscription-tier billing — Managed Agents are billed per-token like all Claude API calls; no OAuth-via-Pro/Max path for third-party apps (banned Feb 2026)
- Client-facing self-service query for end customers of BP engagements — this plan addresses internal analysts; a later "option B" library model handles external clients

## Architecture

### Request flow

```
┌────────────────────────────────┐
│  BP analyst in browser         │
│  "lag rapport om befolkning…"  │
└──────────────┬─────────────────┘
               │ HTTPS
               ▼
┌────────────────────────────────┐
│  Your backend (Next.js /       │
│  FastAPI / Streamlit — ≤200 LOC)│
│  • Auth (SSO)                  │
│  • Rate limits                 │
│  • Assembles request           │
└──────────────┬─────────────────┘
               │ POST /v1/messages
               │ (Managed Agents)
               ▼
┌────────────────────────────────┐
│  Anthropic infrastructure      │
│                                │
│  Managed Agents loop:          │
│   1. Discover skills (metadata │
│      always loaded)            │
│   2. Trigger ssb-report-       │
│      generator on NL match     │
│   3. Load SKILL.md (Level 2)   │
│   4. Invoke ssb_search via     │
│      MCP connector ────────────┼─► SSB MCP (tools.try.no)
│   5. Invoke ssb_get_data       │
│   6. Run generate.py in code   │
│      execution sandbox         │
│   7. Return file + text        │
└──────────────┬─────────────────┘
               │ artifact file_id + narration
               ▼
┌────────────────────────────────┐
│  Backend: Files API download   │
│  → S3/CloudFront or direct     │
│    serve                        │
└──────────────┬─────────────────┘
               │
               ▼
┌────────────────────────────────┐
│  Browser: renders HTML /       │
│  embeds Streamlit in iframe    │
└────────────────────────────────┘
```

### Where the three pieces map in the existing repo

| Claude Code artifact | Cloud destination | Notes |
|---|---|---|
| `.claude/skills/ssb-report-generator/SKILL.md` | Upload via `POST /v1/skills` | Same content, same frontmatter |
| `.claude/skills/ssb-report-generator/references/palette.md` | Bundled in skill zip | Loaded via bash when referenced |
| `.claude/skills/ssb-report-generator/templates/*.j2` | Bundled in skill zip under `templates/` | Read by `generate.py` in sandbox |
| `.claude/skills/ssb-report-generator/scripts/generate.py` | Bundled in skill zip under `scripts/` | Runs in code-execution sandbox (`code-execution-2025-08-25` beta) |
| `.claude/skills/ssb-api/SKILL.md` | Upload separately | Upstream workflow skill |
| `.claude/skills/bearingpoint-brand/SKILL.md` | Upload separately | Brand reference |
| SSB MCP URL in `claude mcp list` | `mcp_servers` request param | Backend secret, not per-user |
| `output/INDEX.md`, `output/reports/`, `output/dashboards/` | S3 bucket or Postgres + object store | Artifact durability + history |

### Critical constraint: sandbox network isolation

**The code-execution sandbox where `generate.py` runs has NO network access.** This matters because:

- `generate.py` already only does pure-function work (slugify, hash, Jinja render, INDEX upsert) → ✅ maps cleanly
- It never calls SSB directly — SSB MCP calls happen at the model/tool layer via the MCP connector, which runs outside the sandbox → ✅ architecture already correct
- If future skill work needs to fetch from an external URL inside a script, that must move to an MCP tool or be pre-fetched into the sandbox via Files API

This constraint is actually a gift: it forces separation between "model does data retrieval via tools" and "skill does deterministic rendering." The existing implementation respects this line.

### Skill upload payload

Each skill is a zip containing:

```
ssb-report-generator/
├── SKILL.md                       # Unchanged
├── references/
│   └── palette.md                 # Unchanged
├── scripts/
│   └── generate.py                # Unchanged — pure functions, no network
└── templates/
    ├── report.html.j2             # Unchanged
    ├── dashboard_app.py.j2        # Unchanged
    └── dashboard_readme.md.j2     # Unchanged
```

`POST /v1/skills` with the zip. Returned `skill_id` goes into request params.

### Request shape

```http
POST /v1/messages
anthropic-version: 2023-06-01
anthropic-beta: skills-2025-10-02,code-execution-2025-08-25,files-api-2025-04-14,mcp-client-2025-11-20
content-type: application/json

{
  "model": "claude-haiku-4-5",
  "max_tokens": 4096,
  "messages": [
    {"role": "user", "content": "lag rapport om befolkning i Oslo siste 10 år"}
  ],
  "skills": [
    {"skill_id": "<ssb-report-generator skill_id>"},
    {"skill_id": "<ssb-api skill_id>"},
    {"skill_id": "<bearingpoint-brand skill_id>"}
  ],
  "tools": [
    {"type": "code_execution_20250825"},
    {"type": "mcp_toolset", "mcp_server_name": "ssb"}
  ],
  "mcp_servers": [
    {
      "type": "url",
      "url": "https://tools.try.no/ssb-mcp/mcp?key=${SSB_MCP_KEY}",
      "name": "ssb"
    }
  ]
}
```

Response contains text blocks + `mcp_tool_use`/`mcp_tool_result` blocks + (for artifacts) file blocks referenceable via Files API.

## Implementation plan

### Phase 1 — Skill-upload + single-shot backend (1 week)

**Goal:** prove the composition works end-to-end. No UI yet, just a CLI that takes a question and returns an artifact.

1. **Package skills**
   - Script `scripts/package-skills.sh` — zips `.claude/skills/ssb-report-generator/`, `ssb-api/`, `bearingpoint-brand/` into `dist/skills/*.zip`
   - Verify reserved-word check: none of our names use "anthropic"/"claude" → safe
2. **Upload skills**
   - Script `scripts/upload-skills.sh` — POSTs each zip to `/v1/skills`, saves returned `skill_id` values to `.env.local` (gitignored)
3. **Backend CLI (`backend/cli.py`, ≤200 LOC)**
   - Reads question from stdin/arg
   - Assembles the `/v1/messages` request above
   - Streams response; on final artifact, downloads via Files API and writes to `dist/artifacts/`
4. **E2E test:** `python backend/cli.py "lag rapport om befolkning i Oslo siste 10 år"` → HTML in `dist/artifacts/` with BP styling + SSB attribution, matches what Claude Code produces locally

Success criteria: artifact from cloud run is byte-identical (or semantically equivalent) to the artifact from a local Claude Code run of the same question.

### Phase 2 — Thin web frontend (1 week)

**Goal:** prompt bar in browser; artifact viewer.

1. **Streamlit app** (`frontend/app.py`)
   - `st.text_input` for the question
   - "Submit" button posts to backend
   - Streams progress updates (optional — use `st.status` with tool-call markers from the response stream)
   - On completion: shows the rendered HTML inline via `components.html`, or links to the Streamlit dashboard with a button that opens it in a new tab
2. **Auth: SSO stub**
   - Development: no auth
   - Staging/prod: Cloudflare Access or BP SSO in front of the Streamlit URL
3. **Artifact storage**
   - Local disk for dev
   - S3 bucket for prod; presigned URLs for viewing
   - `output/INDEX.md` becomes a database row per generation (Postgres or SQLite for MVP)

Success criteria: BP analyst opens URL, types question, clicks submit, sees rendered HTML within 60 seconds. No terminal touched.

### Phase 3 — Polish + ops (1 week)

1. **Rate limiting:** `max_queries_per_user_per_day = 50`; hard cap organization spending
2. **Cost alerting:** Anthropic usage dashboard → weekly Slack report; hard cutoff at $X/month
3. **Observability:** structured logs per request (user, question, skill triggered, MCP tool calls, token usage, artifact path); store in Datadog/Grafana
4. **Accept-gate UX (optional, decide during Phase 2):** show the proposed SSB query + table + chart type before running `ssb_get_data`, require click to proceed. Mirrors the Claude Code chat flow and prevents silent wrong-table runs.
5. **Error surfaces:**
   - No matching SSB table → "kunne ikke finne relevant tabell — prøv omformulering"
   - MCP unreachable → fall back to link to Statbank manually
   - Quota hit → clear error + when quota resets

## What maps vs what doesn't

| From Claude Code | Maps to cloud? | How |
|---|---|---|
| `.claude/skills/*/SKILL.md` | ✅ | Upload via `/v1/skills` |
| Skill auto-trigger on NL | ✅ | Metadata discovery is built-in |
| `generate.py` Jinja rendering | ✅ | Runs in code-execution sandbox |
| SSB MCP integration | ✅ | Via `mcp_servers` connector |
| BearingPoint brand styling | ✅ | In-template; skill is portable |
| Slash commands | ❌ | No API equivalent |
| Hooks (`settings.json`) | ❌ | No API equivalent |
| Status line, `/compact`, fullscreen | ❌ | Claude Code TUI only |
| Subscription billing | ❌ | Banned for 3rd-party apps; per-token only |
| File access outside sandbox | ❌ | Sandbox is isolated; use Files API |

## Cost model

**Assumptions:** Haiku 4.5 as default; Sonnet 4.6 fallback for harder questions (<10% of traffic).

| Input | Value |
|---|---|
| Active BP analysts | 50 |
| Queries per analyst per day | 20 |
| Queries per day | 1,000 |
| Avg tokens per query (Haiku) | ~15k (skill metadata + loaded SKILL.md + MCP tool messages + final output) |
| Haiku 4.5 price | ~$1/$5 per Mtok (in/out) |
| Avg cost per Haiku query | ~$0.03 |
| Daily Haiku cost | ~$30 |
| Sonnet-fallback premium | +20% |
| **Monthly total (20 business days)** | **~$720** |

Subscription to Claude Max plan for 50 developers would be $100 × 50 = $5000/mo — so running as a Managed-Agents product is **~7× cheaper than per-seat Claude Code subscriptions** at this usage profile, assuming these analysts do not also need Claude Code for other work. Break-even on development vs build-it-yourself: ~6 weeks.

## Risks

1. **Beta APIs** — `skills-2025-10-02`, `mcp-client-2025-11-20`, `code-execution-2025-08-25` are all beta. Anthropic may evolve them; expect 1–2 breaking changes per year. Mitigation: pin beta headers in a single config module, version-controlled.
2. **MCP key leakage** — the SSB MCP URL contains a personal key. Treat it as a production secret: inject via env var at request build time, never log, rotate annually. If the key leaks, revoke via TRY's portal and re-request.
3. **Hallucinated attributions** — model might emit a title that misrepresents the SSB data. Mitigation: deterministic source-attribution footer injected by `generate.py` (already done), plus accept-gate UX before running `ssb_get_data`.
4. **Sandbox has no network** — if a future skill needs external HTTP, it must route through an MCP tool or be pre-fetched. Revisit when it comes up.
5. **Quota sprawl** — per-token billing can balloon with retries and long queries. Hard cap at org level; Sonnet fallback should be opt-in per query, not auto.
6. **Vendor lock-in** — this architecture is Anthropic-specific. Migrating to another provider means rewriting the MCP connector usage + skill-upload flow. Acceptable given Anthropic is the only vendor shipping this skill+MCP combination today.
7. **Client-facing deployment** — this plan targets **internal** analysts. Exposing the agent directly to external BP clients (banks, gov) introduces reputational + legal risk (hallucinated stats bearing SSB attribution). Keep clients on the published-artifact library model (option B from the original triage); open a second design doc if that changes.

## Open questions (to resolve before Phase 1 starts)

1. **Hosting target** — BP internal cloud, Vercel, Render, Streamlit Community Cloud? Drives auth + artifact-store choice.
2. **User auth** — BP SSO (OIDC) or a simpler Cloudflare Access gate for MVP?
3. **Artifact persistence** — S3 sufficient, or do we need Postgres for structured history + per-user bookmarks?
4. **Streamlit dashboards at scale** — each dashboard is a separate `app.py`. Running N dashboards means N Streamlit processes. Alternatives:
   - Render dashboards at the same domain under separate paths (Streamlit multi-page pattern with dynamic load)
   - Pre-render dashboard state to static HTML snapshot (kills interactivity, kills point of using Streamlit)
   - Containerize each dashboard (overkill)
   - **Recommended:** single Streamlit app that dispatches on a `?dashboard=<slug>` query param and loads the corresponding parquet + spec
5. **Accept-gate UX** — do it in Phase 2 or Phase 3? Phase 2 is the right answer if analysts are shipping to clients (safety); Phase 3 is fine for internal-only.

## Follow-up artifacts to create when this plan kicks off

- `docs/superpowers/specs/<date>-cloud-agent-deployment-design.md` — formalize Phase 1–2 as a spec
- `docs/superpowers/plans/<date>-cloud-agent-deployment.md` — task-by-task plan (following the same TDD pattern as the local skill implementation)
- `backend/` directory scaffold
- `frontend/` directory scaffold
- `.env.example` updated with `ANTHROPIC_API_KEY`, `SSB_MCP_KEY`, `AWS_BUCKET` etc.

## Not doing (for now)

- Subscription-tier auth (banned)
- Self-hosting Claude models (Anthropic-closed)
- Porting to OpenAI/other providers (vendor lock-in is acceptable trade)
- Multi-tenancy for external BP clients (different product — use published-artifact library instead)
- Real-time collaborative editing of generated dashboards (out of scope; skill overwrites on regen is fine)

## Sources

- [Agent Skills overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [MCP connector docs](https://platform.claude.com/docs/en/agents-and-tools/mcp-connector)
- [Claude API skills guide](https://platform.claude.com/docs/en/build-with-claude/skills-guide)
- Related local spec: `docs/superpowers/specs/2026-04-19-ssb-report-generator-design.md`
- Related local plan: `docs/superpowers/plans/2026-04-19-ssb-report-generator.md`
