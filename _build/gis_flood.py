"""Explicit documentary registration recipe; never called by the public build.

PYTHONPATH=/tmp/kilo/flood-deps python3 -m _build.gis_flood --output /tmp/kilo/flood-registration
Dependencies: Pillow, numpy, pyproj (see gis_flood_requirements.txt).
"""

import argparse
import csv
import hashlib
import json
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import numpy as np
from PIL import Image, ImageDraw
from pyproj import Transformer, __version__ as pyproj_version

from .gis_physical import ROOT, fit_affine, residuals, warp

SOURCE = ROOT / 'datasets/GIS/Better_Mapandan_GIS_V3_2_Flood_Layer_Package/Better_Mapandan_GIS_V3_2_Flood_Layer/sources/flood/Mapandan-Hazard-Map-scaled.jpeg'
SHA256 = 'c0f70629843a37312541f14910af92c91649bd605cc65c31b6a72aea263cf8b5'
CONTROLS = ROOT / 'docs/flood-registration-controls.csv'


def package(png, bounds):
    ns = 'http://www.opengis.net/kml/2.2'
    ET.register_namespace('', ns)
    root = ET.Element(f'{{{ns}}}kml')
    overlay = ET.SubElement(root, 'GroundOverlay')
    ET.SubElement(overlay, 'name').text = 'Historical flood documentary map; license not stated'
    ET.SubElement(ET.SubElement(overlay, 'Icon'), 'href').text = 'overlay.png'
    box = ET.SubElement(overlay, 'LatLonBox')
    for key in ['north', 'south', 'east', 'west']:
        ET.SubElement(box, key).text = f'{bounds[key]:.12f}'
    ET.SubElement(box, 'rotation').text = '0'
    buffer = BytesIO()
    with ZipFile(buffer, 'w', compression=ZIP_DEFLATED) as archive:
        for name, data in [('doc.kml', ET.tostring(root, encoding='utf-8', xml_declaration=True)), ('overlay.png', png)]:
            info = ZipInfo(name, date_time=(2020, 9, 2, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, data)
    return buffer.getvalue()


def prepare(output, source=SOURCE, controls=CONTROLS, *, publication=False):
    if output.resolve().is_relative_to(ROOT.resolve()) and not publication:
        raise ValueError('Workspace output requires explicit publication preparation')
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SHA256:
        raise ValueError('Source hash changed; remeasure controls before preparation')
    image = Image.open(BytesIO(raw)).convert('RGB')
    if image.size != (2048, 1448):
        raise ValueError('Unexpected original dimensions')
    rows = list(csv.DictReader(controls.open(newline='')))
    def points(role):
        return [[float(r[k]) for k in ['pixel_x', 'pixel_y', 'longitude', 'latitude']] for r in rows if r['role'] == role]
    fit, checks, independent = points('fit'), points('grid_check'), points('independent_candidate')
    matrix = fit_affine(fit)
    features = json.loads((ROOT / 'datasets/GIS/highways.geojson').read_text())['features']
    for point in independent:
        if not any(point[2:] in f['geometry']['coordinates'] for f in features):
            raise ValueError('Independent OSM checkpoint coordinate changed')
    metric = Transformer.from_crs('EPSG:4326', 'EPSG:32651', always_xy=True)
    diagnostics = []
    for row in rows:
        if row['role'] not in ['nearest_road', 'nearest_river']:
            continue
        lon, lat = np.array([float(row['pixel_x']), float(row['pixel_y']), 1]) @ matrix
        point = np.array(metric.transform(lon, lat))
        distances = []
        for f in features:
            p = f['properties']
            if not (p.get('highway') and p.get('highway') not in ['footway', 'path', 'steps', 'cycleway'] if row['role'] == 'nearest_road' else p.get('waterway') == 'river'):
                continue
            coords = np.asarray(f['geometry']['coordinates'])
            line = np.column_stack(metric.transform(coords[:, 0], coords[:, 1]))
            start, delta = line[:-1], np.diff(line, axis=0)
            denom = np.sum(delta ** 2, axis=1)
            t = np.clip(np.sum((point-start)*delta, axis=1) / np.maximum(denom, 1e-20), 0, 1)
            distances.append((float(np.linalg.norm(point-(start+t[:, None]*delta), axis=1).min()), p.get('name'), f.get('id')))
        nearest = min(distances, key=lambda item: item[0])
        diagnostics.append({'id': row['id'], 'role': row['role'], 'pixel': [float(row['pixel_x']), float(row['pixel_y'])],
                            'nearest_line_metres': nearest[0], 'osm_name': nearest[1], 'osm_feature_id': nearest[2], 'evidence': row['evidence']})
    # Compare a simpler axis-aligned model, not a high-order rubber sheet.
    a = np.asarray(fit)
    axis = np.zeros((3, 2))
    axis[[0, 2], 0] = np.linalg.lstsq(np.column_stack((a[:, 0], np.ones(len(a)))), a[:, 2], rcond=None)[0]
    axis[[1, 2], 1] = np.linalg.lstsq(np.column_stack((a[:, 1], np.ones(len(a)))), a[:, 3], rcond=None)[0]
    # Entire interior frame, minus opaque legend furniture. Preserve all source
    # thematic shading and linework; no color classification or boundary repair.
    documentary = image.convert('RGBA')
    ImageDraw.Draw(documentary).rectangle((60, 1105, 873, 1370), fill=(0, 0, 0, 0))
    crop = [15, 15, 2033, 1433]
    # Shared warp already expands centre coordinates to half-pixel outer edges.
    # Pass the fitted centre matrix directly; no additional half-pixel shift.
    png, bounds, projected = warp(documentary, matrix, crop, transparent_background=False)
    buffer = BytesIO()
    png.save(buffer, format='PNG')
    legend = [{'label': label, 'color': '#%02x%02x%02x' % image.getpixel(pixel), 'source_pixel': pixel}
              for label, pixel in [('High', (380, 1216)), ('Medium', (380, 1240))]]
    report = {
        'status': 'registered_historical_display' if publication else 'local_candidate_only',
        'publication': 'public historical display; license not stated' if publication else 'local preparation only',
        'geographic_certainty': 'Assumed WGS84; printed-grid registration only, not independently verified ground accuracy',
        'rights': 'Image-specific republication license not stated; municipal website hosting does not establish rights ownership',
        'source_sha256': SHA256, 'source_dimensions': list(image.size),
        'source_crs': 'Unstated printed geographic graticule; global WGS84/EPSG:4326 is an assumption, NOT verified',
        'pixel_convention': 'zero-based pixel centres; manually observed cross centres, 2-4 pixel reading uncertainty',
        'model': 'six-parameter affine pixel to longitude/latitude, then inverse-mapped Web Mercator north-up',
        'affine_pixel_to_lon_lat': matrix.tolist(), 'axis_aligned_comparison': {'fit': residuals(axis, fit), 'grid_check': residuals(axis, checks)},
        'fit': residuals(matrix, fit), 'grid_check': residuals(matrix, checks),
        'independent_candidates': residuals(matrix, independent),
        'distributed_nearest_line_diagnostics': diagnostics,
        'diagnostic_scope': 'Manually selected visible source road/channel points; shortest distance to independent OSM lines, not homologous surveyed checkpoints. Along-line error is unmeasured; river is braided and imagery/OSM dates differ.',
        'checkpoint_scope': 'Two manually identified central blue provincial-road junctions against independent OSM. Not surveyed; no distributed ground validation; not fit inputs.',
        'independent_source': 'datasets/GIS/highways.geojson; OSM export 2026-10-18',
        'independent_source_sha256': hashlib.sha256((ROOT / 'datasets/GIS/highways.geojson').read_bytes()).hexdigest(),
        'crop_pixel_box_exclusive': crop, 'legend_mask_inclusive': [60, 1105, 873, 1370],
        'target_crs': 'EPSG:3857', 'resampling': 'bilinear premultiplied RGBA',
        'bounds': bounds, 'projected_bounds_metres': projected, 'output_dimensions': list(png.size), 'legend': legend,
        'intended_display': 'Historical municipal overview only; no certified scale or positional tolerance. Zoom 13 (~1:70000 at 96 dpi at latitude 16) is a display example, not an accuracy certification. Not parcel/building decisions. Grid error is not ground accuracy.',
        'furniture': 'Opaque legend removed with transparent rectangle; north arrow, place labels, graticule and attribution context remain documentary artwork.',
        'software': {'numpy': np.__version__, 'Pillow': Image.__version__, 'pyproj': pyproj_version},
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / 'flood.png').write_bytes(buffer.getvalue())
    (output / 'flood.kmz').write_bytes(package(buffer.getvalue(), bounds))
    (output / 'registration.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    # Geographically overplot independent OSM linework on the untouched source.
    qa = image.copy()
    draw = ImageDraw.Draw(qa)
    inv = np.linalg.inv(np.vstack((matrix.T, [0, 0, 1])))
    for feature in features:
        if (feature['properties'].get('highway') in ['primary', 'secondary', 'tertiary']
                or feature['properties'].get('name') == 'Fire Tree Avenue' or feature['properties'].get('waterway') == 'river'):
            coords = feature['geometry']['coordinates']
            pixels = np.column_stack((coords, np.ones(len(coords)))) @ inv.T
            draw.line([tuple(p[:2]) for p in pixels], fill='#ff00ff', width=2)
    for row in rows:
        x, y = float(row['pixel_x']), float(row['pixel_y'])
        draw.ellipse((x-7, y-7, x+7, y+7), outline='#00ffff', width=2)
        draw.text((x+9, y+3), row['id'], fill='#00ffff')
    qa.save(output / 'source-osm-check.png')
    print(json.dumps({k: report[k] for k in ['bounds', 'fit', 'grid_check', 'independent_candidates', 'legend']}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--publication', action='store_true', help='Explicitly prepare historical public-display metadata; does not certify accuracy or license')
    args = parser.parse_args()
    prepare(args.output, publication=args.publication)
