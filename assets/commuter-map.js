(function () {
  "use strict";
  var page = document.getElementById("commuter-page");
  if (!page) return;
  var data = JSON.parse(document.getElementById("commuter-data").textContent);
  var labels = data.labels;
  var sheet = document.getElementById("commuter-sheet");
  var sheetBody = document.getElementById("commuter-sheet-body");
  var toolbar = page.querySelector(".sheet-toolbar");
  var handle = page.querySelector(".sheet-handle");
  var explore = document.getElementById("commuter-explore");
  var info = document.getElementById("commuter-info");
  var heading = document.getElementById("commuter-info-title");
  var body = document.getElementById("commuter-info-body");
  var exploreButton = page.querySelector(".sheet-explore");
  var cards = Array.from(page.querySelectorAll(".transport-card"));
  var groups = Array.from(page.querySelectorAll("[data-route]"));
  var search = document.getElementById("commuter-search");
  var filter = document.getElementById("commuter-type");
  var showAll = document.getElementById("commuter-show-all");
  var status = document.getElementById("commuter-map-status");
  var features = data.features.concat(data.observations || []);
  var markers = new Map(), lines = new Map();
  var resources = new Map(), geometry = new Map(), detailCache = new Map(), routeLoads = new Map();
  var pendingFit = null, boundaryTimer;
  data.direction_steps = {};
  var selection = { kind: "none", id: null };
  var activeRouteId = null;
  var stepMarker = null;
  var view = "explore";
  var states = ["collapsed", "half", "expanded"], stops = [96, 300, 540];
  var map, frame, fitTimer, drag = null, suppressClick = false;
  var DRAG_THRESHOLD = 8, FLING_VELOCITY = .45, SAMPLE_WINDOW = 100;
  var paths = {
    flag: '<path d="M3 2h2v2h15l-3 5 3 5H5v8H3V2Z"/>',
    peso: '<path d="M5 2h8a6 6 0 0 1 6 4h3v2h-2v2h2v2h-3a6 6 0 0 1-6 4H9v6H5V12H2v-2h3V8H2V6h3V2Zm4 4h6a3 3 0 0 0-2-1H9v1Zm0 2v2h7V8H9Zm0 4v1h4a3 3 0 0 0 2-1H9Z"/>',
    cornerup: '<path d="m15 1 8 8h-5v8a5 5 0 0 1-5 5H2v-4h11a1 1 0 0 0 1-1V9H9l6-8Z"/>',
    chevron: '<path d="m4 7 8 8 8-8 3 3-11 11L1 10l3-3Z"/>',
    left: '<path d="m10 2-9 8 9 8v-6h7v10h5V7H10V2Z"/>',
    right: '<path d="m14 2 9 8-9 8v-6H7v10H2V7h12V2Z"/>',
    straight: '<path d="m12 1 9 9h-6v13H9V10H3l9-9Z"/>',
    uturn: '<path d="M4 13V8a8 8 0 0 1 16 0v5h4l-6 9-6-9h4V8a4 4 0 0 0-8 0v5H4Z"/>',
    walk: '<path d="M14 1a3 3 0 1 1 0 6 3 3 0 0 1 0-6Zm-5 7h7l3 5h4v3h-6l-2-3-1 4 5 6h-5l-4-5-3 5H3l5-9 1-3-3 2H2v-3h3l4-2Z"/>',
    location: '<path d="M12 1a8 8 0 0 0-8 8c0 6 8 14 8 14s8-8 8-14a8 8 0 0 0-8-8Zm0 5a3 3 0 1 1 0 6 3 3 0 0 1 0-6Z"/>',
    clock: '<path d="M12 1a11 11 0 1 0 0 22 11 11 0 0 0 0-22Zm1 4v6h5v2h-7V5h2Z"/>',
    warning: '<path d="m12 1 12 22H0L12 1Zm-1 7v7h2V8h-2Zm0 9v3h2v-3h-2Z"/>',
    minibus: '<path d="M5 2h14a3 3 0 0 1 3 3v13h-2v3h-4v-3H8v3H4v-3H2V5a3 3 0 0 1 3-3Zm0 4v6h14V6H5Zm1 8a2 2 0 1 0 0 4 2 2 0 0 0 0-4Zm12 0a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z"/>',
    jeepney: '<path d="M3 4h15v3h3v5h2v6h-2v3h-4v-3H7v3H3v-3H1V9h2V4Zm3 3v5h4V7H6Zm6 0v5h4V7h-4Zm6 3v2h2v-2h-2ZM5 14a2 2 0 1 0 0 4 2 2 0 0 0 0-4Zm14 0a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z"/>',
    tricycle: '<path d="M1 5h13v3h-1v7h3l-3-5 3-2h3v2h-2l3 5a4 4 0 1 1-4 4H9a4 4 0 1 1-7-4V8H1V5Zm4 3v6h5V8H5ZM5 17a2 2 0 1 0 0 4 2 2 0 0 0 0-4Zm15 0a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z"/>',
    transfer: '<path d="m16 2 7 6-7 6v-4H3V6h13V2ZM8 10v4h13v4H8v4l-7-6 7-6Z"/>'
  };
  function symbol(mode) { return '<svg class="transport-symbol" viewBox="0 0 24 24" aria-hidden="true">' + (paths[mode] || paths.transfer) + '</svg>'; }
  function name(id) { var f = features.find(function (f) { return f.properties.id === id; }); return labels[id] || (f && f.properties.name) || (data.place_names || {})[id] || id; }
  function paragraph(parent, text) { if (text) { var p = document.createElement("p"); p.textContent = text; parent.appendChild(p); } }
  function coordinatesValid(value) {
    return Array.isArray(value) && value.length >= 2 && value.every(function (point) {
      return Array.isArray(point) && point.length === 2 && point.every(function (n) { return typeof n === "number" && Number.isFinite(n); }) && Math.abs(point[0]) <= 180 && Math.abs(point[1]) <= 90;
    });
  }
  function validResource(payload, pattern, kind) {
    if (!payload || payload.schema_version !== 1 || payload.pattern_id !== pattern || payload.kind !== kind) return false;
    var value = payload.data;
    if (kind === "geometry") return value === null || value && (value.type === "LineString" && coordinatesValid(value.coordinates) || value.type === "MultiLineString" && Array.isArray(value.coordinates) && value.coordinates.length && value.coordinates.every(coordinatesValid));
    if (!value || typeof value !== "object" || !(value.properties === null || value.properties && value.properties.pattern_id === pattern)) return false;
    var source = value.directions;
    return source === null || source && source.pattern_id === pattern && Array.isArray(source.notes) && Array.isArray(source.steps) && source.steps.every(function (step) {
      return step && typeof step.instruction_type === "string" && typeof step.street_name === "string" && Number.isInteger(step.sequence) &&
        (step.waypoint === null || coordinatesValid([step.waypoint, step.waypoint])) && (step.distance_m === null || typeof step.distance_m === "number" && Number.isFinite(step.distance_m));
    });
  }
  function loadResource(pattern, kind) {
    var reference = (data.resources[pattern] || {})[kind];
    if (!reference) return Promise.resolve(null);
    if (resources.has(reference.url)) return resources.get(reference.url);
    var controller = new AbortController(), timeout = setTimeout(function () { controller.abort(); }, 20000);
    var promise = fetch(reference.url, { signal: controller.signal }).then(function (response) {
      if (!response.ok) throw new Error("HTTP " + response.status);
      return response.arrayBuffer();
    }).then(async function (bytes) {
      var hash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))).map(function (n) { return n.toString(16).padStart(2, "0"); }).join("");
      if (hash !== reference.sha256 || !reference.url.endsWith("-" + hash + ".json")) throw new Error("Resource version");
      var payload = JSON.parse(new TextDecoder().decode(bytes));
      if (!validResource(payload, pattern, kind)) throw new Error("Resource schema");
      if (kind === "geometry") geometry.set(pattern, payload.data);
      else { detailCache.set(pattern, payload.data); if (payload.data.directions) data.direction_steps[pattern] = payload.data.directions; }
      return payload.data;
    }).catch(function (error) { resources.delete(reference.url); throw error; }).finally(function () { clearTimeout(timeout); });
    resources.set(reference.url, promise); return promise;
  }
  function lazyDisclosure(element, patterns, draw) {
    var loaded = false, loading = false;
    var content = document.createElement("div"); element.appendChild(content);
    function load() {
      if (loaded || loading || !element.open) return;
      loading = true; content.replaceChildren(); paragraph(content, labels.resource_loading);
      Promise.all(patterns.map(function (pattern) { return loadResource(pattern, "detail"); })).then(function () {
        loaded = true; content.replaceChildren(); draw(content);
      }).catch(function (error) {
        console.warn("Commuter information:", error.message);
        content.replaceChildren(); paragraph(content, labels.resource_failed);
        var retry = document.createElement("button"); retry.type = "button"; retry.textContent = labels.resource_retry; retry.addEventListener("click", load); content.appendChild(retry);
      }).finally(function () { loading = false; });
    }
    element.addEventListener("toggle", load);
  }
  function routeStatus(route, failed) {
    var node = document.getElementById("commuter-route-status");
    if (!node || activeRouteId !== route.id || view !== "route") return;
    node.replaceChildren();
    if (failed) {
      paragraph(node, labels.resource_failed);
      if (route.directions[0].some(function (pattern) { return geometry.get(pattern); })) paragraph(node, labels.partial_geometry);
      var retry = document.createElement("button"); retry.type = "button"; retry.textContent = labels.resource_retry;
      retry.addEventListener("click", function () { pendingFit = route.id; loadRoute(route); }); node.appendChild(retry);
    } else if (routeLoads.has(route.id)) paragraph(node, labels.resource_loading);
    else if (route.directions[0].some(function (pattern) { return !geometry.get(pattern); })) paragraph(node, labels.partial_geometry);
  }
  function createRouteLine(route) {
    if (!map) return;
    var shapes = route.directions[0].filter(function (pattern) { return geometry.get(pattern); }).map(function (pattern) {
      return { type: "Feature", geometry: geometry.get(pattern), properties: { pattern_id: pattern } };
    });
    if (!shapes.length) return;
    var previous = lines.get(route.id); if (previous) map.removeLayer(previous);
    var line = L.geoJSON({ type: "FeatureCollection", features: shapes }, { style: { color: "#16532c", weight: 4, dashArray: "10 7" } });
    line.on("click", function () { choose("route", route.id, true); }); lines.set(route.id, line);
  }
  function loadRoute(route) {
    if (routeLoads.has(route.id)) { routeStatus(route, false); return; }
    var work = Promise.allSettled(route.directions[0].map(function (pattern) { return loadResource(pattern, "geometry"); }));
    routeLoads.set(route.id, work); routeStatus(route, false);
    work.then(function (results) {
      routeLoads.delete(route.id);
      if (activeRouteId !== route.id) return;
      createRouteLine(route); update(); routeStatus(route, results.some(function (r) { return r.status === "rejected"; }));
      if (map && pendingFit === route.id && selection.kind === "route") { pendingFit = null; scheduleFit(); }
    });
  }
  function stationLocation(feature) {
    var geometry = feature && feature.geometry, coordinates = geometry && geometry.coordinates;
    if (!geometry || geometry.type !== "Point" || !Array.isArray(coordinates) || coordinates.length !== 2 ||
        ![coordinates[0], coordinates[1]].every(function (value) { return typeof value === "number" && Number.isFinite(value); }) ||
        Math.abs(coordinates[0]) > 180 || Math.abs(coordinates[1]) > 90) return null;
    var point = [coordinates[1], coordinates[0]], destination = point.join(",");
    return { point: point,
      view: "https://www.google.com/maps/search/?" + new URLSearchParams({ api: "1", query: destination }),
      walking: "https://www.google.com/maps/dir/?" + new URLSearchParams({ api: "1", destination: destination, travelmode: "walking" }) };
  }
  function disclosure(title) { var el = document.createElement("details"), summary = document.createElement("summary"); summary.textContent = title; el.appendChild(summary); body.appendChild(el); return el; }
  function clearStep() {
    if (map && stepMarker) map.removeLayer(stepMarker);
    stepMarker = null;
    body.querySelectorAll(".direction-step button").forEach(function (b) { b.setAttribute("aria-pressed", "false"); });
    delete page.dataset.activeStep;
  }
  function focusStep(step, pattern, button) {
    if (!map || !step.waypoint) return;
    clearTimeout(fitTimer); clearStep();
    var point = [step.waypoint[1], step.waypoint[0]];
    stepMarker = L.marker(point, { keyboard: false, interactive: false,
      icon: L.divIcon({ className: "direction-waypoint", html: symbol("location"), iconSize: [30, 36], iconAnchor: [15, 36] }) }).addTo(map);
    var pad = padding(), zoom = map.getZoom();
    var size = map.getSize(), target = L.point((pad.paddingTopLeft[0] + size.x - pad.paddingBottomRight[0]) / 2,
      (pad.paddingTopLeft[1] + size.y - pad.paddingBottomRight[1]) / 2);
    // The pin extends upward from its coordinate; keep the whole symbol in the visible strip.
    target.y = Math.max(pad.paddingTopLeft[1] + 36, target.y);
    var center = map.project(point, zoom).subtract(target.subtract(size.divideBy(2)));
    map.setView(map.unproject(center, zoom), zoom, { animate: false });
    button.setAttribute("aria-pressed", "true"); page.dataset.activeStep = pattern + ":" + step.sequence;
    document.getElementById("commuter-selection-status").textContent = labels.reported_pin;
  }
  function renderDirections(route) {
    var directions = document.createElement("div"); directions.className = "ride-cards"; body.appendChild(directions);
    route.directions[0].forEach(function (pattern, index) {
      var leg = route.legs[index], collection = (data.direction_steps || {})[pattern];
      var group = document.createElement("section"); group.className = "direction-leg"; group.dataset.pattern = pattern;
      if (index) {
        var transfer = document.createElement("p"); transfer.className = "direction-transfer";
        transfer.innerHTML = symbol("transfer"); transfer.appendChild(document.createTextNode(labels.transfer_notice)); directions.appendChild(transfer);
        if (pattern === "mini-manaoag-sm") paragraph(directions, labels.manaoag_transfer);
      }
      var title = document.createElement("button"); title.type = "button"; title.className = "leg-select"; title.innerHTML = leg.vehicle_types.map(symbol).join("");
      title.appendChild(document.createTextNode(labels[leg.label_key])); group.appendChild(title);
      if (route.legs.length === 1 && route.public_signboard_text) paragraph(group, route.public_signboard_text);
      paragraph(group, leg.vehicle_types.map(function (mode) { return labels[mode]; }).join(" / ") + " / " +
        (leg.fare.amount ? "PHP " + leg.fare.amount.min + "-" + leg.fare.amount.max : labels.unknown_fare) + " / " +
        (leg.driving_minutes == null ? labels.unknown_driving : leg.driving_km + " km / " + leg.driving_minutes + " min"));
      var steps = collection ? collection.steps : [];
      var summary = (data.direction_summaries || {})[pattern] || {};
      var first = summary.first;
      var last = summary.last;
      paragraph(group, labels.where_ride + ": " + (first ? labels["action_" + first.instruction_type].replace("{street}", first.place_id ? name(first.place_id) : first.street_name) : labels.confirm_stops));
      paragraph(group, labels.where_getoff + ": " + (last ? labels.action_arrive.replace("{street}", last.street_name) : labels.confirm_stops));
      if (!data.shapes.some(function (shape) { return shape.properties.pattern_id === pattern && !shape.properties.endpoint_caveat; })) paragraph(group, labels.map_incomplete);
      var detail = document.createElement("details"), toggle = document.createElement("summary");
      detail.className = "route-directions"; toggle.textContent = labels.directions_title; detail.appendChild(toggle); group.appendChild(detail);
      function emphasize(open) {
        page.dataset.activeLeg = pattern;
        directions.querySelectorAll(".leg-select").forEach(function (button) { button.setAttribute("aria-pressed", String(button === title)); });
        var line = lines.get(activeRouteId);
        if (line) line.eachLayer(function (layer) { layer.setStyle({ color: layer.feature.properties.pattern_id === pattern ? "#16532c" : "#789486", weight: layer.feature.properties.pattern_id === pattern ? 7 : 3, opacity: layer.feature.properties.pattern_id === pattern ? 1 : .25 }); });
        if (open) detail.open = true;
      }
      title.addEventListener("click", function () { emphasize(true); });
      detail.addEventListener("toggle", function () { if (detail.open) emphasize(false); });
      lazyDisclosure(detail, [pattern], function (container) {
        collection = data.direction_steps[pattern];
        if (!collection) { paragraph(container, labels.directions_unavailable); return; }
        collection.notes.forEach(function (key) { paragraph(container, labels[key]); });
        var list = document.createElement("ol"); list.className = "direction-timeline";
        collection.steps.forEach(function (step) {
          var item = document.createElement("li"); item.className = "direction-step";
          var action = document.createElement(step.waypoint ? "button" : "span");
          var type = step.instruction_type;
           action.innerHTML = symbol(type === "left" || type === "left_stay" || type === "roundabout_left" ? "left" : type === "right" ? "right" : type === "uturn" ? "uturn" : type === "arrive" ? "flag" : type === "start" || type === "start_head" ? "location" : type === "board" || type === "ask" ? leg.vehicle_types[0] : type === "transfer" ? "transfer" : type === "roundabout_first" ? "cornerup" : "straight");
           var text = document.createElement("span"); text.textContent = labels["action_" + type].replace("{street}", step.place_id ? name(step.place_id) : step.street_name) + (step.distance_m == null ? "" : " / " + step.distance_m + " m"); action.appendChild(text);
          if (step.waypoint) {
             action.type = "button"; action.setAttribute("aria-pressed", "false"); action.title = labels.reported_pin;
             action.addEventListener("mousedown", function (event) { event.preventDefault(); action.focus({ preventScroll: true }); });
            action.addEventListener("click", function () { focusStep(step, pattern, action); });
          }
          item.appendChild(action);
          if (!step.waypoint) paragraph(item, labels.location_not_mapped);
          if (step.warning_key) paragraph(item, labels[step.warning_key]);
          list.appendChild(item);
        });
        container.appendChild(list);
      });
      directions.appendChild(group);
    });
    if (route.directions.length > 1) {
       var reverse = document.createElement("details"), title = document.createElement("summary");
      reverse.className = "reverse-directions";
      title.textContent = labels.return_unconfirmed;
      reverse.appendChild(title);
      lazyDisclosure(reverse, route.directions.slice(1).flat(), function (container) { route.directions.slice(1).forEach(function (patterns) { patterns.forEach(function (pattern) {
        var source = (data.direction_steps || {})[pattern];
        if (!source) paragraph(container, labels.directions_unavailable);
        else { paragraph(container, labels.street_sequence_only); source.steps.forEach(function (step) { paragraph(container, labels.action_reported_street.replace("{street}", step.street_name)); }); }
      }); }); }); directions.appendChild(reverse);
    }
  }
  function fareText(route) {
    var fare = route.fare_summary, amount = fare.amount || fare.known_subtotal;
    return (fare.complete ? labels.total_fare : labels.incomplete_fare) + (amount ? ": PHP " + amount.min + "-" + amount.max : "") + (fare.complete ? "" : " + " + labels.unknown_fare);
  }
  function padding() {
    var rect = map.getContainer().getBoundingClientRect(), panel = sheet.getBoundingClientRect();
    var top = Math.max(24, page.querySelector(".commuter-hero").getBoundingClientRect().bottom - rect.top + 12);
    var side = matchMedia("(min-width: 900px)").matches;
    var attribution = map.getContainer().querySelector(".leaflet-control-attribution");
    var bottom = (attribution ? attribution.getBoundingClientRect().height : 0) + 32;
    return { paddingTopLeft: [side ? panel.right - rect.left + 24 : 24, top], paddingBottomRight: [24, side ? Math.max(40, bottom) : Math.min(panel.height + bottom, rect.height - top - 40)], maxZoom: 16, animate: false };
  }
  function fitSelection() {
    if (!map || selection.kind === "none" && !activeRouteId) return;
    var bounds = L.latLngBounds([]);
    if (activeRouteId) {
      var activeLine = lines.get(activeRouteId);
      if (activeLine) bounds.extend(activeLine.getBounds());
    }
    if (selection.kind === "station") {
      var f = features.find(function (f) { return f.properties.id === selection.id; });
      var location = stationLocation(f);
      if (location) bounds.extend(location.point);
    } else {
      var line = lines.get(selection.id);
      if (line) bounds.extend(line.getBounds());
    }
    if (bounds.isValid()) map.fitBounds(bounds, padding());
  }
  function scheduleFit() {
    clearTimeout(fitTimer);
    fitTimer = setTimeout(fitSelection, matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 200);
  }
  function setSheet(state, fit) {
    if (!states.includes(state)) return;
    if (state === "collapsed" && sheetBody.contains(document.activeElement)) handle.focus({ preventScroll: true });
    sheet.dataset.state = state;
    if (view === "station") document.getElementById("commuter-sheet-title").textContent = state === "collapsed" ? name(selection.id) : labels.station_details;
    sheetBody.hidden = state === "collapsed";
    sheet.style.setProperty("--sheet-height", stops[states.indexOf(state)] + "px");
    page.style.setProperty("--sheet-height", stops[states.indexOf(state)] + "px");
    handle.setAttribute("aria-expanded", String(state !== "collapsed"));
    page.querySelectorAll("[data-sheet-state]").forEach(function (button) { button.setAttribute("aria-pressed", String(button.dataset.sheetState === state)); });
    if (fit !== false) scheduleFit();
  }
  function update() {
    var query = search.value.trim().toLocaleLowerCase(), routePlaces = new Set();
    var route = data.catalog.find(function (r) { return r.id === activeRouteId; });
    if (route) route.marker_ids.forEach(function (id) { routePlaces.add(id); });
    function matches(el) { return (!filter.value || el.dataset.type === filter.value) && el.textContent.toLocaleLowerCase().includes(query); }
    cards.forEach(function (card) {
      card.hidden = !matches(card);
      var selected = selection.kind === "station" && card.dataset.id === selection.id;
      card.classList.toggle("selected", selected); card.querySelector("button").setAttribute("aria-pressed", String(selected));
    });
    groups.forEach(function (group) {
      group.hidden = !matches(group);
      var selected = group.dataset.route === activeRouteId;
      group.classList.toggle("selected", selected); group.setAttribute("aria-pressed", String(selected));
    });
    lines.forEach(function (line, id) {
      if (!map) return;
      if (activeRouteId === id) { if (!map.hasLayer(line)) line.addTo(map); }
      else if (map.hasLayer(line)) map.removeLayer(line);
    });
    features.forEach(function (f) {
      var p = f.properties, marker = markers.get(p.id), selected = selection.kind === "station" && selection.id === p.id;
      var visible = selected || routePlaces.has(p.id) || showAll.checked && (!filter.value || p.transport_type === filter.value) && name(p.id).toLocaleLowerCase().includes(query);
      if (map && marker) {
        if (visible && !map.hasLayer(marker)) marker.addTo(map);
        else if (!visible && map.hasLayer(marker)) map.removeLayer(marker);
        if (marker.getElement()) marker.getElement().classList.toggle("selected", selected);
      }
    });
    document.getElementById("commuter-count").textContent = labels.routes_results + ": " + groups.filter(function (g) { return !g.hidden; }).length + " / " + labels.results + ": " + cards.filter(function (c) { return !c.hidden; }).length;
  }
  function render() {
    explore.hidden = view !== "explore"; info.hidden = view === "explore";
    exploreButton.setAttribute("aria-pressed", String(view === "explore"));
    body.replaceChildren();
    var title = selection.kind === "none" ? labels.explore : name(selection.id), summary = labels.provisional;
    if (selection.kind === "route") {
      var route = data.catalog.find(function (r) { return r.id === selection.id; });
      summary = fareText(route);
      if (view === "route") {
        paragraph(body, name(route.origin_id) + " \u2192 " + name(route.destination_id));
        paragraph(body, summary);
        paragraph(body, route.legs.length + " " + labels.rides + " / " + (route.transfer_count || 0) + " " + labels.transfers);
        paragraph(body, labels.waiting_unknown);
        paragraph(body, labels.unconfirmed_stops);
        var overview = document.createElement("section"); overview.className = "journey-summary";
        while (body.firstChild) overview.appendChild(body.firstChild);
        ["location", "peso", "transfer", "clock", "warning"].forEach(function (icon, index) {
          var item = overview.children[index]; if (!item) return;
          var glyph = document.createElement("span"); glyph.innerHTML = symbol(icon); item.prepend(glyph); item.classList.add("summary-fact");
        });
        var sequence = document.createElement("p"); sequence.className = "ride-sequence";
        route.legs.forEach(function (leg, index) {
          if (index) { var change = document.createElement("span"); change.innerHTML = symbol("transfer"); sequence.appendChild(change); }
          var mode = document.createElement("span"); mode.innerHTML = leg.vehicle_types.map(symbol).join("");
          mode.appendChild(document.createTextNode(leg.vehicle_types.map(function (type) { return labels[type]; }).join(" / "))); sequence.appendChild(mode);
        });
        overview.prepend(sequence); body.appendChild(overview);
        renderDirections(route);
        var resourceStatus = document.createElement("div"); resourceStatus.id = "commuter-route-status"; resourceStatus.setAttribute("role", "status"); body.appendChild(resourceStatus);
        var sources = disclosure(labels.sources);
        sources.className = "route-sources";
        var reverseDirections = body.querySelector(".reverse-directions"); if (reverseDirections) sources.appendChild(reverseDirections);
        lazyDisclosure(sources, route.directions.flat(), function (sources) {
        var routeRecord = (detailCache.get(route.directions[0][0]) || {}).routes || {};
        var sourceRoute = routeRecord[route.id] || route;
        paragraph(sources, labels.local_reports);
        paragraph(sources, labels.fare_change);
        if (!route.fare_summary.complete) paragraph(sources, labels.no_totals);
        var detail = document.createElement("details"), fareTitle = document.createElement("summary"); fareTitle.textContent = labels.reported_range; detail.appendChild(fareTitle); sources.appendChild(detail);
        route.legs.forEach(function (leg) { var amount = leg.fare.amount; paragraph(detail, labels[leg.label_key] + ": " + (amount ? "PHP " + amount.min + "-" + amount.max : labels.unknown_fare)); });
        paragraph(detail, labels.fare_caveat);
        var driving = document.createElement("details"), drivingTitle = document.createElement("summary"); drivingTitle.textContent = labels.driving; driving.appendChild(drivingTitle); sources.appendChild(driving);
        route.legs.forEach(function (leg) { paragraph(driving, labels[leg.label_key] + ": " + (leg.driving_minutes == null ? labels.unknown_driving : leg.driving_km + " km / " + leg.driving_minutes + " min")); });
        if (route.legs.some(function (leg) { return leg.alternate_driving_note_minutes; })) paragraph(driving, labels.alternate_driving);
        paragraph(driving, labels.waiting_unknown);
        var routeShapes = data.shapes.filter(function (s) { return route.directions[0].includes(s.properties.pattern_id); });
        paragraph(sources, labels.source_warning);
        if (sourceRoute.explanation_key) paragraph(sources, labels[sourceRoute.explanation_key]);
        paragraph(sources, route.directions[0].map(name).join("; "));
        if (!routeShapes.length) paragraph(sources, labels.withheld);
        else if (routeShapes.length < route.directions[0].length || routeShapes.some(function (s) { return !!s.properties.endpoint_caveat; })) paragraph(sources, labels.partial_geometry);
        paragraph(sources, sourceRoute.evidence_note); paragraph(sources, sourceRoute.evidence_source || sourceRoute.source_type);
        paragraph(sources, sourceRoute.service_verification_status);
        paragraph(sources, [sourceRoute.last_updated, sourceRoute.created_date, sourceRoute.source_url].filter(Boolean).join(" / "));
        paragraph(sources, data.direction_limitations);
        route.directions[0].forEach(function (pattern) {
          var source = (data.direction_steps || {})[pattern];
          if (source) source.steps.forEach(function (step) {
            paragraph(sources, step.source_amendment);
            paragraph(sources, step.sequence + ". " + step.instruction_text + " | " + step.original_source + " | " + JSON.stringify(step.waypoint) + " | " + step.source_type + " / " + step.verification_status);
          });
        });
        routeShapes.forEach(function (s) {
          var p = (detailCache.get(s.properties.pattern_id) || {}).properties || s.properties;
          paragraph(sources, [p.name, p.verification_status, p.attribution, p.endpoint_caveat, p.retrieved_at, p.warnings].filter(Boolean).map(function (v) { return typeof v === "object" ? JSON.stringify(v) : v; }).join("; "));
          paragraph(sources, labels.geometry_details + ": " + p.distance_m + " m");
        });
        route.directions.flat().forEach(function (pattern) {
          var value = detailCache.get(pattern); if (!value) return;
          var record = document.createElement("details"), title = document.createElement("summary"); title.textContent = name(pattern);
          var raw = document.createElement("pre"); raw.style.whiteSpace = "pre-wrap"; raw.style.overflowWrap = "anywhere"; raw.textContent = JSON.stringify(value, null, 2);
          record.appendChild(title); record.appendChild(raw); sources.appendChild(record);
        });
        });
      }
    } else if (selection.kind === "station") {
      var feature = features.find(function (f) { return f.properties.id === selection.id; }), props = feature.properties;
      summary = props.observed_only ? labels.observed_place : labels[props.transport_type];
      if (view === "station") {
        var panel = document.createElement("section");
        panel.className = "station-detail-card";
        body.appendChild(panel);

        var mode = document.createElement("div");
        mode.className = "station-detail-mode";
        var modeIcon = document.createElement("span");
        modeIcon.innerHTML = symbol(props.transport_type === "transfer" ? "transfer" : props.transport_type);
        mode.appendChild(modeIcon);
        var modeName = document.createElement("span");
        modeName.textContent = summary || props.transport_type;
        mode.appendChild(modeName);
        panel.appendChild(mode);

        var description = props.location_description || (props.name !== title ? props.name : "");
        if (description) {
          var locationDescription = document.createElement("p");
          locationDescription.className = "station-detail-location";
          locationDescription.textContent = description;
          panel.appendChild(locationDescription);
        }

        var location = stationLocation(feature);
        if (location) {
          var actions = document.createElement("div");
          actions.className = "station-actions";
          [["view", labels.google_maps_view], ["walking", labels.google_maps_walk]].forEach(function (action) {
            var link = document.createElement("a");
            link.href = location[action[0]];
            link.textContent = action[1];
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            actions.appendChild(link);
          });
          panel.appendChild(actions);
        } else {
          paragraph(panel, labels.location_unavailable);
        }

        var associated = props.catalog_route_ids || [];
        if (associated.length) {
          var routeSection = document.createElement("section");
          routeSection.className = "station-connected-routes";
          var routeHeading = document.createElement("h3");
          routeHeading.textContent = labels.associated_routes;
          routeSection.appendChild(routeHeading);
          associated.forEach(function (id) {
            var button = document.createElement("button");
            button.type = "button";
            button.className = "station-route-link";
            button.textContent = name(id);
            button.dataset.associatedRoute = id;
            button.addEventListener("click", function () { choose("route", id, true); });
            routeSection.appendChild(button);
          });
          panel.appendChild(routeSection);
        } else {
          var noRoutes = document.createElement("p");
          noRoutes.className = "station-detail-muted";
          noRoutes.textContent = labels.no_routes;
          panel.appendChild(noRoutes);
        }

        if (props.fares && props.fares.length) {
          var fareSection = document.createElement("div");
          fareSection.className = "station-fare-lines";
          props.fares.forEach(function (fare) {
            var amount = fare.amount;
            if (amount) paragraph(fareSection, labels[fare.id] + ": PHP " + amount.min + "-" + amount.max);
          });
          panel.appendChild(fareSection);
        }

        var caveat = document.createElement("p");
        caveat.className = "station-detail-caveat";
        var caveatIcon = document.createElement("span");
        caveatIcon.innerHTML = symbol("warning");
        caveat.appendChild(caveatIcon);
        caveat.appendChild(document.createTextNode(" " + labels.unconfirmed_stops));
        panel.appendChild(caveat);

        var details = document.createElement("details");
        details.className = "station-source-details";
        var disclosureTitle = document.createElement("summary");
        disclosureTitle.textContent = labels.sources;
        details.appendChild(disclosureTitle);
        paragraph(details, props.id);
        paragraph(details, labels.google_maps_note);
        paragraph(details, props.notes);
        if (location) paragraph(details, location.point.join(", "));
        paragraph(details, props.source_note || props.source_type);
        paragraph(details, props.verification_status);
        paragraph(details, labels.source_warning);
        paragraph(details, labels.fare_caveat);
        panel.appendChild(details);

      }
    }
    heading.textContent = selection.kind === "station" ? title : labels.route_details + ": " + title;
    if (view !== "explore") {
      // Station details use a full-width card; do not turn the card into an inline chip.
      var icon = document.createElement("span"); icon.innerHTML = symbol(selection.kind === "station" ? "location" : "transfer"); heading.prepend(icon);
      Array.from(body.children).forEach(function (child) {
        if (child.tagName !== "P") return;
        if ([labels.unconfirmed_stops, labels.fare_change, labels.waiting_unknown].includes(child.textContent)) {
          child.className = "commuter-note";
          var noteIcon = document.createElement("span"); noteIcon.innerHTML = symbol(child.textContent === labels.waiting_unknown ? "clock" : "warning"); child.prepend(noteIcon);
        }
      });
    }
    document.getElementById("commuter-sheet-title").textContent = view === "station" && sheet.dataset.state !== "collapsed" ? labels.station_details : title;
    document.getElementById("commuter-sheet-summary").textContent = view === "station" ? labels[props.transport_type] : summary;
    page.dataset.selectionKind = selection.kind; page.dataset.selectionId = selection.id || ""; page.dataset.view = view;
    page.dataset.activeRouteId = activeRouteId || "";
    page.dataset.focusedFeature = selection.kind;
    update();
    if (selection.kind === "route") routeStatus(route, false);
  }
  function choose(kind, id, focus) {
    if (kind === "route" && !data.catalog.some(function (r) { return r.id === id; }) || kind === "station" && !features.some(function (f) { return f.properties.id === id; })) return;
    clearStep();
    if (kind === "route") {
      pendingFit = id;
      activeRouteId = id; delete page.dataset.activeLeg;
      var line = lines.get(id); if (line) line.setStyle({ color: "#16532c", weight: 4, opacity: 1 });
    } else pendingFit = null;
    selection = { kind: kind, id: id }; view = kind; render(); sheetBody.scrollTop = 0; setSheet("half");
    document.getElementById("commuter-selection-status").textContent = name(id);
    if (focus) heading.focus({ preventScroll: true });
    if (kind === "route") loadRoute(data.catalog.find(function (r) { return r.id === id; }));
  }
  exploreButton.addEventListener("click", function () {
    clearStep();
    view = "explore";
    if (selection.kind === "station") selection = { kind: "none", id: null };
    render(); sheetBody.scrollTop = 0; setSheet("half", false);
    search.focus({ preventScroll: true });
  });
  cards.forEach(function (card) {
    var button = card.querySelector("button"); button.hidden = false;
    button.addEventListener("click", function () { choose("station", card.dataset.id, true); });
  });
  groups.forEach(function (group) {
    var route = data.catalog.find(function (r) { return r.id === group.dataset.route; });
    group.addEventListener("click", function () { choose("route", route.id, true); });
    var modes = document.createElement("span"); modes.className = "route-modes";
    modes.innerHTML = Array.from(new Set(route.legs.flatMap(function (leg) { return leg.vehicle_types; }))).map(symbol).join(""); group.prepend(modes);
  });
  search.addEventListener("input", update); filter.addEventListener("change", update); showAll.addEventListener("change", update);
  document.getElementById("commuter-reset").addEventListener("click", function () {
    clearStep();
    search.value = ""; filter.value = ""; showAll.checked = false;
    selection = { kind: "none", id: null }; activeRouteId = null; pendingFit = null; view = "explore"; clearTimeout(fitTimer); render();
    if (map) map.setView([16.0266, 120.4524], 12, { animate: false });
  });
  function initializeMap() {
    if (map || !window.L) return;
    try {
      var reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
      map = L.map("commuter-map", { zoomSnap: .25, touchZoom: true, dragging: true, scrollWheelZoom: true, zoomAnimation: !reducedMotion, fadeAnimation: !reducedMotion, markerZoomAnimation: !reducedMotion }).setView([16.0266, 120.4524], 12);
      map.on("dragstart zoomstart", function () { clearTimeout(fitTimer); });
      function cancelPendingFit() { pendingFit = null; clearTimeout(fitTimer); }
      map.getContainer().addEventListener("pointerdown", cancelPendingFit);
      map.getContainer().addEventListener("wheel", cancelPendingFit, { passive: true });
      map.getContainer().addEventListener("keydown", cancelPendingFit);
      var pane = map.createPane("commuter-boundaries"); pane.style.zIndex = "350"; pane.style.pointerEvents = "none";
      function loadBoundary() {
        if (routeLoads.size) { boundaryTimer = setTimeout(loadBoundary, 250); return; }
        fetch(map.getContainer().dataset.boundaryUrl, { signal: AbortSignal.timeout(15000), priority: "low" }).then(function (response) { if (!response.ok) throw new Error("Boundary unavailable"); return response.json(); }).then(function (boundary) {
        L.geoJSON(boundary, { pane: "commuter-boundaries", interactive: false, bubblingMouseEvents: false, style: { color: "#557467", weight: 1, opacity: .55, fillColor: "#6c967d", fillOpacity: .08 } }).addTo(map);
        map.attributionControl.addAttribution(labels.boundary_note);
      }).catch(function () { /* Optional context cannot block the directory. */ });
      }
      boundaryTimer = setTimeout(loadBoundary, 1200);
      var tiles = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors', maxZoom: 19 });
      var tileFailed = false; status.textContent = labels.loading;
      tiles.on("tileerror", function () { tileFailed = true; status.textContent = labels.tiles_failed; });
      tiles.on("load", function () { if (!tileFailed) status.textContent = labels.ready; }); tiles.addTo(map);
      features.forEach(function (feature) {
        var location = stationLocation(feature);
        if (!location) return;
        var props = feature.properties, title = name(props.id) + "; " + labels[props.transport_type];
        var marker = L.marker(location.point, { title: title, alt: title, keyboard: true, icon: L.divIcon({ className: "transport-marker transport-icon-" + props.transport_type, html: symbol(props.transport_type), iconSize: [44, 44], iconAnchor: [22, 22] }) });
        marker.on("click", function () { choose("station", props.id, true); });
        marker.on("add", function () {
          var element = marker.getElement(); element.dataset.id = props.id; element.setAttribute("aria-label", title);
          element.onkeydown = function (event) {
            if (event.key === "Enter" || event.key === " ") { event.preventDefault(); event.stopPropagation(); choose("station", props.id, true); }
          };
        }); markers.set(props.id, marker);
      });
      if (activeRouteId) {
        var currentRoute = data.catalog.find(function (r) { return r.id === activeRouteId; });
        createRouteLine(currentRoute);
        if (!routeLoads.has(activeRouteId) && pendingFit === activeRouteId && selection.kind === "route") { pendingFit = null; scheduleFit(); }
      }
      update();
      map.attributionControl.addAttribution('Road geometry: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | <a href="https://www.openstreetmap.org/fixthemap">Fix the map</a>');
    } catch (error) { status.textContent = labels.fallback; map = null; }
  }
  function cancelDrag() {
    if (!drag) return;
    var old = drag; drag = null; suppressClick = old.moved;
    sheet.classList.remove("dragging"); sheet.style.removeProperty("height");
    if (toolbar.hasPointerCapture(old.id)) toolbar.releasePointerCapture(old.id);
    setSheet(old.state, false);
  }
  function resize() {
    cancelDrag();
    clearTimeout(fitTimer);
    if (frame) cancelAnimationFrame(frame);
    frame = requestAnimationFrame(function () {
      var viewport = window.visualViewport;
      var top = Math.max(0, page.getBoundingClientRect().top - (viewport ? viewport.offsetTop : 0));
      var available = Math.max(96, (viewport ? viewport.height : innerHeight) - top);
      page.style.setProperty("--commuter-height", available + "px");
      var maximum = Math.max(96, matchMedia("(min-width: 900px)").matches ? Math.min(available * .9, available - 110) : available * .9);
      var minimum = Math.min(96 + (parseFloat(getComputedStyle(sheet).paddingBottom) || 0), maximum - 16);
       stops = [minimum, Math.max(minimum + 8, Math.min(available * .6, maximum - 8)), maximum];
      sheet.style.setProperty("--sheet-header-height", Math.max(44, Math.min(72, minimum - 20)) + "px");
       setSheet(sheet.dataset.state || "half", false);
      if (map) map.invalidateSize({ pan: false });
    });
  }
  toolbar.addEventListener("pointerdown", function (event) {
    if (drag || !event.isPrimary || event.button !== 0 || event.target.closest("button, input, select, summary, details, a") || matchMedia("(min-width: 900px)").matches) return;
    suppressClick = false;
    drag = { id: event.pointerId, y: event.clientY, height: sheet.getBoundingClientRect().height, state: sheet.dataset.state, moved: false, samples: [{ y: event.clientY, time: event.timeStamp }] };
    toolbar.setPointerCapture(event.pointerId);
  });
  toolbar.addEventListener("pointermove", function (event) {
    if (!drag || drag.id !== event.pointerId) return;
    var delta = drag.y - event.clientY;
    if (Math.abs(delta) >= DRAG_THRESHOLD) drag.moved = true;
    drag.samples.push({ y: event.clientY, time: event.timeStamp });
    drag.samples = drag.samples.filter(function (sample) { return sample.time >= event.timeStamp - SAMPLE_WINDOW; });
    if (!drag.moved) return;
    sheet.classList.add("dragging"); sheetBody.hidden = false;
    sheet.style.height = Math.max(stops[0], Math.min(stops[2], drag.height + delta)) + "px";
  });
  toolbar.addEventListener("pointerup", function (event) {
    if (!drag || drag.id !== event.pointerId) return;
    var old = drag, height = sheet.getBoundingClientRect().height, first = old.samples[0];
    var velocity = (first.y - event.clientY) / Math.max(1, event.timeStamp - first.time);
    var index = stops.reduce(function (best, value, i) { return Math.abs(value - height) < Math.abs(stops[best] - height) ? i : best; }, 0);
    if (old.moved && Math.abs(velocity) >= FLING_VELOCITY) index = Math.max(0, Math.min(2, states.indexOf(old.state) + (velocity > 0 ? 1 : -1)));
    drag = null; suppressClick = old.moved;
    sheet.classList.remove("dragging"); sheet.style.removeProperty("height");
    if (toolbar.hasPointerCapture(old.id)) toolbar.releasePointerCapture(old.id);
    setSheet(old.moved ? states[index] : old.state, old.moved);
  });
  toolbar.addEventListener("pointercancel", function (event) { if (drag && drag.id === event.pointerId) cancelDrag(); });
  toolbar.addEventListener("lostpointercapture", function (event) { if (drag && drag.id === event.pointerId) cancelDrag(); });
  toolbar.addEventListener("click", function (event) {
    if (event.target.closest("button, input, select, summary, details, a")) return;
    if (suppressClick) { suppressClick = false; event.preventDefault(); return; }
    setSheet(sheet.dataset.state === "collapsed" ? "half" : "collapsed");
  });
  handle.addEventListener("keydown", function (event) {
    if (["Enter", " "].includes(event.key)) { event.preventDefault(); setSheet(sheet.dataset.state === "collapsed" ? "half" : "collapsed"); return; }
    if (!["ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) return;
    event.preventDefault(); var index = states.indexOf(sheet.dataset.state);
    setSheet(event.key === "Home" ? "collapsed" : event.key === "End" ? "expanded" : states[Math.max(0, Math.min(2, index + (event.key === "ArrowUp" ? 1 : -1)))]);
  });
  page.querySelector(".sheet-close").addEventListener("click", function () { handle.focus({ preventScroll: true }); setSheet("collapsed"); });
  page.querySelectorAll("[data-sheet-state]").forEach(function (button) { button.addEventListener("click", function () { setSheet(button.dataset.sheetState); page.querySelector(".sheet-size-disclosure").open = false; handle.focus({ preventScroll: true }); }); });
  page.querySelector(".commuter-controls").hidden = false;
  page.querySelector(".sheet-size-disclosure").hidden = false;
  page.querySelector(".sheet-close").hidden = false;
  page.classList.add("enhanced"); render(); setSheet("half", false); resize();
  window.addEventListener("resize", resize);
  if (window.visualViewport) { visualViewport.addEventListener("resize", resize); visualViewport.addEventListener("scroll", resize); }
  page.dataset.ready = "true";
  var library = document.createElement("script"); library.src = "/assets/vendor/leaflet-1.9.4/leaflet.js";
  library.onload = initializeMap; library.onerror = function () { status.textContent = labels.fallback; };
  document.head.appendChild(library);
})();
