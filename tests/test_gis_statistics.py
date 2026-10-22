"""Statistics contracts, adversarial identity cases and measured real-source QA."""
import copy
import json
from pathlib import Path

import pytest

from _build.gis_statistics import EXPECTED_GIDS, IdentityError, build_statistics

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def put(root, relative, value):
    path = root / "src/data" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def fixture(tmp_path):
    put(tmp_path, "gis/barangays.geojson", load(ROOT / "src/data/gis/barangays.geojson"))
    for name, value in (("entities/projects.json", []), ("relationships.json", []),
                        ("entities/contracts.json", []), ("dpwh.json", {"projects": []}),
                        ("fdp_disclosures.json", {"dev_fund": []}),
                        ("audit-reports.json", {"infrastructure_projects": []}),
                        ("procurement.json", {"contracts": []})):
        put(tmp_path, name, value)
    return tmp_path


def project(pid="P-1", **extra):
    return {"project_id": pid, "canonical_name": "Road improvement", "municipality": "Mapandan",
            "province": "Pangasinan", "barangay": [], "provenance": [], **extra}


def dpwh(root, location="Brgy. Jimenez", **extra):
    put(root, "entities/projects.json", [project(source_transaction_id="TX-1")])
    put(root, "dpwh.json", {"projects": [{"transaction_id": "TX-1", "barangay_location": location,
                                          "fiscal_year": 2024, "status": "Completed", **extra}]})


def test_population_complete_and_deterministic(fixture):
    result = build_statistics(fixture)
    assert result == build_statistics(fixture)
    assert result["schema_version"] == 1
    assert result["municipality_psgc"] == "0105528000"
    assert set(result["barangays"]) == EXPECTED_GIDS
    assert result["population"]["total"] == 38228
    assert sum(b["population"]["share"] for b in result["barangays"].values()) == pytest.approx(1)
    assert result["population"]["provenance"][0]["source_url"].startswith("https://psa.gov.ph/")


@pytest.mark.parametrize("value,status", [(None, "missing"), (-1, "invalid"), (True, "invalid"),
                                         (float("nan"), "invalid"), (float("inf"), "invalid"),
                                         ("1656", "invalid"), (1.5, "invalid")])
def test_population_missing_and_invalid_never_zero(fixture, value, status):
    data = load(fixture / "src/data/gis/barangays.geojson")
    data["features"][0]["properties"]["pop2024"] = value
    put(fixture, "gis/barangays.geojson", data)
    result = build_statistics(fixture)
    p = result["barangays"]["0105528001"]["population"]
    assert p == {"count": None, "year": 2024, "status": status, "share": None}
    assert result["population"]["total"] is None
    assert all(b["population"]["share"] is None for b in result["barangays"].values())
    json.dumps(result, allow_nan=False)


def test_zero_and_mixed_year(fixture):
    data = load(fixture / "src/data/gis/barangays.geojson")
    p = data["features"][0]["properties"]
    p["pop2024"] = 0
    put(fixture, "gis/barangays.geojson", data)
    assert build_statistics(fixture)["barangays"][p["gid"]]["population"]["share"] == 0
    p["source_as_of"] = "2020 census"
    put(fixture, "gis/barangays.geojson", data)
    assert build_statistics(fixture)["barangays"][p["gid"]]["population"]["status"] == "mixed_year"


def test_all_zero_population_has_no_divide_by_zero(fixture):
    data = load(fixture / "src/data/gis/barangays.geojson")
    for feature in data["features"]:
        feature["properties"]["pop2024"] = 0
    put(fixture, "gis/barangays.geojson", data)
    result = build_statistics(fixture)
    assert result["population"]["total"] == 0
    assert result["population"]["status"] == "available"
    assert all(b["population"]["share"] is None for b in result["barangays"].values())


@pytest.mark.parametrize("mutation", ["duplicate", "wrong_town", "missing", "numeric"])
def test_invalid_psgc_fails(fixture, mutation):
    data = load(fixture / "src/data/gis/barangays.geojson")
    if mutation == "duplicate":
        data["features"][0] = copy.deepcopy(data["features"][1])
    elif mutation == "wrong_town":
        data["features"][0]["properties"]["gid"] = "0105529001"
    elif mutation == "numeric":
        data["features"][0]["properties"]["gid"] = 105528001
    else:
        data["features"].pop()
    put(fixture, "gis/barangays.geojson", data)
    with pytest.raises(IdentityError):
        build_statistics(fixture)


def test_explicit_multi_barangay_scoped_zero_and_unknown(fixture):
    dpwh(fixture, "Brgy. Amanaoaoac / Brgy. Jimenez", fiscal_year=None, status="invented")
    result = build_statistics(fixture)
    p = result["projects"][0]
    assert p["barangay_gids"] == ["0105528001", "0105528008"]
    assert result["project_coverage"]["count"] == 1
    assert sum(b["projects"]["count"] for b in result["barangays"].values()) == 2
    assert result["barangays"]["0105528002"]["projects"]["count"] == 0
    assert p["references"][0]["year"] is None
    assert p["references"][0]["status"] == "unknown"


@pytest.mark.parametrize("location", ["Mapandan", "Entire Mapandan, Pang.", "Mapandan NHS",
                                      "Jiminez", "Brgy. Jimenez / mystery", "Jimenez Street, Other Town"])
def test_no_fuzzy_or_municipal_or_partial_assignment(fixture, location):
    dpwh(fixture, location, latitude=16, longitude=120.4)
    result = build_statistics(fixture)
    assert result["projects"][0]["barangay_gids"] == []
    assert result["project_coverage"]["unassigned_count"] == 1
    assert result["project_coverage"]["status"] == "incomplete"


def test_ambiguous_alias_and_conflicting_canonical_locations(fixture):
    dpwh(fixture)
    data = load(fixture / "src/data/gis/barangays.geojson")
    data["features"][0]["properties"]["name"] = "Jimenez"
    put(fixture, "gis/barangays.geojson", data)
    result = build_statistics(fixture)
    assert result["projects"][0]["barangay_gids"] == []
    assert result["project_coverage"]["sources"]["dpwh"]["ambiguous_records"] == 1
    put(fixture, "gis/barangays.geojson", load(ROOT / "src/data/gis/barangays.geojson"))
    put(fixture, "entities/projects.json", [project(source_transaction_id="TX-1", barangay=["Poblacion"])])
    result = build_statistics(fixture)
    assert result["projects"][0]["barangay_gids"] == []
    assert result["project_coverage"]["sources"]["dpwh"]["conflicting_records"] == 1


@pytest.mark.parametrize("mutation", ["duplicate_pid", "duplicate_transaction", "unsafe_id", "wrong_town", "duplicate_source"])
def test_canonical_identity_errors_are_fatal(fixture, mutation):
    dpwh(fixture)
    ps = load(fixture / "src/data/entities/projects.json")
    if mutation == "duplicate_pid":
        ps.append(copy.deepcopy(ps[0]))
    elif mutation == "duplicate_transaction":
        ps.append(project("P-2", source_transaction_id="TX-1"))
    elif mutation == "unsafe_id":
        ps[0]["project_id"] = "../../unsafe<script>"
    elif mutation == "wrong_town":
        ps[0]["municipality"] = "Other"
    else:
        source = load(fixture / "src/data/dpwh.json")
        source["projects"].append(copy.deepcopy(source["projects"][0]))
        put(fixture, "dpwh.json", source)
    put(fixture, "entities/projects.json", ps)
    with pytest.raises(IdentityError):
        build_statistics(fixture)


def test_persisted_dpwh_contract_fallback_requires_exact_provenance(fixture):
    dpwh(fixture, contract_id="24AJ001")
    p = project(dpwh_contract_id="24AJ001", provenance=[{"source": "DPWH Transparency Portal", "record_id": "24AJ001"}])
    put(fixture, "entities/projects.json", [p])
    assert len(build_statistics(fixture)["projects"]) == 1
    p["provenance"][0]["record_id"] = "24AJ002"
    put(fixture, "entities/projects.json", [p])
    assert build_statistics(fixture)["projects"] == []


def test_dilg_repeated_reports_no_new_projects_or_inferred_completion(fixture):
    p = project(canonical_name="Drainage", barangay=["Jimenez"], provenance=[{"source": "DILG-FDP"}])
    put(fixture, "entities/projects.json", [p])
    rows = [{"project": "Drainage", "location": "Brgy. Jimenez, Mapandan", "completion": "2024-12-31", "cost": 999}]
    put(fixture, "fdp_disclosures.json", {"dev_fund": [
        {"period": "2023-Q1", "year": 2023, "projects": rows},
        {"period": "2024-Q1", "year": 2024, "projects": [{**rows[0], "pct": 1}]},
        {"period": "2024-Q1", "year": 2024, "projects": [{**rows[0], "pct": 1}]}]})
    result = build_statistics(fixture)
    assert result["project_coverage"]["count"] == 1
    refs = result["projects"][0]["references"]
    assert len(refs) == 2
    assert {(r["year"], r["status"]) for r in refs} == {(2023, "unknown"), (2024, "completed")}
    assert all(r["year_basis"] == "disclosure" for r in refs)
    assert result["project_coverage"]["sources"]["dilg"]["examined_records"] == 3


def test_optional_source_failure_is_atomic_and_zeros_distinct_unavailable(fixture):
    dpwh(fixture)
    put(fixture, "fdp_disclosures.json", {"dev_fund": [{"year": 2024, "projects": None}]})
    result = build_statistics(fixture)
    assert result["project_coverage"]["sources"]["dilg"]["supported"] is False
    assert result["barangays"]["0105528001"]["projects"]["count"] == 0
    assert result["project_coverage"]["count"] == 1
    for path in ("dpwh.json", "audit-reports.json", "procurement.json"):
        (fixture / "src/data" / path).unlink()
    result = build_statistics(fixture)
    assert result["project_coverage"]["status"] == "unavailable"
    assert all(b["projects"]["count"] is None for b in result["barangays"].values())
    assert {d["source"] for d in result["diagnostics"] if d["code"] == "source_unavailable"} == {"dpwh", "dilg", "coa", "philgeps"}


def test_partial_source_failure_does_not_commit_earlier_rows(fixture):
    p = project(provenance=[{"source": "DILG-FDP"}])
    put(fixture, "entities/projects.json", [p])
    put(fixture, "fdp_disclosures.json", {"dev_fund": [
        {"year": 2024, "projects": [{"project": "Road improvement", "location": "Mapandan"}]},
        {"year": 2025, "projects": None}]})
    result = build_statistics(fixture)
    assert not result["projects"]
    assert result["project_coverage"]["sources"]["dilg"]["status"] == "unavailable"


def test_output_runtime_bound_is_enforced(fixture, monkeypatch):
    monkeypatch.setattr("_build.gis_statistics.MAX_OUTPUT_BYTES", 1)
    with pytest.raises(ValueError, match="8 MiB"):
        build_statistics(fixture)


def edge(frm, to, kind, confidence="explicit"):
    return {"from": frm, "to": to, "type": kind, "confidence": confidence, "evidence": ["same reference id"]}


def award_fixture(root, relationships):
    dpwh(root)
    put(root, "relationships.json", relationships)
    row = {"title": "An award", "awardee": "Supplier", "award_date": "2025-01-01", "status": "active"}
    put(root, "procurement.json", {"contracts": [row]})
    put(root, "entities/contracts.json", [{"contract_id": "PHG-1", "source_record_id": "procurement.json#1",
                                           "title": row["title"], "awardee_name": "Supplier", "award_date": row["award_date"]}])


def filtered_ids(result, source=None, year=None, status=None):
    return {p["project_id"] for p in result["projects"] if any(
        (source is None or r["source"] in source) and (year is None or r["year"] == year)
        and (status is None or r["status"] == status) for r in p["references"])}


def test_direct_bid_chain_dedup_and_same_reference_filter_intersections(fixture):
    award_fixture(fixture, [edge("project:P-1", "contract:PHG-1", "has_contract"),
                            edge("project:P-1", "bid:B-1", "has_bid"),
                            edge("bid:B-1", "contract:PHG-1", "resulted_in")])
    result = build_statistics(fixture)
    assert len(result["projects"]) == 1
    assert len(result["projects"][0]["references"]) == 2
    assert filtered_ids(result, {"dpwh", "philgeps"}) == {"P-1"}
    assert filtered_ids(result, {"dpwh"}, 2025) == set()
    assert filtered_ids(result, {"philgeps"}, 2025, "award_active") == {"P-1"}
    assert filtered_ids(result, {"philgeps"}, 2025, "completed") == set()
    assert filtered_ids(result, None, 2024, "award_active") == set()


@pytest.mark.parametrize("confidence", ["strong", "probable", "possible", "unmatched"])
def test_uncertain_award_relationships_are_not_project_identities(fixture, confidence):
    award_fixture(fixture, [edge("project:P-1", "bid:B-1", "has_bid", confidence),
                            edge("bid:B-1", "contract:PHG-1", "resulted_in")])
    result = build_statistics(fixture)
    report = result["project_coverage"]["sources"]["philgeps"]
    assert report["supported"] is False
    assert report["unmapped_records"] == 1
    assert not filtered_ids(result, {"philgeps"})


def test_shared_award_does_not_merge_distinct_canonical_projects(fixture):
    award_fixture(fixture, [edge("project:P-1", "contract:PHG-1", "has_contract"),
                            edge("project:P-2", "contract:PHG-1", "has_contract")])
    ps = load(fixture / "src/data/entities/projects.json")
    ps.append(project("P-2"))
    put(fixture, "entities/projects.json", ps)
    result = build_statistics(fixture)
    assert filtered_ids(result, {"philgeps"}) == {"P-1", "P-2"}
    assert result["project_coverage"]["sources"]["philgeps"]["mapped_records"] == 1
    assert result["project_coverage"]["sources"]["philgeps"]["canonical_count"] == 2


def test_contract_source_drift_and_dangling_project_are_fatal(fixture):
    award_fixture(fixture, [edge("project:absent", "contract:PHG-1", "has_contract")])
    with pytest.raises(IdentityError):
        build_statistics(fixture)
    put(fixture, "relationships.json", [])
    contracts = load(fixture / "src/data/entities/contracts.json")
    contracts[0]["title"] = "Different award"
    put(fixture, "entities/contracts.json", contracts)
    with pytest.raises(IdentityError):
        build_statistics(fixture)


def test_award_enumeration_is_verified_against_amount_not_just_title(fixture):
    award_fixture(fixture, [edge("project:P-1", "contract:PHG-1", "has_contract")])
    contracts = load(fixture / "src/data/entities/contracts.json")
    contracts[0]["award_amount"] = 123
    put(fixture, "entities/contracts.json", contracts)
    with pytest.raises(IdentityError, match="source row"):
        build_statistics(fixture)


def test_coa_explicit_location_not_supplier_or_generic_title(fixture):
    put(fixture, "entities/projects.json", [project(provenance=[{"source": "COA", "record_id": "A-1"}])])
    row = {"id": "A-1", "name": "Market", "description": "Constructed in Barangay Poblacion",
           "supplier_address": "Brgy. Jimenez", "year_started": 2023, "year_completed": 2024, "status": "completed"}
    put(fixture, "audit-reports.json", {"infrastructure_projects": [row]})
    p = build_statistics(fixture)["projects"][0]
    assert p["barangay_gids"] == ["0105528014"]
    assert (p["references"][0]["year"], p["references"][0]["year_basis"]) == (2023, "start")
    row["description"] = "Municipal Market improvement"
    put(fixture, "audit-reports.json", {"infrastructure_projects": [row]})
    assert build_statistics(fixture)["projects"][0]["barangay_gids"] == []


def test_inherited_probable_coa_merge_rejected_without_explicit_edge(fixture):
    put(fixture, "entities/projects.json", [project(provenance=[{"source": "DILG-FDP"}, {"source": "COA", "record_id": "A-1"}])])
    put(fixture, "audit-reports.json", {"infrastructure_projects": [{"id": "A-1", "name": "Market"}]})
    result = build_statistics(fixture)
    assert result["project_coverage"]["sources"]["coa"]["excluded_uncertain_links"] == 1
    assert result["projects"] == []
    put(fixture, "relationships.json", [edge("coa:A-1", "project:P-1", "same_project")])
    assert len(build_statistics(fixture)["projects"]) == 1


def test_safe_allowlisted_output_and_order_independent(fixture):
    dpwh(fixture, status="<script>\x00", contract_amount=float("inf"), latitude=16, longitude=120)
    ps = load(fixture / "src/data/entities/projects.json")
    ps[0]["canonical_name"] = "<script>\x01Road"
    ps[0]["private_notes"] = "secret sentinel"
    put(fixture, "entities/projects.json", ps)
    data = load(fixture / "src/data/gis/barangays.geojson")
    data["features"][0]["properties"]["provenance"]["source_url"] = "javascript:alert(1)"
    put(fixture, "gis/barangays.geojson", data)
    result = build_statistics(fixture)
    encoded = json.dumps(result, allow_nan=False)
    assert all(value not in encoded for value in ("secret sentinel", "<script>", "javascript:", "contract_amount", "latitude", "density"))
    data["features"].reverse()
    put(fixture, "gis/barangays.geojson", data)
    assert build_statistics(fixture) == result


def test_real_source_measurements_and_reconciliation():
    result = build_statistics(ROOT)
    sources = result["project_coverage"]["sources"]
    assert {s: r["examined_records"] for s, r in sources.items()} == {"dpwh": 40, "dilg": 146, "coa": 16, "philgeps": 277}
    assert {s: r["canonical_count"] for s, r in sources.items()} == {"dpwh": 40, "dilg": 52, "coa": 15, "philgeps": 0}
    assert sources["dpwh"]["assigned_count"] == 36
    assert sources["dilg"]["assigned_count"] == 43
    assert sources["coa"]["assigned_count"] == 6
    assert sources["coa"]["excluded_uncertain_links"] == 1
    assert sources["philgeps"]["supported"] is False
    assert result["project_coverage"]["count"] == 107
    assert result["project_coverage"]["assigned_count"] == 85
    assert result["project_coverage"]["unassigned_count"] == 22
    for r in sources.values():
        assert r["mapped_records"] + r["unmapped_records"] == r["examined_records"]
        assert r["assigned_count"] + r["unassigned_count"] == r["canonical_count"]
    projects = {p["project_id"]: p for p in result["projects"]}
    for gid, b in result["barangays"].items():
        assert b["projects"]["ids"] == sorted(pid for pid, p in projects.items() if gid in p["barangay_gids"])
        assert b["projects"]["count"] == len(b["projects"]["ids"])
    encoded = json.dumps(result, sort_keys=True, allow_nan=False)
    assert len(encoded.encode()) < 100000
    assert encoded == json.dumps(build_statistics(ROOT), sort_keys=True, allow_nan=False)


def test_representative_real_records_keep_source_meanings():
    result = build_statistics(ROOT)
    projects = {p["project_id"]: p for p in result["projects"]}
    assert projects["BM-PROJ-2023-D001"]["barangay_gids"] == ["0105528008"]
    dilg = projects["BM-PROJ-2023-002"]
    assert dilg["barangay_gids"] == ["0105528004"]
    assert len(dilg["references"]) == 4
    assert all(r["year_basis"] == "disclosure" for r in dilg["references"])
    assert [r["status"] for r in dilg["references"]] == ["unknown", "unknown", "unknown", "completed"]
    coa = next(p for p in projects.values() if any(r["record_id"] == "cctv-cameras-poblacion" for r in p["references"]))
    assert coa["barangay_gids"] == ["0105528014"]
    assert coa["references"][0]["record_kind"] == "audit_record"
    assert not filtered_ids(result, {"philgeps"})


def test_freshly_rebuilt_real_canonical_schema_matches_persisted_coverage(fixture):
    from _build.entities import build_projects

    raw = {name: load(ROOT / "src/data" / name) for name in (
        "dpwh.json", "fdp_disclosures.json", "audit-reports.json", "procurement.json",
        "entities/contracts.json", "relationships.json")}
    for name, value in raw.items():
        put(fixture, name, value)
    canonical = build_projects(raw["fdp_disclosures.json"], raw["dpwh.json"]["projects"],
                               raw["audit-reports.json"]["infrastructure_projects"], {})
    assert all(p.get("source_transaction_id") for p in canonical if p["project_type"] == "dpwh_infrastructure")
    put(fixture, "entities/projects.json", canonical)
    result = build_statistics(fixture)
    persisted = build_statistics(ROOT)
    assert result["project_coverage"] == persisted["project_coverage"]
    assert result["barangays"] == persisted["barangays"]
