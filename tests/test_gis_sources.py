import copy
import io
import json
import zipfile
from pathlib import Path

import pytest

from _build.gis import script_json
from _build.gis_preview import feature_collection, project_records
from _build.gis_sources import gis_asset_outputs, inspect_kmz, layer_configuration, prepare_inputs


def point(name='Synthetic facility'):
    return {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [120.45, 16.03]},
         'properties': {'id': 'synthetic-1', 'name': name, 'private_notes': 'DO NOT EMIT',
                        'review_notes': 'DO NOT EMIT', 'coordinate_history': ['DO NOT EMIT']}}]}


def configuration(root, layers=None):
    directory = root / 'src/data/gis'
    directory.mkdir(parents=True, exist_ok=True)
    if layers is None:
        layers = [layer('facilities', 'src/data/gis/facilities.geojson')]
    (directory / 'layers.json').write_text(json.dumps({'metadata': {'default_zoom': 14}, 'layers': layers}))
    return directory


def layer(identifier, source, kind='geojson', enabled=True):
    return {'id': identifier, 'title': {'en': identifier}, 'type': kind, 'source': source,
            'enabled': enabled, 'visible_by_default': True}


def kmz(rotation=0, href='tile.png', coordinates=None, extra=None):
    from PIL import Image
    image = io.BytesIO()
    Image.new('RGBA', (2, 2), (20, 30, 40, 100)).save(image, format='PNG')
    bounds = coordinates or '<west>120.4</west><south>16.0</south><east>120.5</east><north>16.1</north>'
    xml = f'<kml xmlns="http://www.opengis.net/kml/2.2"><GroundOverlay><Icon><href>{href}</href></Icon><LatLonBox>{bounds}<rotation>{rotation}</rotation></LatLonBox></GroundOverlay></kml>'
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        archive.writestr('doc.kml', xml)
        archive.writestr('tile.png', image.getvalue())
        if extra:
            archive.writestr(extra, b'unsafe')
    return output.getvalue(), image.getvalue()


def test_normalization_is_immutable_and_safe():
    source = point('</script><script>alert(1)</script>')
    original = copy.deepcopy(source)
    result = feature_collection(source)
    assert source == original
    assert result['features'][0]['geometry'] == original['features'][0]['geometry']
    assert 'DO NOT EMIT' not in script_json(result)
    assert '</script>' not in script_json(result)
    assert 'verification_status' not in result['features'][0]['properties']


@pytest.mark.parametrize('coordinates', [[999, 16], [120, -91], [True, 16], [120, float('inf')], [10 ** 500, 16], [120], []])
def test_invalid_individual_coordinates_skipped(coordinates, caplog):
    source = point()
    bad = copy.deepcopy(source['features'][0])
    bad['properties']['id'] = 'bad-point'
    bad['geometry']['coordinates'] = coordinates
    source['features'].insert(0, bad)
    assert len(feature_collection(source)['features']) == 1
    assert 'bad-point (index 0)' in caplog.text


@pytest.mark.parametrize('geometry', [
    {'type': 'Polygon', 'coordinates': [[[1, 1], [2, 1], [2, 2], [1, 2]]]},
    {'type': 'GeometryCollection', 'geometries': []},
    {'type': 'MultiLineString', 'coordinates': [[[1, 1]]]},
    {'type': 'LineString', 'coordinates': [[1, 1]]},
])
def test_bad_geometry_skipped(geometry):
    source = point()
    source['features'][0]['geometry'] = geometry
    assert feature_collection(source)['features'] == []


def test_missing_optional_inputs_do_not_abort(tmp_path, caplog):
    configuration(tmp_path)
    result = prepare_inputs(tmp_path)
    assert result['facilities']['features'] == []
    assert not result['layers'][0]['available']
    assert 'Missing or oversized GIS input' in result['layers'][0]['unavailable_reason']
    assert 'facilities' in caplog.text and 'src/data/gis/facilities.geojson' in caplog.text


def test_selected_sources_emit_without_approvals_and_disabled_sources_not_read(tmp_path, monkeypatch):
    layers = [layer('facilities', 'src/data/gis/facilities.geojson'),
              layer('roads', 'datasets/GIS/roads.geojson'),
              layer('disabled', 'datasets/GIS/disabled.geojson', enabled=False),
              layer('projects', 'src/data/entities/projects.json', 'records'),
              layer('hazard', 'datasets/GIS/hazard.kmz', 'kmz')]
    directory = configuration(tmp_path, layers)
    (directory / 'facilities.geojson').write_text(json.dumps(point()))
    (tmp_path / 'datasets/GIS').mkdir(parents=True)
    roads = point()
    roads['features'][0]['geometry'] = {'type': 'LineString', 'coordinates': [[120.4, 16], [120.5, 16.1]]}
    (tmp_path / 'datasets/GIS/roads.geojson').write_text(json.dumps(roads))
    raw, png = kmz()
    (tmp_path / 'datasets/GIS/hazard.kmz').write_bytes(raw)
    (tmp_path / 'src/data/entities').mkdir()
    (tmp_path / 'src/data/entities/projects.json').write_text(json.dumps([{'project_id': 'prj-1', 'canonical_name': 'Project'}]))
    import _build.gis_sources as sources
    bounded = sources.bounded_bytes

    def read(path, *args):
        assert 'disabled' not in str(path)
        return bounded(path, *args)

    monkeypatch.setattr(sources, 'bounded_bytes', read)
    result = prepare_inputs(tmp_path, lang_code='pag')
    assert len(result['facilities']['features']) == 1
    assert result['records'][0]['geometry'] is None
    assert result['records'][0]['project_url'] == '/pag/transparency/projects/?project=prj-1'
    assert [entry['available'] for entry in result['layers']] == [True, True, False, True, True]
    assert (tmp_path / 'assets/gis/hazard-0.png').read_bytes() == png
    expected = {'assets/gis/manifest.json', 'assets/gis/roads.geojson', 'assets/gis/hazard-0.png'}
    assert {path.as_posix() for path in gis_asset_outputs(tmp_path)} == expected
    assert not any('publishable' in entry or 'status' in entry for entry in result['layers'])


@pytest.mark.parametrize('source', ['/tmp/file', '../file', 'src/data/../file', 'https://example.org/data',
                                    'src\\data\\file', 'datasets/GIS//file', 'assets/file', 'src/data/./file'])
def test_unsafe_config_path_fails_even_when_disabled(tmp_path, source):
    configuration(tmp_path, [layer('unsafe', source, enabled=False)])
    with pytest.raises(ValueError, match='GIS source'):
        layer_configuration(tmp_path)


@pytest.mark.parametrize('change', [{'id': '../bad'}, {'type': 'unknown'}, {'enabled': 'true'}, {'source_url': 'javascript:alert(1)'}])
def test_bad_configuration_fails(tmp_path, change):
    entry = layer('facilities', 'src/data/gis/facilities.geojson')
    entry.update(change)
    configuration(tmp_path, [entry])
    with pytest.raises(ValueError):
        prepare_inputs(tmp_path)


def test_duplicate_layer_ids_fail(tmp_path):
    entry = layer('same', 'src/data/gis/input.geojson')
    configuration(tmp_path, [entry, entry])
    with pytest.raises(ValueError, match='duplicate'):
        prepare_inputs(tmp_path)


def test_symlink_input_fails(tmp_path):
    directory = configuration(tmp_path)
    (directory / 'facilities.geojson').symlink_to(directory / 'other.geojson')
    with pytest.raises(ValueError, match='Symlink'):
        prepare_inputs(tmp_path)


@pytest.mark.parametrize('kwargs', [{'rotation': 15}, {'href': '../tile.png'}, {'extra': '../bad'},
                                     {'coordinates': '<west>nan</west>'}])
def test_kmz_unsupported_or_unsafe_rejected(kwargs):
    raw, _ = kmz(**kwargs)
    with pytest.raises(ValueError):
        inspect_kmz(raw)


def test_safe_kmz_preserves_png_and_bounds():
    raw, png = kmz()
    assert inspect_kmz(raw) == [(png, {'west': 120.4, 'south': 16.0, 'east': 120.5, 'north': 16.1})]


def test_project_links_only_exact_ids_no_guessed_positions():
    result = project_records([{'project_id': 'id-123', 'canonical_name': 'A', 'latitude': 16},
                              {'project_id': '../bad', 'canonical_name': 'B'}], 'fil')
    assert len(result) == 1
    assert result[0]['geometry'] is None
    assert result[0]['project_url'] == '/fil/transparency/projects/?project=id-123'


def test_asset_manifest_rejects_traversal_and_ignores_stale_files(tmp_path):
    directory = tmp_path / 'assets/gis'
    directory.mkdir(parents=True)
    (directory / 'stale.png').write_bytes(b'stale')
    manifest = directory / 'manifest.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'files': []}))
    assert gis_asset_outputs(tmp_path) == {Path('assets/gis/manifest.json')}
    manifest.write_text(json.dumps({'schema_version': 1, 'files': ['assets/gis/../bad.png']}))
    with pytest.raises(ValueError, match='Unsafe'):
        gis_asset_outputs(tmp_path)


@pytest.mark.parametrize('change', [
    {'opacity': True}, {'opacity': -0.1}, {'opacity': 1.1}, {'opacity': '0.5'},
    {'pane': 'unknown'}, {'group': {'en': 'Only English'}}, {'exclusive_group': ''},
    {'exclusive_group': False}, {'dependencies': 'src/data/file'},
    {'dependencies': ['../unsafe']},
])
def test_v3_metadata_validation(tmp_path, change):
    entry = layer('example', 'src/data/example.geojson', enabled=False)
    entry.update(change)
    configuration(tmp_path, [entry])
    with pytest.raises(ValueError):
        layer_configuration(tmp_path)


def test_v3_metadata_forwarded_without_governance(tmp_path):
    entry = layer('example', 'src/data/example.geojson')
    metadata = {'group': {'en': 'Physical', 'fil': 'Pisikal', 'pag': 'Physical'},
                'pane': 'physical', 'opacity': 0.65, 'exclusive_group': 'historical-physical',
                'semantic_role': 'historical_physical_characteristic'}
    entry.update(metadata)
    directory = configuration(tmp_path, [entry])
    (directory / 'example.geojson').write_text(json.dumps(point()))
    result = prepare_inputs(tmp_path)
    assert all(result['layers'][0][key] == value for key, value in metadata.items())


def test_dpwh_emitted_with_null_records_and_full_safe_contract(tmp_path):
    entry = layer('dpwh-projects', 'src/data/dpwh.json', 'dpwh')
    configuration(tmp_path, [entry])
    directory = tmp_path / 'src/data'
    (directory / 'entities').mkdir()
    canonical = [{'project_id': 'prj-1', 'canonical_name': 'Road', 'source_transaction_id': 'tx-1'}]
    (directory / 'entities/projects.json').write_text(json.dumps(canonical))
    source = {'projects': [{'transaction_id': 'tx-1', 'project_name': 'Road', 'longitude': 120.45,
                            'latitude': 16.03, 'status': 'Completed', 'contract_amount': 1234.5,
                            'actual_start_date': '2024-01-01', 'private_notes': 'DO NOT EMIT'},
                           {'transaction_id': 'tx-2', 'project_name': 'Unlocated'}]}
    (directory / 'dpwh.json').write_text(json.dumps(source))
    result = prepare_inputs(tmp_path, lang_code='fil')
    data = json.loads((tmp_path / 'assets/gis/dpwh-projects.geojson').read_text())
    assert len(data['features']) == 2 and data['features'][1]['geometry'] is None
    first = data['features'][0]['properties']
    assert first['project_id'] == 'prj-1' and first['status_key'] == 'completed'
    assert first['contract_amount'] == 1234.5 and first['actual_start_date'] == '2024-01-01'
    assert first['project_url'] == '/fil/transparency/projects/?project=prj-1'
    assert data['features'][1]['properties']['project_url'] == '/fil/transparency/infrastructure/#dpwh-project-tx-2'
    assert all(record['layer_id'] == 'dpwh-projects' for record in result['records'])
    assert 'DO NOT EMIT' not in script_json(result)


def test_numeric_allowlist_rejects_unsafe_values_and_preserves_psgc():
    source = point()
    props = source['features'][0]['properties']
    props.update(psgc='0105528001', source_name='Source Name', contract_amount=float('inf'),
                 approved_budget=True, accomplishment_percent=95.5, fiscal_year=2025,
                 private_number=1234, source_area_sqkm=1.23)
    result = feature_collection(source)['features'][0]['properties']
    assert result['psgc'] == '0105528001' and result['source_name'] == 'Source Name'
    assert result['accomplishment_percent'] == 95.5 and result['fiscal_year'] == 2025
    assert result['source_area_sqkm'] == 1.23
    assert not {'contract_amount', 'approved_budget', 'private_number'} & result.keys()


def test_boundary_source_identity_and_note_project_to_supported_fields():
    source = point()
    props = source['features'][0]['properties']
    props.update(source_geometry_id=123, source_name='Original source name',
                 source_note='Indicative only; source vintage unknown.',
                 limitations=['Not legal boundaries.'])
    result = feature_collection(source)['features'][0]['properties']
    assert result['provenance']['source_record_id'] == '123'
    assert result['source_name'] == 'Original source name'
    assert result['limitations'] == ['Not legal boundaries.', 'Indicative only; source vintage unknown.']
    assert 'provenance' not in props


def test_boundary_source_identity_does_not_override_explicit_provenance():
    source = point()
    source['features'][0]['properties'].update(
        source_geometry_id='candidate-1', source_note=123,
        provenance={'source': 'Raw shapefile', 'source_record_id': 'raw-1'})
    result = feature_collection(source)['features'][0]['properties']
    assert result['provenance'] == {'source': 'Raw shapefile', 'source_record_id': 'raw-1'}
    assert 'limitations' not in result


def test_source_reference_never_reads_or_emits_artwork(tmp_path, monkeypatch):
    entry = layer('flood-susceptibility', 'datasets/GIS/missing-original.jpeg', 'source-reference')
    entry.update(visible_by_default=False, source_url='https://mapandan.gov.ph/disaster-awareness/',
                 limitations=[{'en': 'Rights and registration unresolved', 'fil': 'Hindi tiyak', 'pag': 'Agni segurado'}])
    directory = configuration(tmp_path, [entry, layer('roads', 'src/data/gis/roads.geojson')])
    (directory / 'roads.geojson').write_text(json.dumps(point()))
    import _build.gis_sources as sources
    bounded = sources.bounded_bytes

    def read(path, *args):
        assert not str(path).endswith('.jpeg')
        return bounded(path, *args)

    monkeypatch.setattr(sources, 'bounded_bytes', read)
    result = prepare_inputs(tmp_path)
    reference, roads = result['layers']
    assert reference['available'] and reference['type'] == 'reference'
    assert not {'data_key', 'url', 'images'} & reference.keys()
    assert reference['limitations'] == entry['limitations']
    assert roads['available']
    assert gis_asset_outputs(tmp_path) == {Path('assets/gis/manifest.json'), Path('assets/gis/roads.geojson')}


@pytest.mark.parametrize('change', [{'visible_by_default': True}, {'source_url': ''}, {'source_url': 'javascript:alert(1)'}])
def test_invalid_source_reference_configuration_fails_before_inputs(tmp_path, change):
    entry = layer('flood', 'datasets/GIS/missing.jpeg', 'source-reference')
    entry.update(visible_by_default=False, source_url='https://mapandan.gov.ph/disaster-awareness/')
    entry.update(change)
    configuration(tmp_path, [entry])
    with pytest.raises(ValueError):
        prepare_inputs(tmp_path)


def test_flood_fallback_and_seven_coordinated_thematic_sources():
    root = Path(__file__).resolve().parents[1]
    layers = layer_configuration(root)['layers']
    themes = [entry for entry in layers if entry.get('exclusive_group') == 'thematic-rasters']
    assert len(themes) == 7
    assert all(not entry['visible_by_default'] for entry in themes)
    flood = next(entry for entry in themes if entry['id'] == 'flood-susceptibility')
    assert flood['type'] == 'source-reference' and flood['pane'] == 'hazards' and flood['opacity'] == 0.6
    assert flood['source_url'] == 'https://mapandan.gov.ph/disaster-awareness/'
    assert 'legend' not in flood
    assert all(set(note) == {'en', 'fil', 'pag'} for note in flood['limitations'])
