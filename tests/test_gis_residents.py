import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from _build.gis import facilities_collection, script_json
from _build.gis_residents import (
    BARANGAY_SLUGS,
    contact_placeholders,
    phone_link,
    reconcile,
    residents,
)
from _build.gis_sources import prepare_inputs

ROOT = Path(__file__).resolve().parents[1]


def source(relative):
    return json.loads((ROOT / relative).read_text())


def in_ring(point, ring):
    x, y = point
    inside = False
    for (a, b), (c, d) in zip(ring, ring[1:]):
        if abs((x-a)*(d-b) - (y-b)*(c-a)) < 1e-12 and min(a,c) <= x <= max(a,c) and min(b,d) <= y <= max(b,d):
            return True
        if (b > y) != (d > y) and x < (c-a)*(y-b)/(d-b)+a:
            inside = not inside
    return inside


def contains(point, geometry):
    polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
    return any(in_ring(point, rings[0]) and not any(in_ring(point, hole) for hole in rings[1:]) for rings in polygons)


def centroid(ring):
    # Translate near the origin to avoid cancellation with geographic coordinates.
    ox, oy = ring[0]
    points = [(x-ox, y-oy) for x, y in ring]
    area = xsum = ysum = 0
    for (x, y), (u, v) in zip(points, points[1:]):
        cross = x*v-u*y
        area += cross
        xsum += (x+u)*cross
        ysum += (y+v)*cross
    return [ox+xsum/(3*area), oy+ysum/(3*area)]


def decode(full):
    alphabet = '23456789CFGHJMPQRVWX'
    code = full.replace('+', '')
    lat, lon = -90, -180
    scale = 20
    for i in range(0, 10, 2):
        lat += alphabet.index(code[i])*scale
        lon += alphabet.index(code[i+1])*scale
        lat_size = lon_size = scale
        scale /= 20
    for char in code[10:]:
        value = alphabet.index(char)
        lat_size /= 5
        lon_size /= 4
        lat += (value//4)*lat_size
        lon += (value%4)*lon_size
    return [lon+lon_size/2, lat+lat_size/2]


def test_complete_inventory_explicit_identity_and_determinism(tmp_path):
    first = prepare_inputs(ROOT, tmp_path)
    second = prepare_inputs(ROOT, tmp_path)
    assert first == second
    features = first['facilities']['features']
    refs = [r for r in first['records'] if r.get('evacuation_id')]
    mapped = [f for f in features if f['properties'].get('evacuation_id')]
    assert len(mapped) == 9 and len(refs) == 3
    assert {f['properties']['evacuation_id'] for f in mapped} | {r['evacuation_id'] for r in refs} == {f'evac-{i:03}' for i in range(1, 13)}
    assert {r['id'] for r in refs} == {'evac-002', 'evac-004', 'evac-005'}
    assert all(r['geometry'] is None for r in refs)
    all_props = [f['properties'] for f in mapped] + refs
    assert all(p['evacuation_capacity'] is None and p['evacuation_source_date'] is None for p in all_props)
    assert next(f for f in mapped if f['properties']['evacuation_id'] == 'evac-003')['properties']['id'] == 'fac-011'
    assert next(f for f in mapped if f['properties']['evacuation_id'] == 'evac-001')['properties']['id'] == 'fac-017'
    assert 'fac-006' not in {f['properties']['id'] for f in features}
    assert first['metadata']['evacuation_counts'] == {'listings':12, 'spatial_locations':9, 'unresolved_listings':3, 'unique_coordinates':9}
    assert all('Current availability not confirmed' in ' '.join(p['limitations']) for p in all_props)


def test_projection_is_stable_across_python_hash_seeds():
    command = """from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
from _build.gis import script_json
from _build.gis_sources import prepare_inputs
with TemporaryDirectory() as directory:
    print(sha256(script_json(prepare_inputs(Path.cwd(), Path(directory))).encode()).hexdigest())
"""
    hashes = [subprocess.check_output([sys.executable, '-c', command], cwd=ROOT,
              env={**os.environ, 'PYTHONHASHSEED': seed}) for seed in ('1', '2')]
    assert hashes[0] == hashes[1]


def test_safe_shared_directory_has_exact_psgc_join_and_no_nested_personal_contacts():
    data = residents(ROOT)
    assert set(data['barangays']) == set(BARANGAY_SLUGS.values())
    assert data['barangays']['0105528016']['slug'] == 'sta-maria'
    assert data['barangays']['0105528016']['url'] == '/government/#barangay-councils'
    raw = source('src/data/barangays.json')['barangays']
    projected = script_json(data['barangays'])
    for row in raw:
        for member in row.get('kagawads', []) + row.get('officials', []):
            if member.get('email'):
                assert member['email'] not in projected
    assert 'email' not in projected and '"contact"' not in projected
    assert data['contacts']['current_confirmation'] is None
    assert data['contacts']['source_verification_claim'] == 'August 2026'


@pytest.mark.parametrize('value', [None, '', 'N/A', 'javascript:alert(1)', '+1;bad', 'abc', '\n911'])
def test_missing_or_unsafe_phone(value):
    assert phone_link(value) is None


def test_publication_exclusions_and_linked_footprints(tmp_path):
    data = prepare_inputs(ROOT, tmp_path)
    public = script_json(data)
    assert 'Mapandan Town Center' not in public
    assert 'coordinate_history' not in public and 'review_notes' not in public
    assert not {'fac-010', 'fac-012', 'fac-013', 'fac-014'} & {f['properties']['id'] for f in data['facilities']['features']}
    refs = {r['id']: r for r in data['records'] if r['layer_id'] == 'facility-references'}
    assert not {'fac-012', 'fac-013', 'fac-014', 'fac-015'} & refs.keys()
    places = json.loads((tmp_path / 'assets/gis/places.geojson').read_text())
    assert len([f for f in places['features'] if f['properties'].get('canonical_facility_id')]) == 8
    assert all(f['geometry']['type'] == 'Polygon' for f in places['features'] if f['properties'].get('canonical_facility_id'))


def test_footprint_positions_reproducible_not_hall_substitutions():
    places = {f['id']:f for f in source('datasets/GIS/places.geojson')['features']}
    facilities = {f['properties']['id']:f for f in source('src/data/gis/facilities.geojson')['features']}
    for row in source('src/data/gis/evacuation-crosswalk.json')['listings']:
        if not row['facility_id'] or not row['osm_ids']:
            continue
        facility = facilities[row['facility_id']]
        footprint = places[row['osm_ids'][0]]
        assert facility['properties']['coordinate_method'] == 'polygon_centroid'
        point = facility['geometry']['coordinates']
        assert contains(point, footprint['geometry'])
        assert point == pytest.approx(centroid(footprint['geometry']['coordinates'][0]), abs=0.000002)
    assert decode('7Q822FG3+XFW') == pytest.approx([120.453703125,16.0274875])
    assert decode('7Q822CHP+7H2') == pytest.approx([120.436390625,16.0281375])
    assert decode('7Q822FP4+VVR') == pytest.approx([120.457140625,16.0372375])


def test_indicative_boundaries_are_qa_not_building_evidence():
    facilities = source('src/data/gis/facilities.geojson')['features']
    boundaries = source('src/data/gis/barangay_boundaries.geojson')['features']
    for f in facilities:
        if f['properties']['id'] not in {'fac-012','fac-013','fac-014','fac-017','fac-018','fac-019','fac-020','fac-021','fac-022','fac-023','fac-024'}:
            continue
        matches = [b['properties']['name'] for b in boundaries if contains(f['geometry']['coordinates'], b['geometry'])]
        print(f['properties']['id'], 'indicative containment:', matches, '; QA only, not building verification')
    outer = [[0,0],[5,0],[5,5],[0,5],[0,0]]
    hole = [[1,1],[2,1],[2,2],[1,2],[1,1]]
    geometry = {'type':'Polygon','coordinates':[outer,hole]}
    assert contains([0,2], geometry) and contains([4,4], geometry)
    assert not contains([1.5,1.5], geometry)


def test_crosswalk_malformed_fails_closed(tmp_path):
    import shutil
    for relative in ('src/data/gis/evacuation-crosswalk.json', 'datasets/GIS/evacuation.json'):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    path = tmp_path / 'src/data/gis/evacuation-crosswalk.json'
    data = json.loads(path.read_text())
    data['listings'][0]['source_name'] = 'OTHER INSTITUTION'
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='does not match source'):
        reconcile(tmp_path, facilities_collection(source('src/data/gis/facilities.geojson')), [])


def test_canonical_contact_change_reaches_map_pages_and_header(tmp_path, monkeypatch):
    from _build import chrome
    data = source('src/data/public-contacts.json')
    data['offices']['mdrrmo']['phones'][2] = '0912-345-6789'
    directory = tmp_path / 'src/data'
    directory.mkdir(parents=True)
    (directory / 'public-contacts.json').write_text(json.dumps(data))
    (directory / 'barangays.json').write_text(json.dumps(source('src/data/barangays.json')))
    partials = tmp_path / 'src/partials'
    partials.mkdir()
    (partials / 'header.html').write_text((ROOT / 'src/partials/header.html').read_text())
    monkeypatch.setattr(chrome, 'SRC_PARTIALS', partials)
    values = contact_placeholders(tmp_path)
    assert '0912-345-6789' in values['PUBLIC_MDRRMO_HOMEPAGE']
    assert '0912-345-6789' in values['PUBLIC_MDRRMO_MOBILE']
    assert residents(tmp_path)['contacts']['offices']['mdrrmo']['phones'][2] == '0912-345-6789'
    header = chrome.build_header({}, '/', 'en', dict(en='/', fil='/fil/', pag='/pag/'))
    assert '0912-345-6789' in header and 'tel:09123456789' in header
    assert '0969-223-6912' not in header
