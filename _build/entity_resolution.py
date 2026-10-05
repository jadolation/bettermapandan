"""Canonical entity resolution for Better Mapandan (Data Architecture v2).

Builds on the battle-tested matchers in src/data/link_procurement_dpwh.py
and src/data/link_coa_projects.py (imported, not duplicated) and adds:

- normalized record adapters per source (PhilGEPS contract, FDP bid,
  FDP development project, DPWH project),
- deterministic Rules 1-5, each returning (decision, evidence, level),
- evidence levels: explicit / strong / probable / possible / unmatched.

Fuzzy similarity (Rule 6) is intentionally absent: anything below the
deterministic bar belongs in datasets/review/ as `possible`, never as
a silent auto-match.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data._utils import (  # noqa: E402
    normalize_barangays,
    parse_fdp_date,
)
from src.data.link_procurement_dpwh import (  # noqa: E402
    amount_proximity,
    normalize_contractor,
    normalize_name,
)

EVIDENCE_LEVELS = ("explicit", "strong", "probable", "possible", "unmatched")


def norm_title(title: str) -> str:
    """Normalized project/contract title for comparison.

    Strips leading program tags (e.g. LDF-) that otherwise poison
    token-subset matching: "LDF-construction of Landbank ATM Hub"
    must match "Construction of LandBank ATM Hub at Pandan Avenue".
    """
    t = re.sub(r"^[A-Za-z]{2,4}-", "", (title or "").strip())
    return normalize_name(t)


def norm_contractor(name: str) -> str:
    """Normalized contractor/awardee/bidder name."""
    return normalize_contractor(name or "")


def norm_philgeps_contract(contract: dict) -> dict:
    """Adapter: raw PhilGEPS record -> normalized comparison record."""
    return {
        "source": "philgeps",
        "ref": contract.get("reference_id") or contract.get("contract_no") or "",
        "title": norm_title(contract.get("title", "")),
        "contractor": norm_contractor(contract.get("awardee", "")),
        "amount": float(contract.get("amount") or 0),
        "year": (contract.get("award_date") or "")[:4] or None,
        "barangays": normalize_barangays(contract.get("title", "")),
    }


def norm_fdp_bid(bid: dict) -> dict:
    """Adapter: raw FDP bid row -> normalized comparison record."""
    return {
        "source": "fdp-bids",
        "ref": bid.get("ref", ""),
        "title": norm_title(bid.get("project", "")),
        "contractor": norm_contractor(bid.get("bidder", "")),
        "amount": float(bid.get("bid_amount") or 0),
        "year": (parse_fdp_date(bid.get("award_date", "")) or "")[:4] or None,
        "barangays": normalize_barangays(bid.get("location", "")),
    }


def norm_fdp_project(row: dict, period: str = "") -> dict:
    """Adapter: raw FDP development-fund row -> normalized record."""
    return {
        "source": "fdp-dev",
        "ref": "",
        "title": norm_title(row.get("project", "")),
        "contractor": "",
        "amount": float(row.get("cost") or 0),
        "year": (period.split("-")[0] if "-" in (period or "") else None),
        "barangays": normalize_barangays(row.get("location", "")),
    }


def norm_dpwh_project(project: dict) -> dict:
    """Adapter: raw DPWH record -> normalized comparison record."""
    return {
        "source": "dpwh",
        "ref": project.get("contract_id", ""),
        "title": norm_title(project.get("project_name", "")),
        "contractor": norm_contractor(project.get("contractor", "")),
        "amount": float(project.get("contract_amount") or 0),
        "year": str(project.get("fiscal_year") or "") or None,
        "barangays": normalize_barangays(project.get("barangay_location", "")),
    }


def _titles_match(a: str, b: str, min_tokens: int = 2) -> bool:
    """Same-title rule: all significant tokens of the shorter title present."""
    stop = {"of", "the", "and", "for", "at", "in", "brgy", "barangay", "phase"}
    ta = [w for w in a.split() if w not in stop and len(w) > 2]
    tb = [w for w in b.split() if w not in stop and len(w) > 2]
    if not ta or not tb:
        return False
    short, long_ = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if len(short) < min_tokens:
        return False
    return all(w in long_ for w in short)


def _phase_markers(title: str) -> set:
    """Explicit phase/stage markers in a normalized title.

    Returns e.g. {"3"} for "phase iii", "phase 3", "stage 3". Roman
    numerals (len>=2 only, to avoid matching initials) normalize to digits.
    """
    marks = set()
    for m in re.finditer(r"\b(?:phase|stage|part)\s+([ivxlcdm\d]+)\b", title or ""):
        tok = m.group(1).upper()
        roman = {"I": "1", "II": "2", "III": "3", "IV": "4", "V": "5",
                 "VI": "6", "VII": "7", "VIII": "8", "IX": "9", "X": "10"}
        marks.add(roman.get(tok, tok.lstrip("0") or "0"))
    for m in re.finditer(r"\b([IVXLCDM]{2,})\b", title or ""):
        tok = m.group(1).upper()
        roman = {"II": "2", "III": "3", "IV": "4", "VI": "6", "VII": "7",
                 "VIII": "8", "IX": "9"}
        if tok in roman:
            marks.add(roman[tok])
    return marks


def _phase_conflict(a: str, b: str) -> bool:
    """True when titles carry differing explicit phase markers.

    Base-vs-Phase, Phase 3-vs-4, Stage II-vs-III all conflict: generic
    municipal titles recur across tranches, so phase mismatch blocks
    title-based auto-matching (Rules 2-4). Exact reference matches
    (Rule 1) and contractor+amount matches (Rule 5) are unaffected —
    they do not assert title identity.
    """
    ma, mb = _phase_markers(a), _phase_markers(b)
    # Conflict unless both sides agree (including both unmarked).
    return bool(ma != mb and (ma or mb))


def _amounts_close(a: float, b: float, tolerance: float = 0.05) -> bool:
    """Amount proximity within tolerance (Rule 5 helper)."""
    if not a or not b:
        return False
    return amount_proximity(a, b, tolerance=tolerance)


def rule_reference_id(a: dict, b: dict):
    """Rule 1: exact project/reference ID. Level: explicit."""
    if a.get("ref") and a["ref"] == b.get("ref"):
        return (True, ["same reference id"], "explicit")
    return (False, [], "unmatched")


def rule_title_year(a: dict, b: dict):
    """Rule 2: same title + same year. Level: probable."""
    if _phase_conflict(a.get("title", ""), b.get("title", "")):
        return (False, [], "unmatched")
    if a.get("title") and a["title"] == b["title"] and a.get("year") and a["year"] == b["year"]:
        return (True, ["same project title", "same fiscal year"], "probable")
    if _titles_match(a.get("title", ""), b.get("title", "")) and a.get("year") and a["year"] == b.get("year"):
        return (True, ["similar project title", "same fiscal year"], "probable")
    return (False, [], "unmatched")


def rule_title_barangay_year(a: dict, b: dict):
    """Rule 3: same title + barangay + year. Level: strong."""
    if not (a.get("title") and b.get("title")):
        return (False, [], "unmatched")
    if _phase_conflict(a["title"], b["title"]):
        return (False, [], "unmatched")
    same_title = a["title"] == b["title"] or _titles_match(a["title"], b["title"])
    same_brgy = bool(set(a.get("barangays", [])) & set(b.get("barangays", [])))
    same_year = bool(a.get("year")) and a["year"] == b.get("year")
    if same_title and same_brgy and same_year:
        return (True, ["same project title", "same barangay", "same fiscal year"], "strong")
    return (False, [], "unmatched")


def _contractors_match(a: str, b: str) -> bool:
    """Contractor identity: exact match, or the shorter name's significant
    tokens are all present in the longer one ("J.L. De Guzman" vs
    "J.L. De Guzman Enterprises")."""
    if not a or not b:
        return False
    if a == b:
        return True
    return _titles_match(a, b, min_tokens=1)


def rule_title_contractor_year(a: dict, b: dict):
    """Rule 4: same title + contractor + year. Level: strong."""
    if not (a.get("title") and b.get("title")):
        return (False, [], "unmatched")
    if _phase_conflict(a["title"], b["title"]):
        return (False, [], "unmatched")
    same_title = a["title"] == b["title"] or _titles_match(a["title"], b["title"])
    same_cont = _contractors_match(a.get("contractor", ""), b.get("contractor", ""))
    same_year = bool(a.get("year")) and a["year"] == b.get("year")
    if same_title and same_cont and same_year:
        return (True, ["same project title", "same contractor", "same fiscal year"], "strong")
    return (False, [], "unmatched")


def rule_contractor_amount_period(a: dict, b: dict):
    """Rule 5: same contractor + approximate amount + same period. Level: probable."""
    same_cont = _contractors_match(a.get("contractor", ""), b.get("contractor", ""))
    close_amt = _amounts_close(a.get("amount", 0), b.get("amount", 0))
    same_year = bool(a.get("year")) and a["year"] == b.get("year")
    if same_cont and close_amt and same_year:
        return (True, ["same contractor", "matching amount", "same fiscal year"], "probable")
    return (False, [], "unmatched")


DETERMINISTIC_RULES = (
    rule_reference_id,
    rule_title_barangay_year,
    rule_title_contractor_year,
    rule_title_year,
    rule_contractor_amount_period,
)


def match_records(a: dict, b: dict) -> dict:
    """Run deterministic Rules 1-5 strongest-first; first hit wins.

    This resolves ENTITY IDENTITY (are these the same activity?) — a
    single canonical decision per pair. It does not enumerate every
    valid association: relationship discovery downstream is multi-valued
    and may preserve several evidenced links (e.g. two co-member
    projects sharing one award).

    Title-based rules (2-4) refuse pairs with conflicting explicit phase
    markers; exact reference (Rule 1) and contractor+amount (Rule 5) do
    not assert title identity and are unaffected.

    Returns {"matched": bool, "rule": name|None, "evidence": [...],
    "level": explicit|strong|probable|possible|unmatched}.
    """
    for rule in DETERMINISTIC_RULES:
        hit, evidence, level = rule(a, b)
        if hit:
            return {"matched": True, "rule": rule.__name__, "evidence": evidence, "level": level}
    return {"matched": False, "rule": None, "evidence": [], "level": "unmatched"}
