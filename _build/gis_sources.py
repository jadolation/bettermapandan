"""Load maintainer-selected local GIS inputs and emit exact map resources."""
import io
import logging
import math
import re
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree

from _build.gis import barangay_collection, facilities_collection, parse_json, script_json
from _build.gis_preview import feature_collection, project_records, safe_url

MAX_SOURCE_BYTES = 32 * 1024 * 1024
LOG = logging.getLogger(__name__)


def bounded_bytes(path, limit=MAX_SOURCE_BYTES):
    path = Path(path)
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Symlink in GIS input")
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError("Missing or oversized GIS input")
    with path.open("rb") as source:
        raw = source.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("GIS input resource limit")
    return raw


def input_path(root, relative):
    """Repository-local inputs only; validate even disabled configuration paths."""
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise ValueError(f"Unsafe GIS source path: {relative!r}")
    path = PurePosixPath(relative)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in relative.split('/')) or path.parts[:2] not in {("src", "data"), ("datasets", "GIS")}:
        raise ValueError(f"GIS source must be repository-relative under src/data/ or datasets/GIS/: {relative!r}")
    result = Path(root) / path
    current = Path(root)
    for part in path.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"Symlink in GIS source path: {relative}")
    return result


def _validate_layer_display(layer):
    if 'group' in layer and (not isinstance(layer['group'], dict) or not all(isinstance(layer['group'].get(lang), str) for lang in ('en', 'fil', 'pag'))):
        raise ValueError('GIS group requires en, fil, and pag labels')
    if 'pane' in layer and layer['pane'] not in {'physical', 'hazards', 'administrative', 'infrastructure', 'facilities'}:
        raise ValueError('Invalid GIS pane')
    if 'opacity' in layer and (type(layer['opacity']) not in (int, float) or not 0 <= layer['opacity'] <= 1 or not math.isfinite(layer['opacity'])):
        raise ValueError('GIS opacity must be a finite number from 0 to 1')
    if 'exclusive_group' in layer and (not isinstance(layer['exclusive_group'], str) or not layer['exclusive_group'] or len(layer['exclusive_group']) > 100):
        raise ValueError('GIS exclusive_group must be a nonempty string')


def layer_configuration(root):
    data = parse_json(bounded_bytes(Path(root) / "src/data/gis/layers.json", 1024 * 1024).decode('utf-8'))
    if not isinstance(data, dict) or not isinstance(data.get('layers'), list) or not isinstance(data.get('metadata', {}), dict):
        raise ValueError("GIS layers.json requires metadata object and layers list")
    if len(data['layers']) > 100:
        raise ValueError("GIS layer resource limit (100)")
    seen = set()
    for layer in data['layers']:
        if not isinstance(layer, dict):
            raise ValueError("GIS layer must be an object")
        identifier = layer.get('id')
        if not isinstance(identifier, str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,79}', identifier) or identifier in seen:
            raise ValueError(f"Invalid or duplicate GIS layer ID: {identifier!r}")
        seen.add(identifier)
        if layer.get('type') not in {'geojson', 'records', 'kmz', 'dpwh', 'source-reference', 'choropleth'}:
            raise ValueError(f"GIS layer {identifier}: unsupported input type")
        if type(layer.get('enabled')) is not bool or type(layer.get('visible_by_default')) is not bool:
            raise ValueError(f"GIS layer {identifier}: enabled and visible_by_default must be booleans")
        if not isinstance(layer.get('title'), dict) or not isinstance(layer['title'].get('en'), str):
            raise ValueError(f"GIS layer {identifier}: title.en is required")
        input_path(root, layer.get('source'))
        if layer['type'] == 'choropleth' and (layer.get('metric') not in {'population', 'projects'}
                or layer.get('geometry_layer') != 'barangay-boundaries' or layer['visible_by_default']):
            raise ValueError('Choropleth requires a supported metric, shared boundaries and default off')
        if 'dependencies' in layer and (not isinstance(layer['dependencies'], list) or len(layer['dependencies']) > 10):
            raise ValueError('GIS dependencies must be a bounded list')
        for dependency in layer.get('dependencies', []):
            input_path(root, dependency)
        _validate_layer_display(layer)
        if 'source_url' in layer and not safe_url(layer['source_url']):
            raise ValueError(f"GIS layer {identifier}: source_url must be HTTP(S)")
        if layer['type'] == 'source-reference' and (not layer.get('source_url') or layer['visible_by_default']):
            raise ValueError('GIS source reference requires source_url and must be off by default')
    return data


def _validate_kmz_entries(archive):
    """Validate KMZ archive entries; return (names, kmls)."""
    entries = archive.infolist()
    if len(entries) > 512 or sum(x.file_size for x in entries) > 128 * 1024 * 1024:
        raise ValueError("KMZ resource limit")
    names = set()
    for entry in entries:
        name = PurePosixPath(entry.filename)
        if (name.is_absolute() or ".." in name.parts or "\\" in entry.filename or ":" in entry.filename
                or entry.filename in names or entry.flag_bits & 1
                or (entry.external_attr >> 16) & 0o170000 == 0o120000
                or entry.file_size > MAX_SOURCE_BYTES
                or entry.file_size > max(1, entry.compress_size) * 1000):
            raise ValueError("Unsafe KMZ entry")
        names.add(entry.filename)
    kmls = [x for x in names if x.lower().endswith(".kml")]
    if not kmls:
        raise ValueError("KMZ has no KML")
    return names, kmls


def _validate_kml_xml(xml):
    """Parse and validate KML XML; return ElementTree root."""
    if len(xml) > 2 * 1024 * 1024 or b'\x00' in xml or re.search(br"<!\s*(?:DOCTYPE|ENTITY)", xml, re.I):
        raise ValueError("Unsafe KML XML")
    tree = ElementTree.fromstring(xml)
    nodes = list(tree.iter())
    if len(nodes) > 20000:
        raise ValueError("KML resource limit")
    if any(x.tag.rsplit("}", 1)[-1] in {"NetworkLink", "Link", "Model", "LatLonQuad"} for x in nodes):
        raise ValueError("Unsupported external or rotated KML registration")
    return tree


def _validate_overlay_bounds(box, ns):
    """Validate LatLonBox bounds; return bounds dict."""
    if box is None or float(box.findtext("k:rotation", "0", ns)) != 0:
        raise ValueError("Unsupported overlay registration/rotation")
    bounds = {key: float(box.findtext("k:" + key, "nan", ns)) for key in ("west", "south", "east", "north")}
    if (not all(math.isfinite(x) for x in bounds.values())
            or not -180 <= bounds["west"] < bounds["east"] <= 180
            or not -90 <= bounds["south"] < bounds["north"] <= 90):
        raise ValueError("Invalid overlay bounds")
    return bounds


def _extract_overlay_image(archive, name, href, names, bounds, extracted_bytes, total_pixels, images):
    """Read and validate a PNG overlay image from the KMZ archive."""
    reference = PurePosixPath(href)
    if not href or reference.is_absolute() or ".." in reference.parts or ":" in href or "\\" in href:
        raise ValueError("Unsafe overlay image reference")
    filename = (PurePosixPath(name).parent / reference).as_posix()
    if filename not in names or not filename.lower().endswith(".png"):
        raise ValueError("Unsupported overlay resource")
    image = archive.read(filename)
    extracted_bytes += len(image)
    if extracted_bytes > 128 * 1024 * 1024:
        raise ValueError("Extracted raster resource limit")
    from PIL import Image
    with Image.open(io.BytesIO(image)) as decoded:
        total_pixels += decoded.width * decoded.height
        if decoded.format != "PNG" or decoded.width * decoded.height > 16000000 or total_pixels > 64000000:
            raise ValueError("Raster resource limit")
        decoded.verify()
    images.append((image, bounds))
    if len(images) > 128:
        raise ValueError("Overlay resource limit")
    return extracted_bytes, total_pixels


def inspect_kmz(raw):
    """Only finite zero-rotation LatLonBox PNG overlays; no network or KML scripts."""
    images = []
    extracted_bytes = total_pixels = 0
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names, kmls = _validate_kmz_entries(archive)
        for name in sorted(kmls):
            xml = archive.read(name)
            tree = _validate_kml_xml(xml)
            ns = {"k": "http://www.opengis.net/kml/2.2"}
            for overlay in tree.findall(".//k:GroundOverlay", ns):
                box = overlay.find("k:LatLonBox", ns)
                bounds = _validate_overlay_bounds(box, ns)
                href = overlay.findtext("k:Icon/k:href", "", ns)
                extracted_bytes, total_pixels = _extract_overlay_image(
                    archive, name, href, names, bounds, extracted_bytes, total_pixels, images)
    if not images:
        raise ValueError("No understood image overlays")
    return images


def prepare_inputs(root, workspace=None, lang_code="en"):
    """Load enabled configured inputs; isolate technical failures by layer."""
    root = Path(root)
    workspace = Path(workspace) if workspace is not None else root
    config = layer_configuration(root)
    result = {"schema_version": 1, "metadata": config.get('metadata', {}).copy(),
              "layers": [], "facilities": {"type": "FeatureCollection", "features": []},
              "barangays": {"type": "FeatureCollection", "features": []}, "records": [],
              "residents": {"barangays": {}, "contacts": {"offices": {}}}}
    asset_dir = workspace / "assets/gis"
    if asset_dir.is_symlink() or (workspace / 'assets').is_symlink():
        raise ValueError("Symlink in generated GIS asset directory")
    asset_dir.mkdir(parents=True, exist_ok=True)
    outputs = set()

    def emit(filename, raw):
        target = asset_dir / filename
        if target.is_symlink():
            raise ValueError("Symlink in generated GIS asset")
        target.write_bytes(raw)
        outputs.add('assets/gis/' + filename)

    fields = ('id', 'title', 'enabled', 'visible_by_default', 'attribution', 'source_url',
              'source_label', 'source_date', 'precision', 'limitations', 'legend', 'semantic_role',
              'group', 'pane', 'opacity', 'exclusive_group', 'metric', 'geometry_layer')
    statistics = None
    statistics_error = None
    for configured in config['layers']:
        identifier, kind = configured['id'], configured['type']
        layer = {key: configured[key] for key in fields if key in configured}
        layer['title'] = {lang: configured['title'].get(lang, configured['title']['en']) for lang in ('en', 'fil', 'pag')}
        layer.update(type='unavailable', available=False)
        result['layers'].append(layer)
        if not configured['enabled']:
            layer['unavailable_reason'] = 'Disabled in layers.json'
            continue
        if kind == 'source-reference':
            # A citation is not permission to read, copy, or publish its local artwork.
            layer.update(type='reference', available=True)
            continue
        relative = configured['source']
        try:
            if kind == 'choropleth':
                if statistics_error:
                    raise ValueError(statistics_error)
                if statistics is None:
                    from .gis_statistics import build_statistics
                    try:
                        statistics = build_statistics(root)
                        encoded = script_json(statistics).encode('utf-8')
                        if len(encoded) > 8 * 1024 * 1024:
                            raise ValueError('Statistics runtime resource limit')
                        emit('barangay-statistics.json', encoded)
                    except Exception:
                        statistics_error = 'Barangay statistics preparation failed'
                        raise
                layer.update(type='choropleth', available=True,
                             statistics_url='assets/gis/barangay-statistics.json')
                continue
            raw = bounded_bytes(input_path(root, relative))
            if kind == 'geojson':
                parsed = parse_json(raw.decode('utf-8'))
                if identifier == 'facilities':
                    data = facilities_collection(parsed)
                    result['facilities'] = data
                    layer.update(type='inline-geojson', data_key='GIS_FACILITIES')
                elif identifier == 'barangay-labels' or configured.get('semantic_role') == 'nonspatial_barangay_reference':
                    data = barangay_collection(parsed)
                    result['barangays'] = data
                    layer.update(type='reference', data_key='GIS_BARANGAYS')
                else:
                    data = feature_collection(parsed, label=identifier)
                    if identifier == 'barangay-halls':
                        from .gis_halls import geographic_qa, hall_collection
                        data = hall_collection(parsed)
                        boundaries = parse_json(bounded_bytes(input_path(root, 'src/data/gis/barangay_boundaries.geojson')).decode('utf-8'))
                        result['metadata']['hall_geographic_qa'] = geographic_qa(data, boundaries)
                    filename = identifier + '.geojson'
                    emit(filename, script_json(data).encode('utf-8'))
                    layer.update(type='geojson', url='assets/gis/' + filename)
            elif kind == 'dpwh':
                from .gis_projects import dpwh_collection
                canonical = parse_json(bounded_bytes(input_path(root, 'src/data/entities/projects.json')).decode('utf-8'))
                data = feature_collection(dpwh_collection(parse_json(raw.decode('utf-8')), canonical, lang_code), label=identifier)
                for feature in data['features']:
                    props = dict(feature['properties'], layer_id=identifier, geometry=feature['geometry'])
                    result['records'].append(props)
                filename = identifier + '.geojson'
                emit(filename, script_json(data).encode('utf-8'))
                layer.update(type='geojson', url='assets/gis/' + filename)
            elif kind == 'records':
                records = project_records(parse_json(raw.decode('utf-8')), lang_code)
                for item in records:
                    item['layer_id'] = identifier
                result['records'].extend(records)
                layer.update(type='reference', data_key='GIS_RECORDS')
            else:
                images = []
                # Validate the entire archive before emitting any resources.
                for index, (image, bounds) in enumerate(inspect_kmz(raw)):
                    filename = f'{identifier}-{index}.png'
                    emit(filename, image)
                    images.append({'url': 'assets/gis/' + filename, 'bounds': bounds})
                layer.update(type='raster-image-overlay', images=images)
            layer['available'] = True
        except Exception as exc:  # noqa: BLE001 - optional input failures do not break other layers
            reason = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            if isinstance(exc, FileNotFoundError):
                reason = 'Input file is missing'
            layer['unavailable_reason'] = reason
            LOG.warning('GIS layer %s (%s): unavailable: %s', identifier, relative, reason)
    if any('src/data/gis/evacuation-crosswalk.json' in layer.get('dependencies', []) for layer in config['layers'] if layer['enabled']):
        _resident_projection(root, result, asset_dir, emit)
    manifest = asset_dir / 'manifest.json'
    if manifest.is_symlink():
        raise ValueError('Symlink in generated GIS asset manifest')
    manifest.write_text(script_json({'schema_version': 1, 'files': sorted(outputs)}), encoding='utf-8')
    return result


def _resident_projection(root, result, asset_dir, emit):
    from _build.gis_residents import reconcile, residents
    crosswalk = reconcile(root, result['facilities'], result['records'])
    result['residents'] = residents(root)
    linked = {osm: row['facility_id'] for row in crosswalk['listings'] if row['facility_id'] for osm in row['osm_ids']}
    # Retain linked footprints, but suppress duplicate directory entries by explicit ID.
    for layer in result['layers']:
        if layer['id'] != 'places' or not layer.get('available'):
            continue
        path = asset_dir / 'places.geojson'
        places = parse_json(path.read_text(encoding='utf-8'))
        places['features'] = [f for f in places['features'] if f['properties']['id'] not in crosswalk['excluded_osm_ids']]
        for feature in places['features']:
            canonical = linked.get(feature['properties']['id'])
            if canonical:
                feature['properties']['canonical_facility_id'] = canonical
        emit('places.geojson', script_json(places).encode('utf-8'))
    spatial = [f for f in result['facilities']['features'] if f['properties'].get('evacuation_id')]
    result['metadata']['evacuation_counts'] = {'listings': 12, 'spatial_locations': len(spatial),
        'unresolved_listings': 12 - len(spatial), 'unique_coordinates': len({tuple(f['geometry']['coordinates']) for f in spatial})}


def gis_asset_outputs(root):
    """Exact current generated resources, never a recursive raw-input inventory."""
    root = Path(root)
    manifest = Path('assets/gis/manifest.json')
    path = root / manifest
    for parent in (path, path.parent, path.parent.parent):
        if parent.is_symlink():
            raise ValueError('Symlink in GIS generated asset manifest')
    if not path.exists():
        return set()
    data = parse_json(bounded_bytes(path, 1024 * 1024).decode('utf-8'))
    if not isinstance(data, dict) or data.get('schema_version') != 1 or not isinstance(data.get('files'), list) or len(data['files']) > 13000:
        raise ValueError('Invalid generated GIS asset manifest')
    outputs = {manifest}
    for name in data['files']:
        if not isinstance(name, str) or not (name == 'assets/gis/barangay-statistics.json'
                or re.fullmatch(r'assets/gis/[a-z][a-z0-9-]{0,85}\.(?:geojson|png)', name)):
            raise ValueError(f'Unsafe generated GIS asset: {name!r}')
        rel = Path(name)
        if rel in outputs or (root / rel).is_symlink() or not (root / rel).is_file():
            raise ValueError(f'Missing, duplicate, or linked generated GIS asset: {name}')
        outputs.add(rel)
    return outputs
