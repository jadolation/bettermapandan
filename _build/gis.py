"""Fail-closed GIS publication boundary (GIS/AGENTS.md section 4.5).

Review contract: issues is required; external_issues, blocked_feature_ids and
publication_approvals are optional lists. Issues block their affected_ids unless
blocking=false or status=resolved with an evidenced resolution_decision. Prose
resolutions do not count. Approvals require feature_id, decision=approved,
reviewed_by, reviewed_at, evidence, and public_feature: an exact snapshot of the
allowlisted Feature. Changing a public claim invalidates its approval.
Evidence requires source, source_url (HTTP(S)), source_record_id, checked_at,
supports (claim names). Approval claims: identity, location, publication;
resolution claims: resolution. Dates are ISO YYYY-MM-DD. Humans must still
review evidence truth and appropriateness; these checks validate the trail only.

Missing/unreadable/malformed input or policy raises GISPublicationError. Invalid
individual candidates are omitted with aggregate internal logging. Missing
approvals means an empty public collection, never a canonical-data fallback.

Eligible statuses: source_verified, field_verified. Required provenance: source,
HTTP(S) source_url, source_record_id, retrieved and last_verified dates. Precision
must be approximate or exact_from_source, with a recognized coordinate_method;
cell centres and footprint centroids must be approximate. Geometry must be a
finite, in-range two-dimensional Point (longitude, latitude). Public fields are
listed below; all other feature/collection/provenance metadata is discarded.

Page handoff: {GIS_FACILITY_DIRECTORY} and {GIS_BARANGAY_DIRECTORY} insert escaped
semantic <ul> fragments; {GIS_FACILITY_COUNT} and {GIS_BARANGAY_COUNT} insert plain
integers. Facilities use exactly the gated payload, not inventory/status counts.
Empty lists render an empty <ul>; localized headings/empty-state prose belong to
the page agent. Directory descriptions accept the page locale; public JSON
coordinate descriptions retain conservative English text.
Existing GIS_*_DATA tokens receive script-safe JSON, not HTML-escaped JSON.
"""
import json
import logging
import math
from datetime import date
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

from _build.locales import t

LOG = logging.getLogger(__name__)
PUBLIC_FIELDS = (
    'id', 'name', 'category', 'facility_type', 'address', 'barangay_gid',
    'plus_code', 'verification_status', 'location_precision', 'coordinate_method',
)
PROVENANCE_FIELDS = ('source', 'source_url', 'source_record_id', 'retrieved', 'last_verified')
METHOD_LABELS = {
    'source_reported': 'Source-reported coordinates',
    'plus_code_cell_center': 'Approximate Plus Code cell centre',
    'polygon_centroid': 'Approximate point derived from a mapped footprint',
    'field_observation': 'Field-verified position',
}


class GISPublicationError(ValueError):
    """Unsafe GIS input must not be embedded in a public page."""


def _reject_constant(value):
    raise GISPublicationError('GIS JSON contains a non-finite number')


def parse_json(raw):
    try:
        return json.loads(raw, parse_constant=_reject_constant)
    except (ValueError, TypeError) as exc:
        raise GISPublicationError('Invalid GIS JSON') from exc


def load_json(path: Path):
    try:
        return parse_json(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError) as exc:
        raise GISPublicationError(f'Cannot read required GIS input: {path.name}') from exc


def script_json(value):
    """Serialize for HTML script context; reject non-finite numbers."""
    try:
        result = json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise GISPublicationError('Cannot serialize GIS payload') from exc
    for char, encoded in (('&', '\\u0026'), ('<', '\\u003c'), ('>', '\\u003e'),
                          ('\u2028', '\\u2028'), ('\u2029', '\\u2029')):
        result = result.replace(char, encoded)
    return result


def _text(value):
    return isinstance(value, str) and value.strip().lower() not in {
        '', 'unknown', 'n/a', 'none', 'null', 'tbd', 'pending',
    }


def _date(value):
    try:
        return isinstance(value, str) and date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _url(value):
    if not _text(value):
        return False
    try:
        parts = urlsplit(value)
        return parts.scheme in {'http', 'https'} and bool(parts.hostname) and not parts.username
    except ValueError:
        return False


def _decision(value, decision, claims):
    if not isinstance(value, dict) or value.get('decision') != decision:
        return False
    if not _text(value.get('reviewed_by')) or not _date(value.get('reviewed_at')):
        return False
    evidence = value.get('evidence')
    if not isinstance(evidence, list) or not evidence:
        return False
    supported = set()
    for item in evidence:
        if not isinstance(item, dict) or not all(_text(item.get(k)) for k in ('source', 'source_record_id')):
            return False
        if not _url(item.get('source_url')) or not _date(item.get('checked_at')):
            return False
        supports = item.get('supports')
        if not isinstance(supports, list) or not all(_text(s) for s in supports):
            return False
        supported.update(supports)
    return claims <= supported


def _ids(value):
    return isinstance(value, list) and all(_text(item) for item in value)


def _policy(review):
    if not isinstance(review, dict) or not isinstance(review.get('issues'), list):
        raise GISPublicationError('GIS review policy requires an issues list')
    for key in ('external_issues', 'blocked_feature_ids', 'publication_approvals'):
        if key in review and not isinstance(review[key], list):
            raise GISPublicationError(f'GIS review policy requires a {key} list')
    blocked = review.get('blocked_feature_ids', [])
    if not _ids(blocked):
        raise GISPublicationError('Invalid GIS blocked_feature_ids')
    blocked = set(blocked)
    for key in ('issues', 'external_issues'):
        for issue in review.get(key, []):
            if not isinstance(issue, dict) or not _text(issue.get('issue_id')) or not isinstance(issue.get('status'), str) or not issue['status'].strip():
                raise GISPublicationError('Invalid GIS review issue')
            # Legacy external issues may describe future datasets/general rules.
            affected = issue.get('affected_ids', [] if key == 'external_issues' else None)
            if not _ids(affected) or ('blocking' in issue and type(issue['blocking']) is not bool):
                raise GISPublicationError('Invalid GIS review issue affected_ids/blocking')
            resolved = issue['status'] == 'resolved' and _decision(
                issue.get('resolution_decision'), 'resolved', {'resolution'})
            if issue.get('blocking', True) and not resolved:
                blocked.update(affected)
    approvals = {}
    for approval in review.get('publication_approvals', []):
        if not isinstance(approval, dict) or not _text(approval.get('feature_id')):
            raise GISPublicationError('Invalid GIS publication approval')
        fid = approval['feature_id']
        if fid in approvals:
            raise GISPublicationError('Duplicate GIS publication approval')
        approvals[fid] = approval
    return blocked, approvals


def _public_feature(feature):
    if not isinstance(feature, dict) or feature.get('type') != 'Feature':
        return None
    props, geometry = feature.get('properties'), feature.get('geometry')
    if not isinstance(props, dict) or not isinstance(geometry, dict) or geometry.get('type') != 'Point':
        return None
    coords = geometry.get('coordinates')
    if not isinstance(coords, list) or len(coords) != 2 or not all(
        (type(n) is int or type(n) is float and math.isfinite(n)) for n in coords
    ) or not (-180 <= coords[0] <= 180 and -90 <= coords[1] <= 90):
        return None
    if not all(_text(props.get(k)) for k in ('id', 'name', 'category')):
        return None
    if props.get('verification_status') not in ('source_verified', 'field_verified'):
        return None
    precision, method = props.get('location_precision'), props.get('coordinate_method')
    if precision not in ('exact_from_source', 'approximate') or not isinstance(method, str) or method not in METHOD_LABELS:
        return None
    if method in ('plus_code_cell_center', 'polygon_centroid') and precision != 'approximate':
        return None
    if method == 'field_observation' and props['verification_status'] != 'field_verified':
        return None
    prov = props.get('provenance')
    if not isinstance(prov, dict) or not all(_text(prov.get(k)) for k in ('source', 'source_record_id')):
        return None
    if not _url(prov.get('source_url')) or not all(_date(prov.get(k)) for k in ('retrieved', 'last_verified')):
        return None
    public = {}
    for key in PUBLIC_FIELDS:
        value = props.get(key)
        if value is not None and not isinstance(value, str):
            return None
        public[key] = value
    public['provenance'] = {key: prov[key] for key in PROVENANCE_FIELDS}
    public['coordinate_description'] = METHOD_LABELS[method]
    if precision == 'approximate' and method == 'source_reported':
        public['coordinate_description'] = 'Approximate source-reported coordinates'
    return {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': coords[:]}, 'properties': public}


def public_facilities(data, review):
    """Return a fresh allowlisted collection; never mutate canonical inputs."""
    blocked, approvals = _policy(review)
    if not isinstance(data, dict) or data.get('type') != 'FeatureCollection' or not isinstance(data.get('features'), list):
        raise GISPublicationError('GIS facilities must be a FeatureCollection with a features list')
    public, seen = [], set()
    for candidate in data['features']:
        feature = _public_feature(candidate)
        if feature is None:
            continue
        fid = feature['properties']['id']
        if fid in seen:
            raise GISPublicationError('Duplicate GIS facility ID')
        seen.add(fid)
        approval = approvals.get(fid, {})
        if fid not in blocked and _decision(approval, 'approved', {'identity', 'location', 'publication'}) and approval.get('public_feature') == feature:
            public.append(feature)
    excluded = len(data['features']) - len(public)
    if excluded:
        LOG.warning('GIS publication gate excluded %d facility candidates', excluded)
    return {'type': 'FeatureCollection', 'features': public,
            'metadata': {'rendered_features': len(public), 'excluded_features': excluded}}


def public_layer_manifest(data, facility_count):
    """Do not embed internal manifest notes or historical release claims.

    Only facilities have an inline renderer. Other canonical layer entries are
    inventory, not emitted assets or implemented overlays.
    """
    if not isinstance(data, dict) or not isinstance(data.get('layers'), list):
        raise GISPublicationError('GIS manifest requires a layers list')
    metadata = data.get('metadata', {})
    if not isinstance(metadata, dict):
        raise GISPublicationError('Invalid GIS manifest metadata')
    layers = []
    fields = ('id', 'title',
              'source_url', 'attribution', 'update_date')
    for layer in data['layers']:
        if not isinstance(layer, dict):
            raise GISPublicationError('Invalid GIS manifest layer')
        public = {key: layer[key] for key in fields if key in layer}
        inline = layer.get('id') == 'facilities'
        public.update(available=inline, type='inline-geojson' if inline else 'unavailable',
                      visible_by_default=inline)
        if layer.get('id') == 'facilities':
            public['verification_notes'] = (
                f'{facility_count} facilities approved for publication. '
                'Source verification alone is not publication approval.'
            )
        layers.append(public)
    return {'layers': layers, 'metadata': {
        key: metadata[key] for key in ('municipality_psgc', 'coordinate_bounds',
                                      'default_map_center', 'default_zoom') if key in metadata
    }}


def directory_html(data, kind, locale=None):
    """Escaped semantic <ul> fragment. Facilities must already be gated.

    Headings and empty-state prose belong to the localized template. Optional
    locale selects plain-text directory labels without changing the public data.
    Omitted locale preserves the original English fragments for existing callers.
    No internal IDs in attributes, source links, scripts or unescaped HTML.
    """
    rows = []
    for feature in data.get('features', []):
        props = feature['properties']
        if kind == 'facilities':
            detail = props['coordinate_description']
            if locale is not None:
                key = {
                    'source_reported': 'source_reported',
                    'plus_code_cell_center': 'cell_center',
                    'polygon_centroid': 'centroid',
                    'field_observation': 'field_position',
                }.get(props.get('coordinate_method'), 'unknown_precision')
                if key == 'source_reported' and props.get('location_precision') == 'approximate':
                    key = 'approximate_source'
                detail = t(locale, f'gis.{key}', detail)
        else:
            detail = f"{props['gid']} / {props['pop2024']} (2024 POPCEN)"
            if locale is not None:
                population = t(locale, 'about.population', 'Population')
                detail = f"PSGC: {props['gid']} / {population}: {props['pop2024']} (2024 POPCEN)"
        rows.append(f'<li><strong>{escape(str(props["name"]))}</strong> <span>{escape(str(detail))}</span></li>')
    return '<ul class="gis-directory">' + ''.join(rows) + '</ul>'
