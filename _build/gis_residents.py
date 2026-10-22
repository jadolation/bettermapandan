"""Explicit civic identity joins and bounded, privacy-safe resident projections."""
import re
from copy import deepcopy
from html import escape

from _build.gis import load_json
from _build.gis_preview import safe_text, safe_url

BARANGAY_SLUGS = {
    'amanoaoac': '0105528001', 'apaya': '0105528002', 'aserda': '0105528003',
    'baloling': '0105528004', 'coral': '0105528006', 'golden': '0105528007',
    'jimenez': '0105528008', 'lambayan': '0105528009', 'luyan': '0105528010',
    'nilombot': '0105528012', 'pias': '0105528013', 'poblacion': '0105528014',
    'primicias': '0105528015', 'sta-maria': '0105528016', 'torres': '0105528018',
}


def read_input(root, relative):
    path = root / relative
    if any(p.is_symlink() for p in (path, *path.parents)) or path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError('Unsafe or oversized resident input')
    return load_json(path)


def available(value):
    return safe_text(value) if isinstance(value, str) and value.strip().lower() not in {'', 'n/a', 'none', 'null'} else None


def phone_link(value):
    if not available(value) or not re.fullmatch(r'[+()\d .-]{3,40}', value):
        return None
    digits = re.sub(r'[^\d+]', '', value)
    if not re.fullmatch(r'\+?\d{3,15}', digits):
        return None
    return 'tel:' + digits


def residents(root):
    """Never copy nested personal email/contact fields into the map payload."""
    source = read_input(root, 'src/data/barangays.json')
    directory = {}
    rows = source.get('barangays')
    if not isinstance(rows, list) or len(rows) > 30:
        raise ValueError('Invalid barangay directory')
    for row in rows:
        gid = BARANGAY_SLUGS.get(row.get('slug'))
        if not gid or gid in directory:
            raise ValueError('Unmapped or duplicate barangay slug')
        entry = {key: value for key in ('name', 'punong_barangay') if (value := available(row.get(key)))}
        entry['slug'] = row['slug']
        entry['url'] = '/government/#barangay-councils'
        entry['officials'] = []
        for member in (row.get('kagawads', []) + row.get('officials', []))[:30]:
            if isinstance(member, dict) and available(member.get('name')):
                entry['officials'].append({'name': member['name'], 'role': available(member.get('position')) or 'Barangay official'})
        if phone_link(row.get('phone')):
            entry['phone'] = row['phone']
        if safe_url(row.get('facebook')):
            entry['official_page'] = row['facebook']
        directory[gid] = entry
    contacts = read_input(root, 'src/data/public-contacts.json')
    public = {'offices': {}, 'facility_offices': {}, 'source': '/government/',
              'source_verification_claim': 'August 2026', 'current_confirmation': None}
    for key in ('mdrrmo', 'fire', 'police', 'rhu', 'hospital'):
        office = contacts['offices'][key]
        clean = {'name': available(office.get('name')) or key,
                 'phones': [phone for phone in office.get('phones', [])[:10] if phone_link(phone)]}
        email = available(office.get('email'))
        if email and re.fullmatch(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', email):
            clean['email'] = email
        public['offices'][key] = clean
    for identifier, office in contacts.get('facility_offices', {}).items():
        if re.fullmatch(r'fac-\d{3}', identifier) and office in public['offices']:
            public['facility_offices'][identifier] = office
    return {'barangays': directory, 'contacts': public}


def reconcile(root, facilities, records):
    crosswalk = read_input(root, 'src/data/gis/evacuation-crosswalk.json')
    if crosswalk.get('source') != 'datasets/GIS/evacuation.json':
        raise ValueError('Evacuation source must be the explicit local inventory')
    source = read_input(root, crosswalk['source'])
    listings = crosswalk.get('listings')
    if not isinstance(listings, list) or len(listings) != 12 or len(source.get('features', [])) != 12:
        raise ValueError('Evacuation inventory must account for all 12 source listings')
    by_id = {f['properties']['id']: f for f in facilities['features']}
    excluded = set(crosswalk['publication_exclusions'])
    from _build.gis_halls import LEGACY_HALL_IDS
    halls = (set(crosswalk['unresolved_halls']) - LEGACY_HALL_IDS) | set(crosswalk.get('unresolved_facilities', []))
    for identifier in sorted(halls):
        feature = deepcopy(by_id[identifier])
        feature['geometry'] = None
        feature['properties'].update(layer_id='facility-references', location_precision='unresolved',
                                     verification_status='needs_review', coordinate_method='unresolved')
        feature['properties']['limitations'] = ['Hall building position is not established. School coordinates and barangay containment do not verify a hall. Listed only; no map pin.']
        if identifier == 'fac-006':
            feature['properties']['limitations'] = ['Older record combines National High School and Central School SPED identities. This unresolved record is not assigned the Central School evacuation listing; listed only, no map pin.']
        records.append(dict(feature['properties'], geometry=None))
    facilities['features'] = [f for f in facilities['features'] if f['properties']['id'] not in excluded | halls | LEGACY_HALL_IDS]
    seen, facility_ids = set(), set()
    for link, original in zip(listings, source['features'], strict=True):
        raw = original['properties']
        identifier = link['id']
        if identifier in seen or not re.fullmatch(r'evac-\d{3}', identifier) or link['source_name'] != raw['name_of_evacuation_center']:
            raise ValueError('Evacuation identity crosswalk does not match source')
        if link['barangay_gid'] not in BARANGAY_SLUGS.values():
            raise ValueError('Unknown evacuation barangay PSGC')
        for key in ('name_of_evacuation_center', 'floor_area', 'proximity_to_health_center', 'proximity_to_hospital'):
            if safe_text(raw.get(key)) is None:
                raise ValueError('Evacuation display values must be bounded text')
        seen.add(identifier)
        target = by_id.get(link['facility_id'])
        if link['facility_id'] and (target is None or link['facility_id'] in excluded | halls):
            raise ValueError('Invalid canonical evacuation facility')
        if target:
            if link['facility_id'] in facility_ids or target['properties'].get('barangay_gid') != link['barangay_gid']:
                raise ValueError('Duplicate or conflicting evacuation facility identity')
            facility_ids.add(link['facility_id'])
            props = target['properties']
        else:
            props = {'id': identifier, 'name': link['source_name'], 'barangay_gid': link['barangay_gid'],
                     'facility_type': 'School' if identifier == 'evac-005' else 'Barangay hall' if identifier == 'evac-004' else 'Public building',
                     'geometry': None, 'layer_id': 'evacuation-references'}
            records.append(props)
        props.update(evacuation_id=identifier, evacuation_source_name=link['source_name'],
                     evacuation_dimensions=raw['floor_area'], evacuation_health=raw['proximity_to_health_center'],
                     evacuation_hospital=raw['proximity_to_hospital'], evacuation_source_date=crosswalk['source_date'],
                     evacuation_capacity=None)
        if identifier in ('evac-006', 'evac-010'):
            props['operational_caution'] = 'undated_closed_notes'
        props.setdefault('limitations', []).append('Undated local evacuation listing; publisher and current official designation unknown. Current availability not confirmed. Listing does not establish safety, capacity or activation.')
        if identifier == 'evac-003':
            props['limitations'].append('Gym position retains a supplied Plus Code candidate; conflicting older location and exact building are not independently resolved.')
        if not target:
            props['limitations'].append('Identity or position unresolved; retained as one list-only source listing.')
    return crosswalk


def contact_placeholders(root):
    contacts = read_input(root, 'src/data/public-contacts.json')
    values = {}
    for key, office in contacts['offices'].items():
        prefix = 'PUBLIC_' + key.upper()
        values[prefix + '_LANDLINE'] = escape(office['phones'][0])
        values[prefix + '_MOBILE'] = escape(' / '.join(office['phones'][1:]))
        mobile = next((phone for phone in office['phones'] if phone.startswith('09') and phone_link(phone)), None)
        if mobile:
            values[prefix + '_TICKER'] = escape(mobile)
            values[prefix + '_TICKER_HREF'] = escape(phone_link(mobile), quote=True)
        values[prefix + '_HOMEPAGE'] = ' · '.join(
            f'<a href="{escape(phone_link(phone), quote=True)}">{escape(phone)}</a>'
            for phone in office['phones'][:contacts['homepage_phone_counts'][key]] if phone_link(phone))
        if office.get('email') and re.fullmatch(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', office['email']):
            values[prefix + '_EMAIL'] = f'<a href="mailto:{escape(office["email"], quote=True)}">{escape(office["email"])}</a>'
    return values
