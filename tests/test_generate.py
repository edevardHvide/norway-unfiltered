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
