"""GIS data validation tests — locks the Phase 1 GIS data contract.

Covers AGENTS.md §8 requirements: GeoJSON validity, coordinate ranges/order,
unique IDs, provenance metadata, barangay PSGC count + population sum, no
fabricated hall polygons, review-status isolation, and layers.json manifest
integrity.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
SRC_DATA = ROOT / "src" / "data"
GIS_DIR = SRC_DATA / "gis"

BARANGAYS_PATH = GIS_DIR / "barangays.geojson"
FACILITIES_PATH = GIS_DIR / "facilities.geojson"
LAYERS_PATH = GIS_DIR / "layers.json"
REVIEW_PATH = GIS_DIR / "review" / "facilities-review.json"

EXPECTED_BRGYS = 15
EXPECTED_POP_SUM = 38228
EXPECTED_FACILITIES = 16

VALID_VERIFY_STATUS = {"unreviewed", "needs_review", "source_verified",
                       "field_verified", "rejected"}
VALID_LOCATION_PRECISION = {"exact_from_source", "approximate",
                            "barangay_level", "unknown"}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_geojson(path: Path) -> dict:
    data = _load_json(path)
    assert data["type"] == "FeatureCollection", (
        f"{path.name}: top-level type must be FeatureCollection, got {data['type']}"
    )
    assert isinstance(data["features"], list), (
        f"{path.name}: 'features' must be a list"
    )
    return data


def test_barangays_geojson_parses():
    """barangays.geojson parses as a valid FeatureCollection."""
    data = _load_geojson(BARANGAYS_PATH)
    assert len(data["features"]) == EXPECTED_BRGYS, (
        f"Expected {EXPECTED_BRGYS} barangays, got {len(data['features'])}"
    )


def test_barangays_all_psgc_codes_present():
    """Every barangay has a 10-digit PSGC code."""
    data = _load_geojson(BARANGAYS_PATH)
    for feat in data["features"]:
        gid = feat["properties"]["gid"]
        assert len(gid) == 10 and gid.isdigit(), (
            f"Invalid PSGC code for {feat['properties']['name']}: {gid}"
        )


def test_barangays_population_sums_to_38228():
    """Population values sum to the official 38,228 (PSA 2024 census)."""
    data = _load_geojson(BARANGAYS_PATH)
    total = sum(f["properties"]["pop2024"] for f in data["features"])
    assert total == EXPECTED_POP_SUM, (
        f"Population sum {total} != expected {EXPECTED_POP_SUM}"
    )


def test_barangays_have_no_fabricated_geometry():
    """Barangay features must have geometry null — no invented polygons."""
    data = _load_geojson(BARANGAYS_PATH)
    for feat in data["features"]:
        assert feat["geometry"] is None, (
            f"{feat['properties']['name']}: barangay geometry must be null "
            f"(no fabricated boundary polygons). Got {feat['geometry']}"
        )


def test_barangays_have_provenance():
    """Every barangay feature has provenance with source and source_url."""
    data = _load_geojson(BARANGAYS_PATH)
    for feat in data["features"]:
        prov = feat["properties"]["provenance"]
        assert prov["source"], f"{feat['properties']['name']}: missing source"
        assert prov["source_url"], f"{feat['properties']['name']}: missing source_url"


def test_facilities_geojson_parses():
    """facilities.geojson parses as a valid FeatureCollection."""
    data = _load_geojson(FACILITIES_PATH)
    assert len(data["features"]) == EXPECTED_FACILITIES, (
        f"Expected {EXPECTED_FACILITIES} facilities, got {len(data['features'])}"
    )


def test_facility_coordinates_valid_and_ordered():
    """All facility coordinates are valid lon/lat and ordered [lon, lat]."""
    data = _load_geojson(FACILITIES_PATH)
    for feat in data["features"]:
        geom = feat["geometry"]
        if geom is None:
            continue
        coords = geom["coordinates"]
        lon, lat = coords[0], coords[1]
        assert -180 <= lon <= 180, (
            f"{feat['properties']['name']}: longitude {lon} out of range"
        )
        assert -90 <= lat <= 90, (
            f"{feat['properties']['name']}: latitude {lat} out of range"
        )
        assert 120.3 <= lon <= 120.6, (
            f"{feat['properties']['name']}: longitude {lon} outside Mapandan bounds"
        )
        assert 15.8 <= lat <= 16.2, (
            f"{feat['properties']['name']}: latitude {lat} outside Mapandan bounds"
        )


def test_facility_ids_unique():
    """Facility IDs are unique within the layer."""
    data = _load_geojson(FACILITIES_PATH)
    ids = [f["properties"]["id"] for f in data["features"]]
    assert len(ids) == len(set(ids)), f"Duplicate facility IDs: {ids}"


def test_all_facilities_are_source_verified():
    """All 16 facilities carry verification_status: source_verified (no needs_review remains).

    Per maintainer review decision (19 October 2026), all §3.5 coordinate conflicts
    were resolved and the 5 previously blocked facilities were released.
    """
    data = _load_geojson(FACILITIES_PATH)
    for feat in data["features"]:
        assert feat["properties"]["verification_status"] == "source_verified", (
            f"{feat['properties']['id']}: expected source_verified, got "
            f"{feat['properties']['verification_status']}"
        )
    assert len(data["features"]) == EXPECTED_FACILITIES


def test_facility_provenance_has_source():
    """Every facility has provenance with source and source_url."""
    data = _load_geojson(FACILITIES_PATH)
    for feat in data["features"]:
        prov = feat["properties"]["provenance"]
        assert prov["source"], f"{feat['properties']['name']}: missing source"
        assert prov["source_url"], f"{feat['properties']['name']}: missing source_url"


def test_facility_location_precision_enum():
    """All location_precision values are from the controlled enum."""
    data = _load_geojson(FACILITIES_PATH)
    for feat in data["features"]:
        precision = feat["properties"]["location_precision"]
        assert precision in VALID_LOCATION_PRECISION, (
            f"Invalid location_precision '{precision}' for "
            f"{feat['properties']['name']}"
        )


def test_no_facility_is_polygon():
    """No facility feature has geometry type Polygon — halls are points only."""
    data = _load_geojson(FACILITIES_PATH)
    for feat in data["features"]:
        geom = feat["geometry"]
        if geom is not None:
            assert geom["type"] != "Polygon", (
                f"{feat['properties']['name']}: facility must not be a Polygon; "
                f"halls are point features, not centroids from nonexistent polygons."
            )


def test_no_hall_marked_as_centroid():
    """Barangay hall features must not claim centroid derivation from polygons."""
    data = _load_geojson(FACILITIES_PATH)
    halls = [f for f in data["features"]
             if f["properties"]["facility_type"] == "Barangay Hall"]
    for hall in halls:
        notes = hall["properties"].get("review_notes") or ""
        assert "centroid" not in notes.lower(), (
            f"{hall['properties']['name']}: hall marked as centroid from polygon "
            f"— not allowed without an approved polygon source."
        )


def test_review_queue_documents_all_contradictions():
    """The review queue lists all known facility contradictions, now resolved."""
    review = _load_json(REVIEW_PATH)
    assert "issues" in review, "Review queue missing 'issues' array"
    issue_ids = {i["issue_id"] for i in review["issues"]}
    expected_issues = {"review-001", "review-002", "review-003",
                       "review-004", "review-007", "review-008"}
    missing = expected_issues - issue_ids
    assert not missing, f"Review queue missing expected issues: {missing}"
    assert review["metadata"]["all_need_review"] is False
    assert review["metadata"]["total_features"] == EXPECTED_FACILITIES
    assert "blocked_feature_ids" in review, "Review queue missing 'blocked_feature_ids'"
    assert review["blocked_feature_ids"] == [], (
        "All facility coordinate conflicts resolved — blocked_feature_ids should be empty"
    )
    assert review["summary"]["status"] == "resolved"


def test_police_fire_colocated_resolution_documented():
    """The co-located police/fire issue is resolved in the review queue with a resolution."""
    review = _load_json(REVIEW_PATH)
    pol_fire = next(i for i in review["issues"] if i["issue_id"] == "review-001")
    assert "fac-001" in pol_fire["affected_ids"]
    assert "fac-002" in pol_fire["affected_ids"]
    assert pol_fire["status"] == "resolved"
    assert "resolution" in pol_fire, "review-001 missing resolution field"


def test_bucas_locality_resolution_documented():
    """BUCAS locality conflict is resolved in the review queue with a resolution."""
    review = _load_json(REVIEW_PATH)
    bucas = next(i for i in review["issues"] if i["issue_id"] == "review-002")
    assert "fac-005" in bucas["affected_ids"]
    assert bucas["status"] == "resolved"
    assert "resolution" in bucas, "review-002 missing resolution field"


def test_verified_features_included_in_public_layer():
    """All 16 verified (source_verified) features are included in the public map layer; 0 excluded."""
    from _build.pages import _filter_public_facilities
    raw = FACILITIES_PATH.read_text(encoding="utf-8")
    filtered = _filter_public_facilities(raw)
    data = json.loads(filtered)
    verified = [f for f in data["features"]
                if f["properties"]["verification_status"] == "source_verified"]
    assert len(verified) == 16, (
        f"Expected 16 verified features, got {len(verified)}"
    )
    assert len(data["features"]) == 16
    assert data["metadata"]["excluded_features"] == 0
    assert data["metadata"]["rendered_features"] == 16


def test_blocked_facilities_excluded_from_public_layer():
    """Previously blocked facilities are now released; all 16 render in the public layer.

    The gate mechanism itself is verified by test_publication_gate_overrides_false_status
    using a synthetic regression fixture.
    """
    from _build.pages import _filter_public_facilities
    raw = FACILITIES_PATH.read_text(encoding="utf-8")
    filtered = _filter_public_facilities(raw)
    data = json.loads(filtered)
    ids = {f["properties"]["id"] for f in data["features"]}
    previously_blocked = {"fac-001", "fac-002", "fac-005", "fac-006", "fac-014"}
    assert len(data["features"]) == 16, f"Expected 16 features, got {len(data['features'])}"
    # Previously blocked facilities must now be present in the public layer
    for fid in previously_blocked:
        assert fid in ids, f"Previously blocked {fid} should now be in the public layer"
    assert data["metadata"]["excluded_features"] == 0


def test_publication_gate_excludes_blocked_facilities():
    """With an empty blocked_feature_ids list, all 16 facilities render (0 excluded)."""
    from _build.pages import _filter_public_facilities
    raw = FACILITIES_PATH.read_text(encoding="utf-8")
    filtered = _filter_public_facilities(raw)
    data = json.loads(filtered)
    assert len(data["features"]) == 16
    assert data["metadata"]["excluded_features"] == 0
    assert data["metadata"]["rendered_features"] == 16
    assert data["metadata"]["excluded_ids"] == []


def test_public_payload_strips_review_notes():
    """The filtered public payload has no review_notes in any feature."""
    from _build.pages import _filter_public_facilities
    raw = FACILITIES_PATH.read_text(encoding="utf-8")
    filtered = _filter_public_facilities(raw)
    data = json.loads(filtered)
    for feat in data["features"]:
        assert "review_notes" not in feat["properties"], (
            f"review_notes leaked for {feat['properties']['id']} in public payload"
        )


def test_publication_gate_overrides_false_status():
    """Regression: a source_verified synthetic feature in blocked_feature_ids is still excluded.

    Uses a synthetic facility ID (fac-999-synthetic) that does not exist in the
    real facilities.geojson, so the regression test is decoupled from real data.
    """
    from _build.pages import _filter_public_facilities
    raw_data = _load_geojson(FACILITIES_PATH)
    fixture = json.loads(json.dumps(raw_data))

    synthetic_id = "fac-999-synthetic"
    fixture["features"].append({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [120.45, 16.03]},
        "properties": {
            "id": synthetic_id,
            "name": "Synthetic Test Facility",
            "category": "Test",
            "facility_type": None,
            "address": None,
            "barangay_gid": None,
            "plus_code": None,
            "verification_status": "source_verified",
            "location_precision": "approximate",
            "review_notes": None,
            "provenance": {
                "source": "Test",
                "source_url": "https://example.com",
                "retrieved": "2026-10-19",
                "last_verified": None,
            },
        },
    })
    fixture_review = {
        "blocked_feature_ids": [synthetic_id],
        "issues": [],
        "external_issues": [],
        "metadata": {"total_features": 17, "all_need_review": False},
        "summary": {"status": "mixed"},
    }
    import shutil
    import tempfile
    tmpdir = tempfile.mkdtemp()
    tmp_src = Path(tmpdir) / "src" / "data"
    review_dir = tmp_src / "gis" / "review"
    review_dir.mkdir(parents=True)
    (review_dir / "facilities-review.json").write_text(
        json.dumps(fixture_review), encoding="utf-8"
    )
    facilities_dir = tmp_src / "gis"
    facilities_dir.mkdir(parents=True, exist_ok=True)
    (facilities_dir / "facilities.geojson").write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    import _build.pages as pages_mod
    original_src = pages_mod.SRC_DATA
    pages_mod.SRC_DATA = tmp_src
    try:
        result = _filter_public_facilities(json.dumps(fixture))
        data = json.loads(result)
        ids = {f["properties"]["id"] for f in data["features"]}
        assert synthetic_id not in ids, (
            "source_verified synthetic feature in blocked_feature_ids must still be excluded"
        )
        assert data["metadata"]["excluded_features"] == 1
    finally:
        pages_mod.SRC_DATA = original_src
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_layers_manifest_has_all_required_fields():
    """Each layer in layers.json has required fields per the GIS schema."""
    data = _load_json(LAYERS_PATH)
    assert "layers" in data
    for layer in data["layers"]:
        for field in ["id", "title", "data", "type", "visible_by_default",
                       "source", "attribution"]:
            assert field in layer, f"Layer {layer.get('id', '?')} missing {field}"
        assert isinstance(layer["title"], dict), (
            f"Layer {layer['id']}: title must be an object with en/fil/pag"
        )
        for lang in ("en", "fil", "pag"):
            assert lang in layer["title"], (
                f"Layer {layer['id']}: title missing '{lang}'"
            )


def test_layers_manifest_facilities_visible_by_default():
    """Facilities layer is visible by default (all features are source_verified)."""
    data = _load_json(LAYERS_PATH)
    fac_layer = next(layer for layer in data["layers"] if layer["id"] == "facilities")
    assert fac_layer["visible_by_default"] is True


def test_facilities_visible_by_default():
    """Facilities layer is visible by default since all features are source_verified."""
    data = _load_json(LAYERS_PATH)
    for layer in data["layers"]:
        if layer["id"] == "facilities":
            assert layer["visible_by_default"] is True
            break
    else:
        raise AssertionError("facilities layer not found in manifest")


def test_layers_manifest_hazard_layers_documented():
    """Both KMZ hazard layers appear in the manifest with GroundOverlay notes."""
    data = _load_json(LAYERS_PATH)
    layer_ids = {layer["id"] for layer in data["layers"]}
    assert "hazard-ground-shaking" in layer_ids
    assert "hazard-liquefaction" in layer_ids
    for lid in ("hazard-ground-shaking", "hazard-liquefaction"):
        layer = next(layer for layer in data["layers"] if layer["id"] == lid)
        assert layer["type"] == "tile-overlay", (
            f"Layer {lid}: KMZs are GroundOverlay raster tiles, not vector"
        )
        assert "GroundOverlay" in layer["verification_notes"], (
            f"Layer {lid}: must document GroundOverlay raster type"
        )


def test_layers_default_map_center_is_mapandan():
    """Default map center falls within Mapandan bounds."""
    data = _load_json(LAYERS_PATH)
    center = data["metadata"]["default_map_center"]
    lon, lat = center[0], center[1]
    assert 120.4 <= lon <= 120.5, f"Map center lon {lon} outside Mapandan"
    assert 16.0 <= lat <= 16.1, f"Map center lat {lat} outside Mapandan"


def test_gis_schemas_registered():
    """GIS schemas are registered in the SCHEMAS dict for validation."""
    from src.data.schemas import SCHEMAS

    for key in ("gis/barangays.geojson", "gis/facilities.geojson", "gis/layers.json"):
        assert key in SCHEMAS, f"Schema not registered: {key}"


def test_gis_files_pass_schema_validation():
    """All GIS data files pass JSON Schema validation via validate_all."""
    from src.data.schemas import validate_all

    errors = [e for e in validate_all(SRC_DATA) if "gis/" in e]
    assert not errors, f"GIS schema validation errors: {errors}"
