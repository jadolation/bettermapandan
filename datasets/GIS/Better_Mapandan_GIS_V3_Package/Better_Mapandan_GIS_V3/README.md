# Better Mapandan GIS V3 handoff

- `GIS_IMPLEMENTATION_PLAN_V3.md` — complete implementation plan and source decisions.
- `extract_mapandan.py` — locally run extractor; it does **not** contain actual barangay polygons.
- `Mapandan Barangay (Water district).png`, `MAPANDAN_BARANGAYS.png` — user-supplied comparison references.

Get the nationwide polygon source from:
https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/download/v2026.4.13.0/barangays.geojson

Then run from Better Mapandan repository root:
`python /path/to/extract_mapandan.py /path/to/barangays.geojson`

**Status:** candidate nationwide polygon dataset located, but downloading / validating its Mapandan subset was not possible in this environment. No claims that 15 polygons have been obtained. Do not publish a candidate subset without visually checking against the supplied maps and canonical PSGC entries.
