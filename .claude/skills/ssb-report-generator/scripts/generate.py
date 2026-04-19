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
import os
import re
import sys
import tempfile
from datetime import date as _date
from pathlib import Path
from typing import NamedTuple

import pandas as pd
import plotly.graph_objects as go
from jinja2 import Environment, FileSystemLoader, select_autoescape

STOP_WORDS = {
    "lag", "vis", "make", "show", "for", "om", "the", "a", "an",
    "of", "on", "and", "to", "report", "rapport",
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


def _to_list(v):
    # Plotly 6.x serializes numpy/pandas arrays as base64-encoded bdata by default,
    # which breaks substring assertions on the figure JSON. Convert to plain lists
    # so the JSON contains the raw numeric values.
    if hasattr(v, "tolist"):
        return v.tolist()
    return list(v)


def _trace(chart_type: str, x, y, name: str, color: str):
    x = _to_list(x)
    y = _to_list(y)
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

    readme_tmpl = env.get_template("dashboard_readme.md.j2")
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


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("slugify")
    s.add_argument("--question", required=True)

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


if __name__ == "__main__":
    sys.exit(main())
