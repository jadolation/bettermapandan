"""Tests for _build/entity_resolution.py — deterministic Rules 1-5."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _build import entity_resolution as er


def _rec(**kw):
    base = {"source": "t", "ref": "", "title": "", "contractor": "",
            "amount": 0.0, "year": None, "barangays": []}
    base.update(kw)
    return base


def test_rule_reference_id_explicit():
    a = _rec(ref="INFR-MUN-2023-07-006")
    b = _rec(ref="INFR-MUN-2023-07-006")
    out = er.match_records(a, b)
    assert out == {"matched": True, "rule": "rule_reference_id",
                   "evidence": ["same reference id"], "level": "explicit"}


def test_rule_title_contractor_year_strong():
    a = _rec(title="construction of one 1 stop shop building phase 3",
             contractor="j l de guzman", amount=2997955.38, year="2023")
    b = _rec(title="construction of one 1 stop shop building phase 3",
             contractor="j l de guzman enterprises", amount=2997995.38, year="2023")
    out = er.match_records(a, b)
    assert out["matched"] and out["level"] == "strong"
    assert out["rule"] == "rule_title_contractor_year"


def test_rule_title_barangay_year_strong():
    a = _rec(title="improvement of multi purpose covered court",
             year="2023", barangays=["Baloling"])
    b = _rec(title="improvement of multi purpose covered court at brgy",
             year="2023", barangays=["Baloling", "Sta. Maria"])
    out = er.match_records(a, b)
    assert out["matched"] and out["level"] == "strong"


def test_rule_contractor_amount_period_probable():
    a = _rec(contractor="ubet trading", amount=998999.70, year="2023")
    b = _rec(contractor="ubet trading", amount=999000.00, year="2023")
    out = er.match_records(a, b)
    assert out["matched"] and out["level"] == "probable"


def test_no_match_unmatched():
    a = _rec(title="supply of office paper", contractor="ubet trading",
             amount=50000.0, year="2023")
    b = _rec(title="construction of covered court", contractor="r f flores",
             amount=995014.52, year="2023")
    assert er.match_records(a, b)["level"] == "unmatched"


def test_evidence_levels_valid():
    assert set(er.EVIDENCE_LEVELS) == {"explicit", "strong", "probable", "possible", "unmatched"}


def test_normalize_barangay_matrix():
    from src.data._utils import normalize_barangay, normalize_barangays
    assert normalize_barangay("Brgy. Baloling, Mapandan") == "Baloling"
    assert normalize_barangay("Brgy.Nilombot") == "Nilombot"
    assert normalize_barangay("Brgy. Golden., Mapandan") == "Golden"
    assert normalize_barangay("Entire Mapandan, Pang.") == ""
    banks = normalize_barangays("Brgy. Amanaoaoac / Brgy. Torres")
    assert [ord(c) for c in banks[0]] == [65, 109, 97, 110, 111, 97, 111, 97, 99]
    assert banks[1] == "Torres"


def test_parse_fdp_date_matrix():
    from src.data._utils import parse_fdp_date
    assert parse_fdp_date("May 19, 2023 at 9:00 AM") == "2023-05-19"
    assert parse_fdp_date("June 08,2026") == "2026-06-08"
    assert parse_fdp_date("December 11 at 9:00 AM") is None
    assert parse_fdp_date("1498197.06") is None
