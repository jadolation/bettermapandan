"""Match COA project findings to DPWH projects, PhilGEPS contracts, and FDP records."""

import json
import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def normalize_name(name: str) -> str:
    """Normalize a name for comparison."""
    if not name:
        return ""
    name = name.replace("&amp;", "and").replace("&", "and")
    name = name.replace("&nbsp;", " ")
    name = re.sub(r"[^\w\s]", " ", name.lower())
    name = re.sub(r"\s+", " ", name).strip()
    return name


def normalize_contractor(name: str) -> str:
    return normalize_name(name)


def normalize_project_name(name: str) -> str:
    return normalize_name(name)


def amount_proximity(a: float, b: float, tolerance: float = 0.10) -> bool:
    if not a or not b:
        return False
    return abs(a - b) / max(abs(a), abs(b)) <= tolerance


def dates_overlap(dpwh_start: str | None, dpwh_end: str | None, philgeps_date: str | None, window_days: int = 90) -> bool:
    if not philgeps_date:
        return False
    if not dpwh_start and not dpwh_end:
        return True
    try:
        phil_year = int(philgeps_date[:4])
        if dpwh_start:
            dpwh_start_year = int(dpwh_start[:4])
            if phil_year == dpwh_start_year:
                return True
        if dpwh_end:
            dpwh_end_year = int(dpwh_end[:4])
            if phil_year == dpwh_end_year:
                return True
    except (ValueError, IndexError):
        pass
    return False


# ---------------------------------------------------------------------------
# Token overlap
# ---------------------------------------------------------------------------

def _token_overlap(a: str, b: str) -> float:
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def _shared_token_count(a: str, b: str) -> int:
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    stop_words = {"of", "the", "and", "at", "in", "for", "a", "an", "to", "brgy", "barangay", "municipality", "of", "along", "construction", "of", "road"}
    tokens_a = tokens_a - stop_words
    tokens_b = tokens_b - stop_words
    return len(tokens_a & tokens_b)


# ---------------------------------------------------------------------------
# Matching: COA project -> DPWH project
# ---------------------------------------------------------------------------

def match_coa_to_dpwh(coa_project: dict, dpwh_projects: list[dict], min_score: float = 35.0) -> list[dict]:
    """Match a single COA project finding to DPWH projects."""
    candidates = []
    coa_title = normalize_project_name(coa_project.get("project_title", ""))
    coa_amount = coa_project.get("cost")
    coa_status = normalize_name(coa_project.get("status", ""))
    
    for dpwh in dpwh_projects:
        score = 0.0
        
        # 1. Title similarity (40 points)
        dpwh_title = normalize_project_name(dpwh.get("project_name", ""))
        shared = _shared_token_count(coa_title, dpwh_title)
        if shared >= 3:
            score += 40
        elif shared >= 2:
            score += 30
        elif shared >= 1:
            score += 15
        elif coa_title == dpwh_title:
            score += 40
        
        # 2. Amount proximity (30 points)
        dpwh_amount = dpwh.get("contract_amount")
        if coa_amount and dpwh_amount:
            if coa_amount == dpwh_amount:
                score += 30
            elif amount_proximity(coa_amount, dpwh_amount, tolerance=0.05):
                score += 25
            elif amount_proximity(coa_amount, dpwh_amount, tolerance=0.10):
                score += 20
            elif amount_proximity(coa_amount, dpwh_amount, tolerance=0.20):
                score += 10
        
        # 3. Status/phase match (15 points)
        dpwh_status = normalize_name(dpwh.get("status", ""))
        if coa_status and dpwh_status:
            if coa_status in dpwh_status or dpwh_status in coa_status:
                score += 15
        
        # 4. Contractor match (15 points) — if COA project has contractor info
        # (not in current coa-project-findings.json project_names, but in contractor_names section)
        
        if score >= min_score:
            candidates.append({
                "coa_project_title": coa_project.get("project_title", ""),
                "coa_cost": coa_amount,
                "dpwh_transaction_id": dpwh.get("transaction_id", ""),
                "dpwh_project_name": dpwh.get("project_name", ""),
                "dpwh_contractor": dpwh.get("contractor", ""),
                "dpwh_contract_amount": dpwh_amount,
                "dpwh_status": dpwh.get("status", ""),
                "score": round(score, 1),
            })
    
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates


# ---------------------------------------------------------------------------
# Matching: COA contractor -> PhilGEPS contract
# ---------------------------------------------------------------------------

def match_coa_contractor_to_philgeps(coa_contractor: dict, philgeps_contracts: list[dict], min_score: float = 40.0) -> list[dict]:
    """Match a COA contractor entry to PhilGEPS contracts."""
    candidates = []
    coa_name = normalize_contractor(coa_contractor.get("company_name", ""))
    coa_project = normalize_project_name(coa_contractor.get("project", ""))
    coa_amount = coa_contractor.get("bid_amount")
    coa_ref = coa_contractor.get("reference_no", "")
    
    for contract in philgeps_contracts:
        score = 0.0
        
        # 1. Contractor name match (35 points)
        philgeps_awardee = normalize_contractor(contract.get("awardee", ""))
        if coa_name and philgeps_awardee:
            if coa_name == philgeps_awardee:
                score += 35
            elif coa_name in philgeps_awardee or philgeps_awardee in coa_name:
                score += 25
            elif _token_overlap(coa_name, philgeps_awardee) >= 0.5:
                score += 15
        
        # 2. Amount proximity (25 points)
        philgeps_amount = contract.get("amount")
        if coa_amount and philgeps_amount:
            if coa_amount == philgeps_amount:
                score += 25
            elif amount_proximity(coa_amount, philgeps_amount, tolerance=0.05):
                score += 20
            elif amount_proximity(coa_amount, philgeps_amount, tolerance=0.10):
                score += 15
        
        # 3. Project title similarity (25 points)
        philgeps_title = normalize_project_name(contract.get("title", ""))
        if coa_project and philgeps_title:
            shared = _shared_token_count(coa_project, philgeps_title)
            if shared >= 2:
                score += 25
            elif shared >= 1:
                score += 15
        
        # 4. Reference number match (15 points)
        philgeps_ref = normalize_name(contract.get("reference_id", "") or contract.get("contract_no", ""))
        if coa_ref and philgeps_ref:
            if coa_ref.lower() == philgeps_ref.lower():
                score += 15
        
        if score >= min_score:
            candidates.append({
                "coa_contractor": coa_contractor.get("company_name", ""),
                "coa_project": coa_contractor.get("project", ""),
                "coa_reference_no": coa_ref,
                "coa_bid_amount": coa_amount,
                "philgeps_reference_id": contract.get("reference_id", ""),
                "philgeps_contract_no": contract.get("contract_no", ""),
                "philgeps_title": contract.get("title", ""),
                "philgeps_awardee": contract.get("awardee", ""),
                "philgeps_amount": philgeps_amount,
                "philgeps_award_date": contract.get("award_date", ""),
                "score": round(score, 1),
            })
    
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates


# ---------------------------------------------------------------------------
# Matching: COA project -> FDP bid
# ---------------------------------------------------------------------------

def match_coa_to_fdp(coa_project: dict, fdp_bids: list[dict], min_score: float = 30.0) -> list[dict]:
    """Match a COA project finding to FDP bid records."""
    candidates = []
    coa_title = normalize_project_name(coa_project.get("project_title", ""))
    coa_amount = coa_project.get("cost")
    coa_fund = normalize_name(coa_project.get("fund_source", ""))
    
    for bid in fdp_bids:
        score = 0.0
        
        # 1. Project title similarity (40 points)
        bid_title = normalize_project_name(bid.get("project", "") or bid.get("description", ""))
        shared = _shared_token_count(coa_title, bid_title)
        if shared >= 3:
            score += 40
        elif shared >= 2:
            score += 30
        elif shared >= 1:
            score += 15
        
        # 2. Amount proximity (25 points)
        bid_amount = bid.get("amount") or bid.get("abc")
        if coa_amount and bid_amount:
            try:
                bid_amount = float(bid_amount)
                if coa_amount == bid_amount:
                    score += 25
                elif amount_proximity(coa_amount, bid_amount, tolerance=0.10):
                    score += 15
            except (ValueError, TypeError):
                pass
        
        # 3. Fund source match (20 points)
        bid_fund = normalize_name(bid.get("fund_source", "") or bid.get("fund", ""))
        if coa_fund and bid_fund:
            if coa_fund in bid_fund or bid_fund in coa_fund:
                score += 20
        
        # 4. Contractor match (15 points)
        bid_contractor = normalize_contractor(bid.get("contractor", "") or bid.get("winning_bidder", ""))
        if bid_contractor and len(bid_contractor) > 3:
            score += 5  # weak signal — contractor info in FDP is pre-award
        
        if score >= min_score:
            candidates.append({
                "coa_project_title": coa_project.get("project_title", ""),
                "coa_cost": coa_amount,
                "fdp_project": bid.get("project", "") or bid.get("description", ""),
                "fdp_amount": bid_amount,
                "fdp_fund_source": bid.get("fund_source", "") or bid.get("fund", ""),
                "fdp_contractor": bid.get("contractor", "") or bid.get("winning_bidder", ""),
                "score": round(score, 1),
            })
    
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_coa_dpwh_report(coa_data: dict, dpwh_data: dict, min_score: float = 35.0) -> dict:
    """Generate COA -> DPWH matching report."""
    coa_projects = coa_data.get("project_names", [])
    dpwh_projects = dpwh_data.get("projects", [])
    
    all_candidates = []
    for coa_proj in coa_projects:
        candidates = match_coa_to_dpwh(coa_proj, dpwh_projects, min_score)
        for c in candidates:
            c["coa_project_id"] = coa_proj.get("id", "")
            c["coa_fund_source"] = coa_proj.get("fund_source", "")
        all_candidates.extend(candidates)
    
    all_candidates.sort(key=lambda c: c["score"], reverse=True)
    scores = [c["score"] for c in all_candidates]
    return {
        "candidates": all_candidates,
        "summary": {
            "total_coa_projects": len(coa_projects),
            "total_dpwh_projects": len(dpwh_projects),
            "candidates_generated": len(all_candidates),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
        },
        "generated_at": "2026-09-20",
    }


def generate_coa_philgeps_report(coa_data: dict, procurement_data: dict, min_score: float = 40.0) -> dict:
    """Generate COA contractor -> PhilGEPS matching report."""
    coa_contractors = coa_data.get("contractor_names", [])
    philgeps_contracts = procurement_data.get("contracts", [])
    
    all_candidates = []
    for coa_contractor in coa_contractors:
        candidates = match_coa_contractor_to_philgeps(coa_contractor, philgeps_contracts, min_score)
        for c in candidates:
            c["coa_reference_no"] = coa_contractor.get("reference_no", "")
        all_candidates.extend(candidates)
    
    all_candidates.sort(key=lambda c: c["score"], reverse=True)
    scores = [c["score"] for c in all_candidates]
    return {
        "candidates": all_candidates,
        "summary": {
            "total_coa_contractors": len(coa_contractors),
            "total_philgeps_contracts": len(philgeps_contracts),
            "candidates_generated": len(all_candidates),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
        },
        "generated_at": "2026-09-20",
    }


def generate_coa_fdp_report(coa_data: dict, fdp_data: dict, min_score: float = 30.0) -> dict:
    """Generate COA project -> FDP bid matching report."""
    coa_projects = coa_data.get("project_names", [])
    fdp_bids = fdp_data.get("bids", [])
    
    all_candidates = []
    for coa_proj in coa_projects:
        candidates = match_coa_to_fdp(coa_proj, fdp_bids, min_score)
        for c in candidates:
            c["coa_project_id"] = coa_proj.get("id", "")
            c["coa_fund_source"] = coa_proj.get("fund_source", "")
        all_candidates.extend(candidates)
    
    all_candidates.sort(key=lambda c: c["score"], reverse=True)
    scores = [c["score"] for c in all_candidates]
    return {
        "candidates": all_candidates,
        "summary": {
            "total_coa_projects": len(coa_projects),
            "total_fdp_bids": len(fdp_bids),
            "candidates_generated": len(all_candidates),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
        },
        "generated_at": "2026-09-20",
    }


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(data: dict, path: Path) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_report(report: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_json(report, output_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def apply_verified_links(dpwh_data: dict, procurement_data: dict, verified_links: list[dict]) -> tuple[dict, dict]:
    """Write verified COA links into dpwh.json and procurement.json.
    
    Args:
        dpwh_data: Full dpwh.json dict.
        procurement_data: Full procurement.json dict.
        verified_links: List of dicts with keys:
            - target_type: "dpwh_project" or "philgeps_contract"
            - target_id: transaction_id (DPWH) or reference_id/contract_no (PhilGEPS)
            - coa_finding_id: str
            - coa_title: str
            - coa_description: str
            - coa_year: int
            - coa_amount_cited: float
            - coa_finding_type: str
            - verified_by: str
    
    Returns:
        Tuple of (updated_dpwh_data, updated_procurement_data).
    """
    dpwh_projects = dpwh_data.get("projects", [])
    dpwh_index = {p.get("transaction_id", ""): p for p in dpwh_projects}
    
    procurement_contracts = procurement_data.get("contracts", [])
    procurement_index = {}
    for c in procurement_contracts:
        ref = c.get("reference_id", "") or c.get("contract_no", "")
        if ref:
            procurement_index[ref] = c
    
    for link in verified_links:
        target_type = link.get("target_type", "")
        target_id = link.get("target_id", "")
        
        if target_type == "dpwh_project":
            project = dpwh_index.get(target_id)
            if not project:
                continue
            coa_findings = project.get("coa_findings", [])
            coa_findings.append({
                "finding_id": link.get("coa_finding_id", ""),
                "title": link.get("coa_title", ""),
                "description": link.get("coa_description", ""),
                "year": link.get("coa_year"),
                "amount_cited": link.get("coa_amount_cited"),
                "finding_type": link.get("coa_finding_type", ""),
                "source": f"COA AAR {link.get('coa_year', '')}",
                "verified_by": link.get("verified_by", ""),
            })
            project["coa_findings"] = coa_findings
        
        elif target_type == "philgeps_contract":
            contract = procurement_index.get(target_id)
            if not contract:
                continue
            crossref = contract.get("crossref", {})
            crossref[link.get("coa_finding_id", "")] = {
                "type": "coa_finding",
                "title": link.get("coa_title", ""),
                "year": link.get("coa_year"),
                "amount_cited": link.get("coa_amount_cited"),
                "finding_type": link.get("coa_finding_type", ""),
            }
            contract["crossref"] = crossref
    
    return dpwh_data, procurement_data
def main() -> int:
    root = Path(__file__).resolve().parent.parent.parent
    coa_path = root / "src" / "data" / "coa-project-findings.json"
    dpwh_path = root / "src" / "data" / "dpwh.json"
    procurement_path = root / "src" / "data" / "procurement.json"
    fdp_path = root / "src" / "data" / "fdp_disclosures.json"
    
    coa_data = load_json(coa_path)
    dpwh_data = load_json(dpwh_path)
    procurement_data = load_json(procurement_path)
    fdp_data = load_json(fdp_path)
    
    # COA -> DPWH
    dpwh_report = generate_coa_dpwh_report(coa_data, dpwh_data)
    write_report(dpwh_report, root / "datasets" / "candidates" / "coa_dpwh_candidates.json")
    print(f"COA -> DPWH: {dpwh_report['summary']['candidates_generated']} candidates")
    print(f"  Score range: {dpwh_report['summary']['min_score']} - {dpwh_report['summary']['max_score']}")
    
    # COA contractor -> PhilGEPS
    philgeps_report = generate_coa_philgeps_report(coa_data, procurement_data)
    write_report(philgeps_report, root / "datasets" / "candidates" / "coa_philgeps_candidates.json")
    print(f"COA -> PhilGEPS: {philgeps_report['summary']['candidates_generated']} candidates")
    print(f"  Score range: {philgeps_report['summary']['min_score']} - {philgeps_report['summary']['max_score']}")
    
    # COA -> FDP
    fdp_report = generate_coa_fdp_report(coa_data, fdp_data)
    write_report(fdp_report, root / "datasets" / "candidates" / "coa_fdp_candidates.json")
    print(f"COA -> FDP: {fdp_report['summary']['candidates_generated']} candidates")
    print(f"  Score range: {fdp_report['summary']['min_score']} - {fdp_report['summary']['max_score']}")
    
    # Demo: apply verified COA links
    verified_links = [
        {
            "target_type": "dpwh_project",
            "target_id": "",
            "coa_finding_id": "COA-2024-INF-001",
            "coa_title": "Uncollected Liquidated Damages",
            "coa_description": "Initial failure to collect liquidated damages...",
            "coa_year": 2023,
            "coa_amount_cited": 127767.63,
            "coa_finding_type": "infrastructure",
            "verified_by": "analyst@example.com",
        }
    ]
    updated_dpwh, updated_procurement = apply_verified_links(dpwh_data, procurement_data, verified_links)
    print(f"apply_verified_links: updated {updated_dpwh['summary']['total_projects']} dpwh projects")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
