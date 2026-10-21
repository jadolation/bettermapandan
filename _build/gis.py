"""Safe GIS display projections and script/static-directory serialization."""
import json
from html import escape
from pathlib import Path

from _build.gis_preview import feature_collection
from _build.locales import t

METHOD_LABELS = {
    'source_reported': 'Source-reported coordinates',
    'plus_code_cell_center': 'Approximate Plus Code cell centre',
    'polygon_centroid': 'Approximate point derived from a mapped footprint',
    'field_observation': 'Field-observed position',
}


class GISDataError(ValueError):
    """GIS input cannot be safely parsed or serialized."""


def _reject_constant(value):
    raise GISDataError('GIS JSON contains a non-finite number')


def parse_json(raw):
    try:
        return json.loads(raw, parse_constant=_reject_constant)
    except (ValueError, TypeError) as exc:
        raise GISDataError('Invalid GIS JSON') from exc


def load_json(path: Path):
    try:
        return parse_json(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError) as exc:
        raise GISDataError(f'Cannot read GIS input: {path.name}') from exc


def script_json(value):
    """Serialize JSON for HTML script context, not HTML attribute context."""
    try:
        result = json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise GISDataError('Cannot serialize GIS payload') from exc
    for char, encoded in (('&', '\\u0026'), ('<', '\\u003c'), ('>', '\\u003e'),
                          ('\u2028', '\\u2028'), ('\u2029', '\\u2029')):
        result = result.replace(char, encoded)
    return result


def facilities_collection(data):
    result = feature_collection(data, points_only=True, label='facilities')
    for feature in result['features']:
        props = feature['properties']
        method = props.get('coordinate_method')
        props['coordinate_description'] = METHOD_LABELS.get(method, 'Unknown precision')
        if props.get('location_precision') == 'approximate' and method == 'source_reported':
            props['coordinate_description'] = 'Approximate source-reported coordinates'
    return result


def barangay_collection(data):
    return feature_collection(data, nonspatial=True, label='barangays')


def directory_html(data, kind, locale=None, residents=None):
    """Return an escaped semantic directory from the same data sent to the map."""
    rows = []
    for feature in data.get('features', []):
        props = feature['properties']
        if kind == 'facilities':
            detail = props.get('coordinate_description', 'Unknown precision')
            if locale is not None:
                key = {'source_reported': 'source_reported', 'plus_code_cell_center': 'cell_center',
                       'polygon_centroid': 'centroid', 'field_observation': 'field_position'}.get(props.get('coordinate_method'), 'unknown_precision')
                if key == 'source_reported' and props.get('location_precision') == 'approximate':
                    key = 'approximate_source'
                detail = t(locale, f'gis.{key}', detail)
        else:
            population = t(locale, 'about.population', 'Population') if locale is not None else 'Population'
            detail = f"PSGC: {props.get('gid', '')} / {population}: {props.get('pop2024', '?')} (2024 POPCEN)"
        if props.get('evacuation_id'):
            detail = (t(locale, 'gis.listed_evacuation', 'Listed evacuation center') if locale else 'Listed evacuation center') + '. ' + (t(locale, 'gis.availability_unknown', 'Current availability not confirmed') if locale else 'Current availability not confirmed')
            detail += '. ' + ('Approximate mapped location' if feature.get('geometry') else 'Location unresolved; list only')
            detail += '. Source publisher/date unknown; capacity not provided.'
            if props.get('operational_caution'):
                detail += ' ' + (locale or {}).get('gis', {}).get('resident', {}).get('operationUnknown', 'Older undated notes say Closed; current school operation is not confirmed.')
        elif props.get('location_precision') == 'unresolved':
            detail = (locale or {}).get('gis', {}).get('resident', {}).get('unresolved', 'Building position unresolved; list only')
        extra = ''
        if residents:
            from _build.gis_residents import phone_link
            barangay = residents['barangays'].get(props.get('barangay_gid') or props.get('gid'))
            if barangay:
                extra += '<p>' + escape(barangay['name'] + ' / Punong Barangay: ' + barangay.get('punong_barangay', 'Not provided')) + '</p>'
                if phone_link(barangay.get('phone')):
                    label = (locale or {}).get('gis', {}).get('resident', {}).get('barangayContact', 'Barangay assistance')
                    extra += f'<p>{escape(label)}: <a href="{escape(phone_link(barangay["phone"]), quote=True)}">{escape(barangay["phone"])}</a></p>'
            if props.get('evacuation_id'):
                phone = residents['contacts']['offices']['mdrrmo']['phones'][0]
                extra += f'<p>MDRRMO: <a href="{escape(phone_link(phone), quote=True)}">{escape(phone)}</a></p>'
        rows.append(f'<li><strong>{escape(str(props["name"]))}</strong> <span>{escape(str(detail))}</span>{extra}</li>')
    return '<ul class="gis-directory">' + ''.join(rows) + '</ul>'
