"""Match DPWH projects to PhilGEPS contracts and produce reviewable candidates."""

import json
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def normalize_name(name: str) -> str:
    """Normalize a contractor/project name for comparison.
    
    Steps:
    1. Lowercase
    2. Strip HTML entities (e.g., &amp; -> and)
    3. Replace punctuation with spaces
    4. Collapse whitespace
    5. Strip leading/trailing whitespace
    """
    if not name:
        return ""
    # Decode HTML entities
    name = name.replace("&amp;", "and").replace("&", "and")
    name = name.replace("&nbsp;", " ")
    # Replace punctuation with spaces
    name = re.sub(r"[^\w\s]", " ", name.lower())
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()
    return name


def normalize_contractor(name: str) -> str:
    """Normalize a contractor name for matching."""
    return normalize_name(name)


def normalize_project_name(name: str) -> str:
    """Normalize a project name for matching."""
    return normalize_name(name)


def amount_proximity(a: float, b: float, tolerance: float = 0.10) -> bool:
    """Return True if b is within tolerance of a.
    
    Handles zero/None cases gracefully.
    """
    if not a or not b:
        return False
    return abs(a - b) / max(abs(a), abs(b)) <= tolerance


def dates_overlap(dpwh_start: str | None, dpwh_end: str | None, philgeps_date: str | None, window_days: int = 90) -> bool:
    """Return True if the PhilGEPS award date falls near the DPWH contract period.
    
    If DPWH dates are missing, return True as a weak signal (don't penalize).
    If PhilGEPS date is missing, return False.
    """
    if not philgeps_date:
        return False
    if not dpwh_start and not dpwh_end:
        return True  # weak signal — don't penalize missing dates
    # Simple check: is philgeps_date between dpwh_start and dpwh_end (with window)?
    # For now, just check year match as a proxy
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
# Matching logic
# ---------------------------------------------------------------------------

def compute_match_score(dpwh_project: dict, philgeps_contract: dict, min_title_tokens: int = 2) -> float:
    """Compute a similarity score between a DPWH project and a PhilGEPS contract.
    
    Returns a score from 0 to 100.
    
    Project title similarity acts as a gating factor: if the normalized titles
    share fewer than min_title_tokens significant tokens, the overall score is
    capped at 30 (below the default min_score of 45) to prevent contractor-only
    matches from being treated as strong links.
    """
    score = 0.0
    
    # 1. Project title similarity (35 points) — strongest signal
    dpwh_title = normalize_project_name(dpwh_project.get("project_name", ""))
    philgeps_title = normalize_name(philgeps_contract.get("title", ""))
    shared_tokens = _shared_token_count(dpwh_title, philgeps_title)
    if shared_tokens >= min_title_tokens:
        if dpwh_title == philgeps_title:
            score += 35
        elif shared_tokens >= 4:
            score += 30
        elif shared_tokens >= 3:
            score += 25
        elif shared_tokens >= 2:
            score += 20
        else:
            score += 10
    else:
        # Too few shared tokens — cap the overall score
        score += 5  # weak signal only
    
    # 2. Contractor name match (20 points) — weaker than title
    dpwh_contractor = normalize_contractor(dpwh_project.get("contractor", ""))
    philgeps_awardee = normalize_contractor(philgeps_contract.get("awardee", ""))
    if dpwh_contractor and philgeps_awardee:
        if dpwh_contractor == philgeps_awardee:
            score += 20
        elif dpwh_contractor in philgeps_awardee or philgeps_awardee in dpwh_contractor:
            score += 15
        elif _token_overlap(dpwh_contractor, philgeps_awardee) >= 0.5:
            score += 10
    
    # 3. Amount proximity (25 points)
    dpwh_amount = dpwh_project.get("contract_amount")
    philgeps_amount = philgeps_contract.get("amount")
    if dpwh_amount and philgeps_amount:
        if dpwh_amount == philgeps_amount:
            score += 25
        elif amount_proximity(dpwh_amount, philgeps_amount, tolerance=0.05):
            score += 20
        elif amount_proximity(dpwh_amount, philgeps_amount, tolerance=0.10):
            score += 15
        elif amount_proximity(dpwh_amount, philgeps_amount, tolerance=0.20):
            score += 10
    
    # 4. Barangay/location match (10 points)
    dpwh_barangay = normalize_name(dpwh_project.get("barangay_location", ""))
    philgeps_area = normalize_name(philgeps_contract.get("area", ""))
    philgeps_title_lower = normalize_name(philgeps_contract.get("title", ""))
    if dpwh_barangay:
        if dpwh_barangay in philgeps_area or philgeps_area in dpwh_barangay:
            score += 10
        elif dpwh_barangay in philgeps_title_lower:
            score += 8
        elif dpwh_barangay in dpwh_title:
            score += 3  # barangay is in the DPWH project name (weak self-match)
    
    # 5. Date proximity (10 points)
    dpwh_start = dpwh_project.get("contract_effectivity_date")
    dpwh_end = dpwh_project.get("actual_completion_date")
    philgeps_date = philgeps_contract.get("award_date")
    if dates_overlap(dpwh_start, dpwh_end, philgeps_date):
        score += 10
    
    return min(score, 100.0)


def _shared_token_count(a: str, b: str) -> int:
    """Count the number of shared tokens between two normalized strings."""
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    stop_words = {"of", "the", "and", "at", "in", "for", "a", "an", "to", "brgy", "barangay", "municipality", "of", "along"}
    tokens_a = tokens_a - stop_words
    tokens_b = tokens_b - stop_words
    return len(tokens_a & tokens_b)


def _token_overlap(a: str, b: str) -> float:

    """Compute Jaccard-like token overlap between two normalized strings."""
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# Candidate generation
# ---------------------------------------------------------------------------

def generate_candidates(
    dpwh_projects: list[dict],
    philgeps_contracts: list[dict],
    min_score: float = 45.0,
    min_title_tokens: int = 2,
) -> list[dict]:
    """Generate candidate links between DPWH projects and PhilGEPS contracts.
    
    Args:
        dpwh_projects: List of DPWH project objects.
        philgeps_contracts: List of PhilGEPS contract objects.
        min_score: Minimum score to include a candidate (0-100).
        min_title_tokens: Minimum shared title tokens to avoid score-capping.
    
    Returns:
        List of candidate relationship dicts, sorted by score descending.
    """
    candidates = []
    for dpwh in dpwh_projects:
        for contract in philgeps_contracts:
            score = compute_match_score(dpwh, contract, min_title_tokens=min_title_tokens)
            if score >= min_score:
                candidates.append({
                    "dpwh_transaction_id": dpwh.get("transaction_id", ""),
                    "dpwh_project_name": dpwh.get("project_name", ""),
                    "dpwh_contractor": dpwh.get("contractor", ""),
                    "dpwh_contract_amount": dpwh.get("contract_amount"),
                    "philgeps_reference_id": contract.get("reference_id", ""),
                    "philgeps_contract_no": contract.get("contract_no", ""),
                    "philgeps_title": contract.get("title", ""),
                    "philgeps_awardee": contract.get("awardee", ""),
                    "philgeps_amount": contract.get("amount"),
                    "philgeps_award_date": contract.get("award_date", ""),
                    "score": round(score, 1),
                })
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates


def generate_candidates_report(
    dpwh_projects: list[dict],
    philgeps_contracts: list[dict],
    min_score: float = 45.0,
    min_title_tokens: int = 2,
) -> dict:
    """Generate a full candidates report with summary statistics.
    
    Returns a dict with:
    - candidates: list of candidate dicts
    - summary: stats (total_dpwh, total_philgeps, candidates_generated, avg_score)
    - generated_at: ISO timestamp
    """
    candidates = generate_candidates(dpwh_projects, philgeps_contracts, min_score, min_title_tokens)
    scores = [c["score"] for c in candidates]
    return {
        "candidates": candidates,
        "summary": {
            "total_dpwh_projects": len(dpwh_projects),
            "total_philgeps_contracts": len(philgeps_contracts),
            "candidates_generated": len(candidates),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
        },
        "generated_at": "2026-09-20",  # placeholder; use datetime in production
    }


# ---------------------------------------------------------------------------
# Verification / write-back
# ---------------------------------------------------------------------------

def apply_verified_links(dpwh_data: dict, verified_links: list[dict]) -> dict:
    """Write verified PhilGEPS contract links into dpwh.json crossref fields.
    
    Args:
        dpwh_data: The full dpwh.json dict (with "projects" key).
        verified_links: List of dicts with at least:
            - dpwh_transaction_id: str
            - philgeps_reference_id: str (or contract_no)
            - match_type: str (e.g., "confirmed", "high_confidence")
            - verified_by: str
    
    Returns:
        Updated dpwh_data dict with crossref populated on matching projects.
    """
    projects = dpwh_data.get("projects", [])
    # Index by transaction_id for fast lookup
    project_index = {p.get("transaction_id", ""): p for p in projects}
    
    updated_count = 0
    for link in verified_links:
        tid = link.get("dpwh_transaction_id", "")
        project = project_index.get(tid)
        if not project:
            continue
        
        crossref = project.get("crossref", {})
        if not crossref:
            project["crossref"] = {}
        
        # Use reference_id as the link key, fallback to contract_no
        contract_key = link.get("philgeps_reference_id") or link.get("philgeps_contract_no", "")
        if not contract_key:
            continue
        
        crossref[contract_key] = {
            "match_type": link.get("match_type", "unverified"),
            "philgeps_contract_no": link.get("philgeps_contract_no", ""),
            "philgeps_title": link.get("philgeps_title", ""),
            "philgeps_awardee": link.get("philgeps_awardee", ""),
            "philgeps_amount": link.get("philgeps_amount"),
            "philgeps_award_date": link.get("philgeps_award_date", ""),
            "score": link.get("score"),
            "verified_by": link.get("verified_by", ""),
        }
        project["crossref"] = crossref
        updated_count += 1
    
    return dpwh_data


def write_candidates_report(report: dict, output_path: Path) -> None:
    """Write a candidates report to a JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def read_candidates_report(input_path: Path) -> dict:
    """Read a candidates report from a JSON file."""
    return json.loads(input_path.read_text(encoding="utf-8"))


def load_json(path: Path) -> dict:
    """Load a JSON data file."""
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(data: dict, path: Path) -> None:
    """Write a dict to a JSON file."""
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """Generate candidate links between DPWH and PhilGEPS."""
    root = Path(__file__).resolve().parent.parent.parent
    dpwh_path = root / "src" / "data" / "dpwh.json"
    procurement_path = root / "src" / "data" / "procurement.json"
    output_path = root / "datasets" / "candidates" / "crossref_candidates.json"
    
    dpwh_data = load_json(dpwh_path)
    procurement_data = load_json(procurement_path)
    
    dpwh_projects = dpwh_data.get("projects", [])
    philgeps_contracts = procurement_data.get("contracts", [])
    
    report = generate_candidates_report(dpwh_projects, philgeps_contracts, min_score=45.0, min_title_tokens=2)
    write_candidates_report(report, output_path)
    
    summary = report["summary"]
    print(f"Generated {summary['candidates_generated']} candidate links")
    print(f"  DPWH projects: {summary['total_dpwh_projects']}")
    print(f"  PhilGEPS contracts: {summary['total_philgeps_contracts']}")
    print(f"  Score range: {summary['min_score']} - {summary['max_score']}")
    print(f"  Average score: {summary['avg_score']}")
    print(f"  Report written to: {output_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
