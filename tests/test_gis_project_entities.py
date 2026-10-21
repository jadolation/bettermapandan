"""DPWH canonical links use explicit source metadata, never title or order."""
import copy
import json
from pathlib import Path

import pytest

from _build.entities import build_all, build_projects
from _build.gis_projects import dpwh_collection

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    out = tmp_path_factory.mktemp("dpwh-entities")
    build_all(data_out=out / "data", assets_out=out / "assets", review_dir=out / "review")
    projects = json.loads((out / "data/entities/projects.json").read_text(encoding="utf-8"))
    source = json.loads((ROOT / "src/data/dpwh.json").read_text(encoding="utf-8"))
    return source, projects


def test_generation_adds_transaction_metadata_without_rewriting_canonical_ids(generated):
    source, projects = generated
    previous = json.loads((ROOT / "src/data/entities/projects.json").read_text(encoding="utf-8"))
    assert [p["project_id"] for p in projects] == [p["project_id"] for p in previous]
    dpwh = [p for p in projects if p["project_type"] == "dpwh_infrastructure"]
    assert len(dpwh) == len(source["projects"])
    for row, project in zip(source["projects"], dpwh):
        assert project["source_transaction_id"] == row["transaction_id"]
        assert project["dpwh_contract_id"] == row.get("contract_id", "")
        assert project["provenance"][0]["record_id"] == row.get("contract_id", "")


def test_changed_names_reversed_orders_still_join_exact_transaction_ids(generated):
    source, projects = copy.deepcopy(generated)
    expected = {p["source_transaction_id"]: p["project_id"] for p in projects
                if p["project_type"] == "dpwh_infrastructure"}
    for project in projects:
        project["canonical_name"] = "Changed canonical name"
    source["projects"].reverse()
    for row in source["projects"]:
        row["project_name"] = "Same renamed source title"
    for item in dpwh_collection(source, projects)["features"]:
        props = item["properties"]
        assert props["project_id"] == expected[props["source_transaction_id"]]


def test_same_name_and_contract_never_substitute_for_transaction_id(generated):
    source, projects = copy.deepcopy(generated)
    row = source["projects"][0]
    old = next(p for p in projects if p.get("source_transaction_id") == row["transaction_id"])
    old["source_transaction_id"] = "different transaction"
    props = dpwh_collection({"projects": [row]}, projects)["features"][0]["properties"]
    assert props["project_id"] is None
    assert "/transparency/infrastructure/#dpwh-project-" in props["project_url"]


def test_entity_with_no_contract_id_does_not_fabricate_one():
    projects = build_projects({}, [{"transaction_id": "SOURCE-TXN", "project_name": "Name", "fiscal_year": 2026}], [], {})
    assert projects[0]["source_transaction_id"] == "SOURCE-TXN"
    assert projects[0]["dpwh_contract_id"] == ""
    assert projects[0]["project_id"] == "BM-PROJ-2026-D001"
    assert projects[0]["provenance"][0]["record_id"] == ""
