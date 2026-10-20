"""Read-only raw boundary preparation (not used by the production build).

Development dependencies only: pip install pyshp pyproj shapely.
Run python -m _build.gis_boundaries --help for explicit input/output paths.
No simplification, snapping, buffering, repair, or inferred geometry is performed.
"""
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


def extract_legacy_boundaries(source, canonical, *, allow_subset=False):
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


def legacy_main():
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
    collection = extract_legacy_boundaries(load_json(args.input), load_json(args.canonical), allow_subset=args.allow_subset)
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


RAW_LIMITATIONS = [
    'Indicative source-derived administrative boundaries, not a legal survey or cadastral boundary.',
    'Source date, acquisition history, licensing and legal currency have not been independently verified.',
    'Geometry validation and agreement between derivatives do not establish positional accuracy or legal authority.',
    'No coordinates have been simplified, snapped, buffered or repaired; source overlaps and gaps are retained.',
    'Source municipality area near 20.44 km2 and printed CLUP area 32.91752 km2 remain unresolved; shapes are not rescaled.',
]
MUNICIPALITY_ALIASES = {'PH0105528', '0105528000', '015528000'}
NAME_ALIASES = {
    '0105528010': {'Luyan', 'Luyan (Luyan South)'},
    '0105528016': {'Santa Maria', 'Santa Maria (Luyan North)'},
}


def canonical_lookup(canonical):
    """Canonical codes, not row order or names, define the expected output set."""
    if canonical.get('type') != 'FeatureCollection' or not isinstance(canonical.get('features'), list):
        raise ValueError('Expected canonical FeatureCollection')
    lookup = {}
    for feature in canonical['features']:
        props = feature.get('properties') or {}
        gid = props.get('gid')
        if not isinstance(gid, str) or len(gid) != 10 or not gid.isascii() or not gid.isdigit() or gid in lookup:
            raise ValueError('Expected unique canonical ten-digit barangay codes')
        if not isinstance(props.get('name'), str):
            raise ValueError('Expected canonical name')
        lookup[gid] = props
    if not lookup:
        raise ValueError('Empty canonical set')
    return lookup


def canonical_code(value):
    """Restore only known PSGC widths; never derive identities from names.

    These DBFs encode the ten-digit alias as a nine-digit integer (leading
    zero lost), not the older nine-digit PSGC system. Genuine nine-digit
    legacy codes are accepted only through explicit canonical aliases below.
    """
    if isinstance(value, bool) or value is None:
        raise ValueError(f'Invalid PSGC value: {value!r}')
    if isinstance(value, int):
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
        if text.startswith('PH'):
            text = text[2:]
    else:
        raise ValueError(f'Non-integral PSGC value: {value!r}')
    if not text.isascii() or not text.isdigit() or len(text) not in (9, 10):
        raise ValueError(f'Unexpected PSGC width: {value!r}')
    return text.zfill(10)


def extract_shapefile(path, canonical):
    """Parse actual SHP/DBF records and validated PRJ; retain all source vertices."""
    import pyproj
    import shapefile
    from shapely.geometry import mapping, shape
    from shapely.ops import transform
    from shapely.validation import explain_validity

    path = Path(path)
    for suffix in ('.shp', '.dbf', '.prj'):
        if not path.with_suffix(suffix).is_file():
            raise ValueError(f'Missing shapefile component: {path.with_suffix(suffix)}')
    try:
        crs = pyproj.CRS.from_wkt(path.with_suffix('.prj').read_text())
    except pyproj.exceptions.CRSError as exc:
        raise ValueError('Unknown or invalid source CRS') from exc
    epsg = crs.to_epsg()
    if epsg not in (4326, 32651):
        raise ValueError(f'Unsupported source CRS: {crs}')
    project = pyproj.Transformer.from_crs(crs, 4326, always_xy=True).transform
    lookup = canonical_lookup(canonical)
    result, seen = [], set()
    with shapefile.Reader(str(path)) as reader:
        fields = {field[0] for field in reader.fields[1:]}
        geographic_schema = {'adm3_pcode', 'adm4_pcode', 'psgc_code', 'adm4_en'} <= fields
        projected_schema = {'adm3_psgc', 'adm4_psgc', 'adm4_en'} <= fields
        if not geographic_schema and not projected_schema:
            raise ValueError('Unsupported DBF identity schema')
        total = len(reader)
        for record in reader.iterRecords():
            props = record.as_dict()
            municipality = props['adm3_pcode'] if geographic_schema else props['adm3_psgc']
            if geographic_schema:
                selected = municipality in MUNICIPALITY_ALIASES
            else:
                selected = municipality in (105528000, '105528000', '0105528000')
            if not selected:
                continue
            source_id = props['adm4_pcode'] if geographic_schema else props['adm4_psgc']
            gid = canonical_code(source_id)
            if gid not in lookup or gid in seen:
                raise ValueError(f'Unexpected or duplicate barangay code: {source_id!r}')
            if geographic_schema and canonical_code(props['psgc_code']) != gid:
                raise ValueError(f'Conflicting source identity aliases: {gid}')
            reference = lookup[gid]
            source_name = props['adm4_en']
            if source_name not in NAME_ALIASES.get(gid, set()) | {reference['name']}:
                raise ValueError(f'Unexpected source name for {gid}: {source_name!r}')
            supplied = reader.shape(record.oid)
            if supplied.shapeType not in (shapefile.POLYGON, shapefile.POLYGONZ, shapefile.POLYGONM):
                raise ValueError(f'Expected non-null polygon shape for {gid}')
            # Validate rings before pyshp can interpret exterior/hole groupings.
            starts = list(supplied.parts) + [len(supplied.points)]
            for start, end in zip(starts, starts[1:]):
                ring = supplied.points[start:end]
                if len(ring) < 4 or ring[0][:2] != ring[-1][:2]:
                    raise ValueError(f'Invalid or unclosed source ring for {gid}')
            geometry = supplied.__geo_interface__
            original = shape(geometry)
            if original.is_empty or not original.is_valid:
                raise ValueError(f'Invalid source geometry for {gid}: {explain_validity(original)}; no repairs attempted')
            if epsg != 4326:
                geometry = mapping(transform(project, original))
            geometry = json.loads(json.dumps(geometry, allow_nan=False))
            output = {'type': 'Feature', 'id': gid, 'geometry': geometry, 'properties': {
                **{key: reference[key] for key in ('name', 'pop2024', 'pop2020') if key in reference},
                'id': gid, 'gid': gid, 'psgc': gid, 'source_name': source_name,
                'source_date': None, 'source_geometry_id': source_id,
                'source_record_id': source_id, 'location_precision': 'indicative',
                'limitations': RAW_LIMITATIONS.copy(),
                'provenance': {'source': path.as_posix(), 'source_record_id': source_id,
                               'source_record_index_zero_based': record.oid, 'source_crs': f'EPSG:{epsg}'},
            }}
            checked = feature_collection({'type': 'FeatureCollection', 'features': [output]})
            if len(checked['features']) != 1:
                raise ValueError(f'Unsafe extracted coordinates for {gid}')
            result.append(output)
            seen.add(gid)
    if seen != set(lookup):
        raise ValueError(f'Expected complete canonical set; missing: {sorted(set(lookup) - seen)}')
    collection = {'type': 'FeatureCollection', 'features': sorted(result, key=lambda f: f['properties']['gid'])}
    metadata = {'path': path.as_posix(), 'record_count': total, 'source_crs': f'EPSG:{epsg}',
                'output_crs': 'EPSG:4326', 'source_date': None,
                'source_date_status': 'unknown; neither DBF has a date field',
                'reprojected': epsg != 4326,
                'field_mapping': {'municipality': 'adm3_pcode' if geographic_schema else 'adm3_psgc',
                                  'source_geometry_id': 'adm4_pcode' if geographic_schema else 'adm4_psgc',
                                  'source_record_id': 'adm4_pcode' if geographic_schema else 'adm4_psgc',
                                  'source_name': 'adm4_en', 'canonical_values': 'exact gid join to canonical directory'},
                'components_sha256': {path.with_suffix(s).name: hashlib.sha256(path.with_suffix(s).read_bytes()).hexdigest()
                                      for s in ('.shp', '.dbf', '.prj', '.shx', '.cpg') if path.with_suffix(s).exists()}}
    return collection, metadata


def geometry_metrics(collection):
    import pyproj
    from shapely.geometry import Polygon, shape
    from shapely.ops import transform, unary_union
    from shapely.validation import explain_validity

    project = pyproj.Transformer.from_crs(4326, 32651, always_xy=True).transform
    features, geometries = [], []
    for feature in collection['features']:
        supplied = feature['geometry']
        geometry = shape(supplied)
        if geometry.geom_type not in ('Polygon', 'MultiPolygon') or geometry.is_empty or not geometry.is_valid:
            raise ValueError(f'Invalid comparison geometry: {explain_validity(geometry)}')
        polygons = [supplied['coordinates']] if supplied['type'] == 'Polygon' else supplied['coordinates']
        counts = [len(ring) for polygon in polygons for ring in polygon]
        projected = transform(project, geometry)
        geometries.append(projected)
        features.append({'gid': feature['properties']['gid'], 'coordinate_positions': sum(counts),
                         'ring_position_counts': counts, 'geometry_type': supplied['type'],
                         'geometry_area_km2': projected.area / 1e6, 'bbox_wgs84': list(geometry.bounds),
                         'is_valid': geometry.is_valid})
    union = unary_union(geometries)
    pairs = [{'gids': [features[i]['gid'], features[j]['gid']], 'overlap_m2': a.intersection(b).area}
             for i, a in enumerate(geometries) for j, b in enumerate(geometries) if j > i and a.intersects(b)]
    tolerance = 1.0
    return {'feature_count': len(features), 'coordinate_positions': sum(f['coordinate_positions'] for f in features),
            'measurement_crs': 'EPSG:32651 (WGS84 / UTM zone 51N)', 'topology_checked': True,
            'all_individually_valid': True, 'bbox_wgs84': list(unary_union([shape(f['geometry']) for f in collection['features']]).bounds),
            'sum_geometry_area_km2': sum(g.area for g in geometries) / 1e6,
            'union_area_km2': union.area / 1e6,
            'overlap_area_km2': max(0, sum(g.area for g in geometries) - union.area) / 1e6,
            'cross_barangay_overlap_tolerance_m2': tolerance,
            'cross_barangay_pairs_exceeding_tolerance': [p for p in pairs if p['overlap_m2'] > tolerance],
            'maximum_pair_overlap_m2': max((p['overlap_m2'] for p in pairs), default=0),
            'interior_gap_area_m2': sum(Polygon(ring).area
                                        for polygon in (list(union.geoms) if union.geom_type == 'MultiPolygon' else [union])
                                        for ring in polygon.interiors),
            'gap_limitations': 'Interior holes only; external missing territory cannot be measured without independent boundary truth.',
            'disposition': 'optional_off_by_default_indicative_boundary',
            'limitations': RAW_LIMITATIONS.copy(), 'features': features}


def compare_geometries(reference, other):
    """Compare source shapes in metres, never against the coarse municipal derivative."""
    import pyproj
    from shapely.geometry import shape
    from shapely.ops import transform

    project = pyproj.Transformer.from_crs(4326, 32651, always_xy=True).transform
    lookup = {f['properties']['gid']: f for f in other['features']}
    expected = {f['properties']['gid'] for f in reference['features']}
    if set(lookup) != expected or len(lookup) != len(other['features']):
        raise ValueError('Comparison requires exact distinct canonical gid set')
    rows = []
    for feature in reference['features']:
        gid = feature['properties']['gid']
        a, b = (transform(project, shape(f['geometry'])) for f in (feature, lookup[gid]))
        if not a.is_valid or not b.is_valid or a.is_empty or b.is_empty:
            raise ValueError('Invalid comparison source geometry; no repairs attempted')
        rows.append({'gid': gid, 'coordinates_equal': feature['geometry'] == lookup[gid]['geometry'],
                     'hausdorff_m': a.hausdorff_distance(b), 'symmetric_difference_m2': a.symmetric_difference(b).area,
                     'area_difference_m2': b.area - a.area})
    distance_tolerance, area_tolerance = 0.01, 1.0
    return {'measurement_crs': 'EPSG:32651', 'features': rows,
            'coordinates_equal': all(r['coordinates_equal'] for r in rows),
            'equivalence_tolerance': {'hausdorff_m': distance_tolerance, 'symmetric_difference_m2': area_tolerance},
            'equivalent_within_tolerance': all(r['hausdorff_m'] <= distance_tolerance and r['symmetric_difference_m2'] <= area_tolerance for r in rows),
            'maximum_hausdorff_m': max(r['hausdorff_m'] for r in rows),
            'total_symmetric_difference_m2': sum(r['symmetric_difference_m2'] for r in rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--input', type=Path, required=True, help='Raw geographic SHP with DBF and PRJ siblings')
    parser.add_argument('--comparison-input', type=Path, required=True, help='Raw projected SHP with DBF and PRJ siblings')
    parser.add_argument('--canonical', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True, help='Bundled V3.1 candidate, compared but never copied')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sources-output', type=Path, required=True)
    parser.add_argument('--legacy-input', type=Path, help='Prior coarse local extract to archive byte-for-byte')
    parser.add_argument('--legacy-archive', type=Path, help='New archive destination with --legacy-input, or existing read-only archive reference')
    parser.add_argument('--overwrite', action='store_true', help='Explicitly replace output/sidecar only; never raw inputs or archive')
    args = parser.parse_args()
    if args.legacy_input and not args.legacy_archive:
        parser.error('--legacy-input requires --legacy-archive')
    if args.legacy_archive and not args.legacy_input and not args.legacy_archive.is_file():
        parser.error('An archive reference without --legacy-input must already exist')
    inputs = [args.input, args.comparison_input, args.canonical, args.candidate]
    protected = {p.resolve() for p in inputs}
    protected.update(p.with_suffix(s).resolve() for p in (args.input, args.comparison_input) for s in ('.dbf', '.prj', '.shx', '.cpg'))
    if args.legacy_archive and not args.legacy_input:
        protected.add(args.legacy_archive.resolve())
    outputs = [args.output, args.sources_output] + ([args.legacy_archive] if args.legacy_input else [])
    if len({p.resolve() for p in outputs}) != len(outputs) or any(p.resolve() in protected for p in outputs):
        parser.error('Outputs must be distinct and must not overwrite input components')
    if any(p.exists() and (not args.overwrite or p == args.legacy_archive) for p in outputs):
        parser.error('Outputs already exist; use --overwrite for output/sidecar only, never archive')
    canonical = load_json(args.canonical)
    collection, source = extract_shapefile(args.input, canonical)
    comparison, comparison_source = extract_shapefile(args.comparison_input, canonical)
    if source['source_crs'] != 'EPSG:4326' or comparison_source['source_crs'] != 'EPSG:32651':
        parser.error('Expected geographic primary and projected comparison source')
    candidate = load_json(args.candidate)
    candidate_lookup = canonical_lookup(candidate)
    for gid, props in canonical_lookup(canonical).items():
        if gid not in candidate_lookup or candidate_lookup[gid]['name'] not in NAME_ALIASES.get(gid, set()) | {props['name']}:
            raise ValueError(f'Candidate canonical name mismatch: {gid}')
    comparisons = {'projected_raw': compare_geometries(collection, comparison),
                   'bundled_candidate': compare_geometries(collection, candidate)}
    if not comparisons['projected_raw']['equivalent_within_tolerance']:
        raise ValueError('Raw source geometry equivalence not confirmed; selection requires investigation')
    import pyproj
    import shapefile
    import shapely
    report = geometry_metrics(collection)
    sidecar = {'description': 'Descriptive source extraction and measured quality; not legal certification or an approval ledger.',
               'source': source, 'comparison_source': comparison_source,
               'canonical_directory': {'path': args.canonical.as_posix(),
                                       'sha256': hashlib.sha256(args.canonical.read_bytes()).hexdigest()},
               'candidate': {'path': args.candidate.as_posix(), 'sha256': hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
                             'quality_report': geometry_metrics(candidate)},
               'source_date': None, 'original_shapefiles_available': True,
               'selection': 'Geographic raw source selected after projected equivalence check; all original positions retained, no candidate copy.',
               'join': 'Exact municipality aliases and canonical ten-digit gid, restoring numeric DBF leading zero; canonical names/populations unchanged.',
               'reprojection': 'Projected comparison transformed EPSG:32651 to EPSG:4326 using always_xy; chosen geographic coordinates unchanged.',
               'comparisons': comparisons, 'projected_quality_report': geometry_metrics(comparison),
               'quality_report': report, 'limitations': RAW_LIMITATIONS.copy(),
               'area_discrepancy': {'known_municipality_source_area_km2_approx': 20.44, 'printed_clup_area_km2': 32.91752,
                                    'calculated_union_area_km2': report['union_area_km2'], 'measurement_crs': report['measurement_crs'],
                                    'status': 'unresolved; neither figure used to alter shapes; calculated area is not official area'},
               'analysis_libraries': {'pyshp': shapefile.__version__, 'pyproj': pyproj.__version__, 'shapely': shapely.__version__},
               'reproduction_command': ['python', '-m', '_build.gis_boundaries', '--input', args.input.as_posix(),
                                        '--comparison-input', args.comparison_input.as_posix(), '--canonical', args.canonical.as_posix(),
                                        '--candidate', args.candidate.as_posix(), '--output', args.output.as_posix(),
                                        '--sources-output', args.sources_output.as_posix()]}
    if args.legacy_archive:
        archive_bytes = (args.legacy_input or args.legacy_archive).read_bytes()
        sidecar['legacy_archive'] = {'path': args.legacy_archive.as_posix(),
                                     'sha256': hashlib.sha256(archive_bytes).hexdigest(),
                                     'disposition': 'Archived coarse predecessor; never used as boundary truth'}
        sidecar['reproduction_command'].extend(['--legacy-archive', args.legacy_archive.as_posix()])
        if args.legacy_input:
            args.legacy_archive.parent.mkdir(parents=True, exist_ok=True)
            with args.legacy_archive.open('xb') as target:
                target.write(archive_bytes)
    for path, data in ((args.output, collection), (args.sources_output, sidecar)):
        with path.open('w' if args.overwrite else 'x', encoding='utf-8') as target:
            json.dump(data, target, ensure_ascii=True, allow_nan=False, indent=2)
            target.write('\n')


if __name__ == '__main__':
    main()
