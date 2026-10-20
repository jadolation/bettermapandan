/* Maintainer-configured explorer with bounded, same-origin layer loading. */
(function () {
  "use strict";
  var TYPES = ["inline-geojson", "geojson", "raster-image-overlay", "reference"];
  var PANES = { physical: 250, hazards: 300, administrative: 400, infrastructure: 450, facilities: 500 };
  var STATUS_COLORS = { completed: "#287943", ongoing: "#b66b08", not_started: "#536ba1", unknown: "#737373" };
  function opacity(value) { return typeof value === "number" && Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0.65; }
  function spatialBarangay(s, f) {
    return s.layer.available === true && !!s.overlay && !!f.geometry && ["Polygon", "MultiPolygon"].indexOf(f.geometry.type) >= 0 &&
      (s.layer.semantic_role === "barangay_boundary" || (s.layer.semantic_role === "barangay_reference_geometry" && s.visible));
  }
  function defaultEntries(states) {
    var projects = new Set(), barangays = new Map();
    states.forEach(function (s) { s.features.forEach(function (f) {
      var p = f.properties;
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
      entries.push({ feature: f, state: s });
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
  };
  if (typeof document === "undefined") return;
  function init() {
    var page = document.getElementById("gis-page");
    if (!page || page.dataset.initialized) return;
    page.dataset.initialized = "true";
    var manifest = window.GIS_LAYERS || {}, meta = manifest.metadata || {};
    var lang = document.documentElement.lang || "en", states = [], groups = new Map(), map = null, returnFocus;
    var selectedFeature = null, selectedItem = null, selectionRequest = 0;
    function node(id) { return document.getElementById("gis-" + id); }
    function text(key) { return page.dataset[key] || key; }
    function statusLabel(key) { return text("status" + (Object.hasOwn(STATUS_COLORS, key) ? key : "unknown").replace(/(^|_)([a-z])/g, function (_, gap, c) { return c.toUpperCase(); })); }
    function local(v) { return v && typeof v === "object" ? String(v[lang] || v.en || "") : String(v == null ? "" : v); }
    function el(tag, value, parent) {
      var n = document.createElement(tag); if (value != null) n.textContent = value; if (parent) parent.appendChild(n); return n;
    }
    function announce(key) { node("map-status").textContent = text(key); }
    node("workspace").hidden = false;
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
      if (map) map.invalidateSize();
    }
    window.addEventListener("resize", resize);
    if (typeof ResizeObserver !== "undefined") {
      var observer = new ResizeObserver(resize);
      observer.observe(node("map"));
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
    function selection(feature, item) {
      if (selectedItem && selectedItem.setStyle) selectedItem.setStyle({ weight: 2 });
      selectedFeature = feature; selectedItem = item;
      if (selectedItem && selectedItem.setStyle) selectedItem.setStyle({ weight: 5 });
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
      field("precisionLabel", precision(p, l));
      field("source", provenance.source || p.source || l.source_label || l.source_id); field("sourceDate", p.source_date || l.source_date);
      field("attribution", l.attribution);
      if (typeof l.source_url === "string") {
        try { var sourceUrl = new URL(l.source_url);
          if (/^https?:$/.test(sourceUrl.protocol) && !sourceUrl.username && !sourceUrl.password) {
            var sourceLink = el("a", text("source"), box); sourceLink.href = sourceUrl.href; sourceLink.rel = "noopener";
          }
        } catch (error) { /* Optional source links must not break record inspection. */ }
      }
      field("scenario", l.scenario); field("address", p.address);
      if (l.semantic_role === "barangay_reference_geometry") el("p", text("coarseGeometry"), box).className = "gis-caution";
      var formatted = {
        contract_amount: "contractAmount", approved_budget: "approvedBudget", accomplishment_percent: "accomplishment",
        fiscal_year: "fiscalYear", contractor: "contractor", status: "projectStatus", status_key: "statusKey",
        source_transaction_id: "transactionId", project_id: "projectId", contract_id: "contractId",
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
      Object.keys(p).forEach(function (key) {
        if (Object.hasOwn(formatted, key) || ["project_url", "layer_id", "name", "title", "address", "source", "source_date", "provenance", "limitations", "quality_flags", "coordinate_method", "location_precision", "verification_status", "publication_status", "review_notes", "coordinate_history", "source_record_id"].indexOf(key) >= 0) return;
        if (typeof p[key] === "string" || typeof p[key] === "number" || typeof p[key] === "boolean") {
          el("dt", key.replace(/_/g, " "), dl); el("dd", String(p[key]), dl);
        }
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
      var q = node("search").value.trim().toLocaleLowerCase(), id = node("layer-filter").value;
      var focused = document.activeElement && document.activeElement.gisFeature, replacementFocus;
      var previousReturn = returnFocus && returnFocus.gisFeature;
      function sameRecord(a, b) { return a && b && (a === b ||
        (a.properties.gid && String(a.properties.gid) === String(b.properties.gid)) ||
        (a.properties.project_id && a.properties.project_id === b.properties.project_id)); }
      var list = node("results"), count = 0; list.replaceChildren();
      var entries = id ? states.filter(function (s) { return s.layer.id === id; }).flatMap(function (s) {
        return s.features.map(function (f) { return { feature: f, state: s }; });
      }) : defaultEntries(states);
      entries.forEach(function (entry) {
          var f = entry.feature, s = entry.state;
          var p = f.properties, haystack = [name(f, s), p.id, p.gid, p.psgc, p.source_name, p.project_id, p.source_transaction_id,
            p.contract_id, p.contractor, p.contractors, p.status, p.raw_status, p.status_key, p.status_key ? statusLabel(p.status_key) : "", p.fiscal_year,
            p.category, p.address, p.barangay, p.barangay_location, s.title].join(" ").toLocaleLowerCase();
          if (q && haystack.indexOf(q) < 0) return;
          count++; var b = el("button", name(f, s), el("li", null, list)); b.type = "button"; b.className = "gis-result";
          b.setAttribute("aria-controls", "gis-details"); b.gisFeature = f;
          if (sameRecord(focused, f)) replacementFocus = b;
          if (sameRecord(previousReturn, f)) returnFocus = b;
          b.setAttribute("aria-pressed", String(f === selectedFeature)); el("small", [s.title, precision(p, s.layer)].filter(Boolean).join(" · "), b);
          b.onclick = function () { choose(f, s, b); };
      });
      if (replacementFocus) replacementFocus.focus({ preventScroll: true });
      node("result-count").textContent = count + " " + text("results"); node("no-results").hidden = count !== 0;
    }
    ["search", "layer-filter"].forEach(function (id) { node(id).addEventListener(id === "search" ? "input" : "change", updateList); });
    function legend() {
      var box = node("legend"); box.replaceChildren();
      states.forEach(function (s) {
        if (!s.visible || !s.overlay) return;
        var entries = s.layer.semantic_role === "dpwh_project" ? Object.keys(STATUS_COLORS).map(function (key) {
          return { color: STATUS_COLORS[key], label: statusLabel(key) };
        }) : s.layer.legend;
        if (!Array.isArray(entries) || !entries.length) return;
        el("h3", s.title, box); el("p", [local(s.layer.scenario), s.layer.source_date, local(s.layer.attribution)].filter(Boolean).join(" · "), box);
        entries.forEach(function (entry) {
          var row = el("p", null, box), swatch = el("span", "", row); swatch.className = "gis-legend-swatch";
          if (/^#[0-9a-f]{3,8}$/i.test(entry.color)) swatch.style.backgroundColor = entry.color;
          el("span", local(entry.label || entry.title || entry.name || entry.value || entry.class), row);
        });
        (s.layer.limitations || []).forEach(function (v) { el("p", local(v), box); });
      }); box.hidden = !box.childNodes.length;
    }
    node("fit").onclick = function () {
      if (!map) return; var bounds = L.latLngBounds([]);
      states.forEach(function (s) {
        if (!s.visible || !s.overlay || s.layer.semantic_role === "label_anchor") return;
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
    function vector(s) {
      if (!map || s.layer.type === "reference") return null;
      var group = L.featureGroup();
      s.pointGroups.forEach(function (shared) {
        var p = shared[0].geometry.coordinates;
        var marker = L.circleMarker([p[1], p[0]], { radius: s.layer.semantic_role === "label_anchor" ? 4 : 7,
          pane: s.pane, color: s.layer.semantic_role === "dpwh_project" ? STATUS_COLORS[shared[0].properties.status_key] || STATUS_COLORS.unknown : "#2d6b1f",
          weight: 2, fillOpacity: 0.8 }).addTo(group);
        shared.forEach(function (f) { s.items.set(f, marker); });
        marker.bindTooltip(escapeHtml(name(shared[0], s)), { permanent: s.layer.semantic_role === "label_anchor" });
        marker.on("click", function () { select(shared[0], s, null, shared, false); });
      });
      L.geoJSON({ type: "FeatureCollection", features: s.features.filter(function (f) { return f.geometry && f.geometry.type !== "Point"; }) }, {
        pane: s.pane,
        style: { color: s.layer.semantic_role === "barangay_reference_geometry" ? "#9b650e" : "#486b87", weight: 2,
          fillOpacity: s.layer.semantic_role === "barangay_boundary" ? 0.04 : s.layer.semantic_role === "barangay_reference_geometry" ? 0.025 : 0.16,
          dashArray: s.layer.semantic_role === "barangay_reference_geometry" ? "6 5" : null },
        onEachFeature: function (f, item) { s.items.set(f, item); item.on("click", function () { select(f, s, null, null, false); }); },
      }).addTo(group); return group;
    }
    async function load(s) {
      if (s.promise) return s.promise;
      s.message.textContent = text("loading");
      s.promise = (async function () {
        try {
          var l = s.layer;
          if (l.type === "raster-image-overlay") {
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
              node("marker-count").textContent = String(s.pointGroups.size);
              node("facility-empty").hidden = s.features.length !== 0;
            }
          }
          s.message.textContent = text(s.features.length || l.type === "raster-image-overlay" ? "loaded" : "emptyLayer");
          if (s.overlay && map) { if (s.visible) s.overlay.addTo(map); else map.removeLayer(s.overlay); }
        } catch (error) {
          if (s.overlay && map) map.removeLayer(s.overlay);
          s.overlay = null; s.features = []; s.visible = false;
          if (s.toggle) { s.toggle.checked = false; s.toggle.disabled = true; }
          s.message.textContent = text("layerError");
        }
        updateList(); legend();
      })(); return s.promise;
    }
    var layers = manifest.schema_version === 1 && Array.isArray(manifest.layers) ? manifest.layers.slice(0, 200) : [], seen = new Set();
    layers.forEach(function (l) {
      if (!l || typeof l.id !== "string" || seen.has(l.id)) return; seen.add(l.id);
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
      var s = { layer: l, title: title, features: [], pointGroups: new Map(), items: new Map(), visible: canRender && l.visible_by_default === true,
        overlay: null, toggle: toggle, message: message, images: [], opacity: opacity(l.opacity),
        pane: "gis-" + pane + (l.type === "raster-image-overlay" ? "-raster" : "") }; states.push(s);
      if (l.semantic_role === "barangay_reference_geometry") el("p", text("coarseGeometry"), row).className = "gis-caution";
      var inspect = el("button", text("details"), row); inspect.type = "button";
      inspect.onclick = function () { select({ properties: { name: title }, geometry: null }, s, inspect, null, false); };
      if (!canLoad) return;
      var option = el("option", title, node("layer-filter")); option.value = l.id;
      if (l.type === "reference") {
        el("p", text("referenceOnly"), row).className = "gis-panel-note";
        var directory = el("button", text("listRecords"), row); directory.type = "button";
        directory.onclick = function () { node("layer-filter").value = l.id; node("search").value = ""; updateList(); activateTab("explore", false); node("layer-filter").focus(); };
      }
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
        if (!s.visible || typeof l.exclusive_group !== "string" || !l.exclusive_group.trim()) return;
        states.forEach(function (other) {
          if (other === s || other.layer.exclusive_group !== l.exclusive_group) return;
          other.visible = false; if (other.toggle) other.toggle.checked = false;
          if (other.overlay && map) map.removeLayer(other.overlay);
        });
      }
      if (toggle) toggle.addEventListener("change", function () {
        s.visible = toggle.checked;
        excludeOthers();
        if (s.visible) load(s).then(function () { if (s.visible && s.overlay && map) s.overlay.addTo(map); });
        else if (s.overlay && map) map.removeLayer(s.overlay);
        updateList(); legend(); // Never fit on toggles: preserve the user's viewport.
      });
      excludeOthers();
      if (l.data_key || s.visible || l.type === "reference") load(s);
    });
    // Directory order is generated from this exact payload; never join by display name.
    var directoryRows = node("barangay-list").querySelectorAll("li"), barangayState = states.find(function (s) { return s.layer.data_key === "GIS_BARANGAYS"; });
    if (barangayState) directoryRows.forEach(function (row, index) {
      var f = barangayState.features[index]; if (!f) return;
      var button = el("button", text("locate"), row); button.type = "button";
      button.onclick = function () { choose(f, barangayState, button); };
    });
    updateList(); node("workspace").dataset.ready = "true";
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
