"""Canonical GIS inventory checks; publication decisions are tested by fixtures.

Source verification and prose review resolutions are not publication approvals.
These checks do not certify source accuracy or authorize new GIS data.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _build.gis import public_facilities

ROOT = Path(__file__).resolve().parent.parent
SRC_DATA = ROOT / 'src' / 'data'
GIS_DIR = SRC_DATA / 'gis'


def load(name):
    return json.loads((GIS_DIR / name).read_text(encoding='utf-8'))


def collection(name):
    data = load(name)
    assert data['type'] == 'FeatureCollection'
    assert isinstance(data['features'], list)
    return data


def test_barangay_reference():
    data = collection('barangays.geojson')
    expected = {'0105528' + suffix for suffix in (
        '001', '002', '003', '004', '006', '007', '008', '009',
        '010', '012', '013', '014', '015', '016', '018',
    )}
    assert len(data['features']) == 15
    assert {f['properties']['gid'] for f in data['features']} == expected
    assert sum(f['properties']['pop2024'] for f in data['features']) == 38228
    for feature in data['features']:
        assert feature['geometry'] is None  # Reference attributes, not boundaries.
        assert feature['properties']['provenance']['source']
        assert feature['properties']['provenance']['source_url']


def test_facility_inventory_geometry_ids_and_provenance():
    data = collection('facilities.geojson')
    ids = [f['properties']['id'] for f in data['features']]
    assert len(ids) == len(set(ids))
    for feature in data['features']:
        props = feature['properties']
        assert props['verification_status'] in {
            'unreviewed', 'needs_review', 'source_verified', 'field_verified', 'rejected',
        }
        assert props['location_precision'] in {
            'exact_from_source', 'approximate', 'barangay_level', 'unknown',
        }
        assert props['provenance']['source']
        assert props['provenance']['source_url']
        geometry = feature['geometry']
        if geometry is None:
            continue
        assert geometry['type'] == 'Point'
        lon, lat = geometry['coordinates']
        assert all(type(n) in (int, float) and math.isfinite(n) for n in (lon, lat))
        assert -180 <= lon <= 180 and -90 <= lat <= 90
        assert 120.3 <= lon <= 120.6 and 15.8 <= lat <= 16.2
        if props.get('facility_type') == 'Barangay Hall':
            assert 'centroid' not in (props.get('review_notes') or '').lower()


def test_review_queue_preserves_known_contradictions():
    review = load('review/facilities-review.json')
    issues = {i['issue_id']: i for i in review['issues']}
    assert {'review-001', 'review-002', 'review-003', 'review-004',
            'review-007', 'review-008'} <= issues.keys()
    assert {'fac-001', 'fac-002'} <= set(issues['review-001']['affected_ids'])
    assert 'fac-005' in issues['review-002']['affected_ids']
    # A resolution string/status alone does not prove that these are resolved.


def test_canonical_public_payload_obeys_explicit_approvals():
    data = collection('facilities.geojson')
    review = load('review/facilities-review.json')
    public = public_facilities(data, review)
    ids = {f['properties']['id'] for f in public['features']}
    approved_ids = {a['feature_id'] for a in review.get('publication_approvals', [])
                    if a.get('decision') == 'approved'}
    assert ids <= approved_ids
    assert public['metadata']['rendered_features'] == len(public['features'])
    assert public['metadata']['excluded_features'] == len(data['features']) - len(public['features'])
    assert 'excluded_ids' not in public['metadata']
    if not approved_ids:
        assert public['features'] == []
    for feature in public['features']:
        assert 'review_notes' not in feature['properties']
        assert 'coordinate_history' not in feature['properties']


def test_layers_manifest_contract():
    data = load('layers.json')
    for layer in data['layers']:
        for field in ('id', 'title', 'data', 'type', 'visible_by_default', 'source', 'attribution'):
            assert field in layer
        assert {'en', 'fil', 'pag'} <= layer['title'].keys()
    assert any(layer['id'] == 'facilities' for layer in data['layers'])
    for lid in ('hazard-ground-shaking', 'hazard-liquefaction'):
        layer = next(layer for layer in data['layers'] if layer['id'] == lid)
        assert layer['type'] == 'tile-overlay'
        assert 'GroundOverlay' in layer['verification_notes']
    lon, lat = data['metadata']['default_map_center']
    assert 120.4 <= lon <= 120.5 and 16.0 <= lat <= 16.1
    # Manifest availability/emission/runtime support requires the later asset agent.


def test_gis_schemas_registered_and_data_valid():
    from src.data.schemas import SCHEMAS, validate_all

    for key in ('gis/barangays.geojson', 'gis/facilities.geojson', 'gis/layers.json'):
        assert key in SCHEMAS
    errors = [e for e in validate_all(SRC_DATA) if 'gis/' in e]
    assert not errors, errors
