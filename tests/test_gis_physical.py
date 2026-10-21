"""Raster preparation is explicit and independent of normal site builds."""

import json
import zipfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

np = pytest.importorskip('numpy')
pytest.importorskip('pyproj')
pytest.importorskip('PIL')
from PIL import Image  # noqa: E402

from _build.gis_physical import (  # noqa: E402
    FORWARD,
    INVERSE,
    SOURCE,
    SPECS,
    background_alpha,
    detect_grid,
    fit_affine,
    kmz_bytes,
    prepare,
    residuals,
    warp,
)

ROOT = Path(__file__).resolve().parents[1]
PREPARED = ROOT / 'datasets/GIS/physical/prepared'


def test_affine_with_independent_checks():
    controls = [[0, 0, 120.4, 16.05], [100, 0, 120.5, 16.05],
                [0, 100, 120.4, 15.95], [100, 100, 120.5, 15.95]]
    matrix = fit_affine(controls)
    assert np.allclose([50, 50, 1] @ matrix, [120.45, 16])
    assert residuals(matrix, [[50, 50, 120.45, 16]])['max_metres'] < 1e-5


@pytest.mark.parametrize('controls', [[], [[0, 0, 0, 0]]*4,
    [[0, 0, 120, 16], [1, 1, 121, 17], [2, 2, 122, 18], [3, 3, 123, 19]],
    [[0, 0, float('nan'), 0]]*4, [[0, 0, 999, 16]]*4,
    [[0, 0, 120, 16], [0, 1, 120, 16], [1, 0, 120, 16], [1, 1, 120, 16]]])
def test_invalid_sparse_and_degenerate_controls(controls):
    with pytest.raises(ValueError):
        fit_affine(controls)


def test_background_retains_thematic_color_and_enclosed_white_label():
    a = np.full((40, 40, 3), 255, dtype='uint8')
    a[8:32, 8:32] = [80, 150, 80]
    a[18:21, 18:21] = 255
    out = np.asarray(background_alpha(Image.fromarray(a)))
    assert out[0, 0, 3] == 0
    assert out[10, 10, 3] == 255
    assert out[19, 19, 3] == 255


def test_mercator_bounds_and_alpha_inverse_mapping():
    a = np.full((60, 60, 3), 255, dtype='uint8')
    a[10:50, 10:50] = [90, 80, 180]
    matrix = fit_affine([[0, 0, 120.4, 16.05], [59, 0, 120.5, 16.05],
                         [0, 59, 120.4, 15.95], [59, 59, 120.5, 15.95]])
    image, bounds, projected = warp(Image.fromarray(a), matrix, [0, 0, 60, 60])
    assert image.size == (60, 60)
    assert np.asarray(image)[30, 30, 3] == 255
    assert np.asarray(image)[0, 0, 3] == 0
    assert np.allclose(FORWARD.transform(bounds['west'], bounds['south']), projected[:2])
    assert np.allclose(FORWARD.transform(bounds['east'], bounds['north']), projected[2:])
    expected = np.array([-.5, -.5, 1]) @ matrix
    assert bounds['west'] == pytest.approx(expected[0])
    assert bounds['north'] == pytest.approx(expected[1])


def test_archive_is_deterministic_local_only_and_zero_rotation():
    bounds = {'north': 16.04, 'south': 16, 'east': 120.48, 'west': 120.42}
    data = kmz_bytes('physical-soil', b'png fixture', bounds)
    assert data == kmz_bytes('physical-soil', b'png fixture', bounds)
    with zipfile.ZipFile(BytesIO(data)) as archive:
        assert archive.namelist() == ['doc.kml', 'overlay.png']
        kml = ET.fromstring(archive.read('doc.kml'))
        ns = {'k': 'http://www.opengis.net/kml/2.2'}
        assert kml.find('.//k:href', ns).text == 'overlay.png'
        assert kml.find('.//k:rotation', ns).text == '0'
        assert archive.read('overlay.png') == b'png fixture'
    with pytest.raises(ValueError):
        kmz_bytes('../injection<xml>', b'', bounds)


def test_warp_rows_follow_mercator_not_poster_bounding_box_stretch():
    a = np.full((100, 100, 3), 80, dtype='uint8')
    a[:, :, 1] = np.arange(100)[:, None] * 2
    matrix = fit_affine([[0, 0, 120.4, 60], [99, 0, 120.5, 60],
                         [0, 99, 120.4, 0], [99, 99, 120.5, 0]])
    image, _, (west, south, east, north) = warp(Image.fromarray(a), matrix, [0, 0, 100, 100])
    _, latitude = INVERSE.transform((west+east)/2, north-50.5*(north-south)/100)
    expected_row = (60-latitude)*99/60
    assert np.asarray(image)[50, 50, 1] == pytest.approx(expected_row*2, abs=1)
    assert abs(expected_row-50) > 5


def test_refuses_overwrite_before_reading_sources(tmp_path):
    (tmp_path / 'physical-elevation.png').write_bytes(b'unchanged')
    with pytest.raises(FileExistsError):
        prepare(tmp_path / 'missing-source', tmp_path)
    assert (tmp_path / 'physical-elevation.png').read_bytes() == b'unchanged'


@pytest.mark.parametrize('layer_id', SPECS)
def test_real_source_registration_and_generated_resource(layer_id):
    filename = SPECS[layer_id][0]
    source = Image.open(SOURCE / filename).convert('RGB')
    controls, checks = detect_grid(source)
    assert len(controls) == len(checks) == 6
    assert set(map(tuple, controls)).isdisjoint(set(map(tuple, checks)))
    report = json.loads((PREPARED / f'{layer_id}.registration.json').read_text())
    record = json.loads((PREPARED / f'{layer_id}.source.json').read_text())
    assert report['fit']['points'] == controls
    assert report['withheld']['points'] == checks
    assert report['withheld']['residual_metres'] == pytest.approx(
        residuals(fit_affine(controls), checks)['residual_metres'], abs=1e-5)
    assert report['target_crs'] == 'EPSG:3857'
    assert report['withheld']['rmse_metres'] > 0  # Measured antialiased grid, not invented exact controls.
    assert record['prepared_date'] == '2021-12-15'
    assert record['data_vintage'] == 'unknown'
    assert 'no datum' in report['datum_assumption']
    for entry in record['legend']:
        assert entry['color'] == '#%02x%02x%02x' % source.getpixel(tuple(entry['source_pixel']))
    png = (PREPARED / f'{layer_id}.png').read_bytes()
    with zipfile.ZipFile(PREPARED / f'{layer_id}.kmz') as archive:
        assert archive.read('overlay.png') == png
    image = Image.open(BytesIO(png))
    assert image.mode == 'RGBA'
    alpha = np.asarray(image)[:, :, 3]
    assert np.any(alpha == 0) and np.any(alpha == 255)
    assert image.size == tuple(report['output_pixel_dimensions'])
