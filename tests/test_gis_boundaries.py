import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from _build.gis_boundaries import extract_boundaries, quality_report

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    canonical = {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'geometry': None, 'properties': {'gid': f'0105528{i:03}', 'name': f'Canonical {i}', 'pop2024': i}}
        for i in range(1, 16)]}
    source = {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'geometry': {'type': 'Polygon', 'coordinates': [[[120.4, 16], [120.41, 16], [120.4, 16.01], [120.4, 16]]]},
         'properties': {'ADM3_PCODE': 'PH0105528', 'ADM4_PCODE': 'PH' + f['properties']['gid'],
                        'psgc_code': f['properties']['gid'], 'ADM4_EN': 'Original source name',
                        'AREA_SQKM': 1.9, 'date': '2022-11-09'}} for f in canonical['features']]}
    return source, canonical


def test_exact_join_preserves_original_shapes_and_canonical_directory():
    source, canonical = inputs()
    before = copy.deepcopy((source, canonical))
    result = extract_boundaries(source, canonical)
    assert (source, canonical) == before
    assert len(result['features']) == 15
    first = result['features'][0]
    assert first['geometry'] == source['features'][0]['geometry']
    assert first['properties']['name'] == 'Canonical 1'
    assert first['properties']['source_name'] == 'Original source name'
    assert first['properties']['pop2024'] == 1
    assert first['properties']['source_area_sqkm'] == 1.9
    assert all(f['geometry'] is None for f in canonical['features'])


@pytest.mark.parametrize('change', ['duplicate', 'unknown_code', 'conflicting_alias', 'null_geometry', 'nonfinite', 'wrong_municipality', 'null_properties'])
def test_bad_or_incomplete_source_not_silently_certified(change):
    source, canonical = inputs()
    first = source['features'][0]
    if change == 'duplicate':
        source['features'].append(copy.deepcopy(first))
    elif change == 'unknown_code':
        first['properties']['ADM4_PCODE'] = 'PH0105528999'
    elif change == 'conflicting_alias':
        first['properties']['psgc_code'] = '0105528999'
    elif change == 'null_geometry':
        first['geometry'] = None
    elif change == 'nonfinite':
        first['geometry']['coordinates'][0][0][0] = float('inf')
    elif change == 'wrong_municipality':
        first['properties']['ADM3_PCODE'] = 'Mapandan'
    elif change == 'null_properties':
        first['properties'] = None
    with pytest.raises(ValueError):
        extract_boundaries(source, canonical)


def test_subset_requires_explicit_mode():
    source, canonical = inputs()
    source['features'] = source['features'][:1]
    with pytest.raises(ValueError, match='all 15'):
        extract_boundaries(source, canonical)
    assert len(extract_boundaries(source, canonical, allow_subset=True)['features']) == 1


def test_no_analysis_dependencies_never_claims_topology_certification():
    source, canonical = inputs()
    report = quality_report(extract_boundaries(source, canonical), None)
    assert report['topology_checked'] is False
    assert report['disposition'] == 'optional_off_by_default_reference_geometry'


def test_real_small_extract_report_and_configuration_are_honest():
    directory = ROOT / 'src/data/gis'
    extracted = json.loads((directory / 'barangay_boundaries.geojson').read_text())
    canonical = json.loads((directory / 'barangays.geojson').read_text())
    report = json.loads((directory / 'barangay_boundaries_sources.json').read_text())['quality_report']
    config = json.loads((directory / 'layers.json').read_text())
    layer = next(layer for layer in config['layers'] if layer['id'] == 'barangay-boundaries')
    assert layer['enabled'] and not layer['visible_by_default']
    assert layer['semantic_role'] == 'barangay_reference_geometry'
    assert {f['properties']['gid'] for f in extracted['features']} == {f['properties']['gid'] for f in canonical['features']}
    assert all(f['geometry'] is None for f in canonical['features'])
    counts = [len(f['geometry']['coordinates'][0]) - 1 for f in extracted['features']]
    assert counts.count(3) == 6 and counts.count(4) == 9
    assert report['topology_checked'] and report['all_individually_valid']
    assert report['municipality_uncovered_percent'] == pytest.approx(25.3144, abs=0.001)
    assert report['overlap_area_km2'] == pytest.approx(0.43550, abs=0.0001)
    assert report['outside_municipality_km2'] == pytest.approx(1.39732, abs=0.0001)
    assert report['source_municipality_area_sqkm_metadata'] > report['municipality_geometry_area_km2']


def test_cli_requires_new_explicit_outputs_and_preserves_originals(tmp_path):
    source, canonical = inputs()
    original = tmp_path / 'source.json'
    reference = tmp_path / 'canonical.json'
    original.write_text(json.dumps(source))
    reference.write_text(json.dumps(canonical))
    output, sidecar = tmp_path / 'extracted.json', tmp_path / 'sources.json'
    command = [sys.executable, '-B', '-m', '_build.gis_boundaries', '--input', str(original),
               '--canonical', str(reference), '--output', str(output), '--sources-output', str(sidecar)]
    assert subprocess.run(command, cwd=ROOT, capture_output=True).returncode == 0
    before = original.read_bytes(), reference.read_bytes(), output.read_bytes(), sidecar.read_bytes()
    assert subprocess.run(command, cwd=ROOT, capture_output=True).returncode != 0
    assert before == (original.read_bytes(), reference.read_bytes(), output.read_bytes(), sidecar.read_bytes())


def test_topology_analysis_measures_overlaps_when_libraries_available():
    pytest.importorskip('shapely')
    pytest.importorskip('pyproj')
    source, canonical = inputs()
    municipality = copy.deepcopy(source)
    municipality['features'] = municipality['features'][:1]
    report = quality_report(extract_boundaries(source, canonical), municipality)
    assert report['topology_checked']
    assert report['overlap_area_km2'] > 0
    assert report['municipality_uncovered_km2'] == pytest.approx(0)
