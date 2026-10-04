"""Tests for COA project linker (COA -> DPWH / PhilGEPS matching)."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.link_coa_projects import (
    apply_verified_links,
    amount_proximity,
    generate_coa_dpwh_report,
    generate_coa_philgeps_report,
    match_coa_contractor_to_philgeps,
    match_coa_to_dpwh,
    normalize_name,
)


def test_normalize_name():
    assert normalize_name("TEST &amp; CO") == "test and co"
    assert "  " not in normalize_name("  many   spaces  ")
    assert normalize_name("hello, world!") == "hello world"
    assert normalize_name("Road Network, Brgy. Jimenez") == "road network brgy jimenez"


def test_amount_proximity():
    assert amount_proximity(1000000, 1000000) is True
    assert amount_proximity(1000000, 1050000) is True
    assert amount_proximity(1000000, 1100000) is True
    assert amount_proximity(1000000, 1200000) is False
    assert amount_proximity(0, 1000000) is False
    assert amount_proximity(1000000, 0) is False
    assert amount_proximity(None, 1000000) is False


def test_match_coa_to_dpwh_high_score():
    coa_project = {
        "project_title": "Construction of Road Network, Brgy. Jimenez",
        "cost": 4841163.36,
    }
    dpwh_projects = [
        {
            "transaction_id": "DPWH-1",
            "project_name": "DPWH Road Network Improvement, Brgy. Jimenez",
            "contract_amount": 4841163.36,
            "status": "Completed",
        }
    ]
    candidates = match_coa_to_dpwh(coa_project, dpwh_projects, min_score=0)
    assert len(candidates) >= 1
    assert candidates[0]["score"] >= 50


def test_match_coa_to_dpwh_low_score():
    coa_project = {
        "project_title": "Municipal Cemetery Extension",
        "cost": 54967555.44,
    }
    dpwh_projects = [
        {
            "transaction_id": "DPWH-1",
            "project_name": "Concreting of Farm to Market Road, Brgy. Luyan",
            "contract_amount": 1000000.0,
            "status": "Completed",
        }
    ]
    candidates = match_coa_to_dpwh(coa_project, dpwh_projects, min_score=35)
    assert len(candidates) == 0


def test_match_coa_contractor_to_philgeps_exact():
    coa_contractor = {
        "company_name": "JJEA AGRIVENTURES CO",
        "bid_amount": 819400.0,
    }
    philgeps_contracts = [
        {
            "reference_id": "ref-1",
            "awardee": "JJEA AGRIVENTURES CO.",
            "amount": 819400.0,
            "title": "Procurement of Support to Farmers - Fertilizer Assistance",
        }
    ]
    candidates = match_coa_contractor_to_philgeps(coa_contractor, philgeps_contracts, min_score=0)
    assert len(candidates) >= 1
    assert candidates[0]["score"] >= 50


def test_match_coa_contractor_to_philgeps_no_match():
    coa_contractor = {
        "company_name": "Unknown Contractor",
        "bid_amount": 500000.0,
    }
    philgeps_contracts = [
        {
            "reference_id": "ref-1",
            "awardee": "Some Other Company",
            "amount": 600000.0,
            "title": "Unrelated Contract",
        }
    ]
    candidates = match_coa_contractor_to_philgeps(coa_contractor, philgeps_contracts, min_score=40)
    assert len(candidates) == 0


def test_generate_coa_dpwh_report():
    root = Path(__file__).resolve().parent.parent
    coa_data = Path(root / "src" / "data" / "coa-project-findings.json")
    dpwh_data = Path(root / "src" / "data" / "dpwh.json")
    assert coa_data.exists()
    assert dpwh_data.exists()

    coa = json.loads(coa_data.read_text(encoding="utf-8"))
    dpwh = json.loads(dpwh_data.read_text(encoding="utf-8"))

    report = generate_coa_dpwh_report(coa, dpwh)
    assert "candidates" in report
    assert "summary" in report
    assert "generated_at" in report
    assert report["summary"]["total_coa_projects"] > 0
    assert report["summary"]["total_dpwh_projects"] > 0
    scores = [c["score"] for c in report["candidates"]]
    assert scores == sorted(scores, reverse=True)


def test_generate_coa_philgeps_report():
    root = Path(__file__).resolve().parent.parent
    coa_data = Path(root / "src" / "data" / "coa-project-findings.json")
    procurement_data = Path(root / "src" / "data" / "procurement.json")
    assert coa_data.exists()
    assert procurement_data.exists()

    coa = json.loads(coa_data.read_text(encoding="utf-8"))
    procurement = json.loads(procurement_data.read_text(encoding="utf-8"))

    report = generate_coa_philgeps_report(coa, procurement)
    assert "candidates" in report
    assert "summary" in report
    assert "generated_at" in report
    assert report["summary"]["total_coa_contractors"] >= 5
    high_score_candidates = [c for c in report["candidates"] if c["score"] >= 70]
    assert len(high_score_candidates) >= 1


def test_apply_verified_links_dpwh():
    dpwh_data = {
        "projects": [
            {
                "transaction_id": "dpwh-1",
                "project_name": "Road Improvement",
                "contractor": "ALPHIN",
                "contract_amount": 1000000,
                "coa_findings": [],
            }
        ]
    }
    procurement_data = {"contracts": []}
    verified_links = [
        {
            "target_type": "dpwh_project",
            "target_id": "dpwh-1",
            "coa_finding_id": "COA-2024-001",
            "coa_title": "Uncollected Damages",
            "coa_description": "Failure to collect liquidated damages",
            "coa_year": 2023,
            "coa_amount_cited": 127767.63,
            "coa_finding_type": "infrastructure",
            "verified_by": "analyst@example.com",
        }
    ]
    updated_dpwh, updated_procurement = apply_verified_links(dpwh_data, procurement_data, verified_links)
    project = updated_dpwh["projects"][0]
    assert len(project["coa_findings"]) == 1
    assert project["coa_findings"][0]["finding_id"] == "COA-2024-001"
    assert project["coa_findings"][0]["finding_type"] == "infrastructure"
    assert project["coa_findings"][0]["year"] == 2023
    assert project["coa_findings"][0]["amount_cited"] == 127767.63


def test_apply_verified_links_philgeps():
    dpwh_data = {"projects": []}
    procurement_data = {
        "contracts": [
            {
                "reference_id": "ref-1",
                "contract_no": "c1",
                "title": "Road Improvement",
                "awardee": "ALPHIN",
                "amount": 1000000,
                "award_date": "2023-05-15",
                "crossref": {},
            }
        ]
    }
    verified_links = [
        {
            "target_type": "philgeps_contract",
            "target_id": "ref-1",
            "coa_finding_id": "COA-2024-002",
            "coa_title": "Contract Variation",
            "coa_description": "Unapproved variation order",
            "coa_year": 2023,
            "coa_amount_cited": 500000.0,
            "coa_finding_type": "contract",
            "verified_by": "analyst@example.com",
        }
    ]
    updated_dpwh, updated_procurement = apply_verified_links(dpwh_data, procurement_data, verified_links)
    contract = updated_procurement["contracts"][0]
    assert "COA-2024-002" in contract["crossref"]
    assert contract["crossref"]["COA-2024-002"]["type"] == "coa_finding"
    assert contract["crossref"]["COA-2024-002"]["finding_type"] == "contract"


def test_apply_verified_links_unknown_target():
    dpwh_data = {
        "projects": [
            {
                "transaction_id": "dpwh-1",
                "project_name": "Road Improvement",
                "coa_findings": [],
            }
        ]
    }
    procurement_data = {
        "contracts": [
            {
                "reference_id": "ref-1",
                "contract_no": "c1",
                "title": "Road Improvement",
                "crossref": {},
            }
        ]
    }
    verified_links = [
        {
            "target_type": "dpwh_project",
            "target_id": "nonexistent-id",
            "coa_finding_id": "COA-2024-003",
            "coa_title": "Test",
            "coa_description": "Test",
            "coa_year": 2023,
            "coa_amount_cited": 100000.0,
            "coa_finding_type": "test",
            "verified_by": "tester",
        },
        {
            "target_type": "philgeps_contract",
            "target_id": "nonexistent-ref",
            "coa_finding_id": "COA-2024-004",
            "coa_title": "Test",
            "coa_description": "Test",
            "coa_year": 2023,
            "coa_amount_cited": 100000.0,
            "coa_finding_type": "test",
            "verified_by": "tester",
        },
    ]
    updated_dpwh, updated_procurement = apply_verified_links(dpwh_data, procurement_data, verified_links)
    assert updated_dpwh["projects"][0]["coa_findings"] == []
    assert updated_procurement["contracts"][0]["crossref"] == {}
