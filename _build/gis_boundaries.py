"""Explicit, code-joined extraction of source geometry; never repair or infer shapes."""
import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path

from .gis import load_json
from .gis_preview import feature_collection

MUNICIPALITY = 'PH0105528'
LIMITATIONS = [
    'Very coarse simplified source geometry, not a reliable administrative boundary.',
    'Severe gaps, overlaps and geometry outside the same simplified municipality; do not use for parcel, routing, hazard or area analysis.',
    'Source AREA_SQKM describes pre-simplification metadata, not the area of these shapes.',
    'Original detailed shapefiles are absent; no detail, coordinate or boundary has been invented or repaired.',
]


def extract_boundaries(source, canonical, *, allow_subset=False):
    """Join only exact ten-digit PSGC aliases and preserve coordinates verbatim."""
    references = canonical.get('features') if isinstance(canonical, dict) else None
    if not isinstance(references, list):
        raise ValueError('Expected canonical FeatureCollection with barangay properties')
    lookup = {}
    for feature in references:
        props = feature.get('properties') if isinstance(feature, dict) else None
        gid = props.get('gid') if isinstance(props, dict) else None
        if not isinstance(gid, str) or len(gid) != 10 or not gid.isdigit() or gid in lookup:
            raise ValueError('Expected unique canonical ten-digit barangay codes')
        lookup[gid] = props
    if len(lookup) != 15:
        raise ValueError('Expected exactly 15 unique canonical ten-digit barangay codes')
    if not isinstance(source, dict) or source.get('type') != 'FeatureCollection' or not isinstance(source.get('features'), list):
        raise ValueError('Expected source FeatureCollection')
    if 'crs' in source:
        feature_collection({'type': 'FeatureCollection', 'features': [], 'crs': source['crs']})
    result, seen = [], set()
    for feature in source['features']:
        if not isinstance(feature, dict):
            raise ValueError('Expected source Feature objects')
        props = feature.get('properties') or {}
        if not isinstance(props, dict):
            raise ValueError('Expected source properties object')
        if props.get('ADM3_PCODE') != MUNICIPALITY:
            continue
        code = props.get('ADM4_PCODE')
        gid = code[2:] if isinstance(code, str) and code.startswith('PH') else None
        if gid not in lookup or props.get('psgc_code', gid) != gid or gid in seen:
            raise ValueError(f'Unexpected, conflicting or duplicate barangay code: {code!r}')
        canonical_props = lookup[gid]
        normalized = {key: canonical_props[key] for key in ('name', 'pop2024', 'pop2020') if key in canonical_props}
        normalized.update(id=gid, gid=gid, psgc=gid, source_name=props.get('ADM4_EN'),
                          source_date=props.get('date'), location_precision='very_coarse',
                          source_area_sqkm=props.get('AREA_SQKM'), limitations=LIMITATIONS.copy(),
                          provenance={'source': 'barangay-boundaries-repository, hierarchical_t0p005',
                                      'source_record_id': code})
        output = {'type': 'Feature', 'geometry': deepcopy(feature.get('geometry')), 'properties': normalized}
        if not isinstance(output['geometry'], dict) or output['geometry'].get('type') not in ('Polygon', 'MultiPolygon'):
            raise ValueError(f'Expected supplied polygon for {gid}')
        checked = feature_collection({'type': 'FeatureCollection', 'features': [output]})
        if len(checked['features']) != 1:
            raise ValueError(f'Unsafe geometry for {gid}')
        result.append(output)
        seen.add(gid)
    if not seen or (not allow_subset and seen != set(lookup)):
        raise ValueError('Expected all 15 exact canonical codes; subset requires explicit allow_subset')
    return {'type': 'FeatureCollection', 'features': sorted(result, key=lambda f: f['properties']['gid'])}


def quality_report(collection, municipality):
    """Optional development analysis, not a runtime dependency or certification."""
    report = {'limitations': LIMITATIONS.copy(), 'feature_count': len(collection['features']),
              'topology_checked': False, 'disposition': 'optional_off_by_default_reference_geometry'}
    if municipality is None:
        report['analysis_unavailable_reason'] = 'No municipality comparison input supplied'
        return report
    try:
        import pyproj
        import shapely
        from shapely.geometry import shape
        from shapely.ops import transform, unary_union
    except ImportError:
        report['analysis_unavailable_reason'] = 'Shapely and pyproj not installed; no topological certification'
        return report
    matches = [f for f in municipality.get('features', []) if (f.get('properties') or {}).get('ADM3_PCODE') == MUNICIPALITY]
    if len(matches) != 1:
        raise ValueError('Expected exactly one same-source municipality code')
    project = pyproj.Transformer.from_crs(4326, 32651, always_xy=True).transform
    geometries = [transform(project, shape(f['geometry'])) for f in collection['features']]
    city = transform(project, shape(matches[0]['geometry']))
    valid = all(g.is_valid and not g.is_empty for g in geometries) and city.is_valid and not city.is_empty
    report.update(analysis_libraries={'shapely': shapely.__version__, 'pyproj': pyproj.__version__},
                  measurement_crs='EPSG:32651 (WGS84 / UTM zone 51N)',
                  all_individually_valid=valid,
                  comparison_limitations='Municipality input is also simplified; comparison is not against an authoritative detailed boundary.')
    if not valid:
        report['analysis_unavailable_reason'] = 'Invalid source geometry; no repairs attempted'
        return report
    union = unary_union(geometries)
    summed = sum(g.area for g in geometries)
    report.update(topology_checked=True, sum_geometry_area_km2=summed / 1e6,
                  union_area_km2=union.area / 1e6, municipality_geometry_area_km2=city.area / 1e6,
                  overlap_area_km2=(summed - union.area) / 1e6,
                  municipality_uncovered_km2=city.difference(union).area / 1e6,
                  outside_municipality_km2=union.difference(city).area / 1e6,
                  municipality_uncovered_percent=100 * city.difference(union).area / city.area,
                  source_municipality_area_sqkm_metadata=matches[0]['properties'].get('AREA_SQKM'),
                  source_barangay_area_sqkm_metadata_sum=sum(f['properties'].get('source_area_sqkm') or 0 for f in collection['features']),
                  features=[{'gid': f['properties']['gid'], 'geometry_area_km2': g.area / 1e6,
                             'source_area_sqkm_metadata': f['properties'].get('source_area_sqkm'),
                             'ring_vertex_counts': [len(r) - 1 for p in ([f['geometry']['coordinates']] if f['geometry']['type'] == 'Polygon' else f['geometry']['coordinates']) for r in p]}
                            for f, g in zip(collection['features'], geometries)])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--canonical', type=Path, required=True)
    parser.add_argument('--municipality', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sources-output', type=Path, required=True)
    parser.add_argument('--allow-subset', action='store_true')
    args = parser.parse_args()
    inputs = [p.resolve() for p in (args.input, args.canonical, args.municipality) if p is not None]
    outputs = [args.output.resolve(), args.sources_output.resolve()]
    if len(set(outputs)) != 2 or any(p in inputs or p.exists() for p in outputs):
        parser.error('Outputs must be distinct new files and must not overwrite inputs or existing outputs')
    collection = extract_boundaries(load_json(args.input), load_json(args.canonical), allow_subset=args.allow_subset)
    sidecar = {'description': 'Descriptive provenance and measured quality, not an approval ledger.',
               'source_url': 'https://github.com/bendlikeabamboo/barangay-boundaries-repository',
               'attribution': 'Repository describes NAMRIA administrative shapefiles enriched with PSA PSGC; local simplified derivative only, not independently verified.',
               'source_path': args.input.as_posix(), 'source_sha256': hashlib.sha256(args.input.read_bytes()).hexdigest(),
               'source_variant': '2023-10-24/hierarchical_t0p005',
               'source_date': '2022-11-09', 'source_valid_on': '2023-11-06',
               'join': 'Exact ADM3_PCODE PH0105528 and ADM4_PCODE PH + canonical ten-digit gid; no name matching',
               'original_shapefiles_available': False,
               'quality_report': quality_report(collection, load_json(args.municipality) if args.municipality else None)}
    if args.municipality:
        sidecar['municipality_comparison'] = {'path': args.municipality.as_posix(),
                                             'sha256': hashlib.sha256(args.municipality.read_bytes()).hexdigest()}
    for path, data in ((args.output, collection), (args.sources_output, sidecar)):
        with path.open('x', encoding='utf-8') as target:
            json.dump(data, target, ensure_ascii=True, allow_nan=False, indent=2)
            target.write('\n')


if __name__ == '__main__':
    main()
