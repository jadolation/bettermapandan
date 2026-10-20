"""Explicit, offline preparation of historical MPDC posters, not a build hook.

Run with Pillow, numpy and pyproj installed. Pixel coordinates refer to pixel
centres in the untouched poster. No boundary polygon participates in the fit.
"""

import argparse
import hashlib
import json
import zipfile
from collections import deque
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from pyproj import Geod, Transformer

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'datasets/GIS/Better_Mapandan_GIS_V3_1_Updated_Package/Better_Mapandan_GIS_V3_1/sources/physical'
LONS = [120.42, 120.44, 120.46, 120.48]
LATS = [16.04, 16.02, 16.0]
FORWARD = Transformer.from_crs('EPSG:4326', 'EPSG:3857', always_xy=True)
INVERSE = Transformer.from_crs('EPSG:3857', 'EPSG:4326', always_xy=True)
GEOD = Geod(ellps='WGS84')
SPECS = {
    'physical-elevation': ('elevation.png', [f'{n} m above sea level' for n in [1, 4, 8, 12, 16, 20, 24, 28]],
                           [(1040, y) for y in [1611, 1633, 1654, 1675, 1696, 1718, 1739, 1760]]),
    'physical-slope': ('slope.png', ['0 - 3%', '3 - 8%'], [(1040, 1611), (1040, 1633)]),
    'physical-soil': ('soil_classification.png', ['San Manuel Fine Sandy Loam', 'San Manuel Silt Loam',
                                               'San Manuel Silty Clay Loam', 'River Wash'],
                      [(1040, y) for y in [1611, 1633, 1654, 1675]]),
    'physical-land-capability': ('land_capability.png', ['Class A', 'Class B'], [(450, 698), (450, 707)]),
}


def fit_affine(controls):
    """Fit pixel centres -> longitude/latitude; reject bad or sparse input."""
    points = np.asarray(controls, dtype=float)
    if points.ndim != 2 or points.shape[1] != 4 or len(points) < 4 or not np.isfinite(points).all():
        raise ValueError('At least four finite x/y/lon/lat controls required')
    if np.any(np.abs(points[:, 2]) > 180) or np.any(np.abs(points[:, 3]) > 85):
        raise ValueError('Controls must be geographic longitude/latitude')
    design = np.column_stack((points[:, :2], np.ones(len(points))))
    if np.linalg.matrix_rank(design) != 3:
        raise ValueError('Degenerate pixel controls')
    matrix = np.linalg.lstsq(design, points[:, 2:], rcond=None)[0]
    if abs(np.linalg.det(matrix[:2])) < 1e-15:
        raise ValueError('Degenerate geographic controls')
    return matrix


def detect_grid(image):
    """Measure each crossing locally, without reusing a fitted regular grid.

    Search windows are visually selected around the printed crossings. Median
    line profiles suppress roads/text; darkness centroids retain antialiasing.
    Crossings with insufficient local line contrast fail rather than snapping.
    """
    a = np.asarray(image.convert('RGB'), dtype=float).mean(axis=2)
    low = image.width == 768
    xs, ys = ([39, 246, 453, 660], [118, 325, 532]) if low else ([91, 569, 1046, 1523], [272, 749, 1227])
    radius = 18 if low else 40
    controls, checks = [], []
    for j, y in enumerate(ys):
        for i, x in enumerate(xs):
            xy = []
            for axis, center in [(0, x), (1, y)]:
                patch = a[y-radius:y+radius+1, x-3:x+4] if axis == 0 else a[y-3:y+4, x-radius:x+radius+1]
                # Two low-resolution crossings overlap dark roads/water marks.
                # Independently selected clear segments on those same printed
                # lines are measured instead; do not force regular spacing.
                if low and axis == 0 and i == 2 and j in (0, 2):
                    start, stop = (72, 90) if j == 0 else (550, 570)
                    patch = a[start:stop, x-3:x+4]
                profile = np.median(patch, axis=axis)
                weights = np.maximum(0, np.median(profile[[0, -1]]) - profile)
                if weights.sum() < 12:
                    raise ValueError(f'Unmeasurable printed crossing at {x},{y}')
                xy.append(float(np.dot(np.arange(center-3, center+4), weights) / weights.sum()))
            (controls if (i+j) % 2 == 0 else checks).append([*xy, LONS[i], LATS[j]])
    return controls, checks


def residuals(matrix, points):
    a = np.asarray(points)
    predicted = np.column_stack((a[:, :2], np.ones(len(a)))) @ matrix
    _, _, metres = GEOD.inv(a[:, 2], a[:, 3], predicted[:, 0], predicted[:, 1])
    return {'points': a.tolist(), 'residual_metres': metres.tolist(),
            'rmse_metres': float(np.sqrt(np.mean(metres ** 2))), 'max_metres': float(np.max(metres))}


def background_alpha(image):
    """Remove near-white exterior paper, not a guessed municipal polygon.

    A 5px connectivity bridge crosses thin printed grid/road strokes. Only the
    original near-white pixels are removed; black exterior labels/roads remain.
    Enclosed white label halos are retained. No thematic class is white here.
    """
    rgba = np.array(image.convert('RGBA'))
    white = np.all(rgba[:, :, :3] >= 250, axis=2)
    bridge = Image.fromarray(white.astype('uint8') * 255).filter(ImageFilter.MaxFilter(5))
    accessible = np.asarray(bridge) > 0
    seen = np.zeros(white.shape, dtype=bool)
    h, w = white.shape
    queue = deque([(x, y) for x in range(w) for y in (0, h-1)] + [(x, y) for y in range(h) for x in (0, w-1)])
    while queue:
        x, y = queue.popleft()
        if not 0 <= x < w or not 0 <= y < h or seen[y, x] or not accessible[y, x]:
            continue
        seen[y, x] = True
        queue.extend(((x-1, y), (x+1, y), (x, y-1), (x, y+1)))
    rgba[white & seen, 3] = 0
    return Image.fromarray(rgba)


def warp(image, matrix, crop):
    """Inverse-map a north-up EPSG:3857 rectangle, bilinear in premultiplied RGBA."""
    left, top, right, bottom = crop
    corners = np.array([[left-.5, top-.5, 1], [right-.5, top-.5, 1],
                        [right-.5, bottom-.5, 1], [left-.5, bottom-.5, 1]]) @ matrix
    xx, yy = FORWARD.transform(corners[:, 0], corners[:, 1])
    west, east, south, north = float(min(xx)), float(max(xx)), float(min(yy)), float(max(yy))
    width, height = right-left, bottom-top
    target_x, target_y = np.meshgrid(west+(np.arange(width)+.5)*(east-west)/width,
                                    north-(np.arange(height)+.5)*(north-south)/height)
    lon, lat = INVERSE.transform(target_x, target_y)
    inverse = np.linalg.inv(np.vstack((matrix.T, [0, 0, 1])))
    sx = inverse[0, 0]*lon + inverse[0, 1]*lat + inverse[0, 2] - left
    sy = inverse[1, 0]*lon + inverse[1, 1]*lat + inverse[1, 2] - top
    source = np.asarray(background_alpha(image.crop(crop)), dtype=float) / 255
    source[:, :, :3] *= source[:, :, 3:4]
    out = np.zeros((height, width, 4))
    ix, iy = np.floor(sx).astype(int), np.floor(sy).astype(int)
    fx, fy = sx-ix, sy-iy
    for dx, dy, weight in [(0, 0, (1-fx)*(1-fy)), (1, 0, fx*(1-fy)), (0, 1, (1-fx)*fy), (1, 1, fx*fy)]:
        valid = (ix+dx >= 0) & (ix+dx < width) & (iy+dy >= 0) & (iy+dy < height)
        out[valid] += source[(iy+dy)[valid], (ix+dx)[valid]] * weight[valid, None]
    np.divide(out[:, :, :3], out[:, :, 3:4], out=out[:, :, :3], where=out[:, :, 3:4] > 0)
    png = Image.fromarray(np.round(np.clip(out, 0, 1)*255).astype('uint8'))
    w, s = INVERSE.transform(west, south)
    e, n = INVERSE.transform(east, north)
    return png, {'west': w, 'south': s, 'east': e, 'north': n}, [west, south, east, north]


def kmz_bytes(layer_id, png, bounds):
    if layer_id not in SPECS:
        raise ValueError('Unknown layer identifier')
    b = bounds
    kml = (f'<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2">'
           f'<GroundOverlay><name>{layer_id}</name><Icon><href>overlay.png</href></Icon><LatLonBox>'
           f'<north>{b["north"]:.12f}</north><south>{b["south"]:.12f}</south>'
           f'<east>{b["east"]:.12f}</east><west>{b["west"]:.12f}</west><rotation>0</rotation>'
           '</LatLonBox></GroundOverlay></kml>')
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in [('doc.kml', kml.encode()), ('overlay.png', png)]:
            info = zipfile.ZipInfo(name, date_time=(2021, 12, 15, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return buffer.getvalue()


def external_checks(matrix, low, root):
    """Two independently identified road junctions, never fitting controls."""
    features = json.loads((root / 'datasets/GIS/highways.geojson').read_text())['features']
    points = [f['geometry']['coordinates'] for f in features if f['properties'].get('@id') == 'way/35866813']
    if not points or points[0][0] != [120.459316, 16.0214496]:
        raise ValueError('Independent OSM check source changed; review required')
    # Visually selected line-centre junctions in each original poster, not inferred
    # by projecting OSM back into the image. Resolution limits are retained.
    source_pixels = [[447, 309], [396, 245]] if low else [[1032, 716], [913, 567]]
    references = [[120.459316, 16.0214496], [120.4538252, 16.0271765]]
    if not any([120.4538252, 16.0271765] in f['geometry']['coordinates']
               for f in features if f['properties'].get('name') == 'Pandan Avenue'):
        raise ValueError('Independent Pandan Avenue check changed; review required')
    return {'method': 'Visual identification of road-junction line centres against independent OSM coordinates; not used in fit',
            'source': 'datasets/GIS/highways.geojson (OpenStreetMap export 2026-10-18; ODbL)',
            'source_sha256': hashlib.sha256((root / 'datasets/GIS/highways.geojson').read_bytes()).hexdigest(),
            'visual_review': 'OSM secondary roads and Angalacan River overplotted in QA; broad correspondence, not exact agreement. Central Fire Tree/Pandan junction disagrees materially (see measured offset); do not use this overlay for precise road/parcel placement. Neither junction adjusts the fit.',
            'features': ['Fire Tree Avenue / Mango Avenue', 'Fire Tree Avenue / Pandan Avenue'],
            **residuals(matrix, [[*p, *r] for p, r in zip(source_pixels, references)])}


def prepare(source, output, *, overwrite=False, qa_dir=None, root=ROOT):
    paths = [output / f'{key}{suffix}' for key in SPECS for suffix in ['.png', '.kmz', '.registration.json', '.source.json']]
    if not overwrite and any(p.exists() for p in paths):
        raise FileExistsError('Output exists; use --overwrite explicitly')
    results = []
    for layer_id, (filename, labels, swatches) in SPECS.items():
        raw = source / filename
        image = Image.open(raw).convert('RGB')
        low = filename == 'land_capability.png'
        if image.size != ((768, 816) if low else (1773, 1883)):
            raise ValueError(f'Unexpected source dimensions: {raw}')
        controls, checks = detect_grid(image)
        matrix = fit_affine(controls)
        crop = [30, 39, 752, 650] if low else [70, 90, 1734, 1500]
        png, bounds, projected = warp(image, matrix, crop)
        buffer = BytesIO()
        png.save(buffer, format='PNG', optimize=False)
        legend = [{'label': label, 'color': '#%02x%02x%02x' % image.getpixel(pixel), 'source_pixel': list(pixel)}
                  for label, pixel in zip(labels, swatches)]
        report = {'schema_version': 1, 'layer_id': layer_id, 'status': 'registered_historical_display',
                  'source_pixel_dimensions': list(image.size), 'source_sha256': hashlib.sha256(raw.read_bytes()).hexdigest(),
                  'pixel_convention': 'zero-based pixel centres; crop edges at half pixels',
                  'crop_pixel_box_exclusive': crop, 'control_detection': 'local median darkness profiles, seven-pixel windows, antialiased centroids',
                  'control_selection': 'checkerboard distributed six crossings fit; other six withheld',
                  'sampling_notes': 'Each crossing measured locally. Land-capability longitude 120.46 at north/south rows uses clear same-line y72:90 and y550:570 segments because roads/water obscure the local profile.' if low else 'Each crossing measured locally without inferred regular spacing.',
                  'affine_pixel_to_lon_lat': matrix.tolist(), 'fit': residuals(matrix, controls), 'withheld': residuals(matrix, checks),
                  'datum_assumption': 'Printed graticule has no datum. EPSG:4326 / WGS84 assumed for display, not verified.',
                  'printed_graticule': {'longitude': LONS, 'latitude': LATS},
                  'target_crs': 'EPSG:3857', 'resampling': 'bilinear premultiplied RGBA inverse mapping; not a geographic bounding-box stretch',
                  'registration_scope': 'Faithful to printed graticule only; independent feature disagreement retained, not repaired. No claim of ground-validated registration.',
                  'projected_bounds_metres': projected, 'bounds': bounds, 'output_pixel_dimensions': list(png.size),
                  'external_checks': external_checks(matrix, low, root),
                  'accuracy_statement': 'Grid residuals measure internal poster registration only, not source accuracy. OSM checks are independent visual diagnostics, not surveyed validation. No invented accuracy threshold.',
                  'alpha_method': 'Near-white exterior connectivity with 5px bridges; no municipal polygon clipping. Black exterior road/context labels and printed grid remain. No white thematic legend class.',
                  'legend': legend}
        record = {'id': layer_id, 'source_label': 'Municipality of Mapandan, Office of the MPDC (historical physical map)',
                  'prepared_date': '2021-12-15', 'date_kind': 'poster preparation date, not underlying data date',
                  'data_vintage': 'unknown', 'publisher': 'Municipal Planning and Development Coordinator, Mapandan',
                  'source_credits': 'Mapandan Cadastral Survey & Index Map; Google Earth; ' + ('Bureau of Soils and Water Management (BSWM)' if layer_id == 'physical-soil' else 'NASA (Shuttle Radar Topography Mission)'),
                  'raw_source': str(raw.relative_to(root)) if raw.is_relative_to(root) else str(raw),
                  'raw_sha256': report['source_sha256'], 'source_pixel_dimensions': list(image.size),
                  'prepared_resource': f'datasets/GIS/physical/prepared/{layer_id}.kmz',
                  'registration_report': f'{layer_id}.registration.json', 'bounds': bounds, 'legend': legend,
                  'usage': 'Historical cartographic context only; not current conditions, cadastral authority, engineering or parcel decisions',
                  'rights': 'Municipal source; republication license not stated in poster',
                  'legend_notes': 'Poster incorrectly heads legend Slope; mapped classes A and B only. Class X mentioned in accompanying text is not mapped.' if low else 'Labels and RGB swatches sampled from the original legend; no analytical classification inferred.'}
        results.append((layer_id, buffer.getvalue(), report, record, image, matrix))
    output.mkdir(parents=True, exist_ok=True)
    for layer_id, png, report, record, image, matrix in results:
        (output / f'{layer_id}.png').write_bytes(png)
        (output / f'{layer_id}.kmz').write_bytes(kmz_bytes(layer_id, png, report['bounds']))
        for suffix, value in [('registration', report), ('source', record)]:
            (output / f'{layer_id}.{suffix}.json').write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
        if qa_dir:
            qa_dir.mkdir(parents=True, exist_ok=True)
            draw = ImageDraw.Draw(image)
            for key, color in [('fit', '#00ffff'), ('withheld', '#ff0000')]:
                for x, y, *_ in report[key]['points']:
                    draw.ellipse((x-8, y-8, x+8, y+8), outline=color, width=2)
            inv = np.linalg.inv(np.vstack((matrix.T, [0, 0, 1])))
            osm = json.loads((root / 'datasets/GIS/highways.geojson').read_text())['features']
            for feature in osm:
                if feature['properties'].get('highway') == 'secondary' or feature['properties'].get('waterway') == 'river':
                    pixels = np.column_stack((feature['geometry']['coordinates'], np.ones(len(feature['geometry']['coordinates'])))) @ inv.T
                    draw.line([tuple(p[:2]) for p in pixels], fill='#ff00ff', width=2)
            image.thumbnail((900, 960))
            image.save(qa_dir / f'{layer_id}-source-check.png')
            warped = Image.open(BytesIO(png))
            draw = ImageDraw.Draw(warped)
            west, south, east, north = report['projected_bounds_metres']
            for key, color in [('fit', '#00ffff'), ('withheld', '#ff0000')]:
                for _, _, lon, lat in report[key]['points']:
                    mx, my = FORWARD.transform(lon, lat)
                    x = (mx-west)/(east-west)*warped.width-.5
                    y = (north-my)/(north-south)*warped.height-.5
                    draw.ellipse((x-8, y-8, x+8, y+8), outline=color, width=2)
            warped.thumbnail((900, 960))
            warped.save(qa_dir / f'{layer_id}-warped.png')
    return [report for _, _, report, *_ in results]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--qa-dir', type=Path)
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    reports = prepare(args.source, args.output, overwrite=args.overwrite, qa_dir=args.qa_dir)
    for report in reports:
        print(report['layer_id'], 'withheld grid RMSE (m):', round(report['withheld']['rmse_metres'], 3),
              'OSM diagnostic (m):', report['external_checks']['residual_metres'])


if __name__ == '__main__':
    main()
