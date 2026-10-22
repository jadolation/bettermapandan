"""Final maintainer-supplied hall positions and nonblocking geographic QA."""
import logging

from _build.gis_preview import feature_collection

LOG = logging.getLogger(__name__)
LEGACY_HALL_IDS = frozenset({'fac-012', 'fac-013', 'fac-014', 'fac-015'})
PROVENANCE = 'Maintainer-supplied building location; maintainer confirms Google Maps/government validation. Not independently field surveyed; not a surveyed entrance.'


def hall_collection(source):
    data = feature_collection(source, points_only=True, label='barangay-halls')
    features = data['features']
    gids = {f['properties'].get('barangay_gid') for f in features}
    from _build.gis_residents import BARANGAY_SLUGS
    if len(features) != 15 or gids != set(BARANGAY_SLUGS.values()):
        raise ValueError('Hall authority must contain exactly 15 unique canonical barangays')
    for feature in features:
        feature['properties'].update(
            facility_type='Barangay Hall', semantic_role='barangay_hall',
            coordinate_method='maintainer_supplied', location_precision='supplied_building_location',
            verification_status='maintainer_confirmed', layer_id='barangay-halls',
            provenance={'source': PROVENANCE},
            limitations=['Supplied building location, not a surveyed entrance. Hall location does not establish evacuation designation, availability or capacity.'])
    return data


def geographic_qa(halls, boundaries):
    """Report containment without moving accepted points or rejecting outliers."""
    def inside(point, ring):
        x, y = point
        contained = False
        for a, b in zip(ring, ring[1:]):
            if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
                contained = not contained
        return contained

    indexed = {f['properties'].get('barangay_gid', f['properties'].get('gid')): f['geometry'] for f in boundaries['features']}
    results = []
    for feature in halls['features']:
        props = feature['properties']
        geometry = indexed.get(props['barangay_gid'])
        polygons = [] if not geometry else [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
        contained = any(inside(feature['geometry']['coordinates'], p[0]) and not any(inside(feature['geometry']['coordinates'], hole) for hole in p[1:]) for p in polygons)
        results.append({'id': props['id'], 'barangay_gid': props['barangay_gid'], 'within_indicative_barangay': contained})
        log = LOG.info if contained else LOG.warning
        log('Hall geographic QA %s: within indicative barangay=%s (nonblocking; final coordinate retained)', props['id'], contained)
    return results
