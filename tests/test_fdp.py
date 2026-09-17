"""FDP disclosure tests — extractor helpers, JSON integrity, generator output."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
FDP_PATH = ROOT / "src" / "data" / "fdp_disclosures.json"


def _load():
    return json.loads(FDP_PATH.read_text(encoding="utf-8"))


def test_to_float_coercions():
    from src.data.extract_fdp import to_float

    assert to_float(123.45) == 123.45
    assert to_float("5,755,400.00") == 5755400.00
    assert to_float("P 77,967,555.44") == 77967555.44
    assert to_float("N/A") is None
    assert to_float("NONE") is None
    assert to_float("not yet started") is None
    assert to_float("-") is None
    assert to_float(None) is None
    assert to_float("-3986694.35") == -3986694.35


def test_year_quarter_variants():
    from src.data.extract_fdp import parse_year_quarter

    assert parse_year_quarter(None, [["Period Covered:", "Q1, 2026"]]) == (2026, 1)
    assert parse_year_quarter(None, [["CALENDAR YEAR:", "", "2025"], ["QUARTER:", "", "4"]]) == (2025, 4)
    assert parse_year_quarter(None, [["REGION:", "1"]]) == (None, None)


def test_fdp_groups_present():
    data = _load()
    for key in ("sre", "sef", "ldrrmf", "bids", "dev_fund", "manpower",
                "indebtedness", "budget", "spp", "cash_advances"):
        assert len(data[key]) > 0, f"{key} empty"
    assert data["meta"]["municipality"] == "Mapandan, Pangasinan"


def test_periods_monotonic_per_form():
    data = _load()
    for key in ("sre", "sef", "ldrrmf", "cash_flows", "bids", "dev_fund"):
        periods = [r["period"] for r in data[key] if r.get("period") != "undated"]
        assert periods == sorted(periods), f"{key} periods not monotonic: {periods}"


def test_amounts_sane():
    data = _load()
    for rec in data["sre"]:
        for row in rec["rows"]:
            for field in ("target", "general_fund", "sef", "trust_fund"):
                value = row.get(field)
                assert value is None or value >= 0, f"sre {rec['period']} {row['label']}"
    for rec in data["dev_fund"]:
        for proj in rec["projects"]:
            assert proj.get("cost") is None or proj["cost"] >= 0
    for rec in data["bids"]:
        for bid in rec["civil_works"] + rec["goods"]:
            assert bid.get("abc") is None or bid["abc"] > 0
            assert bid.get("bidder"), f"bid without bidder in {rec['period']}"


def test_fdp_schema_validates():
    jsonschema = __import__("pytest").importorskip("jsonschema")
    assert jsonschema is not None
    from src.data.schemas import validate_all

    errors = [e for e in validate_all(ROOT / "src" / "data") if "fdp" in e]
    assert errors == []


def test_generator_renders_section():
    from _build.generators.fdp import _build_fdp_labels, generate_fdp
    from _build.locales import load_locale

    en_labels = _build_fdp_labels(load_locale("en"))
    fil_labels = _build_fdp_labels(load_locale("fil"))
    assert en_labels["FDP_TITLE"] == "DILG Disclosure Filings"
    assert fil_labels["FDP_TITLE"] == "Mga Isinumiteng Dokumento sa DILG"
    assert fil_labels["FDP_NIL"] != en_labels["FDP_NIL"]
    html = generate_fdp(load_locale("en"))
    assert 'id="fdp-disclosures"' in html
    assert "Q2 2026" in html
    assert "&#8369;" in html
    fil_html = generate_fdp(load_locale("fil"))
    assert "Pinakabagong filing" in fil_html
