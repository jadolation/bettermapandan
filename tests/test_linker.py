"""Tests for the DPWH-PhilGEPS cross-source linker."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.link_procurement_dpwh import (
    apply_verified_links,
    amount_proximity,
    compute_match_score,
    dates_overlap,
    generate_candidates,
    generate_candidates_report,
    normalize_contractor,
    normalize_name,
)


def test_normalize_name():
    assert normalize_name("TEST &amp; CO") == "test and co"
    assert "  " not in normalize_name("  many   spaces  ")
    assert normalize_name("hello, world!") == "hello world"


def test_normalize_contractor():
    assert normalize_contractor("JEUSMACK BUILDERS & CONSTRUCTION SUPPLY") == "jeusmack builders and construction supply"
    assert normalize_contractor("ALPHIN TRADING AND CONSTRUCTION") == "alphin trading and construction"


def test_amount_proximity():
    assert amount_proximity(1000000, 1000000) is True
    assert amount_proximity(1000000, 1050000) is True
    assert amount_proximity(1000000, 1100000) is True
    assert amount_proximity(1000000, 1200000) is False
    assert amount_proximity(0, 1000000) is False
    assert amount_proximity(1000000, 0) is False
    assert amount_proximity(None, 1000000) is False


def test_dates_overlap():
    assert dates_overlap("2023-06-01", None, "2023-05-15") is True
    assert dates_overlap("2023-06-01", None, "2024-01-01") is False
    assert dates_overlap("2023-06-01", None, None) is False
    assert dates_overlap(None, None, "2023-05-15") is True


def test_compute_match_score():
    base_dpwh = {
        "transaction_id": "dpwh-1",
        "project_name": "Road Improvement",
        "contractor": "ALPHIN TRADING AND CONSTRUCTION",
        "contract_amount": 1000000,
        "barangay_location": "Test Barangay",
        "contract_effectivity_date": "2023-06-01",
        "actual_completion_date": "2023-12-31",
    }
    same_contract = {
        "reference_id": "ref-1",
        "contract_no": "c1",
        "title": "Road Improvement",
        "awardee": "ALPHIN TRADING AND CONSTRUCTION",
        "amount": 1000000,
        "award_date": "2023-05-15",
        "area": "Test Barangay",
    }
    score = compute_match_score(base_dpwh, same_contract)
    assert score >= 80

    diff_contract = {
        "reference_id": "ref-2",
        "contract_no": "c2",
        "title": "Bridge Construction",
        "awardee": "OTHER CONTRACTOR",
        "amount": 500000,
        "award_date": "2024-01-01",
        "area": "Other Area",
    }
    score = compute_match_score(base_dpwh, diff_contract)
    assert score < 30


def test_generate_candidates_filters_low_scores():
    dpwh_projects = [
        {
            "transaction_id": "dpwh-1",
            "project_name": "Road Improvement Project",
            "contractor": "ALPHIN TRADING AND CONSTRUCTION",
            "contract_amount": 1000000,
            "barangay_location": "Test Barangay",
            "contract_effectivity_date": "2023-06-01",
            "actual_completion_date": "2023-12-31",
        },
        {
            "transaction_id": "dpwh-2",
            "project_name": "Bridge Construction Project",
            "contractor": "BUILDMASTER INC",
            "contract_amount": 2000000,
            "barangay_location": "Other Barangay",
            "contract_effectivity_date": "2023-01-01",
            "actual_completion_date": "2023-06-30",
        },
    ]
    philgeps_contracts = [
        {
            "reference_id": "ref-1",
            "contract_no": "c1",
            "title": "Road Improvement Project",
            "awardee": "ALPHIN TRADING AND CONSTRUCTION",
            "amount": 1000000,
            "award_date": "2023-05-15",
            "area": "Test Barangay",
        },
        {
            "reference_id": "ref-2",
            "contract_no": "c2",
            "title": "Water Supply Project",
            "awardee": "BUILDMASTER INC",
            "amount": 500000,
            "award_date": "2024-01-01",
            "area": "Other Area",
        },
    ]
    candidates = generate_candidates(dpwh_projects, philgeps_contracts, min_score=45)
    assert len(candidates) == 1
    assert candidates[0]["dpwh_transaction_id"] == "dpwh-1"


def test_generate_candidates_sorted_by_score():
    dpwh_projects = [
        {
            "transaction_id": "dpwh-1",
            "project_name": "Road Improvement",
            "contractor": "ALPHIN",
            "contract_amount": 1000000,
            "barangay_location": "Test",
            "contract_effectivity_date": "2023-06-01",
            "actual_completion_date": "2023-12-31",
        },
    ]
    philgeps_contracts = [
        {
            "reference_id": "ref-1",
            "contract_no": "c1",
            "title": "Road Improvement",
            "awardee": "ALPHIN",
            "amount": 1000000,
            "award_date": "2023-05-15",
            "area": "Test",
        },
        {
            "reference_id": "ref-2",
            "contract_no": "c2",
            "title": "Road Improvement",
            "awardee": "ALPHIN",
            "amount": 900000,
            "award_date": "2023-05-15",
            "area": "Test",
        },
    ]
    candidates = generate_candidates(dpwh_projects, philgeps_contracts, min_score=0)
    assert candidates[0]["score"] >= candidates[1]["score"]


def test_apply_verified_links():
    dpwh_data = {
        "projects": [
            {
                "transaction_id": "dpwh-1",
                "project_name": "Road Improvement",
                "contractor": "ALPHIN",
                "contract_amount": 1000000,
                "crossref": {},
            },
            {
                "transaction_id": "dpwh-2",
                "project_name": "Bridge Construction",
                "contractor": "BUILDMASTER",
                "contract_amount": 2000000,
                "crossref": {"existing-ref": {"match_type": "confirmed"}},
            },
        ]
    }
    verified_links = [
        {
            "dpwh_transaction_id": "dpwh-1",
            "philgeps_reference_id": "ref-1",
            "philgeps_contract_no": "c1",
            "philgeps_title": "Road Improvement",
            "philgeps_awardee": "ALPHIN",
            "philgeps_amount": 1000000,
            "philgeps_award_date": "2023-05-15",
            "score": 90,
            "match_type": "confirmed",
            "verified_by": "tester",
        }
    ]
    result = apply_verified_links(dpwh_data, verified_links)
    project_1 = next(p for p in result["projects"] if p["transaction_id"] == "dpwh-1")
    assert "ref-1" in project_1["crossref"]
    assert project_1["crossref"]["ref-1"]["match_type"] == "confirmed"

    project_2 = next(p for p in result["projects"] if p["transaction_id"] == "dpwh-2")
    assert "existing-ref" in project_2["crossref"]


def test_apply_verified_links_unknown_transaction_id():
    dpwh_data = {
        "projects": [
            {
                "transaction_id": "dpwh-1",
                "project_name": "Road Improvement",
                "contractor": "ALPHIN",
                "contract_amount": 1000000,
                "crossref": {},
            }
        ]
    }
    verified_links = [
        {
            "dpwh_transaction_id": "nonexistent-id",
            "philgeps_reference_id": "ref-1",
            "philgeps_contract_no": "c1",
            "philgeps_title": "Road Improvement",
            "philgeps_awardee": "ALPHIN",
            "philgeps_amount": 1000000,
            "philgeps_award_date": "2023-05-15",
            "score": 90,
            "match_type": "confirmed",
            "verified_by": "tester",
        }
    ]
    result = apply_verified_links(dpwh_data, verified_links)
    project_1 = next(p for p in result["projects"] if p["transaction_id"] == "dpwh-1")
    assert project_1["crossref"] == {}


def test_generate_candidates_report():
    dpwh_projects = [
        {
            "transaction_id": "dpwh-1",
            "project_name": "Road Improvement",
            "contractor": "ALPHIN",
            "contract_amount": 1000000,
            "barangay_location": "Test",
            "contract_effectivity_date": "2023-06-01",
            "actual_completion_date": "2023-12-31",
        }
    ]
    philgeps_contracts = [
        {
            "reference_id": "ref-1",
            "contract_no": "c1",
            "title": "Road Improvement",
            "awardee": "ALPHIN",
            "amount": 1000000,
            "award_date": "2023-05-15",
            "area": "Test",
        }
    ]
    report = generate_candidates_report(dpwh_projects, philgeps_contracts, min_score=0)
    assert "candidates" in report
    assert "summary" in report
    assert "generated_at" in report
    assert report["summary"]["total_dpwh_projects"] == 1
    assert report["summary"]["total_philgeps_contracts"] == 1
    assert report["summary"]["candidates_generated"] >= 1
