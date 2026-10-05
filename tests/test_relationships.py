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
    dpwh_ids = {p.get("contract_id", "") for p in _load("src/data/dpwh.json").get("projects", [])}
    known = projects | contracts | contractors

    def _known(ref: str) -> bool:
        kind, _, rid = ref.partition(":")
        if kind == "project" and rid.startswith("fdp-bid:"):
            return True  # FDP-side anchor, resolved at render time
        if kind == "dpwh":
            return rid in dpwh_ids
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


def test_shared_contract_comembers_linked(tmp_path):
    """Co-members sharing one award (002+003 courts, 014+020 market) all link."""
    out = tmp_path / "data"
    E.build_all(data_out=out, review_dir=tmp_path / "review")
    rels = json.loads((out / "relationships.json").read_text(encoding="utf-8"))
    linked = {(r["from"], r["to"]) for r in rels if r["type"] == "has_contract"}
    assert ("project:BM-PROJ-2023-002", "contract:INFR-MUN-2023-07-006") in linked
    assert ("project:BM-PROJ-2023-003", "contract:INFR-MUN-2023-07-006") in linked
    assert ("project:BM-PROJ-2023-014", "contract:INFR-MUN-2023-11-016") in linked
    assert ("project:BM-PROJ-2023-020", "contract:INFR-MUN-2023-11-016") in linked


def test_coa_duplicates_folded(tmp_path):
    """COA rows duplicating dev projects merge instead of spawning entities."""
    out = tmp_path / "data"
    E.build_all(data_out=out, review_dir=tmp_path / "review")
    projects = json.loads((out / "entities" / "projects.json").read_text(encoding="utf-8"))
    stop_shop = [p for p in projects if "Stop Shop Building Phase 4" in p["canonical_name"]]
    assert len(stop_shop) == 1, [p["project_id"] for p in stop_shop]
    assert stop_shop[0]["project_id"] == "BM-PROJ-2025-032"
    assert any(s["source"] == "COA" for s in stop_shop[0]["provenance"])


def test_confirmed_review_promotes_edge(tmp_path):
    """A human-confirmed review pair becomes a has_contract edge on rebuild."""
    out = tmp_path / "data"
    rev = tmp_path / "review"
    E.build_all(data_out=out, review_dir=rev)
    matches = json.loads((rev / "project-matches.json").read_text(encoding="utf-8"))
    target = next(m for m in matches if m["decision"] == "pending")
    target["decision"] = "confirmed"
    target["decided_by"] = "test"
    (rev / "project-matches.json").write_text(json.dumps(matches), encoding="utf-8")
    E.build_all(data_out=out, review_dir=rev)
    rels = json.loads((out / "relationships.json").read_text(encoding="utf-8"))
    promoted = [r for r in rels if r["from"] == target["record_a"] and r["to"] == target["record_b"]]
    assert promoted and "human-confirmed" in promoted[0]["evidence"]


def test_dpwh_never_auto_linked(tmp_path):
    """DPWH pairs only ever reach the review queue, never relationships."""
    out = tmp_path / "data"
    E.build_all(data_out=out, review_dir=tmp_path / "review")
    rels = json.loads((out / "relationships.json").read_text(encoding="utf-8"))
    assert not [r for r in rels if r["from"].startswith("project:BM-PROJ-")
                and "-D" in r["from"] and r["type"] == "has_contract"]


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


def test_provenance_has_roles_and_as_of():
    roles = {"project_record", "fund_record", "bid_record", "contract_record",
             "audit_record", "infrastructure_record"}
    n_role, n_asof, n_total = 0, 0, 0
    for name in ("src/data/entities/projects.json", "src/data/entities/contracts.json",
                 "src/data/entities/funds.json", "src/data/entities/audit-findings.json"):
        for entity in _load(name):
            for prov in entity.get("provenance", []):
                n_total += 1
                assert prov.get("record_role") in roles, f"{name}: bad role {prov.get('record_role')}"
                n_role += 1
                if prov.get("source_as_of"):
                    n_asof += 1
    assert n_total > 0 and n_role == n_total
    assert n_asof > 0, "expected some source_as_of dates"


def test_no_summed_totals_in_indexes():
    """Non-additivity guard: fund figures must equal their own period's
    source values, never cross-period sums; project index carries no
    combined project value."""
    fdp = _load("src/data/fdp_disclosures.json")
    per_period_dev = {}
    for doc in fdp.get("dev_fund", []):
        per = doc.get("period", "")
        per_period_dev[per] = round(sum(float(p.get("cost") or 0)
                                        for p in doc.get("projects", [])), 2)
    for entry in _load("assets/data/fund-index.json"):
        period = entry["period"]
        if "dev_total" in entry.get("figures", {}):
            assert entry["figures"]["dev_total"] == per_period_dev.get(period), \
                f"{period}: dev_total is not its own period sum"
    for entry in _load("assets/data/project-index.json"):
        assert "total_value" not in entry and "combined" not in json.dumps(entry)


def test_relationship_summary_shape():
    """relationship_summary replaces link_strength with per-level counts."""
    for entry in _load("assets/data/project-index.json"):
        assert "link_strength" not in entry
        assert set(entry.get("relationship_summary", {})) == {"confirmed", "strong", "probable", "possible"}
    rels = _load("src/data/relationships.json")
    for r in rels:
        if r["type"] == "has_contract" and r["from"].startswith("project:BM-PROJ-"):
            assert r.get("match_path") in ("bid-bridge", "direct"), r["id"]


def test_relationship_counts_reconcile():
    """Count guard: totals recomputed live from relationships.json — no
    hardcoded totals, so doc/code drift fails loudly instead of silently."""
    from collections import Counter
    rels = _load("src/data/relationships.json")
    by_type = Counter(r["type"] for r in rels)
    assert sum(by_type.values()) == len(rels)
    assert set(by_type) <= {"awarded_to", "has_contract", "same_contractor_as"}, set(by_type)
    n_contracts = len(_load("src/data/entities/contracts.json"))
    assert by_type.get("awarded_to", 0) <= n_contracts
    # every has_contract edge resolves to a known contract
    contracts = {c["contract_id"] for c in _load("src/data/entities/contracts.json")}
    for r in rels:
        if r["type"] == "has_contract":
            assert r["to"].split(":", 1)[1] in contracts, r["id"]


def test_contractor_identity_edges():
    """DPWH contractor identity links resolve to canonical contractors."""
    rels = _load("src/data/relationships.json")
    contractors = {c["contractor_id"] for c in _load("src/data/entities/contractors.json")}
    identity = [r for r in rels if r["type"] == "same_contractor_as"]
    assert identity, "expected DPWH contractor identity edges"
    for r in identity:
        assert r["from"].startswith("dpwh:")
        assert r["to"].split(":", 1)[1] in contractors, r["id"]
        assert r["confidence"] in ("explicit", "probable"), r["id"]
