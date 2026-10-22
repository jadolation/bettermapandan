/* Maintainer-configured explorer with bounded, same-origin layer loading. */
/*! Inline glyphs: ISC License, Copyright (c) 2026 Lucide Icons and Contributors.
 * Permission to use, copy, modify, and/or distribute this software for any
 * purpose with or without fee is hereby granted, provided that the above
 * copyright notice and this permission notice appear in all copies.
 * THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 * WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 * ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 * WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 * ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 * OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 */
(function () {
  "use strict";
  var TYPES = ["inline-geojson", "geojson", "raster-image-overlay", "reference", "choropleth"];
  var STAT_COLORS = ["#31875A", "#E8C44D", "#C84B47"], MISSING_COLOR = "#A6ADB4";
  function quantiles(values) {
    var sorted = values.filter(function (v) { return typeof v === "number" && Number.isFinite(v) && v >= 0; }).sort(function (a, b) { return a - b; });
    if (!sorted.length) return [];
    var distinct = Array.from(new Set(sorted)), ends = [];
    if (distinct.length <= 3) ends = distinct;
    else {
      [1, 2, 3].forEach(function (n) { var end = sorted[Math.ceil(sorted.length * n / 3) - 1]; if (ends.indexOf(end) < 0) ends.push(end); });
    }
    return ends.map(function (end, i) {
      var start = i ? sorted.find(function (v) { return v > ends[i - 1]; }) : sorted[0];
      return { min: start, max: end, color: STAT_COLORS[ends.length === 2 && i === 1 ? 2 : i] };
    });
  }
  function statisticColor(value, classes) {
    var entry = typeof value === "number" && Number.isFinite(value) && classes.find(function (c) { return value >= c.min && value <= c.max; });
    return entry ? entry.color : MISSING_COLOR;
  }
  function matchingReferences(project, filters) {
    return project.references.filter(function (ref) {
      return ["source", "year", "status"].every(function (key) {
        return !filters[key] || String(ref[key] == null ? "unknown" : ref[key]) === filters[key];
      });
    });
  }
  function filteredProjects(data, filters) {
    var seen = new Set();
    return data.projects.filter(function (project) {
      var refs = matchingReferences(project, filters);
      if (data.project_coverage) refs = refs.filter(function (ref) { var coverage = data.project_coverage.sources[ref.source]; return coverage && coverage.supported === true; });
      if (seen.has(project.project_id) || !refs.length) return false;
      seen.add(project.project_id); return true;
    });
  }
  function projectInBarangay(project, filters, gid) {
    return matchingReferences(project, filters).some(function (ref) { return ref.barangay_gids.indexOf(gid) >= 0; });
  }
  function validateStatistics(data) {
    function fail() { throw Error("Invalid barangay statistics"); }
    function string(v) { return typeof v === "string" && v.length > 0 && v.length <= 2000 && !/[\x00-\x1f]/.test(v); }
    function count(v) { return Number.isSafeInteger(v) && v >= 0; }
    if (!data || data.schema_version !== 1 || data.municipality_psgc !== "0105528000" || !data.population || data.population.year !== 2024 || !Array.isArray(data.population.provenance) || !data.barangays || Array.isArray(data.barangays) || !Array.isArray(data.projects) || data.projects.length > 10000 || !data.project_coverage || !data.project_coverage.sources) fail();
    var gids = Object.keys(data.barangays), ids = new Set(), coverage = data.project_coverage.sources;
    if (!Object.keys(coverage).length || Object.keys(coverage).length > 4) fail();
    Object.keys(coverage).forEach(function (source) { if (["dpwh", "dilg", "coa", "philgeps"].indexOf(source) < 0 || !coverage[source] || typeof coverage[source].supported !== "boolean") fail(); });
    if (gids.length !== 15) fail();
    gids.forEach(function (gid) {
      var b = data.barangays[gid], p = b && b.population, projects = b && b.projects;
      if (!/^0105528\d{3}$/.test(gid) || !string(b.name) || !p || (p.count !== null && !count(p.count)) || p.year !== 2024 || !string(p.status) || (p.share !== null && (typeof p.share !== "number" || !Number.isFinite(p.share) || p.share < 0 || p.share > 1)) || !projects || (projects.count !== null && !count(projects.count)) || !Array.isArray(projects.ids) || !string(projects.status)) fail();
    });
    data.projects.forEach(function (project) {
      if (!project || !string(project.project_id) || ids.has(project.project_id) || !string(project.name) || !Array.isArray(project.barangay_gids) || new Set(project.barangay_gids).size !== project.barangay_gids.length || !project.barangay_gids.every(function (gid) { return gids.indexOf(gid) >= 0; }) || !Array.isArray(project.references) || !project.references.length || project.references.length > 1000) fail();
      ids.add(project.project_id);
      project.references.forEach(function (ref) {
        if (!ref || !Object.hasOwn(data.project_coverage.sources, ref.source) || (ref.year !== null && (!Number.isInteger(ref.year) || ref.year < 1900 || ref.year > 2200)) || !string(ref.status) || !Array.isArray(ref.barangay_gids) || !ref.barangay_gids.every(function (gid) { return project.barangay_gids.indexOf(gid) >= 0; })) fail();
      });
    });
    gids.forEach(function (gid) {
      var p = data.barangays[gid].projects;
      if (new Set(p.ids).size !== p.ids.length || !p.ids.every(function (id) { return ids.has(id); }) || (p.count !== null && p.count !== p.ids.length)) fail();
      var assigned = data.projects.filter(function (project) { return project.barangay_gids.indexOf(gid) >= 0; });
      if (assigned.length !== p.ids.length || !assigned.every(function (project) { return p.ids.indexOf(project.project_id) >= 0; })) fail();
    });
    return data;
  }
  var PANES = { physical: 250, hazards: 300, administrative: 400, infrastructure: 450, facilities: 500 };
  var STATUS_COLORS = { completed: "#287943", ongoing: "#b66b08", not_started: "#c0392b", stopped: "#c0392b", unknown: "#737373" };
  var ICONS = {
    // Vetted static nodes from https://github.com/lucide-icons/lucide/tree/main/icons.
    "hard-hat": '<path d="M10 10V5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v5"/><path d="M14 6a6 6 0 0 1 6 6v3"/><path d="M4 15v-3a6 6 0 0 1 6-6"/><rect x="2" y="15" width="20" height="4" rx="1"/>',
    "home": '<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-6a2 2 0 0 1 2.582 0l7 6A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "graduation-cap": '<path d="M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.832l8.57 3.908a2 2 0 0 0 1.66 0z"/><path d="M22 10v6"/><path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"/>',
    "heart-pulse": '<path d="M2 9.5a5.5 5.5 0 0 1 9.591-3.676.56.56 0 0 0 .818 0A5.49 5.49 0 0 1 22 9.5c0 2.29-1.5 4-3 5.5l-5.492 5.313a2 2 0 0 1-3 .019L5 15c-1.5-1.5-3-3.2-3-5.5"/><path d="M3.22 13H9.5l.5-1 2 4.5 2-7 1.5 3.5h5.27"/>',
    "shield": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>',
    "landmark": '<path d="M10 18v-7"/><path d="M11.119 2.205a2 2 0 0 1 1.762 0l7.84 3.846A.5.5 0 0 1 20.5 7h-17a.5.5 0 0 1-.22-.949z"/><path d="M14 18v-7"/><path d="M18 18v-7"/><path d="M3 22h18"/><path d="M6 18v-7"/>',
    "map-pin": '<path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/>',
    "layers": '<path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83z"/><path d="M2 12a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 12"/><path d="M2 17a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 17"/>'
  };
  function categoryColor(category, semanticRole, statusKey) {
    if (semanticRole === "dpwh_project") return Object.hasOwn(STATUS_COLORS, statusKey) ? STATUS_COLORS[statusKey] : STATUS_COLORS.unknown;
    var cat = (category || "").toLowerCase();
    if (cat === "listed-evacuation") return "#b66b08";
    if (/school/.test(cat)) return "#2563eb";
    if (/health|medical|hosp/.test(cat)) return "#c0392b";
    if (/police|fire/.test(cat)) return "#1e3a8a";
    if (/barangay/.test(cat)) return "#0f4c3a";
    return "#2d6b1f";
  }
  function iconSvg(iconName, color, size) {
    var safeColor = /^#[0-9a-f]{6}$/i.test(color) ? color : "#737373";
    var safeSize = Number.isFinite(size) && size >= 12 && size <= 36 ? size : 20;
    return '<svg viewBox="0 0 24 24" width="' + safeSize + '" height="' + safeSize + '" fill="none" stroke="' + safeColor + '" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' + (Object.hasOwn(ICONS, iconName) ? ICONS[iconName] : ICONS["map-pin"]) + "</svg>";
  }
  function categoryIcon(category, semanticRole) {
    var cat = (category || "").toLowerCase();
    if (semanticRole === "dpwh_project") return "hard-hat";
    if (cat === "listed-evacuation") return "home";
    if (/school/.test(cat)) return "graduation-cap";
    if (/health|medical|hospital/.test(cat)) return "heart-pulse";
    if (/police|fire/.test(cat)) return "shield";
    if (/barangay/.test(cat)) return "landmark";
    return "map-pin";
  }
  function categoryKey(icon) {
    return { home: "Shelter", "graduation-cap": "School", "heart-pulse": "Health", shield: "Emergency", landmark: "Barangay", "hard-hat": "Project", layers: "Shared" }[icon] || "Default";
  }
  function opacity(value) { return typeof value === "number" && Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0.65; }
  function spatialBarangay(s, f) {
    return s.layer.available === true && !!s.overlay && !!f.geometry && ["Polygon", "MultiPolygon"].indexOf(f.geometry.type) >= 0 &&
      (s.layer.semantic_role === "barangay_boundary" || (s.layer.semantic_role === "barangay_reference_geometry" && s.visible));
  }
  function defaultEntries(states, filledBoundary) {
    states = states.filter(function (s) {
      return s.layer.available === true && s.layer.type !== "reference" && s.overlay && (s.visible || s === filledBoundary);
    }).map(function (s) {
      return Object.assign({}, s, { features: s.features.filter(function (f) { return f.geometry && s.items.has(f); }), original: s });
    });
    var projects = new Set(), barangays = new Map(), facilities = new Set();
    states.forEach(function (s) { s.features.forEach(function (f) {
       var p = f.properties;
       if (s.layer.data_key === "GIS_FACILITIES") facilities.add(p.id);
      if (s.layer.semantic_role === "dpwh_project" && typeof p.project_id === "string" && p.project_id) projects.add(p.project_id);
      if (p.gid && spatialBarangay(s, f) && (!barangays.has(String(p.gid)) || s.layer.semantic_role === "barangay_boundary")) barangays.set(String(p.gid), f);
    }); });
    var usedProjects = new Set(), usedBarangays = new Set(), entries = [];
    states.forEach(function (s) { s.features.forEach(function (f) {
      var p = f.properties, project = typeof p.project_id === "string" && p.project_id;
      if (project && projects.has(project)) {
        if (s.layer.semantic_role !== "dpwh_project" || usedProjects.has(project)) return;
        usedProjects.add(project);
      }
      if (p.gid && barangays.has(String(p.gid))) {
        if (barangays.get(String(p.gid)) !== f || usedBarangays.has(String(p.gid))) return;
        usedBarangays.add(String(p.gid));
      }
      // Optional coarse source geometry is not a second directory when switched off.
      if (s.layer.semantic_role === "barangay_reference_geometry" && !s.visible) return;
       if (p.canonical_facility_id && facilities.has(p.canonical_facility_id)) return;
       entries.push({ feature: f, state: s.original });
    }); });
    return entries;
  }
  function projectUrl(p, lang, origin) {
    var prefix = lang === "fil" || lang === "pag" ? "/" + lang : "";
    function encodeId(value) { return encodeURIComponent(value).replace(/[!'()*]/g, function (c) { return "%" + c.charCodeAt(0).toString(16).toUpperCase(); }); }
    if (typeof p.project_url === "string") {
      try {
        var u = new URL(p.project_url, origin);
        if (u.origin === origin && !u.username && !u.password && !/[\\\x00-\x20]/.test(p.project_url) &&
            /^\/(?:fil\/|pag\/)?transparency\/(?:projects\/|infrastructure\/)$/.test(u.pathname)) {
          if (/\/projects\/$/.test(u.pathname) && typeof p.project_id === "string" && p.project_id && !u.hash &&
              u.searchParams.size === 1 && u.searchParams.get("project") === p.project_id) return u.pathname + u.search;
          if (/\/infrastructure\/$/.test(u.pathname) && !u.search && typeof p.source_transaction_id === "string" &&
              u.hash.indexOf("#dpwh-project-") === 0 && decodeURIComponent(u.hash.slice(14)) === p.source_transaction_id) return u.pathname + u.hash;
        }
      } catch (error) { /* Fall back only to explicit source/canonical IDs. */ }
    }
    if (typeof p.project_id === "string" && p.project_id.trim()) return prefix + "/transparency/projects/?project=" + encodeId(p.project_id);
    if (typeof p.source_transaction_id === "string" && p.source_transaction_id) return prefix + "/transparency/infrastructure/#dpwh-project-" + encodeId(p.source_transaction_id);
    return null;
  }
  function escapeHtml(v) {
    return String(v == null ? "" : v).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function validPoint(p) {
    return Array.isArray(p) && p.length === 2 && p.every(function (n) {
      return typeof n === "number" && Number.isFinite(n);
    }) && Math.abs(p[0]) <= 180 && Math.abs(p[1]) <= 90;
  }
  function validBounds(b) {
    return b && validPoint([b.west, b.south]) && validPoint([b.east, b.north]) && b.west < b.east && b.south < b.north;
  }
  function allowed(l) {
    return !!l && l.enabled === true && l.available === true && TYPES.indexOf(l.type) >= 0;
  }
  function assetUrl(raw, base, origin) {
    if (typeof raw !== "string" || /[%\\\x00-\x20]/.test(raw) || /(^|\/)\.\.?(\/|$)/.test(raw)) throw Error("Unsafe URL");
    var u = new URL(raw, base);
    if (u.origin !== origin || u.username || u.password || u.search || u.hash || !/^https?:$/.test(u.protocol) || /%/.test(u.pathname) ||
        !/^\/assets\/gis\/.+/.test(u.pathname)) throw Error("Asset outside GIS directory");
    return u.href;
  }
  function records(payload) {
    var rows = Array.isArray(payload) ? payload : payload && payload.type === "FeatureCollection" ? payload.features : null;
    if (!Array.isArray(rows) || rows.length > 10000) throw Error("Invalid collection");
    var count = 0;
    function point(p) { return ++count <= 100000 && validPoint(p); }
    function line(c, min) { return Array.isArray(c) && c.length >= min && c.every(point); }
    function polygon(c) { return Array.isArray(c) && c.length > 0 && c.every(function (r) {
      return line(r, 4) && JSON.stringify(r[0]) === JSON.stringify(r[r.length - 1]);
    }); }
    function geometry(g) {
      if (g === null) return true;
      if (!g) return false;
      var c = g.coordinates;
      if (g.type === "Point") return point(c);
      if (g.type === "MultiPoint") return line(c, 1);
      if (g.type === "LineString") return line(c, 2);
      if (g.type === "MultiLineString") return Array.isArray(c) && c.length > 0 && c.every(function (v) { return line(v, 2); });
      if (g.type === "Polygon") return polygon(c);
      if (g.type === "MultiPolygon") return Array.isArray(c) && c.length > 0 && c.every(polygon);
      return false;
    }
    return rows.map(function (row) {
      if (!row || typeof row !== "object") throw Error("Invalid record");
      var f = row.type === "Feature" ? row : { type: "Feature", geometry: null, properties: row };
      if (!f.properties || typeof f.properties !== "object" || !geometry(f.geometry)) throw Error("Invalid geometry");
      return f;
    });
  }
  function exactGroups(features) {
    var groups = new Map();
    features.forEach(function (f) {
      if (!f.geometry || f.geometry.type !== "Point") return;
      var key = JSON.stringify(f.geometry.coordinates);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(f);
    });
    return groups;
  }
  if (typeof module !== "undefined" && module.exports) module.exports = {
    allowed: allowed, assetUrl: assetUrl, records: records, exactGroups: exactGroups,
    validBounds: validBounds, validPoint: validPoint, escapeHtml: escapeHtml,
    opacity: opacity, projectUrl: projectUrl, defaultEntries: defaultEntries, panes: PANES, statusColors: STATUS_COLORS,
    iconSvg: iconSvg, categoryIcon: categoryIcon, categoryColor: categoryColor,
    quantiles: quantiles, statisticColor: statisticColor, matchingReferences: matchingReferences,
    filteredProjects: filteredProjects, validateStatistics: validateStatistics,
    projectInBarangay: projectInBarangay,
  };
  if (typeof document === "undefined") return;
  function init() {
    var page = document.getElementById("gis-page");
    if (!page || page.dataset.initialized) return;
    page.dataset.initialized = "true";
    var manifest = window.GIS_LAYERS || {}, meta = manifest.metadata || {};
    var lang = document.documentElement.lang || "en", states = [], groups = new Map(), map = null, returnFocus;
    var selectedFeature = null, selectedItem = null, selectionRequest = 0;
    var statistics = null, statisticsPromise = null, metricState = null, metricClasses = [], metricValues = {}, projectMatches = [];
    var projectFilters = { source: "", year: "", status: "" }, filterControls = {};
    function node(id) { return document.getElementById("gis-" + id); }
    var residentData = window.GIS_RESIDENTS || {}, residentLabels = residentData.labels || {};
    function text(key) { return residentLabels[key === "categoryShelter" ? "listedEvacuation" : key] || page.dataset[key] || key; }
    function statusLabel(key) { return text("status" + (Object.hasOwn(STATUS_COLORS, key) ? key : "unknown").replace(/(^|_)([a-z])/g, function (_, gap, c) { return c.toUpperCase(); })); }
    function local(v) { return v && typeof v === "object" ? String(v[lang] || v.en || "") : String(v == null ? "" : v); }
    function el(tag, value, parent) {
      var n = document.createElement(tag); if (value != null) n.textContent = value; if (parent) parent.appendChild(n); return n;
    }
    function announce(key) { node("map-status").textContent = text(key); }
    node("workspace").hidden = false;
    if (meta.evacuation_counts) {
      var counts = meta.evacuation_counts;
      el("p", text("counts") + ": " + [counts.listings, counts.spatial_locations, counts.unresolved_listings, counts.unique_coordinates].join(" / "), node("explore-panel"));
    }
    function activateTab(id, focus) {
      ["explore", "layers"].forEach(function (key) {
        var active = key === id, tab = node(key + "-tab");
        tab.setAttribute("aria-selected", String(active)); tab.tabIndex = active ? 0 : -1;
        node(key + "-panel").hidden = !active;
        if (active && focus) tab.focus();
      });
    }
    ["explore", "layers"].forEach(function (id, index) {
      var tab = node(id + "-tab");
      tab.onclick = function () { activateTab(id, false); };
      tab.addEventListener("keydown", function (e) {
        var target;
        if (e.key === "ArrowLeft" || e.key === "ArrowRight") target = index ? "explore" : "layers";
        if (e.key === "Home") target = "explore";
        if (e.key === "End") target = "layers";
        if (target) { e.preventDefault(); activateTab(target, true); }
      });
    });
    function resize() {
      var bar = document.querySelector(".mobile-action-bar");
      var clearance = bar && bar.getClientRects().length ? Math.ceil(bar.getBoundingClientRect().height) + 8 : 8;
      page.style.setProperty("--gis-sticky-clearance", clearance + "px");
      var column = page.querySelector(".gis-map-pane");
      if (column) page.style.setProperty("--gis-column-height", Math.ceil(column.getBoundingClientRect().height) + "px");
      if (map) map.invalidateSize();
    }
    window.addEventListener("resize", resize);
    if (typeof ResizeObserver !== "undefined") {
      var observer = new ResizeObserver(resize);
      observer.observe(node("map"));
      var column = page.querySelector(".gis-map-pane");
      if (column) observer.observe(column);
      var sticky = document.querySelector(".mobile-action-bar");
      if (sticky) observer.observe(sticky);
    }
    resize();
    var assetBase = String(meta.asset_base == null ? page.dataset.assetBase || "." : meta.asset_base);
    var base = new URL(assetBase.replace(/\/*$/, "/"), location.href).href;
    var home = validPoint(meta.default_map_center) ? meta.default_map_center : [120.455, 16.03];
    var zoom = Number.isFinite(meta.default_zoom) && meta.default_zoom >= 0 && meta.default_zoom <= 19 ? meta.default_zoom : 14;
    if (typeof L === "undefined") { node("map").hidden = true; announce("libraryError"); }
    else try {
      map = L.map("gis-map").setView([home[1], home[0]], zoom);
      Object.keys(PANES).forEach(function (key) {
        var pane = map.createPane("gis-" + key); pane.style.zIndex = String(PANES[key]);
        var rasterPane = map.createPane("gis-" + key + "-raster"); rasterPane.style.zIndex = String(PANES[key]);
        rasterPane.style.pointerEvents = "none";
      });
      var failed = false;
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }).on("tileerror", function () { failed = true; node("map-fallback").hidden = false; announce("tileError"); })
        .on("load", function () { if (!failed) { node("map-fallback").hidden = true; announce("ready"); } }).addTo(map);
      L.control.scale({ imperial: false }).addTo(map);
      [[".leaflet-control-zoom-in", "zoomIn"], [".leaflet-control-zoom-out", "zoomOut"]].forEach(function (a) {
        var c = map.getContainer().querySelector(a[0]); if (c) { c.title = text(a[1]); c.setAttribute("aria-label", text(a[1])); }
      });
      resize();
    } catch (error) { map = null; announce("mapError"); }
    node("fit").disabled = node("reset").disabled = !map;
    node("reset").onclick = function () { if (map) map.setView([home[1], home[0]], zoom); };
    function precision(p, l) {
      if (l.semantic_role === "label_anchor") return text("labelAnchor");
      var key = { source_reported: p.location_precision === "approximate" ? "approximateSource" : "sourceReported",
        plus_code_cell_center: "cellCenter", polygon_centroid: "centroid", field_observation: "fieldPosition" }[p.coordinate_method];
      return key ? text(key) : local(p.source_precision || p.location_precision || l.precision);
    }
    function name(f, s) { var p = f.properties; return local(p.name || p.title || p.project_name || p.project_id || p.id || p.gid) || s.title; }
    function featureCategory(f) { return f.properties.evacuation_id ? "listed-evacuation" : f.properties.facility_type || f.properties.category || (f.properties.gid ? "barangay" : ""); }
    function activeMetric() { return metricState && metricState.visible && metricState.loaded ? metricState : null; }
    function boundaryState() { return states.find(function (s) { return s.layer.id === "barangay-boundaries" && s.layer.semantic_role === "barangay_boundary"; }); }
    function boundaryStyle(f, s, item) {
      var active = activeMetric(), selected = item && item === selectedItem;
      return { color: selected ? "#17324D" : "#486b87", weight: selected ? 4 : s.visible ? 2 : 0,
        opacity: selected || s.visible ? 1 : 0, fillColor: active ? statisticColor(metricValues[String(f.properties.gid || f.properties.psgc)], metricClasses) : "#486b87",
        fillOpacity: active ? 0.62 : 0.08, dashArray: selected ? "5 3" : null };
    }
    function refreshBoundaries() {
      var s = boundaryState(); if (!s) return;
      s.items.forEach(function (item, f) { item.gisBaseStyle = boundaryStyle(f, s, item); item.setStyle(item.gisBaseStyle); });
      if (map && s.overlay) { if (s.visible || activeMetric()) s.overlay.addTo(map); else map.removeLayer(s.overlay); }
      updateBoundaryLabels();
    }
    function supportedScope() {
      if (!statistics) return false;
      var keys = projectFilters.source ? [projectFilters.source] : Object.keys(statistics.project_coverage.sources);
      return keys.some(function (key) { var c = statistics.project_coverage.sources[key]; return c && c.supported === true; });
    }
    function refreshMetric() {
      var s = activeMetric(); metricValues = {};
      if (s) {
        projectMatches = filteredProjects(statistics, projectFilters);
        Object.keys(statistics.barangays).forEach(function (gid) {
          var b = statistics.barangays[gid];
          metricValues[gid] = s.layer.metric === "population" ? b.population.count : supportedScope() && b.projects.count !== null
            ? projectMatches.filter(function (p) { return projectInBarangay(p, projectFilters, gid); }).length : null;
        });
      }
      metricClasses = quantiles(Object.values(metricValues)); refreshBoundaries(); refreshStatisticDetails();
      if (node("project-filters")) node("project-filters").hidden = !s || s.layer.metric !== "projects";
    }
    function referenceLabel(ref) {
      var basis = { fiscal: "yearFiscal", disclosure: "yearDisclosure", award: "yearAward", start: "yearStart", completion: "yearCompletion", unknown: "statusUnknown" };
      return [ref.source.toUpperCase(), ref.year == null ? text("statusUnknown") : String(ref.year), text(basis[ref.year_basis] || "yearReference"),
        Object.hasOwn(STATUS_COLORS, ref.status) ? statusLabel(ref.status) : ref.status_label || ref.status].join(" / ");
    }
    function refreshStatisticDetails() {
      var box = node("statistic-details"); if (!box) return;
      box.replaceChildren(); var s = activeMetric(), gid = selectedFeature && String(selectedFeature.properties.gid || selectedFeature.properties.barangay_gid || selectedFeature.properties.psgc || "");
      if (!s || !statistics.barangays[gid]) { box.hidden = true; return; }
      box.hidden = false; var b = statistics.barangays[gid]; el("h4", s.title, box);
      el("p", metricValues[gid] == null ? text("statUnavailable") : new Intl.NumberFormat(lang).format(metricValues[gid]) + " " + text(s.layer.metric === "population" ? "statPeople" : "statProjects"), box);
      if (s.layer.metric === "population") {
        el("p", String(b.population.year) + " / " + (b.population.share == null ? text("statUnavailable") : new Intl.NumberFormat(lang, { style: "percent", maximumFractionDigits: 2 }).format(b.population.share) + " " + text("statShare")), box);
        statistics.population.provenance.forEach(function (p) {
          el("p", local(p.source), box);
          try { var url = new URL(p.source_url); if (/^https?:$/.test(url.protocol) && !url.username && !url.password) { var source = el("a", text("source"), box); source.href = url.href; source.rel = "noopener"; } } catch (error) { /* Optional source URL. */ }
        });
      } else {
        el("p", text("statCoverage"), box).className = "gis-caution";
        var list = el("ul", null, box);
        projectMatches.filter(function (p) { return projectInBarangay(p, projectFilters, gid); }).forEach(function (p) {
          var li = el("li", null, list), link = el("a", p.name, li); link.href = projectUrl({ project_id: p.project_id }, lang, location.origin);
          el("small", text("projectId") + ": " + p.project_id, li);
          matchingReferences(p, projectFilters).forEach(function (ref) { el("p", referenceLabel(ref), li); if (ref.record_id) el("small", text("sourceId") + ": " + ref.record_id, li); });
        });
      }
      el("p", text("statPrecision"), box);
    }
    function selection(feature, item) {
      function highlight(target, active) {
        if (!target) return;
        if (target.setStyle) target.setStyle(active ? { weight: 4 } : target.gisBaseStyle || { weight: 2 });
        var element = target.getElement && target.getElement();
        if (element) { element.classList.toggle("gis-marker-selected", active); element.setAttribute("aria-pressed", String(active)); }
      }
      highlight(selectedItem, false);
      selectedFeature = feature; selectedItem = item;
      highlight(selectedItem, true);
      refreshBoundaries();
      updateBoundaryLabels();
      node("results").querySelectorAll("button").forEach(function (button) {
        button.setAttribute("aria-pressed", String(button.gisFeature === feature));
      });
    }
    function close() {
      selectionRequest++;
      node("details").hidden = true; selection(null, null);
      if (returnFocus && returnFocus.isConnected) {
        if (node("explore-panel").contains(returnFocus)) activateTab("explore", false);
        if (node("layers-panel").contains(returnFocus)) activateTab("layers", false);
        returnFocus.focus({ preventScroll: true });
      } else node("explore-tab").focus({ preventScroll: true });
    }
    node("close").onclick = close;
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !node("details").hidden) { e.preventDefault(); close(); }
    });
    function select(f, s, trigger, shared, navigate) {
      selectionRequest++;
      returnFocus = trigger || document.activeElement;
      selection(f, s.items.get(f));
      var box = node("detail-content"); box.replaceChildren(); el("h3", name(f, s), box);
      var p = f.properties, l = s.layer, provenance = p.provenance || {}, dl = el("dl", null, box);
      function field(key, value) { if (value != null && value !== "") { el("dt", text(key), dl); el("dd", local(value), dl); } }
      var gid = p.barangay_gid || p.gid, barangay = (residentData.barangays || {})[gid];
      var statsBox = el("section", null, box); statsBox.id = "gis-statistic-details"; refreshStatisticDetails();
      field("placeType", p.facility_type || p.highway || p.waterway || p.amenity || p.class_name || l.title);
      field("barangayName", barangay ? barangay.name : p.barangay_location);
      field("address", p.address);
      field("purpose", p.description);
      field("population", p.pop2024);
      field("scenario", l.scenario);
      function action(label, raw, parent) {
        if (typeof raw !== "string" || /[\x00-\x20]/.test(raw)) return;
        try { var url = new URL(raw, location.origin);
          if (url.username || url.password || !/^(https?:|tel:|mailto:)$/.test(url.protocol)) return;
          if (url.protocol === "tel:" && !/^tel:\+?\d{3,15}$/.test(raw)) return;
          if (url.protocol === "mailto:" && !/^mailto:[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}$/.test(raw)) return;
          var link = el("a", label, el("p", null, parent || box)); link.href = url.href; link.rel = "noopener";
        } catch (error) { /* Invalid optional contact must not break details. */ }
      }
      function officeContact(key, label) {
        var contacts = residentData.contacts || {}, office = (contacts.offices || {})[key];
        if (!office) return;
        el("h4", label || office.name, box);
        (office.phones || []).forEach(function (phone) {
          if (typeof phone === "string" && /^[+()\d .-]{3,40}$/.test(phone)) action(phone, "tel:" + phone.replace(/[^\d+]/g, ""));
        });
        if (office.email) action(office.email, "mailto:" + office.email);
        el("p", text("contactDate"), box);
      }
      if (p.evacuation_id) {
        el("h4", text("listedEvacuation"), box);
        el("p", text("availabilityUnknown"), box).className = "gis-caution";
        officeContact("mdrrmo", text("mdrrmo"));
        el("p", text("unknownSource"), box);
        el("p", text("capacityUnknown"), box);
        if (p.operational_caution) el("p", text("operationUnknown"), box).className = "gis-caution";
        var placeDetails = dl; dl = el("dl", null, box);
        field("dimensions", p.evacuation_dimensions); field("nearbyHealth", p.evacuation_health); field("nearbyHospital", p.evacuation_hospital);
        dl = placeDetails;
      }
      if (/school/i.test(p.facility_type || "")) el("p", text("schoolContactUnknown"), box);
      var officeKey = ((residentData.contacts || {}).facility_offices || {})[p.id];
      if (officeKey) officeContact(officeKey);
      if (barangay) {
        el("h4", text("officials"), box);
        if (barangay.punong_barangay) el("p", text("captain") + ": " + barangay.punong_barangay, box);
        var council = el("details", null, box); el("summary", text("council"), council);
        var officials = el("ul", null, council);
        (barangay.officials || []).forEach(function (official) { el("li", official.name + " - " + official.role, officials); });
        if (barangay.phone && /^[+()\d .-]{3,40}$/.test(barangay.phone)) action(text("barangayContact") + ": " + barangay.phone, "tel:" + barangay.phone.replace(/[^\d+]/g, ""));
        if (barangay.official_page) action(text("officialPage"), barangay.official_page);
        var prefix = lang === "en" ? "" : "/" + lang;
        if (barangay.url === "/government/#barangay-councils") action(text("directory"), prefix + barangay.url);
      }
      if (l.semantic_role === "barangay_reference_geometry") el("p", text("coarseGeometry"), box).className = "gis-caution";
      var formatted = {
        contract_amount: "contractAmount", approved_budget: "approvedBudget", accomplishment_percent: "accomplishment",
        fiscal_year: "fiscalYear", contractor: "contractor", status: "projectStatus", status_key: "projectStatus",
        actual_start_date: "actualStartDate", actual_completion_date: "actualCompletionDate",
        contract_effectivity_date: "contractEffectivityDate", contract_expiry_date: "contractExpiryDate",
      };
      Object.keys(formatted).forEach(function (key) {
        var value = p[key];
        if (value == null || value === "") return;
        if (["contract_amount", "approved_budget", "accomplishment_percent", "fiscal_year"].indexOf(key) >= 0) {
          if (typeof value !== "number" || !Number.isFinite(value)) return;
          if (key === "fiscal_year") value = String(value);
          else if (key === "accomplishment_percent") value = new Intl.NumberFormat(lang, { maximumFractionDigits: 2 }).format(value) + "%";
          else value = new Intl.NumberFormat(lang, { style: "currency", currency: "PHP" }).format(value);
        }
        if (key === "status_key") value = statusLabel(value);
        field(formatted[key], value);
      });
      if (shared && shared.length > 1) {
        el("p", text("shared"), box); var ul = el("ul", null, box);
        shared.forEach(function (record) { var b = el("button", name(record, s), el("li", null, ul)); b.type = "button";
          b.onclick = function () { select(record, s, trigger, shared, false); }; });
      }
      var limits = [].concat(l.limitations || [], p.limitations || [], l.quality_flags || [], p.quality_flags || []);
      if (limits.length) { el("h4", text("limitations"), box); var list = el("ul", null, box);
        limits.forEach(function (v) { el("li", local(v), list); }); }
      // Explicit canonical IDs only: never infer a relationship from location or names.
      var canonicalLink = projectUrl(p, lang, location.origin);
      if (canonicalLink) {
        var link = el("a", text("projectLink"), box);
        link.href = canonicalLink;
        field("confidence", p.relationship_confidence || p.confidence); field("evidence", p.relationship_evidence || p.evidence);
      }
      if (!f.geometry) el("p", text("nonspatial"), box);
      var technical = el("details", null, box); el("summary", text("sourceMap"), technical);
      dl = el("dl", null, technical);
      field("precisionLabel", precision(p, l));
      field("source", provenance.source || p.source || l.source_label);
      field("sourceDate", p.source_date || l.source_date);
      field("sourceId", provenance.source_record_id || p.evacuation_id);
      field("internalId", p.id); field("plusCode", p.plus_code);
      field("attribution", l.attribution);
      if (provenance.retrieved) field("retrieved", provenance.retrieved);
      action(text("source"), provenance.source_url || p.source_url || l.source_url, technical);
      if (p.canonical_facility_id) {
        var canonicalState = states.find(function (state) { return state.layer.data_key === "GIS_FACILITIES"; });
        var canonicalFacility = canonicalState && canonicalState.features.find(function (feature) { return feature.properties.id === p.canonical_facility_id; });
        if (canonicalFacility) { var canonicalButton = el("button", name(canonicalFacility, canonicalState), box); canonicalButton.type = "button";
          canonicalButton.onclick = function () { select(canonicalFacility, canonicalState, trigger, null, false); }; }
      }
      node("details").hidden = false; node("close").focus({ preventScroll: true });
      if (navigate && map && f.geometry && l.semantic_role !== "label_anchor") {
        if (f.geometry.type === "Point") map.panTo([f.geometry.coordinates[1], f.geometry.coordinates[0]]);
        else { var bounds = L.geoJSON(f).getBounds(); if (bounds.isValid()) map.fitBounds(bounds, { maxZoom: 16, padding: [24, 24] }); }
      }
    }
    async function choose(f, s, trigger) {
      select(f, s, trigger, s.pointGroups.get(f.geometry && JSON.stringify(f.geometry.coordinates)), true);
      var request = selectionRequest;
      var gid = f.properties.gid;
      if (gid && !f.geometry) {
        var candidates = states.filter(function (other) {
          return allowed(other.layer) && (other.layer.semantic_role === "barangay_boundary" ||
            (other.layer.semantic_role === "barangay_reference_geometry" && other.visible));
        });
        await Promise.all(candidates.map(load));
        if (request !== selectionRequest) return;
        for (var i = 0; i < candidates.length; i++) {
          var match = candidates[i].features.find(function (other) { return String(other.properties.gid) === String(gid) && spatialBarangay(candidates[i], other); });
          if (match) {
            f = match; s = candidates[i]; s.visible = true; if (s.toggle) s.toggle.checked = true;
            if (map && s.overlay) s.overlay.addTo(map);
            legend(); select(f, s, trigger && !trigger.isConnected ? returnFocus : trigger, null, true); break;
          }
        }
      }
    }
    function updateList() {
      var q = node("search").value.trim().toLocaleLowerCase();
      var focused = document.activeElement && document.activeElement.gisFeature, replacementFocus;
      var previousReturn = returnFocus && returnFocus.gisFeature;
      function sameRecord(a, b) { return a && b && (a === b ||
        (a.properties.gid && String(a.properties.gid) === String(b.properties.gid)) ||
        (a.properties.project_id && a.properties.project_id === b.properties.project_id)); }
      var list = node("results"), count = 0; list.replaceChildren();
      var entries = defaultEntries(states, activeMetric() && boundaryState());
      entries.forEach(function (entry) {
          var f = entry.feature, s = entry.state;
           var p = f.properties, haystack = [name(f, s), p.id, p.gid, p.psgc, p.source_name, p.project_id, p.source_transaction_id,
            p.contract_id, p.contractor, p.contractors, p.status, p.raw_status, p.status_key, p.status_key ? statusLabel(p.status_key) : "", p.fiscal_year,
             p.category, p.address, p.barangay, p.barangay_location, s.title].join(" ").toLocaleLowerCase();
          if (q && haystack.indexOf(q) < 0) return;
          count++; var b = el("button", null, el("li", null, list)); b.type = "button"; b.className = "gis-result";
          b.setAttribute("aria-controls", "gis-details"); b.gisFeature = f;
          if (sameRecord(focused, f)) replacementFocus = b;
          if (sameRecord(previousReturn, f)) returnFocus = b;
          b.setAttribute("aria-pressed", String(f === selectedFeature));
          var prefix = el("span", "", b); prefix.className = "gis-result-prefix"; prefix.innerHTML = iconSvg(categoryIcon(featureCategory(f), s.layer.semantic_role), categoryColor(featureCategory(f), s.layer.semantic_role, p.status_key), 20);
          el("span", name(f, s) + " ", b); el("small", [s.title, precision(p, s.layer)].filter(Boolean).join(" · "), b);
          b.onclick = function () { choose(f, s, b); };
      });
      if (replacementFocus) replacementFocus.focus({ preventScroll: true });
      node("result-count").textContent = count + " " + text("results"); node("no-results").hidden = count !== 0;
    }
    node("search").addEventListener("input", updateList);
     function legend() {
      var box = node("legend"); box.replaceChildren();
      states.forEach(function (s) {
        if (s.layer.type === "choropleth" && s === activeMetric()) {
          el("h3", s.title, box);
          el("p", s.layer.metric === "population" ? String(statistics.population.year || 2024) + " / " + text("statPeople") : text("statProjects"), box);
          metricClasses.forEach(function (entry) {
            var row = el("p", null, box), swatch = el("span", "", row); swatch.className = "gis-legend-swatch"; swatch.style.backgroundColor = entry.color;
            el("span", new Intl.NumberFormat(lang).format(entry.min) + (entry.min === entry.max ? "" : " - " + new Intl.NumberFormat(lang).format(entry.max)), row);
          });
          var missing = el("p", null, box), gray = el("span", "", missing); gray.className = "gis-legend-swatch"; gray.style.backgroundColor = MISSING_COLOR;
          el("span", text("statUnavailable"), missing);
          if (s.layer.metric === "projects") {
            el("p", text("statCoverage"), box).className = "gis-caution";
            el("p", text("statZero"), box);
            Object.keys(statistics.project_coverage.sources).forEach(function (source) {
              var c = statistics.project_coverage.sources[source];
              el("p", source.toUpperCase() + ": " + (c.supported ? text("statSupported") : text("statUnavailable")) + (Number.isSafeInteger(c.unassigned_count) ? " / " + text("statUnassigned") + ": " + c.unassigned_count : ""), box);
            });
          }
          el("p", text("statPrecision"), box); return;
        }
        if (!s.visible || !s.overlay) return;
        var role = s.layer.semantic_role;
        var sourceLine = [local(s.layer.scenario), s.layer.source_date, local(s.layer.attribution)].filter(Boolean).join(" · ");
        var limitations = (s.layer.limitations || []).map(local);
        if (role === "dpwh_project") {
          el("h3", s.title, box);
          if (sourceLine) el("p", sourceLine, box);
          Object.keys(STATUS_COLORS).forEach(function (key) {
            var row = el("p", null, box), swatch = el("span", "", row); swatch.className = "gis-legend-icon"; swatch.innerHTML = iconSvg("hard-hat", STATUS_COLORS[key], 20);
            el("span", local(text("status" + key.replace(/(^|_)([a-z])/g, function (_, gap, c) { return c.toUpperCase(); }))), row);
          });
          limitations.forEach(function (v) { el("p", v, box); });
        } else if (role === "facility" || s.layer.data_key === "GIS_FACILITIES") {
          var seen = [], rows = [];
          s.features.forEach(function (f) {
            var category = featureCategory(f);
            var icon = categoryIcon(category, role);
            if (seen.indexOf(icon) >= 0) return;
            seen.push(icon);
            rows.push({ icon: icon, color: categoryColor(category, role), label: text("category" + categoryKey(icon)) });
          });
          if (rows.length) {
            el("h3", s.title, box);
            if (sourceLine) el("p", sourceLine, box);
            rows.forEach(function (entry) {
              var row = el("p", null, box), swatch = el("div", null, row); swatch.className = "gis-legend-icon"; swatch.innerHTML = iconSvg(entry.icon, entry.color, 18);
              el("span", entry.label, row);
            });
            limitations.forEach(function (v) { el("p", v, box); });
          }
        } else if (Array.isArray(s.layer.legend) && s.layer.legend.length) {
          el("h3", s.title, box); if (sourceLine) el("p", sourceLine, box);
          if (Array.isArray(s.layer.legend)) s.layer.legend.forEach(function (entry) {
            var row = el("p", null, box), swatch = el("span", "", row); swatch.className = "gis-legend-swatch";
            if (/^#[0-9a-f]{3,8}$/i.test(entry.color)) swatch.style.backgroundColor = entry.color;
            el("span", local(entry.label || entry.title || entry.name || entry.value || entry.class), row);
          });
          limitations.forEach(function (v) { el("p", v, box); });
        }
      }); box.hidden = !box.childNodes.length;
    }
    node("fit").onclick = function () {
      if (!map) return; var bounds = L.latLngBounds([]);
      states.forEach(function (s) {
        if ((!s.visible && !(s === boundaryState() && activeMetric())) || !s.overlay || s.layer.semantic_role === "label_anchor") return;
        var b = s.overlay.getBounds(); if (b.isValid()) bounds.extend(b);
      });
      if (bounds.isValid()) map.fitBounds(bounds, { maxZoom: 16, padding: [24, 24] }); else announce("noGeometry");
    };
    async function fetchData(raw) {
      var url = assetUrl(raw, base, location.origin), abort = new AbortController();
      var timeout = setTimeout(function () { abort.abort(); }, 12000);
      try {
        var response = await fetch(url, { signal: abort.signal, credentials: "same-origin", redirect: "error" });
        if (!response.ok || Number(response.headers.get("content-length")) > 8388608 || !response.body) throw Error("Layer unavailable");
        var reader = response.body.getReader(), chunks = [], size = 0;
        while (true) { var c = await reader.read(); if (c.done) break; size += c.value.byteLength;
          if (size > 8388608) { await reader.cancel(); throw Error("Layer too large"); } chunks.push(c.value); }
        var bytes = new Uint8Array(size), offset = 0;
        chunks.forEach(function (c) { bytes.set(c, offset); offset += c.length; });
        return JSON.parse(new TextDecoder().decode(bytes));
      } finally { clearTimeout(timeout); }
    }
    function iconMarker(shared, s) {
      var p = shared[0].properties || {};
      var iconName = categoryIcon(featureCategory(shared[0]), s.layer.semantic_role), color = categoryColor(featureCategory(shared[0]), s.layer.semantic_role, p.status_key);
      var mixed = shared.some(function (f) { return categoryIcon(featureCategory(f), s.layer.semantic_role) !== iconName || categoryColor(featureCategory(f), s.layer.semantic_role, f.properties.status_key) !== color; });
      var svg = iconSvg(mixed ? "layers" : iconName, mixed ? "#53616a" : color, 20);
      if (shared.length > 1) svg += '<span class="gis-marker-count" aria-hidden="true">' + shared.length + '</span>';
      return L.divIcon({ html: svg, className: "gis-icon-marker", iconSize: [36, 36], iconAnchor: [18, 18] });
    }
    function updateBoundaryLabels() {
      states.forEach(function (s) {
        if (s.layer.semantic_role !== "barangay_boundary") return;
        s.items.forEach(function (item) {
          if (!item.openTooltip) return;
          if (item === selectedItem || map && map.getZoom() >= 15) item.openTooltip();
          else if (item.closeTooltip) item.closeTooltip();
        });
      });
    }
    if (map && map.on) map.on("zoomend", updateBoundaryLabels);
    function vector(s) {
      if (!map || s.layer.type === "reference") return null;
      var group = L.featureGroup();
      s.pointGroups.forEach(function (shared) {
        var p = shared[0].geometry.coordinates;
        var title = shared.map(function (f) { return name(f, s) + " (" + text("category" + categoryKey(categoryIcon(featureCategory(f), s.layer.semantic_role))) + (s.layer.semantic_role === "dpwh_project" ? ": " + statusLabel(f.properties.status_key) : "") + ")"; }).join("; ");
        if (shared.length > 1) title = text("categoryShared") + " (" + shared.length + "): " + title;
        var marker = L.marker && L.divIcon
          ? L.marker([p[1], p[0]], { pane: s.pane, icon: iconMarker(shared, s), keyboard: true, title: title, alt: title })
          : L.circleMarker([p[1], p[0]], { radius: s.layer.semantic_role === "label_anchor" ? 4 : 7,
            pane: s.pane, color: categoryColor(featureCategory(shared[0]), s.layer.semantic_role, shared[0].properties.status_key),
            weight: 2, fillOpacity: 0.8, title: title });
        marker.addTo(group);
        marker.gisBaseStyle = { weight: 2, fillOpacity: 0.8 };
        marker.on("add", function () {
          var element = marker.getElement && marker.getElement();
          if (!element) return;
          element.setAttribute("role", "button"); element.setAttribute("aria-label", title); element.setAttribute("aria-pressed", String(marker === selectedItem));
          element.classList.toggle("gis-marker-selected", marker === selectedItem);
          element.tabIndex = 0;
          element.onkeydown = function (event) {
            if (event.key === " " || event.key === "Enter") { event.preventDefault(); event.stopPropagation(); select(shared[0], s, element, shared, false); }
          };
        });
        shared.forEach(function (f) { s.items.set(f, marker); });
        if (marker.bindTooltip) marker.bindTooltip(escapeHtml(title), { permanent: s.layer.semantic_role === "label_anchor" });
        marker.on("click", function () { select(shared[0], s, null, shared, false); });
      });
      L.geoJSON({ type: "FeatureCollection", features: s.features.filter(function (f) { return f.geometry && f.geometry.type !== "Point"; }) }, {
        pane: s.pane,
        style: { color: s.layer.semantic_role === "barangay_reference_geometry" ? "#9b650e" : "#486b87", weight: 2,
          fillOpacity: s.layer.semantic_role === "barangay_boundary" ? 0.08 : s.layer.semantic_role === "barangay_reference_geometry" ? 0.025 : 0.16,
          dashArray: s.layer.semantic_role === "barangay_reference_geometry" ? "6 5" : null },
        onEachFeature: function (f, item) {
          s.items.set(f, item); item.gisBaseStyle = { weight: 2, fillOpacity: s.layer.semantic_role === "barangay_boundary" ? 0.08 : s.layer.semantic_role === "barangay_reference_geometry" ? 0.025 : 0.16 };
          item.on("click", function () { select(f, s, null, null, false); });
          if (s.layer.semantic_role === "barangay_boundary") {
            if (item.bindTooltip) item.bindTooltip(escapeHtml(name(f, s)), { permanent: true, direction: "center", className: "gis-boundary-label" });
             item.on("mouseover", function () { if (item !== selectedItem) item.setStyle(Object.assign({}, boundaryStyle(f, s, item), { weight: 3, opacity: 1 })); });
             item.on("mouseout", function () { item.setStyle(boundaryStyle(f, s, item)); });
             item.on("add", function () {
               updateBoundaryLabels();
               var path = item.getElement && item.getElement(); if (!path) return;
               path.setAttribute("role", "button"); path.setAttribute("aria-label", name(f, s)); path.setAttribute("aria-pressed", String(item === selectedItem)); path.tabIndex = 0;
               path.onkeydown = function (event) { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); event.stopPropagation(); select(f, s, path, null, false); } };
             });
          }
        },
      }).addTo(group); return group;
    }
    async function load(s) {
      if (s.promise) return s.promise;
      s.message.textContent = text("loading");
      s.promise = (async function () {
        try {
          var l = s.layer;
          if (l.type === "choropleth") {
            if (["population", "projects"].indexOf(l.metric) < 0 || l.geometry_layer !== "barangay-boundaries") throw Error("Invalid statistical mode");
            var boundaries = boundaryState(); if (!boundaries || !allowed(boundaries.layer)) throw Error("Missing boundaries");
            if (!statisticsPromise) statisticsPromise = fetchData(l.statistics_url).then(validateStatistics).then(function (data) { statistics = data; setupProjectFilters(); return data; }).catch(function (error) { statisticsPromise = null; throw error; });
            await Promise.all([load(boundaries), statisticsPromise]);
            if (!boundaries.loaded || boundaries.features.length !== 15 || boundaries.features.some(function (f) { return !Object.hasOwn(statistics.barangays, String(f.properties.gid || f.properties.psgc)); })) throw Error("Invalid geometry join");
          } else if (l.type === "raster-image-overlay") {
            if (!map || !Array.isArray(l.images) || !l.images.length || l.images.length > 128) throw Error("Invalid imagery");
            var images = l.images.map(function (image) {
              if (!validBounds(image.bounds)) throw Error("Invalid bounds");
              var url = assetUrl(image.url, base, location.origin);
              if (!/\.(png|jpe?g|webp)$/i.test(new URL(url).pathname)) throw Error("Unsupported image");
              return { url: url, bounds: image.bounds };
            });
            s.overlay = L.featureGroup();
            if (s.visible) s.overlay.addTo(map);
            await Promise.all(images.map(function (image) { return new Promise(function (resolve, reject) {
              var b = image.bounds, item = L.imageOverlay(image.url, [[b.south, b.west], [b.north, b.east]], {
                opacity: s.opacity, pane: s.pane, attribution: escapeHtml(local(l.attribution)), interactive: false });
              s.images.push(item);
              var timeout = setTimeout(function () { reject(Error("Image timeout")); }, 12000);
              item.on("load", function () { clearTimeout(timeout); resolve(); });
              item.on("error", function () { clearTimeout(timeout); reject(Error("Image failed")); });
              item.addTo(s.overlay);
            }); }));
          } else {
            var payload;
            if (l.type === "inline-geojson" || l.type === "reference") {
              if (l.type === "inline-geojson" ? l.data_key !== "GIS_FACILITIES" : ["GIS_BARANGAYS", "GIS_RECORDS"].indexOf(l.data_key) < 0) throw Error("Invalid data key");
              payload = window[l.data_key];
            } else payload = await fetchData(l.url);
            s.features = records(payload);
            if (l.data_key === "GIS_RECORDS") {
              var scoped = s.features.some(function (f) { return typeof f.properties.layer_id === "string"; });
              s.features = s.features.filter(function (f) { return scoped ? f.properties.layer_id === l.id : s === states.find(function (other) { return other.layer.data_key === "GIS_RECORDS" && allowed(other.layer); }); });
            }
            if (l.type === "reference") s.features = s.features.map(function (f) { return { type: "Feature", properties: f.properties, geometry: null }; });
            s.pointGroups = exactGroups(s.features); s.overlay = vector(s);
            if (l.data_key === "GIS_FACILITIES") {
              if (node("marker-count")) node("marker-count").textContent = String(s.overlay ? s.pointGroups.size : 0);
               if (node("facility-empty")) node("facility-empty").hidden = s.features.length !== 0;
            }
          }
           s.loaded = true;
            if (s.message) s.message.textContent = text("loaded");
            if (s.overlay && map) { if (s.visible || s === boundaryState() && activeMetric()) s.overlay.addTo(map); else map.removeLayer(s.overlay); }
            refreshMetric();
        } catch (error) {
          if (s.overlay && map) map.removeLayer(s.overlay);
          var restore = s.visible && s.previous && s.previous.loaded ? s.previous : null;
          s.overlay = null; s.images = []; s.features = []; s.visible = false;
          if (s.toggle) { s.toggle.checked = false; s.toggle.disabled = ["raster-image-overlay", "choropleth"].indexOf(s.layer.type) < 0; }
          // Only the current selection may roll back. A later selection hides
          // this state before its asynchronous load can finish or fail.
          if (restore) {
            restore.visible = true; restore.toggle.checked = true;
            if (restore.layer.type === "choropleth") metricState = restore;
            if (map && restore.overlay) restore.overlay.addTo(map);
          }
          s.message.textContent = text(s.layer.type === "choropleth" ? "statError" : "layerError"); refreshMetric();
        }
        updateList(); legend();
      })();
      var pending = s.promise;
      pending.then(function () { if (!s.loaded && s.promise === pending) s.promise = null; });
      return pending;
    }
    function setupProjectFilters() {
      var box = node("project-filters"); if (!box || box.dataset.ready) return; box.dataset.ready = "true";
      ["source", "year", "status"].forEach(function (key) {
        var label = el("label", text(key === "source" ? "source" : key === "year" ? "yearReference" : "projectStatus"), box);
        var control = el("select", null, box); control.id = "gis-project-" + key; label.htmlFor = control.id; filterControls[key] = control;
        el("option", text("statAll"), control).value = "";
        var values = new Set();
        if (key === "source") Object.keys(statistics.project_coverage.sources).forEach(function (source) { values.add(source); });
        else statistics.projects.forEach(function (p) { p.references.forEach(function (r) { if (statistics.project_coverage.sources[r.source] && statistics.project_coverage.sources[r.source].supported) values.add(String(r[key] == null ? "unknown" : r[key])); }); });
        Array.from(values).sort().forEach(function (value) {
          var supported = key !== "source" || statistics.project_coverage.sources[value].supported;
          var reference = key === "status" && statistics.projects.flatMap(function (p) { return p.references; }).find(function (ref) { return ref.status === value; });
          var title = key === "source" ? value.toUpperCase() : value === "unknown" ? text("statusUnknown") : key === "status" && Object.hasOwn(STATUS_COLORS, value) ? statusLabel(value) : reference && reference.status_label || value;
          var option = el("option", title + (supported ? "" : " / " + text("statUnavailable")), control); option.value = value; option.disabled = !supported;
        });
        control.onchange = function () { projectFilters[key] = control.value; refreshMetric(); legend(); };
      });
      el("p", text("statFilterHelp"), box).className = "gis-panel-note";
    }
    function thematic(l) { return l.type === "choropleth" || l.type === "raster-image-overlay"; }
    function exclusive(a, b) { return thematic(a) && thematic(b) || a.exclusive_group && a.exclusive_group === b.exclusive_group; }
    var layers = manifest.schema_version === 1 && Array.isArray(manifest.layers) ? manifest.layers.slice(0, 200) : [], seen = new Set();
    layers.forEach(function (l) {
      if (!l || typeof l.id !== "string" || seen.has(l.id)) return; seen.add(l.id);
      if (l.type === "reference") {
        if (l.data_key) states.push({ layer: l, title: local(l.title) || l.id, features: window[l.data_key] ? records(window[l.data_key]) : [], pointGroups: new Map(), items: new Map(), visible: false, overlay: null });
        return;
      }
      var group = local(l.group) || text("layers");
      if (!groups.has(group)) { var fieldset = el("fieldset", null, node("layer-list")); el("legend", group, fieldset); groups.set(group, fieldset); }
      var row = el("div", null, groups.get(group)); row.className = "gis-layer";
      row.dataset.layerId = l.id;
      var label = el(l.type === "reference" ? "div" : "label", null, row), toggle = l.type === "reference" ? null : el("input", null, label);
      if (toggle) toggle.type = "checkbox";
      var title = local(l.title) || l.id; el("span", title, label);
      var message = el("small", null, row); message.setAttribute("role", "status");
      var canLoad = allowed(l), canRender = canLoad && l.type !== "reference" && !!map;
      if (toggle) toggle.disabled = !canRender;
      message.textContent = canLoad ? text("notLoaded") : text("unavailableLayer");
      var pane = Object.hasOwn(PANES, l.pane) ? l.pane : l.type === "raster-image-overlay" ? "physical" :
        l.semantic_role === "dpwh_project" ? "infrastructure" : l.data_key === "GIS_FACILITIES" ? "facilities" : "administrative";
      var s = { layer: l, title: title, features: [], pointGroups: new Map(), items: new Map(), visible: canRender && l.type !== "choropleth" && l.visible_by_default === true,
        overlay: null, toggle: toggle, message: message, images: [], opacity: opacity(l.opacity),
        pane: "gis-" + pane + (l.type === "raster-image-overlay" ? "-raster" : "") }; states.push(s);
      if (l.semantic_role === "barangay_reference_geometry") el("p", text("coarseGeometry"), row).className = "gis-caution";
      if (l.type === "reference" && !l.data_key) {
        message.textContent = text("nonspatial");
        (l.limitations || []).forEach(function (note) { el("p", local(note), row).className = "gis-panel-note"; });
        try {
          var source = new URL(l.source_url);
          if (/^https?:$/.test(source.protocol) && !source.username && !source.password) {
            var citation = el("a", text("source"), row); citation.href = source.href; citation.rel = "noopener";
          }
        } catch (error) { /* Invalid citation must not prevent other layers loading. */ }
        return;
      }
      if (!canLoad) return;
      var details = el("button", text("details"), row); details.type = "button";
      details.onclick = function () { select({ properties: { name: title }, geometry: null }, s, details, null, false); };
      if (l.type === "raster-image-overlay") {
        var opacityLabel = el("label", null, row), slider = el("input", null, opacityLabel), output = el("output", null, opacityLabel);
        slider.type = "range"; slider.min = "0"; slider.max = "100"; slider.step = "any"; slider.value = String(s.opacity * 100);
        slider.setAttribute("aria-label", text("opacity") + ": " + title);
        function updateOpacity() {
          s.opacity = opacity(Number(slider.value) / 100);
          output.textContent = text("opacity") + " " + new Intl.NumberFormat(lang, { maximumFractionDigits: 2 }).format(s.opacity * 100) + "%";
          slider.setAttribute("aria-valuetext", output.textContent);
          s.images.forEach(function (image) { image.setOpacity(s.opacity); });
        }
        slider.addEventListener("input", updateOpacity); updateOpacity();
      }
      if (toggle) toggle.checked = s.visible;
      function excludeOthers() {
        if (!s.visible) return;
        states.forEach(function (other) {
          if (other === s || !exclusive(l, other.layer)) return;
          other.visible = false; if (other.toggle) other.toggle.checked = false;
          if (other.overlay && map) map.removeLayer(other.overlay);
        });
      }
      if (toggle) toggle.addEventListener("change", function () {
        if (toggle.checked) {
          var current = states.find(function (other) { return other !== s && other.visible && exclusive(l, other.layer); });
          s.previous = current ? (current.loaded ? current : current.previous) : null;
        }
        s.visible = toggle.checked;
        if (s.visible && l.type === "choropleth") metricState = s;
        excludeOthers();
        if (s.visible) load(s).then(function () { if (s.visible && s.overlay && map) s.overlay.addTo(map); refreshMetric(); legend(); });
        else if (s.overlay && map) map.removeLayer(s.overlay);
        refreshMetric();
        updateList(); legend(); // Never fit on toggles: preserve the user's viewport.
      });
      excludeOthers();
      if (l.data_key || s.visible || l.type === "reference") load(s);
    });
    // Directory order is generated from this exact payload; never join by display name.
    var directoryRows = node("barangay-list") ? node("barangay-list").querySelectorAll("li") : [], barangayState = states.find(function (s) { return s.layer.data_key === "GIS_BARANGAYS"; });
    var directoryLink = page.querySelector('.gis-toolbar a[href="#gis-barangay-title"]');
    if (directoryLink && !node("barangay-title")) directoryLink.hidden = true;
    if (barangayState) directoryRows.forEach(function (row, index) {
      var f = barangayState.features[index]; if (!f) return;
      var button = el("button", text("locate"), row); button.type = "button";
      button.onclick = function () { choose(f, barangayState, button); };
    });
    updateList();
    // Keep static directories available until the interactive Explorer is initialized.
    if (node("directories")) node("directories").hidden = true;
    if (node("directory-link")) node("directory-link").hidden = true;
    node("workspace").dataset.ready = "true";
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
