"""Content-editable canonical data checks, without fixed record counts or approvals."""
import json
from pathlib import Path

from _build.gis import barangay_collection, facilities_collection
from _build.gis_sources import layer_configuration, prepare_inputs

ROOT = Path(__file__).resolve().parents[1]
SRC_DATA = ROOT / 'src/data'


def load(name):
    return json.loads((SRC_DATA / 'gis' / name).read_text(encoding='utf-8'))


def test_canonical_facilities_display_with_geometry_and_status_unchanged():
    data = load('facilities.geojson')
    result = facilities_collection(data)
    assert len(result['features']) == len(data['features'])
    original = {feature['properties']['id']: feature for feature in data['features']}
    for feature in result['features']:
        source = original[feature['properties']['id']]
        assert feature['geometry'] == source['geometry']
        assert feature['properties'].get('verification_status') == source['properties'].get('verification_status')
        assert 'review_notes' not in feature['properties']
        assert 'coordinate_history' not in feature['properties']


def test_barangay_references_keep_supplied_identity_population_and_no_positions():
    source = load('barangays.geojson')
    result = barangay_collection(source)
    assert len(result['features']) == len(source['features'])
    assert len({feature['properties']['gid'] for feature in result['features']}) == len(result['features'])
    for feature, original in zip(result['features'], source['features'], strict=True):
        assert feature['geometry'] is None
        for key in ('gid', 'name', 'pop2024'):
            assert feature['properties'][key] == original['properties'][key]


def test_initial_layers_are_real_inputs_not_fictional_boundaries():
    config = layer_configuration(ROOT)
    assert all((ROOT / layer['source']).is_file() for layer in config['layers'])
    assert not any(layer['id'] == 'municipality-boundary' or 'UNVALIDATED' in layer['source'] or 'CANDIDATE' in layer['source'] for layer in config['layers'])
    assert next(layer for layer in config['layers'] if layer['id'] == 'places')['source'] == 'datasets/GIS/places.geojson'


def test_real_inputs_prepare_into_temp_assets_without_approval_configuration(tmp_path):
    result = prepare_inputs(ROOT, tmp_path)
    assert all(layer['available'] for layer in result['layers'])
    assert len(result['facilities']['features']) == len(load('facilities.geojson')['features'])
    assert all(record['geometry'] is None for record in result['records'])
    places = json.loads((tmp_path / 'assets/gis/places.geojson').read_text())
    assert any(feature['geometry']['type'] == 'Polygon' for feature in places['features'])
    assert all(layer.get('images') for layer in result['layers'] if layer['type'] == 'raster-image-overlay')


def test_gis_schemas_registered_and_data_valid():
    from src.data.schemas import SCHEMAS, validate_all
    assert {'gis/barangays.geojson', 'gis/facilities.geojson', 'gis/layers.json'} <= SCHEMAS.keys()
    assert not [error for error in validate_all(SRC_DATA) if 'gis/' in error]
