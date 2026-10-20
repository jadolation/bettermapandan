"""Bounded GIS geometry and display-field normalization."""
import logging
import math
import re
from copy import deepcopy
from urllib.parse import urlsplit

LOG = logging.getLogger(__name__)
MAX_FEATURES = 10000
MAX_VERTICES = 200000
FIELDS = ("id", "name", "category", "facility_type", "address", "barangay_gid",
          "plus_code", "verification_status", "location_precision", "coordinate_method",
          "source", "source_date", "scenario", "class", "class_name", "label", "description",
          "gid", "psgc", "psgc_code", "source_name", "slug", "source_as_of", "highway", "waterway", "amenity", "building",
          "source_transaction_id", "project_id", "status_key", "raw_status", "status", "contractor",
          "start_date", "completion_date", "contract_effectivity_date", "expiry_date", "semantic_role", "layer_id",
          "contract_id", "barangay_location", "executing_agency", "source_of_funds", "contract_expiry_date",
          "actual_start_date", "actual_completion_date")


def safe_text(value):
    return value if isinstance(value, str) and len(value) <= 2000 else None


def finite_number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def safe_url(value):
    if not isinstance(value, str) or len(value) > 2000 or any(ord(c) < 32 for c in value):
        return False
    try:
        parts = urlsplit(value)
        return parts.scheme in {"http", "https"} and bool(parts.hostname) and not parts.username and not parts.password
    except ValueError:
        return False


def feature_collection(data, *, points_only=False, nonspatial=False, label="GIS"):
    """Skip bad individual features; reject malformed/oversized collections."""
    if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
        raise ValueError("Expected FeatureCollection")
    if 'crs' in data and data['crs'] not in (
            {'type': 'name', 'properties': {'name': 'urn:ogc:def:crs:OGC:1.3:CRS84'}},
            {'type': 'name', 'properties': {'name': 'EPSG:4326'}}):
        raise ValueError("Unsupported coordinate reference system")
    features = data.get("features")
    if not isinstance(features, list) or len(features) > MAX_FEATURES:
        raise ValueError("Feature resource limit or missing features list")
    budget = [MAX_VERTICES]

    def coordinate(value, depth):
        if not isinstance(value, list) or not value or len(value) > MAX_VERTICES:
            raise ValueError("Invalid coordinates or coordinate resource limit")
        if depth == 0:
            budget[0] -= 1
            if budget[0] < 0:
                raise ValueError("Coordinate resource limit")
            if len(value) != 2 or not all(finite_number(n) for n in value):
                raise ValueError("Coordinates must be finite longitude/latitude pairs")
            if not (-180 <= value[0] <= 180 and -90 <= value[1] <= 90):
                raise ValueError("Coordinates out of range")
        else:
            for child in value:
                coordinate(child, depth - 1)

    result, seen = [], set()
    for index, feature in enumerate(features):
        identifier = str(index + 1)
        try:
            if not isinstance(feature, dict) or feature.get("type") != "Feature" or not isinstance(feature.get("properties"), dict):
                raise ValueError("Expected Feature with properties")
            original = feature["properties"]
            identifier = safe_text(original.get("id")) or safe_text(original.get("gid")) or str(feature.get("id", index + 1))
            if identifier in seen:
                raise ValueError("Duplicate feature ID")
            geometry = feature.get("geometry")
            if points_only and (not isinstance(geometry, dict) or geometry.get("type") != "Point"):
                raise ValueError("Facility geometry must be Point")
            if nonspatial and geometry is not None:
                raise ValueError("Reference geometry must be null; no position inferred")
            if geometry is not None:
                if not isinstance(geometry, dict):
                    raise ValueError("Invalid geometry")
                depths = {"Point": 0, "MultiPoint": 1, "LineString": 1, "MultiLineString": 2, "Polygon": 2, "MultiPolygon": 3}
                kind = geometry.get("type")
                if kind not in depths:
                    raise ValueError("Unsupported geometry")
                coordinate(geometry.get("coordinates"), depths[kind])
                if kind in ("Polygon", "MultiPolygon"):
                    polygons = [geometry["coordinates"]] if kind == "Polygon" else geometry["coordinates"]
                    for polygon in polygons:
                        for ring in polygon:
                            if len(ring) < 4 or ring[0] != ring[-1]:
                                raise ValueError("Polygon rings must be closed and have at least four positions")
                lines = [geometry["coordinates"]] if kind == "LineString" else geometry["coordinates"] if kind == "MultiLineString" else []
                if any(len(line) < 2 for line in lines):
                    raise ValueError("Line requires at least two positions")
            props = {key: value for key in FIELDS if (value := safe_text(original.get(key))) is not None}
            props.setdefault("id", identifier)
            props.setdefault("name", props.get("label", identifier))
            for key in ("pop2024", "pop2020"):
                if type(original.get(key)) is int and original[key] >= 0:
                    props[key] = original[key]
            for key in ('fiscal_year', 'contract_amount', 'approved_budget', 'accomplishment_percent', 'source_area_sqkm'):
                value = original.get(key)
                if finite_number(value):
                    props[key] = value
                elif key in original and value is None:
                    props[key] = None
            if 'project_id' in original and original['project_id'] is None:
                props['project_id'] = None
            provenance = original.get('provenance')
            if isinstance(provenance, dict):
                props['provenance'] = {key: value for key in ('source', 'source_record_id', 'retrieved', 'last_verified')
                                       if (value := safe_text(provenance.get(key))) is not None}
                if safe_url(provenance.get('source_url')):
                    props['provenance']['source_url'] = provenance['source_url']
            for key in ('source_url', 'source_document_url'):
                if safe_url(original.get(key)):
                    props[key] = original[key]
            project_url = original.get('project_url')
            if isinstance(project_url, str) and len(project_url) <= 4000 and re.fullmatch(r'/(?:fil/|pag/)?transparency/(?:projects/\?project=|infrastructure/#dpwh-project-)(?:[A-Za-z0-9_.~-]|%[A-Fa-f0-9]{2})+', project_url):
                props['project_url'] = project_url
            for key in ('quality_flags', 'limitations', 'contractors'):
                values = original.get(key)
                if isinstance(values, list):
                    props[key] = [clean for value in values[:100] if (clean := safe_text(value)) is not None]
            source_geometry_id = original.get('source_geometry_id')
            if type(source_geometry_id) is int or safe_text(source_geometry_id) is not None:
                props.setdefault('provenance', {}).setdefault('source_record_id', str(source_geometry_id))
            source_note = safe_text(original.get('source_note'))
            if source_note and source_note not in props.get('limitations', []):
                props.setdefault('limitations', []).append(source_note)
            safe_geometry = None if geometry is None else {'type': geometry['type'], 'coordinates': deepcopy(geometry['coordinates'])}
            result.append({"type": "Feature", "geometry": safe_geometry, "properties": props})
            seen.add(identifier)
        except ValueError as exc:
            LOG.warning("GIS layer %s: skipped feature %s (index %d): %s", label, identifier, index, exc)
    return {"type": "FeatureCollection", "features": result}


def project_records(data, lang_code="en"):
    if not isinstance(data, list) or len(data) > MAX_FEATURES:
        raise ValueError("Expected project records list within resource limit")
    records, seen = [], set()
    for index, project in enumerate(data):
        if not isinstance(project, dict):
            LOG.warning("GIS projects: skipped record index %d: expected object", index)
            continue
        identifier = project.get("project_id")
        name = safe_text(project.get("canonical_name"))
        if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", identifier) or not name or identifier in seen:
            LOG.warning("GIS projects: skipped record index %d: invalid/duplicate ID or missing name", index)
            continue
        seen.add(identifier)
        records.append({"id": identifier, "project_id": identifier, "name": name,
                        "geometry": None, "semantic_role": "nonspatial_project",
                        "project_url": ("" if lang_code == "en" else "/" + lang_code)
                        + "/transparency/projects/?project=" + identifier,
                        "limitations": ["No supplied project position; listed only"]})
    return records
