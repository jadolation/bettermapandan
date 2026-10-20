#!/usr/bin/env python3
"""Extract candidate Mapandan polygons from locally downloaded nationwide GeoJSON.
Usage: python extract_mapandan.py ~/Downloads/barangays.geojson
Prints matches and writes src/data/gis/barangay_boundaries.geojson ONLY after
15 expected names are found exactly once with valid Polygon/MultiPolygon geometry.
Review output against canonical GIS barangays and local map before publishing.
"""
import json, re, sys
from collections import Counter
from pathlib import Path

EXPECTED = {'amanoaoac','apaya','aserda','baloling','coral','golden','jimenez',
            'lambayan','luyan','nilombot','pias','poblacion','primicias','santa maria','torres'}

def canon(s):
    return re.sub(r'[^a-z0-9]', '', str(s).lower().replace('sta.', 'santa ').replace('sta ', 'santa '))
EXPECTED_N = {canon(x) for x in EXPECTED}

def main():
    if len(sys.argv) != 2:
        sys.exit('Usage: python extract_mapandan.py path/to/barangays.geojson')
    data=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    if data.get('type') != 'FeatureCollection': sys.exit('Expected FeatureCollection')
    candidates=[]
    for feat in data.get('features', []):
        prop=feat.get('properties') or {}
        nm=next((str(prop[k]) for k in ('psgc_name','name','NAME_4','ADM4_EN','brgy_name','barangay') if prop.get(k)), '')
        code=next((str(prop[k]) for k in ('psgc_code','psgc_id','gid','ADM4_PCODE','adm4_pcode') if prop.get(k)), '')
        code_digits=re.sub(r'\D','',code)
        # Code prefixes vary in year/representation: explicitly inspect fields in output.
        if (canon(nm) in EXPECTED_N and code_digits.startswith('0105528')) or (
            canon(nm) in EXPECTED_N and 'mapandan' in str(prop).lower()):
            candidates.append((nm,code,feat))
    print('Candidate features:',len(candidates))
    for nm,code,f in candidates: print(nm,code,f.get('geometry',{}).get('type'),f.get('properties'))
    counts=Counter(canon(nm) for nm,_,_ in candidates)
    bad={k:v for k,v in counts.items() if v!=1}
    missing=EXPECTED_N-set(counts)
    invalid=[nm for nm,_,f in candidates if not isinstance(f.get('geometry'),dict) or f['geometry'].get('type') not in ('Polygon','MultiPolygon')]
    if len(candidates)!=15 or missing or bad or invalid:
        sys.exit(f'NOT EXPORTED: missing={sorted(missing)}, duplicate={bad}, invalid={invalid}. Review schema/code fields; avoid blind exports.')
    out=Path('src/data/gis/barangay_boundaries.geojson')
    out.parent.mkdir(parents=True,exist_ok=True)
    features=[]
    for nm,code,f in candidates:
        p=f.get('properties',{})
        features.append({'type':'Feature','geometry':f['geometry'],'properties':{
            'name':nm,'psgc':code,'source':'NAMRIA-derived barangay-boundaries-repository',
            'source_date':'NAMRIA 2023-11-06 / PSGC 2023-10-24',
            'precision':'Simplified reference geometry; not a surveyed legal boundary',
            'upstream_properties':p}})
    out.write_text(json.dumps({'type':'FeatureCollection','features':features},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('EXPORTED',out,'— GIS visual validation is still required')
if __name__=='__main__': main()
