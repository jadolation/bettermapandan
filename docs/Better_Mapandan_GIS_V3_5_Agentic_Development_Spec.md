# Better Mapandan GIS V3.5 — Weather Explorer

**Document type:** Agentic development specification  
**Status:** Implementation-ready specification; not an implementation report  
**Version:** 1.0  
**Prepared:** 2026-10-22  
**Primary audience:** Autonomous coding agents, maintainers, reviewers, and QA agents

---

## 0. Agent mission and operating contract

You are the development agent responsible for implementing **V3.5 Weather Explorer** in the existing **Better Mapandan GIS** project.

The intended architecture is **static Python build tooling + Leaflet + vanilla JavaScript**, with no required application server, database, or commercial weather subscription. The GIS already has map controls, barangay polygons, facilities, and other thematic layers. Previous versions may include V3.3 choropleths and V3.4 route/navigation capabilities.

**Your assignment:** Inspect the actual repository, implement the **four mandatory weather modes** (temperature, feels-like temperature, wind, and precipitation), integrate them non-destructively with the existing GIS, add resilient loading/caching/localization, test the result, and report factual evidence of completion. **Optional recent radar** may be implemented only after verifying current provider terms, coverage, and data reliability.

### Non-negotiable agent rules

1. **Inspect before modifying.** Locate actual entry points, build pipeline, map initialization, existing UI patterns, localization files, and tests. Paths in this document are proposals, not proof that files already exist.
2. **Preserve existing functionality.** Do not regress barangay selection, facility details, thematic rasters/choropleths, search, or route state. Avoid replacing the Leaflet map or rewriting the project architecture.
3. **Respect repository conventions.** Match the project's module style, naming, static build output, lint/test patterns, and localization strategy. If a proposed path is absent, use the corresponding actual path and explain the mapping in your final report.
4. **Keep weather runtime-only.** The isolated/offline Python build must not make weather API requests. External weather API requests originate in the visitor's browser only after weather is activated.
5. **No fictional granularity.** Weather model grid samples are not physical weather stations or barangay-specific observations. Do not fabricate hyperlocal values by adding offsets or interpolating fake precision.
6. **Accurate terminology.** `apparent_temperature` is **feels-like/apparent temperature**, not an official PAGASA heat index. Forecast `precipitation` is not observed current rainfall. Show provider and applicable valid times.
7. **Fail safely.** Network errors, rate limits, missing data, offline access, and radar unavailability must never break the GIS.
8. **No secrets or location tracking.** Do not require API keys, a new backend, or the visitor's geolocation for ordinary Mapandan weather viewing.
9. **Verify current external contracts.** Before implementation, re-check official Open-Meteo and RainViewer documentation, licensing, noncommercial terms, request limits, timestamp semantics, and tile restrictions. Record any changes to this specification in a short decision log.
10. **Do not claim success without evidence.** Run automated tests, an offline build, and a real-browser smoke test; clearly identify any checks you cannot execute.

### Definition of complete

The core feature is complete only when a visitor can enable one of the four weather modes, see accurate **source-labeled and time-stamped** weather data, select a valid forecast time, switch modes without repeated unnecessary network requests, and disable Weather to restore the original GIS state. All existing GIS controls must remain functional. Radar is not required for core acceptance.

---

## 1. Product scope

### 1.1 Mandatory in scope

- **Temperature** visualization in degrees Celsius using `temperature_2m`.
- **Feels-like temperature** visualization using `apparent_temperature`.
- **Wind** visualization using `wind_speed_10m` (km/h) and `wind_direction_10m` (degrees).
- **Hourly precipitation** visualization using `precipitation` (mm per provider time interval; label the interval accurately).
- A **Weather** control in the current Leaflet map UI, with one weather mode visible at a time.
- Forecast-time selection using real valid provider timestamps (not arbitrary labels disconnected from returned data).
- Loading, empty, failed, rate-limited, and stale states; refresh and caching.
- Data source attribution, valid/retrieval timestamps, timezone display, units, legend, and a weather warning/disclaimer.
- Keyboard and mobile usability, English/Filipino/Pangasinan localization with safe fallbacks.
- Automated build/unit/integration coverage and browser verification.

### 1.2 Optional, gated scope

- **Recent rain radar** using RainViewer tiles and available past frames. Implement only if current terms permit the intended use and the area has reliable coverage. The UI must explain that these are **recent/past radar frames**, never live future radar forecasts. A radar implementation must respect provider tile and native zoom limits.

### 1.3 Explicitly out of scope

- A new Python web server, database, proxy, paid weather feed, account system, or API-key storage.
- Flood-risk calculation, road-passability prediction, weather-dependent evacuation-center safety, route safety claims, and parcel/building-scale weather estimates.
- Mandatory browser geolocation or continuous location tracking.
- Invention of values for every barangay, source-free interpolation, or assertions that model values are field measurements.
- Changing existing GIS data formats purely to make weather work unless carefully validated, backwards compatible, and documented.

---

## 2. Repository reconnaissance — required first action

Before coding, perform the following and record findings:

1. Read the project's `README`, build instructions, current GIS UI, and any contributor/test instructions (including `AGENTS.md` where present).
2. Locate the Leaflet `L.map(...)` creation, layer/group registration, layer-ordering conventions, and map teardown logic.
3. Locate barangay polygon handlers, facility markers/popups, selected feature state, navigation route state, and choropleth visibility logic.
4. Identify how `src/pages/gis.html`, `_build/pages.py`, `_build/staging.py`, `assets/gis-map.js`, `assets/css/map.css`, and `src/data/gis/layers.json` (or their actual equivalents) are used.
5. Determine how `locales/en.json`, `locales/fil.json`, and `locales/pag.json` (or equivalent resources) are compiled and used.
6. Inspect existing test conventions, offline build behavior, JS tooling, error boundaries, caching patterns, and accessibility controls.
7. Check current provider documentation and usage terms:
   - Open-Meteo API: <https://open-meteo.com/en/docs>
   - Open-Meteo pricing/terms: <https://open-meteo.com/en/pricing>
   - RainViewer API (optional): <https://www.rainviewer.com/api.html>
   - PAGASA official information: <https://www.pagasa.dost.gov.ph/>
8. Inspect deployment restrictions: CSP, allowed origins, static asset paths, page load order, and any cache policy.

**Reconnaissance gate:** Before making extensive changes, state the actual file map, applicable provider restrictions, expected integration points, and any departures from this plan in the agent's work log or final report. Do not block progress on clarification when a reasonable repository-consistent choice exists.

---

## 3. Solution architecture and data flow

```text
Existing Better Mapandan GIS
  └── Existing Leaflet map instance
       ├── Existing barangays, facilities, rasters, routes, controls
       └── WeatherController (new, isolated)
            ├── Weather UI: mode, forecast time, refresh, status, legend
            ├── Weather API client (Open-Meteo; browser runtime only)
            ├── Normalizer/validator (time, units, coordinates, missing values)
            ├── Memory cache + request deduplication + abort/stale-response guards
            ├── One active weather overlay group
            └── Optional RainViewer adapter (separate, feature-gated)
```

**Integration contract:** Attach to the existing map instance; do not construct another map. Keep weather overlays and state in an isolated controller, and provide explicit `enable()`, `setMode()`, `setForecastTime()`, `refresh()`, `disable()`, and `destroy()` behavior or equivalent methods matched to project conventions. Clean up timers, AbortControllers, event listeners, and LayerGroups.

Prefer a single controller and provider adapters over mixing HTTP logic into map click handlers. The build may embed validated static weather configuration; it must not generate live weather data.

### 3.1 Proposed file manifest (adapt to actual repository)

| Proposed file | Expected responsibility |
|---|---|
| `src/data/gis/weather.json` | Static settings; geographic configuration; enabled modes |
| `assets/js/gis-weather.js` | Weather controller, API client, normalization, cache, overlay rendering |
| `assets/gis-map.js` | Attach and initialize weather controller against existing `L.Map` |
| `src/pages/gis.html` | Accessible weather controls and status/legend containers |
| `assets/css/map.css` | Visual styling, contrast, responsive layout, arrows/labels |
| `_build/pages.py` | Validate/expose weather config and localized text as appropriate |
| `_build/staging.py` | Include/copy weather scripts and assets in build output |
| `locales/en.json` | English UI strings |
| `locales/fil.json` | Filipino UI strings |
| `locales/pag.json` | Pangasinan UI strings; fallback for unverified technical terms |
| `tests/test_gis_weather.py` | Config/build/offline/static integration assertions |
| `tests/gis-weather.cjs` | JS unit tests, including request normalization and race conditions |
| `tests/browser/gis-weather.cjs` | Browser GIS/weather integration smoke tests |

If `layers.json` restricts supported layer types, **do not add a `weather` type** without corresponding schema, build, and runtime support. Prefer separate `weather.json` + a controller attached to the map.

---

## 4. Configuration and geographic sampling

Create repository-consistent, versioned, validated JSON configuration; example:

```json
{
  "schema_version": 1,
  "provider": "open-meteo",
  "center": {
    "latitude": 16.03,
    "longitude": 120.455
  },
  "timezone": "Asia/Manila",
  "refresh_minutes": 20,
  "timeout_ms": 10000,
  "default_visible": false,
  "modes": [
    "temperature",
    "apparent-temperature",
    "wind",
    "rain"
  ]
}
```

**Coordinate warning:** `16.03, 120.455` is a starting reference point for configuration, **not a surveyed claim about the municipal centroid**. Verify against the GIS's existing Mapandan geometry and preferred center before use.

### 4.1 Sampling strategy

- Prefer a modest number of geographically distributed points within/near the project's true Mapandan coverage; derive positions from real GIS geometry or validated site data. Do not assume barangay centroids equal weather observation stations.
- Batch multiple latitudes/longitudes if allowed by the current API and handle the response's actual multi-location shape.
- Detect and gracefully handle nearly identical repeated weather values/grid cells; avoid any false appearance of independent barangay readings.
- Label sample points **model estimate** or **forecast sample** rather than "station".
- At tighter zooms, avoid misleading high-resolution heatmaps or precision. Numeric sample markers with modest visual shading are safer than fabricated continuous measurements.
- If there is insufficient geographic sampling to substantiate a spatial gradient, default to a representative area reading instead of manufacturing one.

### 4.2 Configuration validation

Validate schema version, allowed modes, finite coordinates, latitude/longitude bounds, valid timezone, sane refresh/timeout limits, uniqueness/count of sample positions, and all optional feature flags. Fail the build clearly on malformed local configuration, but never make external API requests during validation.

---

## 5. Primary data provider: Open-Meteo

Implement using the official Forecast API, subject to current documentation and license restrictions. Intended request variables:

- `current`: `temperature_2m`, `apparent_temperature`, `wind_speed_10m`, `wind_direction_10m`.
- `hourly`: `temperature_2m`, `apparent_temperature`, `wind_speed_10m`, `wind_direction_10m`, `precipitation`, optionally `precipitation_probability` if relevant to a descriptive UI.
- `temperature_unit=celsius`, `wind_speed_unit=kmh`, `precipitation_unit=mm`, `timezone=Asia/Manila`, `forecast_days=2` (or an evidence-based supported horizon).

**Illustrative request only — construct programmatically and verify provider support:**

```text
https://api.open-meteo.com/v1/forecast?latitude=16.03&longitude=120.455&current=temperature_2m,apparent_temperature,wind_speed_10m,wind_direction_10m&hourly=temperature_2m,apparent_temperature,wind_speed_10m,wind_direction_10m,precipitation,precipitation_probability&temperature_unit=celsius&wind_speed_unit=kmh&precipitation_unit=mm&timezone=Asia%2FManila&forecast_days=2
```

### 5.1 Data normalization contract

Normalize the provider response to a single internal shape, for example:

```ts
// Illustrative interface (do not introduce TypeScript tooling solely for this).
type WeatherSample = {
  sampleId: string;
  latitude: number;
  longitude: number;
  source: "open-meteo";
  kind: "current-model" | "hourly-forecast";
  validTime: string;       // ISO time with explicit timezone interpretation
  retrievedAt: string;     // client retrieval timestamp
  temperatureC: number | null;
  apparentTemperatureC: number | null;
  windSpeedKmh: number | null;
  windFromDegrees: number | null; // meteorological direction FROM
  precipitationMm: number | null;
};
```

Additional mandatory rules:

- Read provider metadata for units and time offsets; parse valid times reliably across its timestamp formats.
- Render times in **Asia/Manila**, explicitly label **PHT**, and never present a future forecast as an observation.
- Inspect missing/null/NaN/non-finite values, array lengths, index bounds, and API error payloads before rendering.
- Preserve source precision reasonably: e.g., rounded displayed temperatures and winds; do not imply arbitrary accuracy.
- `wind_direction_10m` represents the direction wind **comes from**. If drawing movement-direction arrows, rotate by 180 degrees and document/test this transform.
- Weather time entries displayed in the selector must match existing hourly data indices. If "Latest" is offered, define it precisely as the provider's `current` data where appropriate and restrict unavailable modes (such as precipitation if only `hourly`) to a real available hourly interval.
- Treat hourly precipitation amount as the provider-defined hourly accumulation, not an instantaneous measurement. The UI must state the correct period.

### 5.2 Commercial-use gate

The project must comply with applicable provider terms. Do not assume Open-Meteo's free noncommercial tier is valid for every deployment. If actual website purpose, usage, or traffic exceeds free-tier terms, flag the restriction and provide a configurable provider upgrade path; do not silently circumvent rate limits. Avoid baking transient quotas into application logic without verifying documentation.

---

## 6. Weather modes and rendering

| Mode key | Source variable(s) | Default UI label | Presentation |
|---|---|---|---|
| `temperature` | `temperature_2m` | Temperature (°C) | Categorical/continuous legend plus truthful numeric sample values |
| `apparent-temperature` | `apparent_temperature` | Feels-like temperature (°C) | Similar sample rendering and legend |
| `wind` | `wind_speed_10m`, `wind_direction_10m` | Wind (km/h) | Accessible speed values plus arrows with correct direction semantics |
| `rain` | Hourly `precipitation` | Hourly precipitation (mm) | Rain amounts, hourly interval, and legend |
| `radar` (optional) | RainViewer tile metadata | Recent radar | Past radar frames with exact frame timestamps and attribution |

### 6.1 Overlay constraints

- Use a dedicated Leaflet `LayerGroup` or equivalent; own only weather layers.
- Keep a single active weather mode. Remove obsolete weather symbols before drawing another mode.
- Maintain barangay boundaries and click target access. Do not block pointer events intended for polygons/facility markers. Set pane ordering appropriately for the current map.
- Do not remove or restyle unrelated GIS layers by side effect. If weather temporarily suppresses conflicting thematic fills, remember and restore the **prior** visibility/state on exit.
- Do not recenter, change zoom, clear search results, or reset selected feature/navigation state when weather is enabled or switched.
- If the map has expensive marker counts, use density/decluttering and efficient layer updates instead of constantly rebuilding unrelated map content.
- Provide legend scales aligned with actually displayed data and units. Do not use a misleading fixed scale without documenting its range.

### 6.2 Required UI states

- **Disabled:** No weather overlay and no weather API fetch/auto-refresh.
- **Loading:** Accessible busy indication; retain existing base map and controls.
- **Ready:** Source, valid time, retrieval time, units, and legend shown.
- **Empty:** Clear "weather data not available for selected time/location" indication.
- **Network/API failure:** Nonfatal message and explicit retry/refresh option.
- **Rate limited:** Explain temporary unavailability without a tight retry loop.
- **Stale cached result:** Keep usable display only if visibly marked **Stale** with its actual valid/retrieved timestamps.
- **Optional radar not available:** Explain unavailability, hide/disable the optional option as appropriate, and keep mandatory modes operational.

### 6.3 Forecast-time selector

Offer only valid times returned by the API. Compact shortcuts such as "Latest", "+1 hr", "+3 hr", "+6 hr" are acceptable **only** if mapped to actual timestamps with accurate availability and clear nearest-hour behavior. Never display a time when all requested mode values are missing. Prefer a single normalized selection state shared across modes where timestamps intersect, and fall back predictably when they do not.

---

## 7. Caching, requests, refresh, and resilience

Use an initial **20-minute cache TTL** configurable via local weather JSON, subject to actual provider response/update behavior. A cached response's TTL and the forecast's **valid time** are different concepts.

**Required mechanics:**

1. Do not fetch until the visitor enables Weather.
2. Deduplicate concurrent identical requests. Cache normalized successful responses by provider, coordinate batch, requested variables, and forecast/timezone parameters.
3. Reuse the same response when visitors switch between the four modes or forecast times.
4. Refresh only while weather is enabled and the document is visible; do not keep active polling in hidden tabs. Stop when disabled/destroyed.
5. Protect against overlapping requests. Use request IDs and/or AbortController so older responses cannot overwrite newer state.
6. Abort outstanding requests on teardown and when an obsolete request should be canceled.
7. Apply a bounded timeout (initial suggestion: 10 seconds), no unbounded retries, and backoff/cooldown for 429/5xx; respect `Retry-After` if supplied.
8. Refresh button must have a sensible cooldown and must not generate repeated requests on rapid clicks.
9. Handle offline mode, CORS/API failures, malformed responses, clock issues, and absent variables without throwing uncaught exceptions.
10. Use browser memory by default. Avoid persistent caching of stale weather forecasts unless justified and documented.
11. Do not expose provider API tokens or user identifiers in query strings, URLs, logs, or error reports.

Include tests for cache hits, mode switching, timing boundaries, stale data, timeout, deduplication, race conditions, missing values, and teardown.

---

## 8. Optional radar gate (RainViewer)

**Do not block core V3.5 on radar.** The radar task becomes eligible only if all conditions hold:

1. Current official provider API/terms allow the project's use.
2. Recent/past imagery actually covers Mapandan with useful regional accuracy.
3. Correct provider frame metadata and tiles can be requested by the browser under deployment/CSP restrictions.
4. Attribution is displayed and native tile zoom constraints are honored.
5. The UI clearly states frame time, update recency, and "recent/past radar" rather than implying a live nowcast or forecast.
6. API failure or missing local coverage degrades gracefully, leaving core weather modes intact.

If any gate fails, do **not** implement a fake radar layer. Record the exact blocker and leave a clean optional integration seam for later.

---

## 9. UI, accessibility, and responsive requirements

Implement a **Weather** section in the existing map-layer panel (or the project's consistent equivalent). Provide:

- Mode selection using accessible radio buttons or equivalent single-select controls.
- Weather on/off and a refresh control with status feedback.
- Forecast time picker that announces the chosen time and has disabled/unavailable states.
- Legend, weather-provider attribution, **valid at** timestamp, **retrieved at** timestamp, and stale marker when needed.
- A visible disclaimer that readings are model estimates/forecasts and may differ from conditions at individual barangays.
- PAGASA official weather information link: <https://www.pagasa.dost.gov.ph/>.
- Keyboard focus order, accessible names, high-contrast status/legend, `aria-live` for status changes as appropriate, and reduced-motion support for any animations.
- Mobile-safe control layout without covering important map controls, facility popups, or route UI.

Color must not be the only carrier of meaning: sample values, directional indicators, text labels, and accessible alternatives are required.

### 9.1 Conceptual control mockup

```text
Weather [off/on]
  ( ) Temperature (°C)
  ( ) Feels-like temperature (°C)
  ( ) Wind speed/direction (km/h)
  ( ) Hourly precipitation (mm)
  ( ) Recent radar [optional]

Forecast time: [Latest / available provider times]
[Refresh]  [Loading / Updated / Stale / Error]
Legend: ...
Source: Open-Meteo | Valid: YYYY-MM-DD HH:mm PHT
Retrieved: YYYY-MM-DD HH:mm PHT
Model estimate / forecast; consult PAGASA for official warnings.
```

Do not hardcode the illustrative timestamps above into the app.

---

## 10. Localization requirements

Add or reuse the site's existing localization keys for at least:

- Weather Layers / Weather / Enable Weather / Disable Weather
- Temperature / Feels-like temperature / Wind speed / Wind direction / Hourly precipitation / Recent radar
- Forecast time / Latest / Refresh / Loading / Updated / Last updated / Valid at / Retrieved at
- °C / km/h / mm and time-related unit labels
- Model estimate / Hourly forecast / Source / Stale data / No data / Could not load / Try again / Rate limited
- Accessibility names and provider/safety disclaimer

**English and Filipino examples:**

| English | Filipino |
|---|---|
| Weather Layers | Mga Layer ng Panahon |
| Temperature | Temperatura |
| Feels-like Temperature | Nararamdamang Temperatura |
| Wind Speed | Bilis ng Hangin |
| Wind Direction | Direksiyon ng Hangin |
| Hourly Rainfall | Pag-ulan Bawat Oras |
| Recent Radar | Kamakailang Radar |
| Last Updated | Huling Na-update |
| Weather Data Unavailable | Walang Makuhang Datos ng Panahon |

For **Pangasinan**, follow the site's established dictionary and translation review practices. Prefer a verified translation or an explicit English fallback over invented technical terminology. Keep variable keys consistent across all languages. Use a stable PHT timezone across localized pages; do not translate or alter measurement values.

---

## 11. Compatibility and safety invariants

The agent **must assert and test** that:

- The Leaflet map still loads when weather is disabled or its JavaScript/API fails.
- Existing search, barangay selection, polygon click events, and facility information remain accessible.
- Existing layer toggles and V3.3 choropleth styling remain correct, or temporary suppression is restored exactly.
- V3.4 route/navigation state (if present) is never reset or presented as weather-safe.
- A weather map has no claim of flood depth, evacuation safety, or road passability.
- The site remains statically deployable and its offline/isolated build does not require internet.
- The no-weather load path makes **zero** requests to weather services.
- External use respects CSP and provider attribution/terms.

Security/reliability: escape untrusted data before injection into DOM or tooltip HTML; do not trust API content as markup; avoid building HTML from unknown text fields; constrain external URLs and tile domains to verified providers.

---

## 12. Implementation phases and execution gates

### Phase A — Discovery and decisions

- Map actual repository files and current GIS control flow.
- Confirm provider API and licensing/usage fit.
- Create a short decision log for deviations.
- Identify test environments and browser smoke-test method.

**Gate:** integration plan is repository-specific; build/network boundaries are understood.

### Phase B — Static config and weather foundation

- Add configuration with schema and safe validation.
- Implement HTTP client, parser/normalizer, correct timestamps, units, and error paths.
- Implement cache, deduplication, abort/race guards, and refresh lifecycle.
- Add unit tests with deterministic mocked API responses.

**Gate:** weather data is trustworthy and testable independent of map rendering.

### Phase C — Core map integration

- Add isolated Leaflet weather overlay group and accessible controls.
- Implement temperature, apparent temperature, wind, and hourly precipitation.
- Add truthful legends, source/timestamp labels, and mode/time selection.
- Ensure map event propagation and pane ordering preserve existing controls.

**Gate:** all four modes render in a real browser without regressing existing map functionality.

### Phase D — Localization and robust user experience

- Add English, Filipino, and Pangasinan labels/fallbacks.
- Add loading/error/no-data/stale/rate-limit states and responsive styling.
- Confirm accessibility, keyboard interaction, and mobile panel usability.

**Gate:** data states and translated views function across supported routes.

### Phase E — Optional radar feasibility and implementation

- Review current RainViewer terms and metadata/tile constraints.
- Test Mapandan coverage and recency.
- Implement only if justified; otherwise log deferment without false claims.

**Gate:** optional radar is either compliant and functional or explicitly deferred.

### Phase F — Regression and release evidence

- Run all existing repository tests and any newly added suites.
- Run isolated/offline build: `python build.py --isolated --offline` if present; otherwise locate and run the repository's equivalent, and document the actual command.
- Verify built output includes the weather assets and translated labels.
- Perform a browser smoke test with and without API connectivity and record results.
- Report changed files, decisions, provider restrictions, tests, screenshots/notes if appropriate, and unresolved issues.

**Gate:** no unverified completion claims; final report is evidence-based.

---

## 13. Acceptance tests and evidence matrix

The agent should implement these tests at the appropriate unit, integration, build, and browser layers.

| ID | Scenario | Expected result |
|---|---|---|
| W-001 | Load GIS with weather disabled | Original map works; zero weather API requests |
| W-002 | Enable Temperature | °C values render, explicitly marked model data with source and valid time |
| W-003 | Enable Feels-like | Uses `apparent_temperature`; never labeled official heat index |
| W-004 | Enable Wind | Speed displayed in km/h; arrow semantics match source wind-from degrees |
| W-005 | Enable Rain | Displays actual hourly precipitation values and correct time interval |
| W-006 | Change forecast selection | Values correspond to the selected returned provider timestamp |
| W-007 | Switch weather modes repeatedly | Reuses cached response; no unnecessary re-fetch or overlay accumulation |
| W-008 | API timeout/offline/bad response | Graceful nonfatal error; GIS remains usable |
| W-009 | Rate limit/429 | Backoff/cooldown; no retry storm; actionable status |
| W-010 | Older request resolves late | No stale result overrides new selection |
| W-011 | Cached data ages past TTL | Clearly marked Stale if retained; correct timestamps shown |
| W-012 | Disable Weather | Weather overlays/refresh stop; no unrelated map state changes |
| W-013 | Select barangay and facility | Polygons and markers remain clickable and meaningful |
| W-014 | Existing GIS thematic layers | Correct visibility/restoration and click behavior |
| W-015 | Existing navigation, if present | Prior route/destination intact; no weather-safety assertion |
| W-016 | Optional radar absent/unavailable | Clear fallback, core four modes unaffected |
| W-017 | Keyboard and mobile navigation | Controls usable, labels understandable, not obscuring GIS |
| W-018 | EN/FIL/PAG pages | Localization works with verified/fallback strings |
| W-019 | Offline/isolated static build | Completes without live weather requests |
| W-020 | Generated output/deployment | Weather JS and CSS delivered on actual deployed GIS path |
| W-021 | Duplicate model grid readings | Not falsely presented as independent observations |
| W-022 | Missing provider values/partial arrays | No invented zeros and no malformed legend/uncaught exception |

**Testing guidance:** Mock response payloads for success, multiple coordinate batches, missing arrays, timestamps near midnight in PHT, 429, 5xx, malformed responses, timeout, and aborted requests. Use network interception during browser tests to assert zero requests before activation. Check computed map pane order and inspect click behavior rather than relying solely on snapshots.

### Suggested commands, subject to repository inspection

```bash
python build.py --isolated --offline
# Then run existing Python/JS test commands from the repository.
# Run added unit and browser suites with the existing test runner.
```

Do not introduce a new package manager or framework solely for this feature if established tooling suffices.

---

## 14. Change management and agent communication

### Commit/change discipline

- Keep changes scoped to the GIS/weather feature, translations, build wiring, and tests.
- Prefer small, reversible changes. Avoid unrelated refactors, dependency upgrades, or redesigns.
- Preserve public contracts of existing GIS config and layer types.
- Document additional third-party requests or CSP modifications.
- If live provider verification is unavailable in the execution environment, build and test using mocks, report this limitation, and do not assert that live radar or weather availability has been verified.

### Required final agent report structure

Provide all of the following at the end of implementation:

1. **Outcome:** core complete, partial, or blocked; radar implemented/deferred and why.
2. **Actual changed files:** concise summary of each significant modification.
3. **Architecture summary:** how the controller attaches to existing Leaflet and how the runtime-only data flow works.
4. **Data integrity:** exact provider fields, sample locations, timestamp interpretation, and wind-arrow convention.
5. **Tests executed:** exact commands, pass/fail counts or outputs, browser checks, and unavailable checks.
6. **Compatibility evidence:** barangay/facilities, V3.3 thematic layers, V3.4 navigation if present, EN/FIL/PAG views.
7. **License/terms check:** provider terms consulted and any commercial-use/restriction decisions.
8. **Known limitations and next steps:** factual blockers, missing coverage, and optional radar status.

Do not state "done" merely because code compiles. The release gate is satisfied only when the mandatory behaviors are demonstrated with evidence.

---

## 15. Decision defaults when repository details differ

Use these defaults unless an established project standard is clearly better:

- **Provider:** Open-Meteo for model/forecast data.
- **Refresh:** every 20 minutes while enabled and tab visible; with cooldowns and cache reuse.
- **Forecast horizon:** up to 2 days, constrained to actual data returned.
- **Initial state:** weather disabled.
- **UI integration:** add section to existing layers control; do not replace other panels.
- **Overlay representation:** sparse, labeled samples; no artificial hyperlocal gradient.
- **Radar:** optional and separate; do not make core delivery dependent on it.
- **Units:** °C, km/h, and mm with meaningful time interval.
- **Time:** Asia/Manila / PHT.
- **Fallbacks:** readable no-data/error state and intact base GIS.
- **Localization:** English/Filipino/Pangasinan with verified/fallback terms.
- **Build:** self-contained static output; no external request during build.

If there is a conflict between this specification and the real repository, prioritize maintaining backward compatibility and record the deviation.

---

## 16. Final delivery checklist

- [ ] Actual repository structure and GIS integration points reviewed.
- [ ] Provider contracts/terms and any commercial-use concerns checked.
- [ ] Validated weather config included in static output.
- [ ] Isolated weather controller attaches to existing map.
- [ ] Weather disabled by default; no initial weather fetch.
- [ ] Temperature visualization is accurate and time-stamped.
- [ ] Feels-like visualization is accurately named.
- [ ] Wind visualization has correct speed/direction interpretation.
- [ ] Hourly precipitation has correct accumulation interval and valid time.
- [ ] Forecast times map to actual data, not invented labels.
- [ ] Cache, deduplication, throttling, abort/timeout, and stale-state logic tested.
- [ ] One weather overlay active; no unintended base GIS changes.
- [ ] EN/FIL/PAG controls with verified translations/fallbacks.
- [ ] Mobile/keyboard/accessibility review passed.
- [ ] Provider attribution, disclaimer, and PAGASA link shown.
- [ ] Optional radar supported correctly or explicitly deferred.
- [ ] Offline build successful without weather-network access.
- [ ] Regression tests and browser smoke tests completed.
- [ ] Final agent report contains verified evidence and limitations.

---

**Release target:** Better Mapandan GIS **V3.5 core Weather Explorer**, with optional recent radar as a separate gated enhancement.  
**Implementation status at authorship:** specification only; code and deployment have not been modified by this document.
