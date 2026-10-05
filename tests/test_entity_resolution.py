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


def test_phase_mismatch_blocks_title_rules():
    """Base vs Phase III, Phase 3 vs 4: same activity family, different
    tranches — must never auto-merge, regardless of other rules."""
    base = _rec(title="improvement of mapandan public market", year="2023")
    phase3 = _rec(title="improvement of mapandan public market phase iii", year="2023")
    assert er.match_records(base, phase3)["level"] == "unmatched"
    p3 = _rec(title="construction of one 1 stop shop building phase 3", year="2023")
    p4 = _rec(title="construction of one 1 stop shop building phase 4", year="2025")
    assert er.match_records(p3, p4)["level"] == "unmatched"


def test_phase_agreement_still_matches():
    """Identical markers (Phase III vs Phase 3) must not block."""
    a = _rec(title="drainage canal phase iii", year="2024")
    b = _rec(title="drainage canal phase 3", year="2024")
    assert er.match_records(a, b)["matched"] is True


def test_reference_id_ignores_phase_guard():
    """Rule 1 asserts record identity, not title identity — unaffected."""
    a = _rec(ref="INFR-MUN-2023-11-016", title="market base", year="2023")
    b = _rec(ref="INFR-MUN-2023-11-016", title="market phase iii", year="2023")
    out = er.match_records(a, b)
    assert out["level"] == "explicit" and out["rule"] == "rule_reference_id"


def test_generic_title_variants_stay_distinct():
    """Tennis court vs clubhouse, stalls vs sewerage plant: shared generic
    words must not merge different facilities."""
    a = _rec(title="renovation of mapandan tennis club court", year="2023")
    b = _rec(title="improvement of mapandan tennis clubhouse", year="2023")
    assert er.match_records(a, b)["level"] == "unmatched"
    c = _rec(title="construction of stalls for ambulant vendors at public market", year="2026")
    d = _rec(title="construction of sewerage treatment plant at public market", year="2026")
    assert er.match_records(c, d)["level"] == "unmatched"


def test_typo_pairs_stay_unmatched():
    """Papata/Papaya, conctruction/construction: near-duplicates must go
    to human review, never auto-merge."""
    a = _rec(title="improvement brgy road papata ave apaya", year="2023")
    b = _rec(title="improvement brgy road papaya ave apaya", year="2023")
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
