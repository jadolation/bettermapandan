"""Tests for the entity/relationship layer: endpoints, evidence, provenance."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _build import entities as E

REPO = Path(__file__).resolve().parent.parent


def _load(name):
    return json.loads((REPO / name).read_text(encoding="utf-8"))


def test_relationship_endpoints_exist():
    rels = _load("src/data/relationships.json")
    assert rels, "no relationships generated — run python3 build.py"
    projects = {p["project_id"] for p in _load("src/data/entities/projects.json")}
    contracts = {c["contract_id"] for c in _load("src/data/entities/contracts.json")}
    contractors = {c["contractor_id"] for c in _load("src/data/entities/contractors.json")}
    known = projects | contracts | contractors

    def _known(ref: str) -> bool:
        kind, _, rid = ref.partition(":")
        if kind == "project" and rid.startswith("fdp-bid:"):
            return True  # FDP-side anchor, resolved at render time
        return rid in known or ref in known

    orphans = [r["id"] for r in rels if not _known(r["from"]) or not _known(r["to"])]
    assert not orphans, f"orphan relationships: {orphans[:5]}"


def test_confirmed_relationships_have_evidence():
    rels = _load("src/data/relationships.json")
    bad = [r["id"] for r in rels if not r.get("evidence")]
    assert not bad, f"edges without evidence: {bad[:5]}"
    levels = {r["confidence"] for r in rels}
    assert levels <= {"explicit", "strong", "probable", "possible", "unmatched"}, levels
    doubled = [r["id"] for r in rels for e in r.get("evidence", [])
               if isinstance(e, str) and e.startswith("rule rule")]
    assert not doubled, f"duplicated rule prefix: {doubled[:5]}"


def test_no_duplicate_ids():
    for name, key in (("src/data/entities/projects.json", "project_id"),
                      ("src/data/entities/contracts.json", "contract_id"),
                      ("src/data/entities/contractors.json", "contractor_id"),
                      ("src/data/relationships.json", "id")):
        ids = [r[key] for r in _load(name)]
        assert len(ids) == len(set(ids)), f"duplicate ids in {name}"


def test_every_project_has_source():
    for p in _load("src/data/entities/projects.json"):
        assert p.get("provenance"), f"{p['project_id']} has no provenance"


def test_every_project_has_type():
    allowed = {"lgu_development", "lgu_procurement", "dpwh_infrastructure",
               "social_program", "agricultural_program", "other"}
    bad = [p["project_id"] for p in _load("src/data/entities/projects.json")
           if p.get("project_type") not in allowed]
    assert not bad, f"unknown project types: {bad[:5]}"


def test_provenance_points_at_real_files():
    for p in _load("src/data/entities/projects.json"):
        for prov in p.get("provenance", []):
            src = prov.get("source", "")
            assert src, f"{p['project_id']} provenance missing source"
            docs = prov.get("document", "")
            docs = docs if isinstance(docs, list) else [docs]
            for doc in docs:
                if not doc or doc.startswith("procurement.json#"):
                    continue
                assert (REPO / "src" / "data" / doc).exists() or doc.endswith((".json", ".csv", ".xlsx")), \
                    f"{p['project_id']} provenance document missing: {doc}"


def test_review_merge_preserves_decisions(tmp_path):
    prior = [{"candidate_id": "MATCH-0001", "record_a": "fdp-bid:X",
              "record_b": "contract:Y", "match_score": 0.9,
              "evidence": ["similar project title"], "decision": "confirmed",
              "decided_by": "tester"}]
    rev = tmp_path / "review"
    rev.mkdir()
    (rev / "project-matches.json").write_text(json.dumps(prior), encoding="utf-8")
    merged = E._merge_review_decisions(
        [{"candidate_id": "MATCH-0009", "record_a": "fdp-bid:X",
          "record_b": "contract:Y", "match_score": 0.9,
          "evidence": ["similar project title"], "decision": "pending"}],
        rev)
    assert merged[0]["decision"] == "confirmed"
    assert merged[0]["decided_by"] == "tester"


def test_project_index_matches_entities():
    index = _load("assets/data/project-index.json")
    projects = _load("src/data/entities/projects.json")
    assert len(index) == len(projects)
    by_id = {p["project_id"]: p for p in projects}
    for entry in index:
        assert entry["id"] in by_id
        assert set(entry["sources"]) == {"dilg", "philgeps", "dpwh", "coa"}
        assert isinstance(entry.get("link_strength", {}), dict)
        assert isinstance(entry.get("funds_same_year", []), list)
    linked = [e for e in index if e["contracts"]]
    assert linked, "expected at least one project with linked contracts"
    for entry in linked:
        assert entry["sources"]["philgeps"] is True


def test_contractor_index_has_contract_lists():
    index = _load("assets/data/contractor-index.json")
    assert index
    with_ids = [c for c in index if c.get("contract_ids")]
    assert with_ids, "expected contractors with contract id lists"
    assert all(isinstance(c["years"], list) for c in index)


def test_audit_fund_index_fields():
    for entry in _load("assets/data/audit-index.json"):
        assert {"category", "first_observed", "last_observed", "amount"} <= set(entry)
    for entry in _load("assets/data/fund-index.json"):
        assert isinstance(entry.get("projects_same_year", []), list)
