"""Final coordinate authority, explicit reconciliation and geographic QA contracts."""
import json
from copy import deepcopy
from pathlib import Path

import pytest

from _build.gis import facilities_collection
from _build.gis_halls import LEGACY_HALL_IDS, geographic_qa, hall_collection
from _build.gis_residents import reconcile
from _build.gis_sources import prepare_inputs

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    '0105528001': [120.445297, 16.017088],
    '0105528002': [120.445703, 16.024513],
    '0105528003': [120.462234, 16.022888],
    '0105528004': [120.455938, 16.038688],
    '0105528007': [120.441922, 16.022763],
    '0105528008': [120.467104, 16.009689],
    '0105528009': [120.470141, 16.001063],
    '0105528010': [120.472813, 16.014563],
    '0105528012': [120.437297, 16.029238],
    '0105528014': [120.453976, 16.026470],
    '0105528016': [120.46858197702797, 16.028728751444635],
    '0105528015': [120.47970027277864, 15.997556990588695],
    '0105528006': [120.45199439609885, 16.031355521238535],
    '0105528018': [120.46612085847998, 16.01515706627226],
    '0105528013': [120.44610424027763, 16.03685116767425],
}


def read(name):
    return json.loads((ROOT / 'src/data/gis' / name).read_text())


def test_exact_final_coordinates_and_safe_semantics():
    raw = read('barangay_halls.geojson')
    data = hall_collection(raw)
    assert {f['properties']['barangay_gid']: f['geometry']['coordinates'] for f in data['features']} == EXPECTED
    assert len({f['properties']['id'] for f in data['features']}) == 15
    for feature in data['features']:
        props = feature['properties']
        assert props['facility_type'] == 'Barangay Hall'
        assert props['semantic_role'] == 'barangay_hall'
        assert props['coordinate_method'] == 'maintainer_supplied'
        assert props['location_precision'] == 'supplied_building_location'
        assert 'source_url' not in props['provenance']
        assert 'not a surveyed entrance' in props['limitations'][0]


@pytest.mark.parametrize('mutation', ['missing', 'duplicate_gid', 'bad_coordinate', 'duplicate_id'])
def test_hall_authority_rejects_incomplete_or_ambiguous_inventory(mutation):
    raw = read('barangay_halls.geojson')
    if mutation == 'missing':
        raw['features'].pop()
    elif mutation == 'duplicate_gid':
        raw['features'][1]['properties']['barangay_gid'] = raw['features'][0]['properties']['barangay_gid']
    elif mutation == 'duplicate_id':
        raw['features'][1]['properties']['id'] = raw['features'][0]['properties']['id']
    else:
        raw['features'][0]['geometry']['coordinates'] = [True, 16]
    with pytest.raises(ValueError, match='15 unique canonical barangays'):
        hall_collection(raw)


def test_reconciled_identity_preserves_municipal_and_evacuation_meaning():
    facilities = facilities_collection(read('facilities.geojson'))
    municipal = deepcopy(next(f for f in facilities['features'] if f['properties']['id'] == 'fac-016'))
    records = []
    reconcile(ROOT, facilities, records)
    assert next(f for f in facilities['features'] if f['properties']['id'] == 'fac-016') == municipal
    assert not LEGACY_HALL_IDS & {f['properties']['id'] for f in facilities['features']}
    assert not LEGACY_HALL_IDS & {r['id'] for r in records}
    coral = next(r for r in records if r.get('evacuation_id') == 'evac-004')
    assert coral['geometry'] is None and coral['evacuation_capacity'] is None
    halls = hall_collection(read('barangay_halls.geojson'))
    assert all('evacuation_id' not in f['properties'] for f in halls['features'])
    poblacion = next(f for f in halls['features'] if f['properties']['barangay_gid'] == '0105528014')
    assert poblacion['properties']['id'] != 'fac-016'
    assert poblacion['geometry'] != municipal['geometry']


def test_qa_preserves_all_coordinates_and_reports_containment():
    halls = hall_collection(read('barangay_halls.geojson'))
    before = deepcopy(halls)
    results = geographic_qa(halls, read('barangay_boundaries.geojson'))
    assert len(results) == 15 and halls == before
    assert all(isinstance(r['within_indicative_barangay'], bool) for r in results)
    assert {r['barangay_gid'] for r in results} == set(EXPECTED)
    for gid in ('0105528013', '0105528006'):
        assert next(r for r in results if r['barangay_gid'] == gid)['within_indicative_barangay'] is True


def test_build_emits_safe_default_on_layer_and_inventory(tmp_path):
    data = prepare_inputs(ROOT, tmp_path)
    layer = next(row for row in data['layers'] if row['id'] == 'barangay-halls')
    assert layer['available'] and layer['visible_by_default'] and layer['type'] == 'geojson'
    output = tmp_path / layer['url']
    assert output.is_file()
    assert json.loads(output.read_text()) == hall_collection(read('barangay_halls.geojson'))
    assert 'assets/gis/barangay-halls.geojson' in json.loads((tmp_path / 'assets/gis/manifest.json').read_text())['files']
    assert len(data['metadata']['hall_geographic_qa']) == 15
    assert 'coordinate_history' not in output.read_text()
