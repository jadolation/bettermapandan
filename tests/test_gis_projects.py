"""DPWH projection preserves source identity, evidence, and missing positions."""
import copy
import json
import math
from pathlib import Path
from urllib.parse import quote

import pytest

from _build.gis_projects import dpwh_collection

ROOT = Path(__file__).resolve().parent.parent


def record(**overrides):
    return {"transaction_id": "DPWH-T1", "project_name": "Original name",
            "latitude": 16.0, "longitude": 120.4, **overrides}


def feature(row, canonical=None, lang="en"):
    return dpwh_collection({"projects": [row]}, canonical or [], lang)["features"][0]


def test_real_source_all_records_and_numeric_positions_retained():
    source = json.loads((ROOT / "src/data/dpwh.json").read_text(encoding="utf-8"))
    original = copy.deepcopy(source)
    result = dpwh_collection(source, [])
    assert result["type"] == "FeatureCollection"
    assert len(result["features"]) == len(source["projects"])
    for row, item in zip(source["projects"], result["features"]):
        props = item["properties"]
        assert props["id"] == props["source_transaction_id"] == row["transaction_id"]
        assert props["contract_id"] == row.get("contract_id", "")
        lon, lat = row.get("longitude"), row.get("latitude")
        valid = (type(lon) in (int, float) and type(lat) in (int, float)
                 and math.isfinite(lon) and math.isfinite(lat)
                 and -180 <= lon <= 180 and -90 <= lat <= 90)
        assert item["geometry"] == ({"type": "Point", "coordinates": [lon, lat]} if valid else None)
        assert props["limitations"]
    assert source == original
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("lon,lat", [
    (True, 16), (120, False), (float("nan"), 16), (120, float("inf")),
    (181, 16), (-181, 16), (120, 91), (120, -91), (None, 16), (120, None),
    ("120.4", "16"), (16, 120), ({}, []), (10 ** 400, 16),
])
def test_invalid_positions_stay_null_without_component_or_barangay_guess(lon, lat):
    item = feature(record(longitude=lon, latitude=lat,
                          project_components=[{"latitude": 16, "longitude": 120}],
                          barangay_location="Coral"))
    assert item["geometry"] is None
    assert any("no map position inferred" in text for text in item["properties"]["limitations"])


@pytest.mark.parametrize("lon,lat", [(-180, -90), (180, 90), (0, 0)])
def test_valid_boundary_coordinates_not_discarded(lon, lat):
    assert feature(record(longitude=lon, latitude=lat))["geometry"]["coordinates"] == [lon, lat]


def test_missing_coordinates_are_not_zero():
    assert feature({"transaction_id": "missing"})["geometry"] is None


@pytest.mark.parametrize("value", [None, "", "  ", True, 123, "x" * 2001])
def test_invalid_identity_is_actionable_build_error(value):
    with pytest.raises(ValueError, match=r"projects\[0\].*nonempty transaction_id"):
        feature(record(transaction_id=value))


def test_duplicate_source_ids_fail_even_if_name_or_position_differs():
    with pytest.raises(ValueError, match=r"Duplicate DPWH transaction_id.*DPWH-T1.*projects\[0\].*projects\[1\]"):
        dpwh_collection({"projects": [record(), record(project_name="Different", latitude=None)]}, [])


@pytest.mark.parametrize("status,key", [
    ("Completed", "completed"), ("Finished", "completed"), (" On-Going ", "ongoing"), ("Ongoing", "ongoing"),
    ("In Progress", "ongoing"), ("In-Progress", "ongoing"),
    ("Not Yet Started", "not_started"), ("Not Started", "not_started"),
    ("Stopped", "stopped"), (" SUSPENDED ", "stopped"), ("Halted", "stopped"),
    ("On Hold", "stopped"), ("On-Hold", "stopped"),
    ("Reported complete pending review", "unknown"), (None, "unknown"), ("", "unknown"),
])
def test_status_is_explicit_not_inferred_from_accomplishment(status, key):
    props = feature(record(status=status, accomplishment_percent=100))["properties"]
    assert props["status_key"] == key
    assert props["status"] == (status.strip() if status else "")


def test_dates_names_numeric_source_fields_and_bounded_allowlist():
    row = record(project_name="  A source name  ", fiscal_year="2026",
                 contract_amount="PHP 1,234,567.89", approved_budget="\u20b1 2,000.00",
                 accomplishment_percent="23.75", actual_start_date="  unparsed date  ",
                 actual_completion_date=None, contract_expiry_date={"unsafe": "value"},
                 contractor="  A & B  ", contractors=["A & B", " C ", "C", {}],
                 source_document_url=" https://transparency.dpwh.gov.ph/ ",
                 bidders=[{"huge": "secret"}], project_components=[{"huge": "secret"}],
                 crossref={"huge": "secret"}, unknown="secret", source_date="  source date  ")
    props = feature(row)["properties"]
    assert props["name"] == "A source name"
    assert props["fiscal_year"] == 2026 and type(props["fiscal_year"]) is int
    assert props["contract_amount"] == 1234567.89
    assert props["approved_budget"] == 2000
    assert props["accomplishment_percent"] == 23.75
    assert props["actual_start_date"] == "unparsed date"
    assert props["actual_completion_date"] == props["contract_expiry_date"] == ""
    assert props["contractor"] == "A & B" and props["contractors"] == ["A & B", "C"]
    assert props["source_date"] == "source date"
    assert props["contract_id"] == ""  # Transaction identity is not a contract number.
    assert props["source_document_url"] == props["source_url"] == "https://transparency.dpwh.gov.ph/"
    assert not {"bidders", "project_components", "crossref", "unknown"} & props.keys()
    assert len(feature(record(project_name="n" * 10000))["properties"]["name"]) == 2000


@pytest.mark.parametrize("value", [True, False, float("nan"), float("inf"), "NaN", "Infinity", "unreported", "1,2", {}, None])
def test_invalid_numbers_remain_null(value):
    props = feature(record(contract_amount=value, approved_budget=value,
                           accomplishment_percent=value, fiscal_year=value))["properties"]
    assert all(props[key] is None for key in ("contract_amount", "approved_budget", "accomplishment_percent", "fiscal_year"))
    json.dumps(props, allow_nan=False)


@pytest.mark.parametrize("url", ["javascript:alert(1)", "data:text/html,x", "//evil.test", "/local",
                               "https://user:password@example.org/", "https://example.org/\nunsafe", "https://[bad", "x" * 2001])
def test_unsafe_urls_not_emitted(url):
    props = feature(record(source_document_url=url))["properties"]
    assert props["source_url"] == props["source_document_url"] == ""


@pytest.mark.parametrize("lang,prefix", [("en", ""), ("fil", "/fil"), ("pag", "/pag"), ("../bad", "")])
def test_localized_encoded_exact_canonical_and_fallback_links(lang, prefix):
    row = record(transaction_id="T /?&#")
    canonical = [{"source_transaction_id": row["transaction_id"], "project_id": "P /?&#"}]
    props = feature(row, canonical, lang)["properties"]
    assert props["project_id"] == "P /?&#"
    assert props["project_url"] == prefix + "/transparency/projects/?project=" + quote("P /?&#", safe="")
    props = feature(row, [], lang)["properties"]
    assert props["project_id"] is None
    assert props["project_url"] == prefix + "/transparency/infrastructure/#dpwh-project-" + quote(row["transaction_id"], safe="")


@pytest.mark.parametrize("canonical", [
    [{"project_id": "P1", "source_transaction_id": "DPWH-T1"}, {"project_id": "P2", "source_transaction_id": "DPWH-T1"}],
    [{"project_id": "P1", "source_transaction_id": "DPWH-T1"}] * 2,
    [{"project_id": "P1", "source_transaction_id": "DPWH-T1"}, {"project_id": "P1", "source_transaction_id": "other"}],
    [{"project_id": "P1", "source_transaction_id": "DPWH-T1"}, {"project_id": None, "source_transaction_id": "DPWH-T1"}],
    [{"project_id": "", "source_transaction_id": "DPWH-T1"}],
    [{"project_id": "P1", "canonical_name": "Original name", "dpwh_contract_id": "DPWH-T1"}],
])
def test_ambiguous_or_nonexact_canonical_matches_use_real_fallback(canonical):
    props = feature(record(), canonical)["properties"]
    assert props["project_id"] is None
    assert props["project_url"] == "/transparency/infrastructure/#dpwh-project-DPWH-T1"


def test_collection_validation():
    for source in (None, {}, {"projects": {}}, {"projects": [None]}):
        with pytest.raises(ValueError, match="DPWH"):
            dpwh_collection(source, [])


def load_facilities():
    return json.loads((ROOT / 'src/data/gis/facilities.geojson').read_text(encoding='utf-8'))


def load_boundaries():
    return json.loads((ROOT / 'src/data/gis/barangay_boundaries.geojson').read_text(encoding='utf-8'))


def point_in_polygon(lon, lat, polygon):
    # Winding-number test over the (possibly overlapping/gapped, indicative)
    # PSGC ADM4 boundary rings. Robust to the self-touching edges that a naive
    # ray-cast mishandles, so it is preferred over a bounding-box approximation.
    x, y = lon, lat
    winding = 0
    for ring in polygon:
        points = ring
        count = len(points)
        j = count - 1
        for i in range(count):
            xi, yi = points[i]
            xj, yj = points[j]
            if yi <= y:
                if yj > y and (xj - xi) * (y - yi) - (x - xi) * (yj - yi) > 0:
                    winding += 1
            elif yj <= y and (xj - xi) * (y - yi) - (x - xi) * (yj - yi) < 0:
                winding -= 1
            j = i
    return winding != 0


# Facilities corrected per .kilo/plans/1792394702315-fix-misplaced-facility-coordinates.md.
# Each row asserts the corrected coordinate and that the point now falls within
# its assigned barangay_gid boundary polygon (previously it landed in a neighbour).
@pytest.mark.parametrize('fac_id, expected, barangay_gid', [
    ('fac-007', [120.4581, 16.0377], '0105528004'),        # Baloling National High School
    ('fac-013', [120.4571406, 16.0372375], '0105528004'),  # Baloling Barangay Hall
    ('fac-014', [120.4364, 16.0281], '0105528012'),        # Nilombot Barangay Hall
])
def test_corrected_facility_coordinates_within_assigned_barangay(fac_id, expected, barangay_gid):
    boundaries = load_boundaries()
    polygons = {feature['properties']['gid']: feature['geometry']['coordinates']
                for feature in boundaries['features']}
    facilities = load_facilities()
    feature = next(f for f in facilities['features'] if f['properties']['id'] == fac_id)
    lon, lat = feature['geometry']['coordinates']
    assert [lon, lat] == expected
    assert feature['properties']['barangay_gid'] == barangay_gid
    assert point_in_polygon(lon, lat, polygons[barangay_gid])
