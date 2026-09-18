"""FDP disclosure tests — extractor helpers, JSON integrity, generator output."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
FDP_PATH = ROOT / "src" / "data" / "fdp_disclosures.json"

from src.data.extract_fdp import classify_csv, sniff_kind, read_rows, to_float, parse_year_quarter


def _load():
    return json.loads(FDP_PATH.read_text(encoding="utf-8"))


def test_to_float_coercions():
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
            if row["label"].upper().startswith("NET "):
                continue  # deficit quarters legitimately go negative
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


def test_csv_routing_covers_new_sheets():
    base = ROOT / "datasets" / "fdp-csv" / "2023"
    app_file = next(base.glob("*__APP_MDRRM_Office.csv"))
    assert classify_csv(app_file) == "app"
    summary = next(base.glob("*__Form_4b_-_APP_Summary.csv"))
    assert classify_csv(summary) == "app_summary"
    loan = next((base.parent / "2026").glob("*__TERM_LOAN_10.csv"))
    assert classify_csv(loan) == "sipb"
    enterprises = next((base.parent / "2024").glob("*__GENERAL_FUND.csv"))
    assert sniff_kind(read_rows(enterprises)) == "fund_matrix"
    calamity = next((base.parent / "2024").glob("*__LPB_2c_*"))
    assert sniff_kind(read_rows(calamity)) == "spa"


def test_app_offices_and_summary():
    data = _load()
    offices = sorted({r.get("office") for r in data["app"] if r.get("form") == "app" and r.get("office")})
    assert len(offices) >= 10, offices
    summaries = [r for r in data["app"] if r.get("form") == "app_summary"]
    assert summaries and summaries[0]["summary"], "APP summary missing"
    for rec in data["app"]:
        if rec.get("form") != "app":
            continue
        for item in rec["items"]:
            assert item["project"], rec.get("office")
            assert item.get("total") is None or item["total"] >= 0


def test_accuracy_regressions():
    """Pinned values from workbook verification (Q2 2026 unless noted)."""
    data = _load()
    sre = next(r for r in data["sre"] if r["period"] == "2026-Q2" and r.get("sheet") == "sre_report")
    income = next(r for r in sre["rows"] if r["label"] == "TOTAL CURRENT OPERATING INCOME")
    assert income["general_fund"] == 115479786.02
    cf = next(r for r in data["cash_flows"] if r["period"] == "2026-Q2")
    assert cf["key"]["ending"] == 63525772.21
    dev = next(r for r in data["dev_fund"] if r["period"] == "2026-Q2")
    assert not [p for p in dev["projects"] if p["project"].upper() == "TOTAL"]
    loan = next(p for p in dev["projects"] if "Loan" in p["project"])
    assert abs(loan["pct"] - 0.49667861375065) < 1e-6
    assert loan["incurred"] == 11272309.42
    assert len(dev["projects"]) == 19
