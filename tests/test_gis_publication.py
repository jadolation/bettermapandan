"""Synthetic publication-policy fixtures, never approvals for canonical data."""
import copy
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _build.gis import (
    GISPublicationError,
    _public_feature,
    directory_html,
    parse_json,
    public_facilities,
    public_layer_manifest,
    script_json,
)


def decision(kind='approved'):
    return {
        'decision': kind, 'reviewed_by': 'Synthetic test reviewer',
        'reviewed_at': '2026-10-19',
        'evidence': [{
            'source': 'Synthetic institution record',
            'source_url': 'https://example.org/records/test-1',
            'source_record_id': 'test-1', 'checked_at': '2026-10-19',
            'supports': ['identity', 'location', 'publication', 'resolution'],
        }],
    }


@pytest.fixture
def approved():
    feature = {
        'type': 'Feature',
        'geometry': {'type': 'Point', 'coordinates': [120.45, 16.03]},
        'properties': {
            'id': 'synthetic-1', 'name': 'Synthetic clinic', 'category': 'Health',
            'facility_type': 'Clinic', 'verification_status': 'source_verified',
            'location_precision': 'approximate', 'coordinate_method': 'plus_code_cell_center',
            'provenance': {
                'source': 'Synthetic directory', 'source_url': 'https://example.org/test-1',
                'source_record_id': 'test-1', 'retrieved': '2026-10-18',
                'last_verified': '2026-10-19',
            },
            'review_notes': 'PRIVATE REVIEW', 'coordinate_history': ['PRIVATE HISTORY'],
            'internal_metadata': {'secret': 'PRIVATE METADATA'},
        },
        'internal': 'PRIVATE FEATURE',
    }
    approval = decision()
    approval.update(feature_id='synthetic-1', public_feature=_public_feature(feature))
    data = {'type': 'FeatureCollection', 'features': [feature], 'metadata': {'secret': 'PRIVATE COLLECTION'}}
    review = {'issues': [], 'blocked_feature_ids': [], 'publication_approvals': [approval]}
    return data, review


def test_evidenced_approval_passes_without_mutating_inputs(approved):
    data, review = approved
    before = copy.deepcopy(approved)
    result = public_facilities(data, review)
    assert len(result['features']) == 1
    assert result['metadata'] == {'rendered_features': 1, 'excluded_features': 0}
    assert approved == before
    assert 'PRIVATE' not in script_json(result)
    assert set(result) == {'type', 'features', 'metadata'}
    assert 'Approximate Plus Code cell centre' in directory_html(result, 'facilities')


@pytest.mark.parametrize('status', ['unreviewed', 'needs_review', 'rejected', 'approved', '', None])
def test_status_never_bypassed_by_approval(approved, status):
    data, review = approved
    data['features'][0]['properties']['verification_status'] = status
    assert public_facilities(data, review)['features'] == []


@pytest.mark.parametrize('key,value', [
    ('location_precision', 'unknown'), ('location_precision', 'barangay_level'),
    ('location_precision', 'exact_from_source'), ('coordinate_method', None),
    ('coordinate_method', {}), ('name', '  '), ('id', None), ('category', 'unknown'),
])
def test_invalid_properties_fail_closed(approved, key, value):
    data, review = approved
    data['features'][0]['properties'][key] = value
    assert public_facilities(data, review)['features'] == []


@pytest.mark.parametrize('key,value', [
    ('source', ''), ('source_url', 'javascript:alert(1)'), ('source_record_id', 'unknown'),
    ('retrieved', 'yesterday'), ('last_verified', None), ('last_verified', '2026-02-30'),
])
def test_missing_meaningful_provenance_denied(approved, key, value):
    data, review = approved
    data['features'][0]['properties']['provenance'][key] = value
    assert public_facilities(data, review)['features'] == []


@pytest.mark.parametrize('geometry', [
    None, {}, {'type': 'Polygon', 'coordinates': []},
    *({'type': 'Point', 'coordinates': c} for c in (
        [], [120, 16, 9], [181, 16], [120, -91], ['120', 16],
        [True, 16], [float('nan'), 16], [120, float('inf')],
    )),
])
def test_invalid_geometry_denied(approved, geometry):
    data, review = approved
    data['features'][0]['geometry'] = geometry
    assert public_facilities(data, review)['features'] == []


@pytest.mark.parametrize('status', ['open', 'pending', 'needs_review', 'resolved'])
@pytest.mark.parametrize('key', ['issues', 'external_issues'])
def test_issue_affected_ids_override_false_source_verified_and_empty_denylist(approved, status, key):
    data, review = approved
    review[key] = [{
        'issue_id': 'test-issue', 'affected_ids': ['synthetic-1'],
        'status': status, 'resolution': 'Maintainer says approved, no cited evidence',
    }]
    assert public_facilities(data, review)['features'] == []


def test_all_affected_ids_blocked(approved):
    data, review = approved
    other = copy.deepcopy(data['features'][0])
    other['properties']['id'] = 'synthetic-2'
    data['features'].append(other)
    approval = copy.deepcopy(review['publication_approvals'][0])
    approval.update(feature_id='synthetic-2', public_feature=_public_feature(other))
    review['publication_approvals'].append(approval)
    review['issues'] = [{'issue_id': 'shared-site', 'affected_ids': ['synthetic-1', 'synthetic-2'], 'status': 'open'}]
    assert public_facilities(data, review)['features'] == []


def test_evidenced_resolution_still_requires_publication_approval(approved):
    data, review = approved
    review['issues'] = [{
        'issue_id': 'test-issue', 'affected_ids': ['synthetic-1'], 'status': 'resolved',
        'resolution_decision': decision('resolved'),
    }]
    assert len(public_facilities(data, review)['features']) == 1
    review['publication_approvals'] = []
    assert public_facilities(data, review)['features'] == []


@pytest.mark.parametrize('change', ['absent', 'no_evidence', 'empty_evidence', 'no_record', 'no_location', 'no_reviewer', 'bad_date', 'denied', 'snapshot'])
def test_approval_must_be_explicit_evidenced_and_claim_bound(approved, change):
    data, review = approved
    approval = review['publication_approvals'][0]
    if change == 'absent':
        del review['publication_approvals']
    elif change == 'no_evidence':
        del approval['evidence']
    elif change == 'empty_evidence':
        approval['evidence'] = []
    elif change == 'no_record':
        del approval['evidence'][0]['source_record_id']
    elif change == 'no_location':
        approval['evidence'][0]['supports'] = ['publication', 'identity']
    elif change == 'no_reviewer':
        approval['reviewed_by'] = ''
    elif change == 'bad_date':
        approval['reviewed_at'] = '2026-02-30'
    elif change == 'denied':
        approval['decision'] = 'rejected'
    else:
        data['features'][0]['properties']['name'] = 'Different identity'
    assert public_facilities(data, review)['features'] == []


def test_explicit_denylist_remains_defense_in_depth(approved):
    data, review = approved
    review['blocked_feature_ids'] = ['synthetic-1']
    result = public_facilities(data, review)
    assert result['features'] == []
    assert 'synthetic-1' not in script_json(result)


@pytest.mark.parametrize('review', [
    None, [], {}, {'issues': {}}, {'issues': [None]},
    {'issues': [{'issue_id': 'x', 'status': 'open'}]},
    {'issues': [], 'blocked_feature_ids': 'synthetic-1'},
    {'issues': [], 'publication_approvals': {}},
    {'issues': [], 'external_issues': None},
])
def test_malformed_review_policy_stops_build(approved, review):
    with pytest.raises(GISPublicationError, match='GIS'):
        public_facilities(approved[0], review)


@pytest.mark.parametrize('data', [None, [], {}, {'features': []}, {'type': 'FeatureCollection', 'features': {}}])
def test_malformed_collection_is_never_emitted(approved, data):
    with pytest.raises(GISPublicationError, match='FeatureCollection'):
        public_facilities(data, approved[1])


def test_malformed_individual_features_are_omitted(approved):
    data, review = approved
    data['features'].extend([None, [], {}, {'type': 'Feature', 'properties': None}])
    assert len(public_facilities(data, review)['features']) == 1


def test_duplicate_ids_or_approvals_stop_build(approved):
    data, review = approved
    data['features'].append(copy.deepcopy(data['features'][0]))
    with pytest.raises(GISPublicationError, match='Duplicate'):
        public_facilities(data, review)
    data['features'].pop()
    review['publication_approvals'] *= 2
    with pytest.raises(GISPublicationError, match='Duplicate'):
        public_facilities(data, review)


def test_script_json_round_trip_and_nonfinite_rejection():
    unsafe = '</script><script>alert("&")</script>\u2028\u2029'
    result = script_json({'name': unsafe})
    assert not any(char in result for char in '<>&\u2028\u2029')
    assert json.loads(result)['name'] == unsafe
    for value in (float('nan'), float('inf'), -float('inf')):
        with pytest.raises(GISPublicationError):
            script_json({'value': value})
    for raw in ('NaN', 'Infinity', '-Infinity', '{broken'):
        with pytest.raises(GISPublicationError):
            parse_json(raw)


def test_missing_or_malformed_review_file_is_clear_error(tmp_path, monkeypatch, approved):
    import _build.pages as pages

    monkeypatch.setattr(pages, 'SRC_DATA', tmp_path)
    raw = json.dumps(approved[0])
    with pytest.raises(GISPublicationError, match='facilities-review.json'):
        pages._filter_public_facilities(raw)
    review_dir = tmp_path / 'gis' / 'review'
    review_dir.mkdir(parents=True)
    (review_dir / 'facilities-review.json').write_text('{broken', encoding='utf-8')
    with pytest.raises(GISPublicationError, match='Invalid GIS JSON'):
        pages._filter_public_facilities(raw)


@pytest.mark.parametrize('lang', ['en', 'fil', 'pag'])
@pytest.mark.parametrize('publish', [True, False])
def test_rendered_page_payloads_directories_and_counts(tmp_path, monkeypatch, approved, lang, publish):
    """Render the real page processor in isolation, without assets/network/build."""
    import _build.pages as pages

    data, review = approved
    unsafe = '</script><img src=x onerror=alert(1)>&\u2028\u2029{GIS_FACILITY_COUNT}'
    data['features'][0]['properties']['name'] = unsafe
    review['publication_approvals'][0]['public_feature'] = _public_feature(data['features'][0])
    if not publish:
        review['publication_approvals'] = []
    gis = tmp_path / 'data' / 'gis'
    (gis / 'review').mkdir(parents=True)
    barangays = {'type': 'FeatureCollection', 'features': [{
        'type': 'Feature', 'geometry': None,
        'properties': {'name': unsafe, 'gid': '0105528001', 'pop2024': 1656},
    }]}
    layers = {'layers': [{'id': 'facilities', 'title': {'en': unsafe},
                          'verification_notes': 'PRIVATE synthetic-1 released'}]}
    for name, value in (('facilities.geojson', data), ('layers.json', layers),
                        ('barangays.geojson', barangays), ('review/facilities-review.json', review)):
        (gis / name).write_text(json.dumps(value), encoding='utf-8')
    monkeypatch.setattr(pages, 'SRC_DATA', gis.parent)
    for name in ('build_breadcrumbs', 'build_header', 'build_footer', 'build_hero', 'build_breadcrumb_jsonld'):
        monkeypatch.setattr(pages, name, lambda *args: '')
    monkeypatch.setattr(pages, '_apply_page_meta', lambda meta, *args: meta)
    monkeypatch.setattr(pages, 'resolve_body_placeholders', lambda body, *args: body)
    monkeypatch.setattr(pages, 'assemble_page', lambda *args: '<html><body>' + args[5] + '</body></html>')
    body = '\n'.join(f'<script>window.{key} = {{{key}_DATA}};</script>' for key in (
        'GIS_LAYERS', 'GIS_BARANGAYS', 'GIS_FACILITIES',
    )) + '<p>{GIS_FACILITY_COUNT}/{GIS_BARANGAY_COUNT}</p>{GIS_FACILITY_DIRECTORY}{GIS_BARANGAY_DIRECTORY}'
    out = tmp_path / lang
    entries = []
    pages._process_static_page(lang, {}, Path('gis.html'), {'title': 'GIS', 'description': 'Test'},
                               body, '', '', out, entries)
    html = (out / 'gis' / 'index.html').read_text(encoding='utf-8')
    assert html.count('<script>') == 3
    assert '<img' not in html and '&lt;/script&gt;' in html
    for script in re.findall(r'<script>(.*?)</script>', html, re.S):
        assert not any(c in script for c in '<>&\u2028\u2029')
    assert f'<p>{int(publish)}/1</p>' in html
    assert 'PRIVATE' not in html and 'coordinate_history' not in html
    if not publish:
        assert 'synthetic-1' not in html
    assert entries and '{GIS_FACILITY_COUNT}' in html  # Source text is not re-expanded.


@pytest.mark.parametrize('method,precision,status,label', [
    ('source_reported', 'exact_from_source', 'source_verified', 'Source-reported'),
    ('source_reported', 'approximate', 'source_verified', 'Approximate source-reported'),
    ('polygon_centroid', 'approximate', 'source_verified', 'mapped footprint'),
    ('field_observation', 'exact_from_source', 'field_verified', 'Field-verified'),
])
def test_supported_coordinate_claims_can_be_approved(approved, method, precision, status, label):
    data, review = approved
    data['features'][0]['properties'].update(
        coordinate_method=method, location_precision=precision, verification_status=status)
    review['publication_approvals'][0]['public_feature'] = _public_feature(data['features'][0])
    result = public_facilities(data, review)
    assert len(result['features']) == 1
    assert label in result['features'][0]['properties']['coordinate_description']


def test_manifest_drops_internal_notes_and_release_ids():
    data = {'metadata': {'excluded_ids': ['synthetic-private'], 'default_zoom': 14},
            'layers': [{'id': 'facilities', 'title': {'en': 'Facilities'},
                        'verification_notes': 'synthetic-private approved',
                        'internal_metadata': 'private'}]}
    result = public_layer_manifest(data, 0)
    assert 'synthetic-private' not in script_json(result)
    assert result['metadata'] == {'default_zoom': 14}
    assert result['layers'][0]['verification_notes'].startswith('0 facilities')


def test_manifest_never_advertises_unemitted_assets_or_unsupported_overlays():
    root = Path(__file__).resolve().parents[1]
    inventory = json.loads((root / 'src/data/gis/layers.json').read_text(encoding='utf-8'))
    result = public_layer_manifest(inventory, 0)
    for layer in result['layers']:
        assert 'data' not in layer
        assert layer['available'] == (layer['id'] == 'facilities')
        assert layer['visible_by_default'] == layer['available']
        assert layer['type'] == ('inline-geojson' if layer['available'] else 'unavailable')



def test_unevidenced_resolution_decision_stays_blocked(approved):
    data, review = approved
    resolution = decision('resolved')
    resolution['evidence'] = []
    review['issues'] = [{'issue_id': 'x', 'status': 'resolved', 'affected_ids': ['synthetic-1'],
                         'resolution_decision': resolution}]
    assert public_facilities(data, review)['features'] == []
