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
