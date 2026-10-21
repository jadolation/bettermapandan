"""Safe map display, without publication approval policy."""
import copy

import pytest
from test_gis_sources import point

from _build.gis import (
    GISDataError,
    barangay_collection,
    directory_html,
    facilities_collection,
    parse_json,
    script_json,
)


@pytest.mark.parametrize('status', [None, 'unreviewed', 'needs_review', 'rejected', 'source_verified', 'field_verified'])
def test_structural_facilities_display_without_provenance_or_approval(status):
    data = point()
    if status is not None:
        data['features'][0]['properties']['verification_status'] = status
    original = copy.deepcopy(data)
    result = facilities_collection(data)
    assert len(result['features']) == 1
    assert data == original
    props = result['features'][0]['properties']
    assert props.get('verification_status') == status
    assert 'provenance' not in props
    assert props['coordinate_description'] == 'Unknown precision'
    assert 'review_notes' not in props and 'coordinate_history' not in props


def test_directories_escape_and_counts_follow_normalized_features():
    result = facilities_collection(point('<img src=x onerror=alert(1)>'))
    directory = directory_html(result, 'facilities')
    assert '<img' not in directory and '&lt;img' in directory
    assert directory.count('<li>') == len(result['features'])


def test_barangays_stay_nonspatial_and_editable():
    data = point()
    data['features'][0]['geometry'] = None
    data['features'][0]['properties'].update(gid='123', pop2024=100)
    result = barangay_collection(data)
    assert result['features'][0]['geometry'] is None
    assert 'PSGC: 123' in directory_html(result, 'barangays')
    assert barangay_collection({'type': 'FeatureCollection', 'features': []})['features'] == []


@pytest.mark.parametrize('raw', ['{"value": NaN}', '{broken', '{"value": Infinity}'])
def test_invalid_json_rejected(raw):
    with pytest.raises(GISDataError):
        parse_json(raw)


def test_script_context_escaping_and_nonfinite_rejection():
    rendered = script_json({'text': '</script>&\u2028\u2029'})
    assert '</script>' not in rendered and '<' not in rendered and '&' not in rendered
    assert '\\u2028' in rendered and '\\u2029' in rendered
    with pytest.raises(GISDataError):
        script_json({'number': float('nan')})


def test_unsafe_source_urls_are_not_projected():
    data = point()
    data['features'][0]['properties']['provenance'] = {'source': 'Source', 'source_url': 'javascript:alert(1)'}
    result = facilities_collection(data)
    assert result['features'][0]['properties']['provenance'] == {'source': 'Source'}


def test_project_records_remain_searchable_without_static_project_dump():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    template = (root / 'src/pages/gis.html').read_text(encoding='utf-8')
    assert '{GIS_RECORD_DIRECTORY}' not in template
    assert 'window.GIS_RECORDS = {GIS_RECORDS_DATA}' in template
    assert '{{ASSET_BASE}}transparency/projects/' in template
    assert template.count('<details class="gis-panel"') == 2
