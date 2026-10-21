"""Development-only binary SHP/DBF round trips; no GIS dependencies at runtime."""
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from _build.gis_boundaries import (
    canonical_code,
    compare_geometries,
    extract_shapefile,
    geometry_metrics,
)

ROOT = Path(__file__).resolve().parents[1]
GID = '0105528001'
RING = [[120.44, 16.0], [120.44, 16.01], [120.45, 16.01], [120.45, 16.0], [120.44, 16.0]]


@pytest.fixture
def gis():
    return (pytest.importorskip('shapefile'), pytest.importorskip('pyproj'), pytest.importorskip('shapely'))


def canonical():
    return {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'geometry': None,
            'properties': {'gid': GID, 'name': 'Amanoaoac', 'pop2024': 1656, 'pop2020': 1636}}]}


def write_shape(tmp_path, gis, *, projected=False, rings=None, code=None, alias=105528001,
                name='Amanoaoac', municipality=None, duplicate=False, null=False):
    shapefile, pyproj, _ = gis
    path = tmp_path / ('projected.shp' if projected else 'geographic.shp')
    rings = copy.deepcopy(rings if rings is not None else [RING])
    if projected:
        project = pyproj.Transformer.from_crs(4326, 32651, always_xy=True)
        rings = [[project.transform(*point) for point in ring] for ring in rings]
    with shapefile.Writer(str(path), shapeType=shapefile.POLYGON) as writer:
        if projected:
            writer.field('adm3_psgc', 'N', 18)
            writer.field('adm4_psgc', 'N', 18)
            writer.field('adm4_en', 'C', 80)
        else:
            writer.field('adm3_pcode', 'C', 20)
            writer.field('adm4_pcode', 'C', 20)
            writer.field('psgc_code', 'N', 18)
            writer.field('adm4_en', 'C', 80)
        for _ in range(2 if duplicate else 1):
            if null:
                writer.null()
            else:
                writer.poly(rings)
            if projected:
                writer.record(105528000 if municipality is None else municipality,
                              105528001 if code is None else code, name)
            else:
                writer.record('PH0105528' if municipality is None else municipality,
                              'PH' + GID if code is None else code, alias, name)
    path.with_suffix('.prj').write_text(pyproj.CRS.from_epsg(32651 if projected else 4326).to_wkt())
    return path


@pytest.mark.parametrize('code', [105528001, '105528001', '0105528001', 'PH0105528001'])
def test_exact_numeric_padding_preserves_zero_identity(code):
    assert canonical_code(code) == GID


@pytest.mark.parametrize('code', [None, True, 105528001.0, 'Mapandan', '015528001', '10552801'])
def test_no_guessing_or_float_identity(code):
    if code == '015528001':
        # Padding cannot silently turn an older nine-digit PSGC into our gid.
        assert canonical_code(code) != GID
    else:
        with pytest.raises(ValueError):
            canonical_code(code)


def test_binary_geographic_roundtrip_is_verbatim_and_has_no_fifteen_assumption(tmp_path, gis):
    path = write_shape(tmp_path, gis)
    before = canonical()
    result, metadata = extract_shapefile(path, before)
    assert before == canonical()
    assert len(result['features']) == 1
    feature = result['features'][0]
    assert feature['geometry']['coordinates'] == [RING]
    assert feature['id'] == GID
    assert feature['properties']['pop2024'] == 1656
    assert feature['properties']['source_geometry_id'] == 'PH' + GID
    assert feature['properties']['provenance']['source_record_index_zero_based'] == 0
    assert feature['properties']['source_date'] is None
    assert metadata['source_crs'] == 'EPSG:4326' and not metadata['reprojected']
    assert metadata['record_count'] == 1


def test_projected_numeric_dbf_reprojection_and_faithful_equivalence(tmp_path, gis):
    geographic, _ = extract_shapefile(write_shape(tmp_path, gis), canonical())
    projected, metadata = extract_shapefile(write_shape(tmp_path, gis, projected=True), canonical())
    comparison = compare_geometries(geographic, projected)
    assert metadata['source_crs'] == 'EPSG:32651' and metadata['reprojected']
    assert projected['features'][0]['properties']['source_geometry_id'] == 105528001
    assert comparison['equivalent_within_tolerance']
    assert comparison['maximum_hausdorff_m'] < 1e-6
    assert geometry_metrics(projected)['coordinate_positions'] == 5


def test_multipart_and_hole_rings_are_not_flattened_or_dropped(tmp_path, gis):
    hole = [[120.442, 16.002], [120.444, 16.002], [120.444, 16.004], [120.442, 16.004], [120.442, 16.002]]
    island = [[x + .02, y] for x, y in RING]
    result, _ = extract_shapefile(write_shape(tmp_path, gis, rings=[RING, hole, island]), canonical())
    geometry = result['features'][0]['geometry']
    assert geometry['type'] == 'MultiPolygon'
    assert sorted(len(p) for p in geometry['coordinates']) == [1, 2]
    assert geometry_metrics(result)['coordinate_positions'] == 15


def test_overlap_quality_reports_material_conflicts_without_repairs(tmp_path, gis):
    result, _ = extract_shapefile(write_shape(tmp_path, gis), canonical())
    overlap = copy.deepcopy(result['features'][0])
    overlap['properties']['gid'] = '0105528002'
    result['features'].append(overlap)
    before = copy.deepcopy(result)
    report = geometry_metrics(result)
    assert report['cross_barangay_overlap_tolerance_m2'] == 1.0
    assert len(report['cross_barangay_pairs_exceeding_tolerance']) == 1
    assert report['overlap_area_km2'] > 1
    assert result == before


@pytest.mark.parametrize('problem', ['missing_dbf', 'missing_prj', 'unknown_crs', 'duplicate', 'null',
                                     'invalid', 'empty_ring', 'unknown_gid', 'conflicting_alias', 'name', 'municipality'])
def test_bad_binary_sources_fail_without_repair(tmp_path, gis, problem):
    options = {}
    if problem == 'duplicate':
        options['duplicate'] = True
    elif problem == 'null':
        options['null'] = True
    elif problem == 'invalid':
        options['rings'] = [[[120.44, 16], [120.45, 16.01], [120.44, 16.01], [120.45, 16], [120.44, 16]]]
    elif problem == 'empty_ring':
        options['rings'] = [[[120.44, 16]] * 4]
    elif problem == 'unknown_gid':
        options['code'] = 'PH0105528999'
    elif problem == 'conflicting_alias':
        options['alias'] = 105528002
    elif problem == 'name':
        options['name'] = 'Wrong name'
    elif problem == 'municipality':
        options['municipality'] = 'Mapandan'
    path = write_shape(tmp_path, gis, **options)
    if problem.startswith('missing_'):
        path.with_suffix('.dbf' if problem == 'missing_dbf' else '.prj').unlink()
    elif problem == 'unknown_crs':
        path.with_suffix('.prj').write_text('unknown')
    with pytest.raises(ValueError):
        extract_shapefile(path, canonical())


def test_cli_explicit_outputs_reproducible_readonly_inputs_and_no_overwrite(tmp_path, gis):
    primary = write_shape(tmp_path, gis)
    comparison = write_shape(tmp_path, gis, projected=True)
    reference = tmp_path / 'canonical.json'
    reference.write_text(json.dumps(canonical()))
    extracted, _ = extract_shapefile(primary, canonical())
    candidate = tmp_path / 'candidate.json'
    candidate.write_text(json.dumps(extracted))
    output, sidecar = tmp_path / 'output.geojson', tmp_path / 'sources.json'
    command = [sys.executable, '-B', '-m', '_build.gis_boundaries', '--input', str(primary),
               '--comparison-input', str(comparison), '--canonical', str(reference), '--candidate', str(candidate),
               '--output', str(output), '--sources-output', str(sidecar)]
    before = {p: p.read_bytes() for p in tmp_path.iterdir()}
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert all(p.read_bytes() == contents for p, contents in before.items())
    written = output.read_bytes(), sidecar.read_bytes()
    assert subprocess.run(command, cwd=ROOT, capture_output=True).returncode != 0
    assert written == (output.read_bytes(), sidecar.read_bytes())
    assert subprocess.run(command + ['--overwrite'], cwd=ROOT, capture_output=True).returncode == 0
    assert written == (output.read_bytes(), sidecar.read_bytes())
    unsafe = command.copy()
    unsafe[unsafe.index('--output') + 1] = str(primary.with_suffix('.dbf'))
    assert subprocess.run(unsafe + ['--overwrite'], cwd=ROOT, capture_output=True).returncode != 0
    assert all(p.read_bytes() == contents for p, contents in before.items())
    archive = tmp_path / 'legacy.geojson'
    archive_command = command + ['--overwrite', '--legacy-input', str(candidate), '--legacy-archive', str(archive)]
    assert subprocess.run(archive_command, cwd=ROOT, capture_output=True).returncode == 0
    assert archive.read_bytes() == candidate.read_bytes()
    archived_report = sidecar.read_bytes()
    assert subprocess.run(archive_command, cwd=ROOT, capture_output=True).returncode != 0
    # Reproduction references the existing archive without copying or replacing it.
    assert subprocess.run(command + ['--overwrite', '--legacy-archive', str(archive)],
                          cwd=ROOT, capture_output=True).returncode == 0
    assert sidecar.read_bytes() == archived_report
    assert archive.read_bytes() == candidate.read_bytes()


def test_checked_in_raw_provenance_candidate_relationship_and_legacy_archive():
    sidecar = json.loads((ROOT / 'src/data/gis/barangay_boundaries_sources.json').read_text())
    assert sidecar['source']['record_count'] == 45597
    assert sidecar['comparison_source']['record_count'] == 42017
    assert sidecar['source']['source_date'] is None
    assert sidecar['comparisons']['bundled_candidate']['coordinates_equal']
    assert sidecar['comparisons']['projected_raw']['equivalent_within_tolerance']
    assert sidecar['quality_report']['coordinate_positions'] == 985
    assert sidecar['projected_quality_report']['coordinate_positions'] == 985
    assert sidecar['candidate']['quality_report']['coordinate_positions'] == 985
    assert sidecar['area_discrepancy']['printed_clup_area_km2'] == 32.91752
    assert 'unresolved' in sidecar['area_discrepancy']['status']
    archive = ROOT / sidecar['legacy_archive']['path']
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == sidecar['legacy_archive']['sha256']
    archived = json.loads(archive.read_text())
    assert len(archived['features']) == 15
    assert all(f['properties']['location_precision'] == 'very_coarse' for f in archived['features'])


def test_actual_binary_sources_reproduce_committed_extract(gis):
    directory = ROOT / 'datasets/GIS/PH_Adm4_BgySubMuns.shp'
    if not directory.exists():
        pytest.skip('Large read-only source shapefiles not distributed in checkout')
    canonical_data = json.loads((ROOT / 'src/data/gis/barangays.geojson').read_text())
    expected = json.loads((ROOT / 'src/data/gis/barangay_boundaries.geojson').read_text())
    geographic, _ = extract_shapefile(directory / 'BgySubMuns.shp.shp', canonical_data)
    projected, _ = extract_shapefile(directory / 'PH_Adm4_BgySubMuns.shp.shp', canonical_data)
    assert len(geographic['features']) == 15
    for actual, committed in zip(geographic['features'], expected['features']):
        assert actual['geometry'] == committed['geometry']
        for key in ('gid', 'name', 'pop2024', 'pop2020', 'source_name'):
            assert actual['properties'][key] == committed['properties'][key]
    assert compare_geometries(geographic, projected)['equivalent_within_tolerance']
