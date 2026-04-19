# SSB Report Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repo-local Claude Code skill (`ssb-report-generator`) that turns Norwegian-statistics questions into either standalone HTML reports or Streamlit dashboards using the SSB MCP for data and BearingPoint brand for visual identity.

**Architecture:** Skill markdown defines a deterministic workflow that Claude Code follows when triggered. A small Python helper (`generate.py`) handles slugification, cache-key hashing, template rendering (Jinja2), and INDEX.md maintenance. Two Jinja templates produce the artifacts: a self-contained HTML report and a Streamlit dashboard scaffold. Data is cached as Parquet under `output/data/` (gitignored); generated artifacts under `output/reports/` and `output/dashboards/` are committed.

**Tech Stack:** Python 3.11+, Jinja2 (templating), pandas + pyarrow (Parquet), plotly (charts), streamlit (interactive dashboards), pytest (tests), Claude Code Skills, SSB MCP server (already configured at `tools.try.no/ssb-mcp`).

**Spec:** `docs/superpowers/specs/2026-04-19-ssb-report-generator-design.md`

---

## File Structure

| Path | Responsibility |
|---|---|
| `.claude/skills/ssb-report-generator/SKILL.md` | Workflow definition: triggers, steps, decision rules, naming, examples |
| `.claude/skills/ssb-report-generator/references/palette.md` | BP palette + chart-type selection rules condensed (mirrors `bearingpoint-brand` for skill self-containment) |
| `.claude/skills/ssb-report-generator/templates/report.html.j2` | Self-contained HTML report template (Plotly via CDN, BP styling) |
| `.claude/skills/ssb-report-generator/templates/dashboard_app.py.j2` | Streamlit dashboard scaffold (sidebar filters, BP styling) |
| `.claude/skills/ssb-report-generator/templates/dashboard_readme.md.j2` | Per-dashboard README with run + refresh instructions |
| `.claude/skills/ssb-report-generator/scripts/generate.py` | CLI helper: slugify, hash, render templates, update INDEX.md |
| `.claude/skills/ssb-report-generator/scripts/__init__.py` | Make `scripts/` importable from tests |
| `tests/__init__.py` | Make `tests/` a package |
| `tests/test_generate.py` | Unit tests for `generate.py` (slugify, hash, INDEX append, template render) |
| `tests/fixtures/sample_07459.parquet` | Tiny Parquet fixture (Oslo population, 5 years) for template-render tests |
| `output/INDEX.md` | Auto-updated catalog of generated artifacts |
| `output/.gitkeep`, `output/reports/.gitkeep`, `output/dashboards/.gitkeep` | Keep directories present in repo |
| `requirements.txt` | Replace `pydeck` with `jinja2`, `pyarrow`, `requests`; add `pytest` to dev deps section |
| `.gitignore` | Verify `output/data/` ignored (already done) |
| `CLAUDE.md` | Add a section pointing at the new skill + INDEX.md |

**Files deleted:**
- `app.py` (root) — replaced by generated dashboards
- `data/*.json` (all seven) — pre-baked statistics no longer needed
- `render.yaml` — no hosting

---

## Task 1: Repo cleanup

**Files:**
- Delete: `app.py`, `data/alcohol.json`, `data/crime.json`, `data/divorces.json`, `data/divorces_regional.json`, `data/food_spending.json`, `data/roadkill.json`, `data/time_use.json`, `render.yaml`
- Modify: `requirements.txt`
- Modify: `.gitignore` (verify entries)

- [ ] **Step 1: Delete legacy files**

```bash
git rm app.py data/alcohol.json data/crime.json data/divorces.json data/divorces_regional.json data/food_spending.json data/roadkill.json data/time_use.json render.yaml
rmdir data 2>/dev/null || true
```

Expected: `git status` shows 9 deletions, no `data/` directory remaining.

- [ ] **Step 2: Rewrite requirements.txt**

Overwrite `/Users/edevard/norway-unfiltered/requirements.txt` with:

```
streamlit>=1.32
pandas>=2.2
plotly>=5.20
jinja2>=3.1
pyarrow>=15.0
requests>=2.31

# dev
pytest>=8.0
```

- [ ] **Step 3: Verify .gitignore has the cache entry**

Run: `grep -F 'output/data/' /Users/edevard/norway-unfiltered/.gitignore`
Expected: prints `output/data/`. If missing, append it via `echo 'output/data/' >> /Users/edevard/norway-unfiltered/.gitignore`.

- [ ] **Step 4: Commit cleanup**

```bash
git add -A
git commit -m "chore: remove static dashboard, prep deps for report generator skill"
```

---

## Task 2: Output directory scaffolding

**Files:**
- Create: `output/.gitkeep`, `output/reports/.gitkeep`, `output/dashboards/.gitkeep`, `output/data/.gitkeep`
- Create: `output/INDEX.md`

- [ ] **Step 1: Create directories with sentinels**

```bash
mkdir -p output/reports output/dashboards output/data
touch output/reports/.gitkeep output/dashboards/.gitkeep output/data/.gitkeep
```

- [ ] **Step 2: Create initial INDEX.md**

Write `/Users/edevard/norway-unfiltered/output/INDEX.md`:

```markdown
# Norway Unfiltered — Generated Artifacts

> Auto-maintained by `.claude/skills/ssb-report-generator`. Do not edit manually — your changes will be overwritten on next generation.

| Generated | Title | Type | SSB Table | Path |
|-----------|-------|------|-----------|------|
```

- [ ] **Step 3: Commit scaffold**

```bash
git add output/
git commit -m "chore: scaffold output/ tree with empty INDEX"
```

---

## Task 3: Skill scaffold (SKILL.md + references)

**Files:**
- Create: `.claude/skills/ssb-report-generator/SKILL.md`
- Create: `.claude/skills/ssb-report-generator/references/palette.md`

- [ ] **Step 1: Write SKILL.md**

Write `/Users/edevard/norway-unfiltered/.claude/skills/ssb-report-generator/SKILL.md`:

```markdown
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
```

- [ ] **Step 2: Write references/palette.md**

Write `/Users/edevard/norway-unfiltered/.claude/skills/ssb-report-generator/references/palette.md`:

```markdown
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
```

- [ ] **Step 3: Commit skill scaffold**

```bash
git add .claude/skills/ssb-report-generator/
git commit -m "feat(skill): add ssb-report-generator scaffold (SKILL.md + palette reference)"
```

---

## Task 4: Generator helper — slugify (TDD)

**Files:**
- Create: `tests/__init__.py` (empty)
- Create: `tests/test_generate.py`
- Create: `.claude/skills/ssb-report-generator/scripts/__init__.py` (empty)
- Create: `.claude/skills/ssb-report-generator/scripts/generate.py`

- [ ] **Step 1: Create empty package init files**

```bash
mkdir -p tests .claude/skills/ssb-report-generator/scripts
touch tests/__init__.py .claude/skills/ssb-report-generator/scripts/__init__.py
```

- [ ] **Step 2: Write the failing slugify tests**

Create `/Users/edevard/norway-unfiltered/tests/test_generate.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".claude" / "skills" / "ssb-report-generator" / "scripts"))

from generate import slugify


def test_slugify_basic():
    assert slugify("Roadkill by county") == "roadkill-by-county"


def test_slugify_norwegian_chars():
    assert slugify("Befolkning i Trøndelag og Møre") == "befolkning-i-troendelag-og-moere"


def test_slugify_strips_stop_words():
    assert slugify("lag rapport om befolkning i Oslo") == "befolkning-i-oslo"


def test_slugify_max_60_chars_at_word_boundary():
    long = "befolkningsutvikling i alle kommuner i hele norge gjennom hundre aar"
    out = slugify(long)
    assert len(out) <= 60
    assert not out.endswith("-")
    assert "kommun" in out  # truncation happens after a word, not mid-word


def test_slugify_strips_make_show():
    assert slugify("Make a report on crime in Bergen") == "crime-in-bergen"


def test_slugify_idempotent():
    s = "lag rapport om befolkning i Oslo"
    assert slugify(slugify(s)) == slugify(s)


def test_slugify_strips_special_punctuation():
    # KPI is a meaningful content acronym — not a stop word.
    assert slugify("KPI: konsumprisindeks (2025=100)?") == "kpi-konsumprisindeks-2025-100"
```

- [ ] **Step 3: Run the tests and verify they fail**

```bash
cd /Users/edevard/norway-unfiltered && python -m pytest tests/test_generate.py -v
```

Expected: ImportError or ModuleNotFoundError because `generate.py` doesn't exist yet.

- [ ] **Step 4: Implement `slugify` in generate.py**

Create `/Users/edevard/norway-unfiltered/.claude/skills/ssb-report-generator/scripts/generate.py`:

```python
"""Helpers for the ssb-report-generator skill.

CLI:
    python generate.py slugify --question "..."
    python generate.py hash --filters '{"Region":["0301"]}'
    python generate.py render --question ... --type html|dashboard ...

Pure functions; no SSB or Anthropic calls. Claude invokes this from the skill
workflow after collecting all inputs through the SSB MCP.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

STOP_WORDS = {
    "lag", "vis", "make", "show", "for", "om", "the", "a", "an",
    "of", "on", "i", "and", "og", "in", "to", "report", "rapport",
    "dashboard", "oppsummering", "summary", "interaktiv", "interactive",
}

NORWEGIAN_TRANSLITERATION = str.maketrans({
    "æ": "ae", "Æ": "ae",
    "ø": "oe", "Ø": "oe",
    "å": "aa", "Å": "aa",
})

MAX_SLUG_LEN = 60


def slugify(text: str) -> str:
    """Deterministic kebab-case slug from a free-text question.

    1. Lowercase + Norwegian transliteration.
    2. Drop non-ASCII alphanumerics (keep digits + spaces + hyphens).
    3. Tokenize, drop stop words.
    4. Join with hyphens; collapse runs of hyphens.
    5. Truncate at <=MAX_SLUG_LEN at a word boundary; trim trailing hyphens.
    """
    if not text:
        return ""
    text = text.lower().translate(NORWEGIAN_TRANSLITERATION)
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    tokens = [t for t in re.split(r"[\s\-]+", text) if t and t not in STOP_WORDS]
    slug = "-".join(tokens)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if len(slug) <= MAX_SLUG_LEN:
        return slug
    cut = slug[:MAX_SLUG_LEN]
    last_hyphen = cut.rfind("-")
    if last_hyphen > 0:
        cut = cut[:last_hyphen]
    return cut.rstrip("-")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("slugify")
    s.add_argument("--question", required=True)
    args = parser.parse_args()
    if args.cmd == "slugify":
        print(slugify(args.question))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run tests and verify they pass**

```bash
cd /Users/edevard/norway-unfiltered && python -m pytest tests/test_generate.py -v
```

Expected: 7 passed.

- [ ] **Step 6: Commit**

```bash
git add tests/__init__.py tests/test_generate.py .claude/skills/ssb-report-generator/scripts/
git commit -m "feat(generate): slugify with Norwegian transliteration + stop-word strip"
```

---

## Task 5: Generator helper — cache-key hash (TDD)

**Files:**
- Modify: `tests/test_generate.py` (append tests)
- Modify: `.claude/skills/ssb-report-generator/scripts/generate.py` (add `cache_key`)

- [ ] **Step 1: Write the failing hash tests**

Append to `tests/test_generate.py`:

```python
from generate import cache_key


def test_cache_key_deterministic():
    f1 = [{"variableCode": "Region", "valueCodes": ["0301"]}]
    assert cache_key("07459", f1) == cache_key("07459", f1)


def test_cache_key_invariant_to_filter_order():
    f1 = [
        {"variableCode": "Region", "valueCodes": ["0301"]},
        {"variableCode": "Tid", "valueCodes": ["top(5)"]},
    ]
    f2 = list(reversed(f1))
    assert cache_key("07459", f1) == cache_key("07459", f2)


def test_cache_key_invariant_to_value_order():
    f1 = [{"variableCode": "Region", "valueCodes": ["0301", "1103"]}]
    f2 = [{"variableCode": "Region", "valueCodes": ["1103", "0301"]}]
    assert cache_key("07459", f1) == cache_key("07459", f2)


def test_cache_key_changes_with_table_id():
    f = [{"variableCode": "Region", "valueCodes": ["0301"]}]
    assert cache_key("07459", f) != cache_key("99999", f)


def test_cache_key_changes_with_filters():
    f1 = [{"variableCode": "Region", "valueCodes": ["0301"]}]
    f2 = [{"variableCode": "Region", "valueCodes": ["1103"]}]
    assert cache_key("07459", f1) != cache_key("07459", f2)


def test_cache_key_format():
    out = cache_key("07459", [{"variableCode": "X", "valueCodes": ["1"]}])
    assert len(out) == 8
    assert all(c in "0123456789abcdef" for c in out)
```

- [ ] **Step 2: Run tests and verify they fail**

```bash
cd /Users/edevard/norway-unfiltered && python -m pytest tests/test_generate.py -v
```

Expected: 6 new failures (`ImportError: cannot import name 'cache_key'`).

- [ ] **Step 3: Implement `cache_key`**

Add to `generate.py` (above `def main`):

```python
def cache_key(table_id: str, filters: list[dict]) -> str:
    """Stable 8-char hex hash for a (table_id, filters) pair.

    Canonicalizes by sorting valueCodes within each Selection and sorting the
    outer filter list by variableCode, so equivalent orderings produce identical
    keys.
    """
    canonical = sorted(
        ({"variableCode": f["variableCode"], "valueCodes": sorted(f["valueCodes"])} for f in filters),
        key=lambda f: f["variableCode"],
    )
    payload = table_id + "|" + json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8]
```

- [ ] **Step 4: Extend the CLI**

In `main()`, add a `hash` subparser:

```python
    h = sub.add_parser("hash")
    h.add_argument("--table-id", required=True)
    h.add_argument("--filters", required=True, help="JSON array of Selection objects")
    args = parser.parse_args()
    if args.cmd == "slugify":
        print(slugify(args.question))
        return 0
    if args.cmd == "hash":
        print(cache_key(args.table_id, json.loads(args.filters)))
        return 0
    return 2
```

- [ ] **Step 5: Run tests and verify they pass**

```bash
cd /Users/edevard/norway-unfiltered && python -m pytest tests/test_generate.py -v
```

Expected: 13 passed.

- [ ] **Step 6: Smoke-test the CLI**

```bash
python .claude/skills/ssb-report-generator/scripts/generate.py hash \
    --table-id 07459 --filters '[{"variableCode":"Region","valueCodes":["0301"]}]'
```

Expected: an 8-char hex string (e.g. `a3f8b1c2`).

```bash
python .claude/skills/ssb-report-generator/scripts/generate.py slugify --question "lag rapport om befolkning i Oslo"
```

Expected: `befolkning-i-oslo`.

- [ ] **Step 7: Commit**

```bash
git add tests/test_generate.py .claude/skills/ssb-report-generator/scripts/generate.py
git commit -m "feat(generate): cache_key with canonical filter ordering"
```

---

## Task 6: Generator helper — INDEX.md append (TDD)

**Files:**
- Modify: `tests/test_generate.py`
- Modify: `.claude/skills/ssb-report-generator/scripts/generate.py`

- [ ] **Step 1: Write the failing index tests**

Append to `tests/test_generate.py`:

```python
from datetime import date
from generate import upsert_index_row, render_index


def test_upsert_index_appends_new_row(tmp_path):
    index = tmp_path / "INDEX.md"
    index.write_text("# Index\n\n| Generated | Title | Type | SSB Table | Path |\n|---|---|---|---|---|\n")
    upsert_index_row(
        index,
        generated=date(2026, 4, 19),
        title="Befolkning Oslo",
        type_="HTML",
        table_id="07459",
        path="reports/befolkning-oslo.html",
    )
    contents = index.read_text()
    assert "Befolkning Oslo" in contents
    assert "07459" in contents
    assert "reports/befolkning-oslo.html" in contents


def test_upsert_index_updates_date_on_same_path(tmp_path):
    index = tmp_path / "INDEX.md"
    index.write_text("# Index\n\n| Generated | Title | Type | SSB Table | Path |\n|---|---|---|---|---|\n")
    upsert_index_row(index, date(2026, 4, 19), "T", "HTML", "07459", "reports/x.html")
    upsert_index_row(index, date(2026, 4, 20), "T", "HTML", "07459", "reports/x.html")
    contents = index.read_text()
    assert contents.count("reports/x.html") == 1
    assert "2026-04-20" in contents
    assert "2026-04-19" not in contents


def test_upsert_index_sorts_newest_first(tmp_path):
    index = tmp_path / "INDEX.md"
    index.write_text("# Index\n\n| Generated | Title | Type | SSB Table | Path |\n|---|---|---|---|---|\n")
    upsert_index_row(index, date(2026, 4, 18), "Older", "HTML", "1", "reports/older.html")
    upsert_index_row(index, date(2026, 4, 20), "Newer", "HTML", "2", "reports/newer.html")
    contents = index.read_text()
    newer_pos = contents.find("Newer")
    older_pos = contents.find("Older")
    assert 0 < newer_pos < older_pos
```

- [ ] **Step 2: Run tests and verify they fail**

```bash
cd /Users/edevard/norway-unfiltered && python -m pytest tests/test_generate.py -v
```

Expected: 3 new failures (`cannot import name 'upsert_index_row'`).

- [ ] **Step 3: Implement INDEX maintenance**

Add to `generate.py`:

```python
from datetime import date as _date
from typing import NamedTuple


class IndexRow(NamedTuple):
    generated: _date
    title: str
    type_: str
    table_id: str
    path: str

    def to_md(self) -> str:
        return f"| {self.generated.isoformat()} | {self.title} | {self.type_} | {self.table_id} | {self.path} |"


_HEADER = "# Norway Unfiltered — Generated Artifacts\n\n> Auto-maintained by `.claude/skills/ssb-report-generator`. Do not edit manually — your changes will be overwritten on next generation.\n\n| Generated | Title | Type | SSB Table | Path |\n|-----------|-------|------|-----------|------|\n"


def _parse_existing_rows(text: str) -> list[IndexRow]:
    rows: list[IndexRow] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("| 20"):  # data row starts with a date in 20xx
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) != 5:
            continue
        try:
            d = _date.fromisoformat(parts[0])
        except ValueError:
            continue
        rows.append(IndexRow(d, parts[1], parts[2], parts[3], parts[4]))
    return rows


def render_index(rows: list[IndexRow]) -> str:
    sorted_rows = sorted(rows, key=lambda r: r.generated, reverse=True)
    body = "\n".join(r.to_md() for r in sorted_rows)
    return _HEADER + (body + "\n" if body else "")


def upsert_index_row(
    index_path: Path,
    generated: _date,
    title: str,
    type_: str,
    table_id: str,
    path: str,
) -> None:
    text = index_path.read_text() if index_path.exists() else _HEADER
    rows = _parse_existing_rows(text)
    rows = [r for r in rows if r.path != path]  # remove existing same-path row
    rows.append(IndexRow(generated, title, type_, table_id, path))
    index_path.write_text(render_index(rows))
```

- [ ] **Step 4: Run tests and verify they pass**

```bash
cd /Users/edevard/norway-unfiltered && python -m pytest tests/test_generate.py -v
```

Expected: 16 passed.

- [ ] **Step 5: Commit**

```bash
git add tests/test_generate.py .claude/skills/ssb-report-generator/scripts/generate.py
git commit -m "feat(generate): INDEX.md upsert + descending sort"
```

---

## Task 7: HTML report template

**Files:**
- Create: `.claude/skills/ssb-report-generator/templates/report.html.j2`
- Create: `tests/fixtures/sample_07459.parquet`
- Modify: `tests/test_generate.py`
- Modify: `.claude/skills/ssb-report-generator/scripts/generate.py` (add `render_html`)

- [ ] **Step 1: Generate the test fixture parquet**

Run inline (do not commit a generator script — the parquet is the artifact):

```bash
cd /Users/edevard/norway-unfiltered && mkdir -p tests/fixtures && python -c "
import pandas as pd
df = pd.DataFrame({
    'Tid': ['2020', '2021', '2022', '2023', '2024'],
    'value': [697549, 699827, 702543, 709037, 717710],
})
df.to_parquet('tests/fixtures/sample_07459.parquet')
"
ls -la tests/fixtures/sample_07459.parquet
```

Expected: file exists, ~3 KB.

- [ ] **Step 2: Write the HTML template**

Create `/Users/edevard/norway-unfiltered/.claude/skills/ssb-report-generator/templates/report.html.j2`:

```html
<!DOCTYPE html>
<html lang="no">
<head>
  <meta charset="UTF-8" />
  <title>{{ title }}</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
  <style>
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
    body {
      margin: 0;
      background: var(--bp-light-2);
      color: var(--bp-dark-1);
      font-family: var(--bp-font-body);
      font-size: 14px;
      line-height: 1.5;
    }
    .container { max-width: 1100px; margin: 0 auto; padding: 48px 32px; }
    h1 {
      font-family: var(--bp-font-heading);
      font-weight: 700;
      font-size: 32px;
      letter-spacing: -0.5px;
      margin: 0 0 8px 0;
    }
    .subtitle { color: var(--bp-accent-4); margin-bottom: 32px; font-size: 16px; }
    .chart { background: var(--bp-light-1); padding: 24px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
    .footer {
      margin-top: 24px;
      color: var(--bp-accent-5);
      font-size: 12px;
      border-top: 1px solid var(--bp-accent-5);
      padding-top: 12px;
    }
    a { color: var(--bp-link); }
    a:visited { color: var(--bp-link-visited); }
  </style>
</head>
<body>
  <div class="container">
    <h1>{{ title }}</h1>
    <div class="subtitle">{{ rationale }}</div>
    <div class="chart">
      <div id="chart"></div>
    </div>
    <div class="footer">
      Kilde: SSB, tabell {{ table_id }}. Sist oppdatert: {{ generated }}.<br>
      Generert av BearingPoint Norway Unfiltered.
    </div>
  </div>
  <script>
    const figure = {{ figure_json | safe }};
    Plotly.newPlot('chart', figure.data, figure.layout, {responsive: true, displayModeBar: false});
  </script>
</body>
</html>
```

- [ ] **Step 3: Write the failing render-html test**

Append to `tests/test_generate.py`:

```python
from generate import render_html


def test_render_html_writes_artifact(tmp_path):
    df_path = Path(__file__).parent / "fixtures" / "sample_07459.parquet"
    out = tmp_path / "report.html"
    render_html(
        out_path=out,
        title="Befolkning Oslo siste 5 år",
        rationale="Folkemengden i Oslo har vokst jevnt gjennom femårsperioden.",
        table_id="07459",
        generated=date(2026, 4, 19),
        data_file=df_path,
        chart_spec={"chart_type": "line", "x": "Tid", "y": "value", "title": "Befolkning Oslo siste 5 år"},
    )
    html = out.read_text(encoding="utf-8")
    assert "Befolkning Oslo siste 5 år" in html
    assert "Kilde: SSB, tabell 07459" in html
    assert "BearingPoint" in html
    assert "#99171D" in html  # BP accent 1 in CSS
    assert "Plotly.newPlot" in html
    assert "717710" in html  # last data point baked into figure JSON
```

- [ ] **Step 4: Run tests and verify they fail**

```bash
cd /Users/edevard/norway-unfiltered && python -m pytest tests/test_generate.py::test_render_html_writes_artifact -v
```

Expected: import error or function missing.

- [ ] **Step 5: Implement `render_html`**

Add imports at top of `generate.py`:

```python
import os
import tempfile
import pandas as pd
import plotly.graph_objects as go
from jinja2 import Environment, FileSystemLoader, select_autoescape
```

Add helpers + `render_html` to `generate.py`:

```python
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

BP_COLORS = ["#99171D", "#FF787A", "#421799", "#806659", "#B2A59F", "#FFB1B5"]


def _build_figure(df: pd.DataFrame, spec: dict) -> go.Figure:
    chart_type = spec["chart_type"]
    x = spec["x"]
    y = spec.get("y") or [c for c in df.columns if c != x and pd.api.types.is_numeric_dtype(df[c])][0]
    color = spec.get("color")
    title = spec.get("title", "")

    fig = go.Figure()
    if color and color in df.columns:
        for i, (cat, group) in enumerate(df.groupby(color)):
            fig.add_trace(_trace(chart_type, group[x], group[y], str(cat), BP_COLORS[i % len(BP_COLORS)]))
    else:
        fig.add_trace(_trace(chart_type, df[x], df[y], y, BP_COLORS[0]))

    fig.update_layout(
        title=title,
        font=dict(family="Aptos, Calibri, sans-serif", size=13, color="#000000"),
        title_font=dict(family="Aptos Display, Calibri, sans-serif", size=20, color="#000000"),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FAF8F7",
        margin=dict(l=40, r=20, t=60, b=40),
        showlegend=bool(color),
    )
    # Bars must start at 0 on their VALUE axis. Vertical bars: Y axis. Horizontal bars: X axis (we swap data in _trace).
    x_rangemode = "tozero" if chart_type == "horizontal_bar" else "normal"
    y_rangemode = "tozero" if chart_type == "bar" else "normal"
    fig.update_xaxes(showgrid=False, linecolor="#B2A59F", rangemode=x_rangemode)
    fig.update_yaxes(gridcolor="#FAF8F7", linecolor="#B2A59F", rangemode=y_rangemode)
    return fig


def _trace(chart_type: str, x, y, name: str, color: str):
    if chart_type == "line":
        return go.Scatter(x=x, y=y, mode="lines+markers", name=name, line=dict(color=color, width=3), marker=dict(color=color, size=8))
    if chart_type == "bar":
        return go.Bar(x=x, y=y, name=name, marker_color=color)
    if chart_type == "horizontal_bar":
        return go.Bar(x=y, y=x, name=name, orientation="h", marker_color=color)
    if chart_type == "area":
        return go.Scatter(x=x, y=y, mode="lines", name=name, line=dict(color=color, width=2), fill="tozeroy")
    if chart_type == "donut":
        return go.Pie(labels=x, values=y, hole=0.5, marker=dict(colors=BP_COLORS))
    return go.Scatter(x=x, y=y, mode="lines+markers", name=name, line=dict(color=color))


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp_", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def render_html(
    out_path: Path,
    title: str,
    rationale: str,
    table_id: str,
    generated: _date,
    data_file: Path,
    chart_spec: dict,
) -> None:
    df = pd.read_parquet(data_file)
    figure = _build_figure(df, chart_spec)
    figure_json = figure.to_json()
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
    )
    tmpl = env.get_template("report.html.j2")
    html = tmpl.render(
        title=title,
        rationale=rationale,
        table_id=table_id,
        generated=generated.isoformat(),
        figure_json=figure_json,
    )
    _atomic_write(out_path, html)
```

- [ ] **Step 6: Run tests and verify they pass**

```bash
cd /Users/edevard/norway-unfiltered && python -m pytest tests/test_generate.py -v
```

Expected: 17 passed.

- [ ] **Step 7: Manual smoke — open the test artifact**

```bash
cd /Users/edevard/norway-unfiltered && python -c "
from datetime import date
from pathlib import Path
import sys
sys.path.insert(0, '.claude/skills/ssb-report-generator/scripts')
from generate import render_html
render_html(
    out_path=Path('output/reports/_smoke.html'),
    title='Smoke test — Oslo befolkning',
    rationale='Sanity check at template+chart render successfully.',
    table_id='07459',
    generated=date(2026, 4, 19),
    data_file=Path('tests/fixtures/sample_07459.parquet'),
    chart_spec={'chart_type': 'line', 'x': 'Tid', 'y': 'value', 'title': 'Smoke'},
)
print('OK:', Path('output/reports/_smoke.html').stat().st_size, 'bytes')
"
open output/reports/_smoke.html
```

Expected: terminal prints `OK: ~XXXX bytes`; browser opens a BP-styled page with a deep-red line chart, source footer, and BP wordmark.

- [ ] **Step 8: Clean up smoke artifact + commit**

```bash
rm output/reports/_smoke.html
git add tests/fixtures/sample_07459.parquet tests/test_generate.py .claude/skills/ssb-report-generator/templates/report.html.j2 .claude/skills/ssb-report-generator/scripts/generate.py
git commit -m "feat(generate): HTML report template + render_html with BP styling"
```

---

## Task 8: Streamlit dashboard template + render

**Files:**
- Create: `.claude/skills/ssb-report-generator/templates/dashboard_app.py.j2`
- Create: `.claude/skills/ssb-report-generator/templates/dashboard_readme.md.j2`
- Modify: `tests/test_generate.py`
- Modify: `.claude/skills/ssb-report-generator/scripts/generate.py` (add `render_dashboard`)

- [ ] **Step 1: Write the Streamlit template**

Create `/Users/edevard/norway-unfiltered/.claude/skills/ssb-report-generator/templates/dashboard_app.py.j2`:

```python
"""Generated Streamlit dashboard. Re-generate via the ssb-report-generator skill."""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "{{ data_filename }}"
BP_COLORS = ["#99171D", "#FF787A", "#421799", "#806659", "#B2A59F", "#FFB1B5"]

st.set_page_config(page_title="{{ title }}", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
      .stApp { background: #FAF8F7; color: #000000; font-family: Aptos, Calibri, sans-serif; }
      h1, h2, h3 { font-family: 'Aptos Display', Calibri, sans-serif; color: #000000; }
      .footer { color: #B2A59F; font-size: 12px; border-top: 1px solid #B2A59F; padding-top: 8px; margin-top: 24px; }
      a { color: #A070FF; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("{{ title }}")
st.caption("{{ rationale }}")

df = pd.read_parquet(DATA_PATH)

{% if filterable_columns %}
with st.sidebar:
    st.header("Filtre")
{%- for col in filterable_columns %}
    sel_{{ col }} = st.multiselect("{{ col }}", sorted(df["{{ col }}"].unique().tolist()))
    if sel_{{ col }}:
        df = df[df["{{ col }}"].isin(sel_{{ col }})]
{%- endfor %}
{% endif %}

x = "{{ chart_x }}"
y = "{{ chart_y }}"
chart_type = "{{ chart_type }}"

fig = go.Figure()
if chart_type == "line":
    fig.add_trace(go.Scatter(x=df[x], y=df[y], mode="lines+markers", line=dict(color=BP_COLORS[0], width=3)))
elif chart_type == "horizontal_bar":
    fig.add_trace(go.Bar(x=df[y], y=df[x], orientation="h", marker_color=BP_COLORS[0]))
elif chart_type == "bar":
    fig.add_trace(go.Bar(x=df[x], y=df[y], marker_color=BP_COLORS[0]))
else:
    fig.add_trace(go.Scatter(x=df[x], y=df[y], mode="lines+markers", line=dict(color=BP_COLORS[0])))

fig.update_layout(
    font=dict(family="Aptos, Calibri, sans-serif", size=13, color="#000000"),
    title_font=dict(family="Aptos Display, Calibri, sans-serif", size=20, color="#000000"),
    plot_bgcolor="#FFFFFF",
    paper_bgcolor="#FAF8F7",
    margin=dict(l=40, r=20, t=20, b=40),
    showlegend=False,
)
fig.update_xaxes(showgrid=False, linecolor="#B2A59F")
fig.update_yaxes(gridcolor="#FAF8F7", linecolor="#B2A59F", rangemode="tozero" if chart_type in {"bar", "horizontal_bar"} else "normal")

st.plotly_chart(fig, use_container_width=True)

st.markdown(
    f'<div class="footer">Kilde: SSB, tabell {{ table_id }}. Sist oppdatert: {{ generated }}.<br>Generert av BearingPoint Norway Unfiltered.</div>',
    unsafe_allow_html=True,
)
```

- [ ] **Step 2: Write the per-dashboard README template**

Create `/Users/edevard/norway-unfiltered/.claude/skills/ssb-report-generator/templates/dashboard_readme.md.j2`:

```markdown
# {{ title }}

> Generated by `ssb-report-generator` on {{ generated }} from the question: _"{{ question }}"_

## Run

```bash
streamlit run output/dashboards/{{ slug }}/app.py
```

## Refresh data

In Claude Code in this repo, ask:

```
refresh dashboard {{ slug }}
```

This re-runs the SSB query, overwrites the cached parquet, and re-renders this dashboard.

## Source

- SSB table: **{{ table_id }}**
- Filters: `{{ filters_json }}`
- Cached data: `output/data/{{ data_filename }}`

## Editing

This file is regenerated on every refresh. To preserve manual edits, rename the dashboard folder before regenerating.
```

- [ ] **Step 3: Write the failing render-dashboard test**

Append to `tests/test_generate.py`:

```python
from generate import render_dashboard


def test_render_dashboard_writes_app_and_readme(tmp_path):
    df_path = Path(__file__).parent / "fixtures" / "sample_07459.parquet"
    dash_dir = tmp_path / "dashboards" / "befolkning-oslo"
    render_dashboard(
        out_dir=dash_dir,
        slug="befolkning-oslo",
        title="Befolkning Oslo siste 5 år",
        rationale="Vekstkurve over fem år.",
        question="lag dashboard for befolkning i Oslo",
        table_id="07459",
        generated=date(2026, 4, 19),
        data_file=df_path,
        chart_spec={"chart_type": "line", "x": "Tid", "y": "value"},
        filterable_columns=["Tid"],
        filters_json='[{"variableCode":"Region","valueCodes":["0301"]}]',
    )
    app = (dash_dir / "app.py").read_text()
    assert "Befolkning Oslo siste 5 år" in app
    assert "#99171D" in app
    assert "Kilde: SSB, tabell 07459" in app
    assert "BearingPoint" in app
    readme = (dash_dir / "README.md").read_text()
    assert "streamlit run output/dashboards/befolkning-oslo/app.py" in readme
    assert "refresh dashboard befolkning-oslo" in readme
```

- [ ] **Step 4: Run tests and verify they fail**

```bash
cd /Users/edevard/norway-unfiltered && python -m pytest tests/test_generate.py::test_render_dashboard_writes_app_and_readme -v
```

Expected: import error.

- [ ] **Step 5: Implement `render_dashboard`**

Add to `generate.py`:

```python
def render_dashboard(
    out_dir: Path,
    slug: str,
    title: str,
    rationale: str,
    question: str,
    table_id: str,
    generated: _date,
    data_file: Path,
    chart_spec: dict,
    filterable_columns: list[str] | None = None,
    filters_json: str = "[]",
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    data_filename = data_file.name
    # Copy the parquet into output/data/ (caller is responsible for putting it
    # there beforehand; the dashboard reads from output/data/<filename>).
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,  # python source, not HTML
    )
    app_tmpl = env.get_template("dashboard_app.py.j2")
    app_src = app_tmpl.render(
        title=title,
        rationale=rationale,
        table_id=table_id,
        generated=generated.isoformat(),
        data_filename=data_filename,
        chart_x=chart_spec["x"],
        chart_y=chart_spec.get("y", "value"),
        chart_type=chart_spec["chart_type"],
        filterable_columns=filterable_columns or [],
    )
    _atomic_write(out_dir / "app.py", app_src)

    readme_env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
    )
    readme_tmpl = readme_env.get_template("dashboard_readme.md.j2")
    readme_src = readme_tmpl.render(
        title=title,
        question=question,
        generated=generated.isoformat(),
        slug=slug,
        table_id=table_id,
        filters_json=filters_json,
        data_filename=data_filename,
    )
    _atomic_write(out_dir / "README.md", readme_src)
```

- [ ] **Step 6: Run tests and verify they pass**

```bash
cd /Users/edevard/norway-unfiltered && python -m pytest tests/test_generate.py -v
```

Expected: 18 passed.

- [ ] **Step 7: Manual smoke — generate + run a dashboard**

```bash
cd /Users/edevard/norway-unfiltered && cp tests/fixtures/sample_07459.parquet output/data/07459__smoke000.parquet
python -c "
from datetime import date
from pathlib import Path
import sys
sys.path.insert(0, '.claude/skills/ssb-report-generator/scripts')
from generate import render_dashboard
render_dashboard(
    out_dir=Path('output/dashboards/_smoke'),
    slug='_smoke',
    title='Smoke dashboard',
    rationale='Manual verification.',
    question='smoke test',
    table_id='07459',
    generated=date(2026, 4, 19),
    data_file=Path('output/data/07459__smoke000.parquet'),
    chart_spec={'chart_type': 'line', 'x': 'Tid', 'y': 'value'},
    filterable_columns=['Tid'],
)
print('Generated:', list(Path('output/dashboards/_smoke').iterdir()))
"
streamlit run output/dashboards/_smoke/app.py --server.headless true &
SL_PID=$!
sleep 4
curl -sI http://localhost:8501 | head -1
kill $SL_PID 2>/dev/null
```

Expected: prints `Generated: [...app.py..., ...README.md...]` and `HTTP/1.1 200 OK`.

- [ ] **Step 8: Clean up smoke + commit**

```bash
rm -rf output/dashboards/_smoke output/data/07459__smoke000.parquet
git add tests/test_generate.py .claude/skills/ssb-report-generator/templates/ .claude/skills/ssb-report-generator/scripts/generate.py
git commit -m "feat(generate): Streamlit dashboard template + render_dashboard"
```

---

## Task 9: `render` CLI subcommand (orchestration)

**Files:**
- Modify: `.claude/skills/ssb-report-generator/scripts/generate.py`

- [ ] **Step 1: Extend the CLI in `main()`**

Replace `main()` with:

```python
def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("slugify")
    s.add_argument("--question", required=True)

    h = sub.add_parser("hash")
    h.add_argument("--table-id", required=True)
    h.add_argument("--filters", required=True)

    r = sub.add_parser("render")
    r.add_argument("--question", required=True)
    r.add_argument("--table-id", required=True)
    r.add_argument("--table-title", required=True)
    r.add_argument("--filters", required=True, help="JSON Selection list")
    r.add_argument("--type", choices=["html", "dashboard"], required=True)
    r.add_argument("--data-file", required=True, type=Path)
    r.add_argument("--chart-spec", required=True, help="JSON chart spec")
    r.add_argument("--rationale", required=True)
    r.add_argument("--filterable-columns", default="", help="comma-separated")
    r.add_argument("--repo-root", default=".", type=Path)
    r.add_argument("--overwrite", action="store_true", help="Skip slug-conflict resolution; reuse existing slug (refresh path)")

    args = parser.parse_args()
    if args.cmd == "slugify":
        print(slugify(args.question))
        return 0
    if args.cmd == "hash":
        print(cache_key(args.table_id, json.loads(args.filters)))
        return 0
    if args.cmd == "render":
        return _cmd_render(args)
    return 2


def _cmd_render(args) -> int:
    today = _date.today()
    base_slug = slugify(args.question)
    slug = base_slug if args.overwrite else _resolve_slug_conflict(base_slug, args)
    chart_spec = json.loads(args.chart_spec)
    repo_root = args.repo_root.resolve()

    if args.type == "html":
        out_path = repo_root / "output" / "reports" / f"{slug}.html"
        render_html(
            out_path=out_path,
            title=chart_spec.get("title", args.table_title),
            rationale=args.rationale,
            table_id=args.table_id,
            generated=today,
            data_file=args.data_file,
            chart_spec=chart_spec,
        )
        rel_path = f"reports/{slug}.html"
    else:
        out_dir = repo_root / "output" / "dashboards" / slug
        filterable = [c for c in args.filterable_columns.split(",") if c.strip()]
        render_dashboard(
            out_dir=out_dir,
            slug=slug,
            title=args.table_title,
            rationale=args.rationale,
            question=args.question,
            table_id=args.table_id,
            generated=today,
            data_file=args.data_file,
            chart_spec=chart_spec,
            filterable_columns=filterable,
            filters_json=args.filters,
        )
        rel_path = f"dashboards/{slug}/"

    upsert_index_row(
        repo_root / "output" / "INDEX.md",
        generated=today,
        title=chart_spec.get("title", args.table_title),
        type_="HTML" if args.type == "html" else "Dashboard",
        table_id=args.table_id,
        path=rel_path,
    )
    print(f"OK {rel_path}")
    return 0


def _resolve_slug_conflict(base: str, args) -> str:
    """If a same-typed artifact with the same slug already exists, append -2, -3, ..., up to -9."""
    repo_root = args.repo_root.resolve()
    if args.type == "html":
        target = repo_root / "output" / "reports"
        suffix = ".html"
        exists = lambda s: (target / f"{s}{suffix}").exists()
    else:
        target = repo_root / "output" / "dashboards"
        exists = lambda s: (target / s).exists()
    if not exists(base):
        return base
    for i in range(2, 10):
        candidate = f"{base}-{i}"
        if not exists(candidate):
            return candidate
    raise SystemExit(f"Slug collision: 9 variants of '{base}' already exist. Pass an explicit --slug.")
```

- [ ] **Step 2: Smoke-test the render CLI end-to-end**

```bash
cd /Users/edevard/norway-unfiltered && cp tests/fixtures/sample_07459.parquet output/data/07459__c11ren00.parquet
python .claude/skills/ssb-report-generator/scripts/generate.py render \
    --question "lag rapport om befolkning i Oslo siste 5 aar" \
    --table-id 07459 \
    --table-title "Folkemengde, Oslo" \
    --filters '[{"variableCode":"Region","valueCodes":["0301"]}]' \
    --type html \
    --data-file output/data/07459__c11ren00.parquet \
    --chart-spec '{"chart_type":"line","x":"Tid","y":"value","title":"Befolkning i Oslo har vokst jevnt 2020–2024"}' \
    --rationale "Femårig trend, monoton vekst." \
    --repo-root .
ls -la output/reports/befolkning-i-oslo-siste-5-aar.html
grep -c "Kilde: SSB, tabell 07459" output/INDEX.md
```

Expected: artifact exists; INDEX shows 1 SSB-attributed entry.

- [ ] **Step 3: Clean up smoke + commit**

```bash
rm output/reports/befolkning-i-oslo-siste-5-aar.html output/data/07459__c11ren00.parquet
# Reset INDEX.md to empty header (we'll commit a clean version)
cat > output/INDEX.md <<'EOF'
# Norway Unfiltered — Generated Artifacts

> Auto-maintained by `.claude/skills/ssb-report-generator`. Do not edit manually — your changes will be overwritten on next generation.

| Generated | Title | Type | SSB Table | Path |
|-----------|-------|------|-----------|------|
EOF
git add .claude/skills/ssb-report-generator/scripts/generate.py output/INDEX.md
git commit -m "feat(generate): render CLI orchestrates slug+template+index update"
```

---

## Task 10: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Append the skill pointer**

Edit `/Users/edevard/norway-unfiltered/CLAUDE.md`, append:

```markdown

## Generating reports + dashboards

This repo includes a local skill `ssb-report-generator` (at `.claude/skills/ssb-report-generator/`) that turns Norwegian-statistics questions into either HTML reports or Streamlit dashboards using the SSB MCP. Visual identity is BearingPoint (palette in `.claude/skills/bearingpoint-brand/SKILL.md`).

- Catalog of generated artifacts: `output/INDEX.md`
- HTML reports: `output/reports/*.html`
- Streamlit dashboards: `output/dashboards/<slug>/app.py`
- Cached SSB data: `output/data/*.parquet` (gitignored)

Just ask: "lag rapport om …" or "lag dashboard for …".
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: point CLAUDE.md at the new ssb-report-generator skill"
```

---

## Task 11: End-to-end manual verification

This is verification, not new code. Tests must pass and one real SSB query must round-trip successfully before declaring done.

- [ ] **Step 1: Full unit suite green**

```bash
cd /Users/edevard/norway-unfiltered && python -m pytest tests/ -v
```

Expected: all tests pass (18 by current count).

- [ ] **Step 2: Verify skill is discoverable**

In a fresh Claude Code session in this repo, run `/help` or check the loaded skills list. Expect `ssb-report-generator` and `bearingpoint-brand` to appear under repo-local skills.

- [ ] **Step 3: Real SSB query — HTML happy path**

In Claude Code: `lag rapport om befolkningsutvikling i Oslo siste 10 år`. Verify Claude:
1. Triggers ssb-api workflow, picks table 07459
2. Proposes filters in chat, decides HTML
3. After your "ja", invokes `generate.py render --type html ...`
4. Reports the artifact path

Open the HTML in a browser. Expect: BP red line chart, Aptos/Calibri typography, SSB attribution footer, BP wordmark.

- [ ] **Step 4: Real SSB query — Streamlit happy path**

Ask: `lag interaktivt dashboard for arbeidsledighet per fylke`. After Claude generates the artifact, run:

```bash
streamlit run output/dashboards/<slug>/app.py
```

Expect: Streamlit opens with BP styling, sidebar filters, chart renders.

- [ ] **Step 5: Refresh round-trip**

Ask: `refresh dashboard <slug-from-step-4>`. Verify:
- Parquet file's mtime updates (cache bypassed)
- Dashboard `app.py` is re-rendered (mtime updates)
- The slug is **unchanged** — no new `<slug>-2/` directory created
- `output/INDEX.md` shows the **same single row** for this dashboard, with its `Generated` date advanced to today

If a `<slug>-2/` appears or INDEX gains a duplicate row, the refresh path failed to pass `--overwrite` to `generate.py render` — fix the SKILL.md workflow before continuing.

- [ ] **Step 6: Empty-result handling**

Ask: `lag rapport om eksport av varer til Mars`. Expect Claude to refuse cleanly with a "no matching table / empty result" message and NOT generate an artifact.

- [ ] **Step 7: Final commit if any tweaks made**

If any tweaks to skill markdown or templates were needed during E2E:

```bash
git add -A
git commit -m "fix: address E2E findings from manual verification"
```

---

## Done when

- All 18+ unit tests pass
- Three manual E2E scenarios (HTML, Streamlit, refresh) work in a fresh Claude Code session in this repo
- `output/INDEX.md` correctly catalogs all generated artifacts
- A reader who has never seen this repo can run a generated dashboard via the README in its folder
- Generated artifacts visibly use BearingPoint colors and typography while attributing data to SSB
