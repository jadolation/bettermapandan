"""Content-editable canonical data checks, without fixed record counts or approvals."""
import json
from pathlib import Path

from _build.gis import barangay_collection, facilities_collection
from _build.gis_sources import gis_asset_outputs, layer_configuration, prepare_inputs

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
    assert len(result['facilities']['features']) == len(load('facilities.geojson')['features']) - 5
    assert not {'fac-006', 'fac-010', 'fac-012', 'fac-013', 'fac-014'} & {f['properties']['id'] for f in result['facilities']['features']}
    references = [r for r in result['records'] if r['layer_id'] == 'project-references']
    dpwh = [r for r in result['records'] if r['layer_id'] == 'dpwh-projects']
    assert len(references) == 107
    assert all(record['geometry'] is None for record in references)
    assert len(dpwh) == 40
    assert all(record['geometry'] is None or record['geometry']['type'] == 'Point' for record in dpwh)
    places = json.loads((tmp_path / 'assets/gis/places.geojson').read_text())
    assert any(feature['geometry']['type'] == 'Polygon' for feature in places['features'])
    assert all(layer.get('images') for layer in result['layers'] if layer['type'] == 'raster-image-overlay')
    outputs = gis_asset_outputs(tmp_path)
    images = [image for layer in result['layers'] for image in layer.get('images', [])]
    assert {Path(image['url']) for image in images} == {path for path in outputs if path.suffix == '.png'}
    assert len(images) == 85  # 81 native hazard images and four prepared physical images.
    assert len([path for path in outputs if path.suffix == '.geojson']) == 4
    assert len(outputs) == 90  # 89 emitted resources plus their exact manifest.


def test_physical_configuration_matches_prepared_source_legends_and_dates():
    config = layer_configuration(ROOT)
    expected = {'physical-elevation', 'physical-slope', 'physical-soil', 'physical-land-capability'}
    physical = {entry['id']: entry for entry in config['layers'] if entry['pane'] == 'physical'}
    assert set(physical) == expected
    for identifier, entry in physical.items():
        source = json.loads((ROOT / f'datasets/GIS/physical/prepared/{identifier}.source.json').read_text())
        assert entry['source'] == source['prepared_resource']
        assert entry['type'] == 'kmz' and entry['enabled'] and not entry['visible_by_default']
        assert entry['source_date'] == source['prepared_date'] == '2021-12-15'
        assert entry['source_label'] == source['source_label']
        assert entry['legend'] == [{key: item[key] for key in ('label', 'color')} for item in source['legend']]
        assert entry['exclusive_group'] == 'physical-characteristics' and entry['opacity'] == 0.6
        assert all(entry['title'].get(lang) and entry['group'].get(lang) for lang in ('en', 'fil', 'pag'))
        assert 'vintage is unknown' in ' '.join(entry['limitations'])


def test_indicative_boundary_contract_preserves_canonical_reference_data():
    from _build.gis_preview import feature_collection

    config = layer_configuration(ROOT)
    entry = next(layer for layer in config['layers'] if layer['id'] == 'barangay-boundaries')
    assert entry['semantic_role'] == 'barangay_boundary'
    assert entry['enabled'] and not entry['visible_by_default'] and entry['pane'] == 'administrative'
    boundaries = feature_collection(load('barangay_boundaries.geojson'))
    canonical = {feature['properties']['gid']: feature['properties'] for feature in load('barangays.geojson')['features']}
    assert {feature['properties']['gid'] for feature in boundaries['features']} == set(canonical)
    for feature in boundaries['features']:
        props = feature['properties']
        assert feature['geometry']['type'] == 'Polygon'
        for key in ('name', 'pop2024', 'pop2020'):
            assert props[key] == canonical[props['gid']][key]
        assert props['provenance']['source_record_id']
        assert props['source_name'] and props['limitations']


def test_gis_schemas_registered_and_data_valid():
    from src.data.schemas import SCHEMAS, validate_all
    assert {'gis/barangays.geojson', 'gis/facilities.geojson', 'gis/layers.json'} <= SCHEMAS.keys()
    assert not [error for error in validate_all(SRC_DATA) if 'gis/' in error]
