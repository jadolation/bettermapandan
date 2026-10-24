(function () {
  "use strict";
  var page = document.getElementById("commuter-page");
  if (!page) return;
  var data = JSON.parse(document.getElementById("commuter-data").textContent);
  var labels = data.labels;
  var sheet = document.getElementById("commuter-sheet");
  var sheetBody = document.getElementById("commuter-sheet-body");
  var cards = Array.from(page.querySelectorAll(".transport-card"));
  var search = document.getElementById("commuter-search");
  var filter = document.getElementById("commuter-type");
  var status = document.getElementById("commuter-map-status");
  var features = data.features.concat(data.observations || []);
  var markers = new Map();
  var lines = new Map();
  var map;
  var selectedPoint = null;
  var selectedId = null;
  var showAll = document.getElementById("commuter-show-all");
  var reopen = page.querySelector(".sheet-reopen");
  var frame;
  var pendingFit = false;
  var paths = {
    minibus: '<path d="M5 2h14a3 3 0 0 1 3 3v13h-2v3h-4v-3H8v3H4v-3H2V5a3 3 0 0 1 3-3Zm0 4v6h14V6H5Zm1 8a2 2 0 1 0 0 4 2 2 0 0 0 0-4Zm12 0a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z"/>',
    jeepney: '<path d="M3 4h15v3h3v5h2v6h-2v3h-4v-3H7v3H3v-3H1V9h2V4Zm3 3v5h4V7H6Zm6 0v5h4V7h-4Zm6 3v2h2v-2h-2ZM5 14a2 2 0 1 0 0 4 2 2 0 0 0 0-4Zm14 0a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z"/>',
    tricycle: '<path d="M1 5h13v3h-1v7h3l-3-5 3-2h3v2h-2l3 5a4 4 0 1 1-4 4H9a4 4 0 1 1-7-4V8H1V5Zm4 3v6h5V8H5ZM5 17a2 2 0 1 0 0 4 2 2 0 0 0 0-4Zm15 0a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z"/>',
    transfer: '<path d="m16 2 7 6-7 6v-4H3V6h13V2ZM8 10v4h13v4H8v4l-7-6 7-6Z"/>',
    money: '<path fill-rule="evenodd" d="M1 5h22v14H1V5Zm3 3v8h16V8H4Zm8 1a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z"/>'
  };
  function symbol(mode) {
    return '<svg class="transport-symbol" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' + (paths[mode] || paths.transfer) + '</svg>';
  }
  function padding() {
    var rect = map.getContainer().getBoundingClientRect();
    var panel = sheet.getBoundingClientRect();
    var top = Math.max(32, page.querySelector(".commuter-hero").getBoundingClientRect().bottom - rect.top + 16);
    var side = window.matchMedia("(min-width: 900px)").matches;
    var hidden = sheet.dataset.state === "hidden";
    return { paddingTopLeft: [side && !hidden ? panel.right - rect.left + 24 : 32, top],
      paddingBottomRight: [32, side ? 32 : Math.min((hidden ? 52 : panel.height) + 24, rect.height - top - 80)], maxZoom: 16, animate: false };
  }
  function fitVisible() {
    if (!map) return;
    var bounds = L.latLngBounds([]);
    if (selectedPoint) bounds.extend(selectedPoint);
    else {
      lines.forEach(function (line) { if (map.hasLayer(line)) bounds.extend(line.getBounds()); });
      if (bounds.isValid()) {
        page.querySelectorAll(".candidate-toggle:checked").forEach(function (input) {
          var route = data.catalog.find(function (r) { return r.id === input.closest("fieldset").dataset.route; });
          features.forEach(function (f) {
            if (f.properties.id === route.origin_id || f.properties.id === route.destination_id) bounds.extend([f.geometry.coordinates[1], f.geometry.coordinates[0]]);
          });
        });
      }
      features.forEach(function (f) {
        var marker = markers.get(f.properties.id);
        if (marker && map.hasLayer(marker)) bounds.extend([f.geometry.coordinates[1], f.geometry.coordinates[0]]);
      });
    }
    if (bounds.isValid()) {
      // Preserve the existing route/selection fit padding at whole zoom levels.
      var snap = map.options.zoomSnap;
      map.options.zoomSnap = 1;
      try { map.fitBounds(bounds, padding()); }
      finally { map.options.zoomSnap = snap; }
    }
  }
  function resize(refit) {
    pendingFit = pendingFit || refit === true;
    if (frame) cancelAnimationFrame(frame);
    frame = requestAnimationFrame(function () {
      var viewport = window.visualViewport;
      var top = Math.max(0, page.getBoundingClientRect().top - (viewport ? viewport.offsetTop : 0));
      page.style.setProperty("--commuter-height", Math.max(180, (viewport ? viewport.height : innerHeight) - top) + "px");
      // Browser chrome and page zoom resize the visual viewport, not the selection.
      if (map) { map.invalidateSize({ pan: false }); if (pendingFit) fitVisible(); }
      pendingFit = false;
    });
  }
  function setSheet(state) {
    var moveFocus = sheet.contains(document.activeElement) && (state === "hidden" || sheetBody.contains(document.activeElement) && state === "collapsed");
    sheet.dataset.state = state;
    sheetBody.hidden = state === "collapsed" || state === "hidden";
    sheet.inert = state === "hidden";
    reopen.hidden = state !== "hidden";
    if (moveFocus) (state === "hidden" ? reopen : page.querySelector(".sheet-handle")).focus({ preventScroll: true });
    page.querySelectorAll("[data-sheet-state]").forEach(function (button) {
      button.setAttribute("aria-pressed", String(button.dataset.sheetState === state));
      button.setAttribute("aria-expanded", String(state !== "collapsed" && state !== "hidden"));
    });
    resize(true);
  }
  function select(feature, focus) {
    var id = feature.properties.id;
    var card = cards.find(function (item) { return item.dataset.id === id; });
    cards.forEach(function (item) {
      item.classList.toggle("selected", item === card);
      item.querySelector("button").setAttribute("aria-pressed", String(item === card));
    });
    markers.forEach(function (marker, key) {
      if (marker.getElement()) marker.getElement().classList.toggle("selected", key === id);
    });
    document.getElementById("commuter-info").hidden = false;
    document.getElementById("commuter-info-title").textContent = labels[id];
    var body = document.getElementById("commuter-info-body");
    body.replaceChildren();
    if (card) Array.from(card.children).forEach(function (child) {
      if (child.tagName !== "H3" && child.tagName !== "BUTTON") body.appendChild(child.cloneNode(true));
    });
    else {
      var note = document.createElement("p"); note.textContent = labels.observed_place; body.appendChild(note);
    }
    selectedPoint = [feature.geometry.coordinates[1], feature.geometry.coordinates[0]];
    selectedId = id;
    update();
    if (map) setSheet(["collapsed", "hidden"].includes(sheet.dataset.state) ? "half" : sheet.dataset.state);
    if (focus) document.getElementById("commuter-info").focus({ preventScroll: true });
    if (map) requestAnimationFrame(function () {
      sheetBody.scrollTop += document.getElementById("commuter-info").getBoundingClientRect().top - sheetBody.getBoundingClientRect().top;
    });
  }
  function update() {
    var count = 0;
    var routeCount = 0;
    var query = search.value.trim().toLocaleLowerCase();
    var routePlaces = new Set();
    page.querySelectorAll(".candidate-toggle:checked").forEach(function (input) {
      var route = data.catalog.find(function (r) { return r.id === input.closest("fieldset").dataset.route; });
      route.marker_ids.forEach(function (id) { routePlaces.add(id); });
    });
    cards.forEach(function (card) {
      var visible = (!filter.value || card.dataset.type === filter.value) && card.textContent.toLocaleLowerCase().includes(query);
      card.hidden = !visible;
    });
    page.querySelectorAll("#commuter-lines fieldset").forEach(function (group) {
      group.hidden = !!((filter.value && group.dataset.type !== filter.value) || !group.textContent.toLocaleLowerCase().includes(query));
      if (!group.hidden) routeCount++;
    });
    features.forEach(function (feature) {
      var props = feature.properties;
      var marker = markers.get(props.id);
      var matches = (!filter.value || props.transport_type === filter.value) && (labels[props.id] || "").toLocaleLowerCase().includes(query);
      var visible = props.id === selectedId || routePlaces.has(props.id) || showAll.checked && matches;
      if (matches) count++;
      if (map && marker) {
        if (visible && !map.hasLayer(marker)) marker.addTo(map);
        else if (!visible && map.hasLayer(marker)) map.removeLayer(marker);
      }
    });
    document.getElementById("commuter-count").textContent = labels.routes_results + ": " + routeCount + " / " + labels.results + ": " + count;
  }
  page.querySelector(".commuter-controls").hidden = false;
  cards.forEach(function (card) {
    var button = card.querySelector("button");
    button.hidden = false;
    button.setAttribute("aria-pressed", "false");
    button.addEventListener("click", function () { select(features.find(function (f) { return f.properties.id === card.dataset.id; }), true); });
  });
  search.addEventListener("input", update);
  filter.addEventListener("change", update);
  showAll.addEventListener("change", function () { update(); fitVisible(); });
  document.getElementById("commuter-reset").addEventListener("click", function () {
    search.value = ""; filter.value = ""; selectedPoint = null; selectedId = null; showAll.checked = false;
    lines.forEach(function (line) { if (map && map.hasLayer(line)) map.removeLayer(line); });
    page.querySelectorAll(".candidate-toggle").forEach(function (input) { input.checked = false; });
    page.querySelectorAll(".selected").forEach(function (item) { item.classList.remove("selected"); });
    cards.forEach(function (card) { card.querySelector("button").setAttribute("aria-pressed", "false"); });
    document.getElementById("commuter-info").hidden = true;
    update();
    if (map) map.setView([16.0266, 120.4524], 12, { animate: false });
    fitVisible();
  });
  if (window.L) {
    try {
      var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      // Keep native pinch movement; settle gently instead of snapping to a whole zoom level.
      map = L.map("commuter-map", { zoomSnap: 0.25, touchZoom: true, dragging: true, scrollWheelZoom: true, zoomAnimation: !reducedMotion, fadeAnimation: !reducedMotion, markerZoomAnimation: !reducedMotion });
      map.setView([16.0266, 120.4524], 12);
      var boundaryPane = map.createPane("commuter-boundaries");
      boundaryPane.style.zIndex = "350";
      boundaryPane.style.pointerEvents = "none";
      fetch(map.getContainer().dataset.boundaryUrl).then(function (response) {
        if (!response.ok) throw new Error("Boundary unavailable");
        return response.json();
      }).then(function (boundary) {
        L.geoJSON(boundary, { pane: "commuter-boundaries", interactive: false, bubblingMouseEvents: false,
          style: { color: "#557467", weight: 1, opacity: .55, fillColor: "#6c967d", fillOpacity: .08 } }).addTo(map);
        map.attributionControl.addAttribution(labels.boundary_note);
      }).catch(function () { /* Optional context must not interrupt the commuter map. */ });
      var tiles = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors', maxZoom: 19
      });
      status.textContent = labels.loading;
      var tileFailed = false;
      tiles.on("tileerror", function () { tileFailed = true; status.textContent = labels.tiles_failed; });
      tiles.on("load", function () { if (!tileFailed) status.textContent = labels.ready; });
      tiles.addTo(map);
      features.forEach(function (feature) {
        var props = feature.properties;
        var name = labels[props.id] + "; " + labels[props.transport_type];
        var marker = L.marker([feature.geometry.coordinates[1], feature.geometry.coordinates[0]], {
          title: name, alt: name, keyboard: true,
          icon: L.divIcon({ className: "transport-marker transport-icon-" + props.transport_type,
            html: symbol(props.transport_type), iconSize: [44, 44], iconAnchor: [22, 22] })
        });
        marker.on("click", function () { select(feature, true); });
        marker.on("add", function () {
          marker.getElement().setAttribute("aria-label", name);
          marker.getElement().dataset.id = props.id;
          marker.getElement().classList.toggle("selected", selectedId === props.id);
          marker.getElement().onkeydown = function (event) {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault(); event.stopPropagation(); select(feature, true);
          }
          };
        });
        markers.set(props.id, marker);
      });
      data.catalog.forEach(function (corridor, index) {
        var direction = 0;
        var group = page.querySelector('[data-route="' + corridor.id + '"]');
        var modes = document.createElement("span"); modes.className = "route-modes";
        var vehicleTypes = Array.from(new Set(corridor.legs.flatMap(function (leg) { return leg.vehicle_types; })));
        modes.innerHTML = vehicleTypes.map(symbol).join("") + (corridor.transfer_count ? symbol("transfer") : "");
        modes.setAttribute("role", "img");
        modes.setAttribute("aria-label", vehicleTypes.map(function (mode) { return labels[mode]; }).join(", ") + (corridor.transfer_count ? "; " + labels.transfer : ""));
        group.querySelector("legend").prepend(modes);
        group.querySelector(".fare-summary").insertAdjacentHTML("afterbegin", symbol("money") + " ");
        var label = document.createElement("label");
        var input = document.createElement("input");
        input.type = "checkbox"; input.className = "candidate-toggle";
        input.setAttribute("aria-controls", "commuter-map");
        label.appendChild(input);
        var directionLabel = document.createElement("span");
        directionLabel.setAttribute("aria-live", "polite"); label.appendChild(directionLabel);
        group.insertBefore(label, group.querySelector("details"));
        var note = document.createElement("p"); note.setAttribute("role", "status"); group.appendChild(note);
        var candidates = corridor.directions.map(function (ids, i) {
          var shapes = ids.map(function (id) { return data.shapes.find(function (item) { return item.properties.pattern_id === id; }); }).filter(Boolean);
          var line = shapes.length ? L.geoJSON({ type: "FeatureCollection", features: shapes }, { style: { color: ["#185da3", "#a74608", "#087c75", "#713da6"][index % 4], weight: 4, dashArray: "10 7" } }) : null;
          if (line) lines.set(corridor.id + ":" + i, line);
          return { line: line, partial: shapes.length < ids.length || shapes.some(function (s) { return !!s.properties.endpoint_caveat; }) };
        });
        function render(fit) {
          candidates.forEach(function (candidate) { if (candidate.line && map.hasLayer(candidate.line)) map.removeLayer(candidate.line); });
          var ids = corridor.directions[direction];
          var line = candidates[direction].line;
          input.dataset.pattern = ids.join("+");
          directionLabel.textContent = labels.show_route;
          input.disabled = !line;
          note.textContent = !line ? labels.withheld : labels.partial_geometry;
          note.hidden = !!line && !candidates[direction].partial;
          if (line) group.querySelector("details").appendChild(note);
          else group.appendChild(note);
          if (input.checked && line) line.addTo(map);
          group.classList.toggle("selected", input.checked);
          if (fit) {
            selectedPoint = null; selectedId = null;
            document.getElementById("commuter-info").hidden = true;
            update();
            if (input.checked && !window.matchMedia("(min-width: 900px)").matches) setSheet("hidden");
            else resize(true);
          }
        }
        input.addEventListener("change", function () { render(true); });
        render(false);
      });
      map.attributionControl.addAttribution('Road geometry: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | <a href="https://www.openstreetmap.org/fixthemap">Fix the map</a>');
      page.classList.add("enhanced");
      page.querySelector(".sheet-sizes").hidden = false;
      page.querySelectorAll("[data-sheet-state]").forEach(function (button) {
        button.addEventListener("click", function () {
          setSheet(button.dataset.sheetState);
          if (button === reopen) page.querySelector(".sheet-handle").focus({ preventScroll: true });
        });
      });
      var handle = page.querySelector(".sheet-handle");
      var drag = null;
      var dragged = false;
      var states = ["hidden", "collapsed", "half", "expanded"];
      function heights() { return [0, 58, page.clientHeight * .52, page.clientHeight]; }
      handle.addEventListener("pointerdown", function (event) {
        if (event.button !== 0 || window.matchMedia("(min-width: 900px)").matches) return;
        dragged = false;
        drag = { id: event.pointerId, y: event.clientY, height: sheet.getBoundingClientRect().height, state: sheet.dataset.state };
        handle.setPointerCapture(event.pointerId);
      });
      handle.addEventListener("pointermove", function (event) {
        if (!drag || drag.id !== event.pointerId) return;
        var delta = drag.y - event.clientY;
        if (Math.abs(delta) > 8) dragged = true;
        if (!dragged) return;
        sheetBody.hidden = false;
        sheet.style.height = Math.max(0, Math.min(page.clientHeight, drag.height + delta)) + "px";
      });
      function endDrag(event) {
        if (!drag || drag.id !== event.pointerId) return;
        var state = drag.state;
        if (dragged && event.type !== "pointercancel") {
          var height = Math.max(0, Math.min(page.clientHeight, drag.height + drag.y - event.clientY));
          var sizes = heights();
          state = states[sizes.reduce(function (best, value, i) { return Math.abs(value - height) < Math.abs(sizes[best] - height) ? i : best; }, 0)];
        }
        drag = null;
        sheet.style.removeProperty("height");
        setSheet(state);
      }
      handle.addEventListener("pointerup", endDrag);
      handle.addEventListener("pointercancel", endDrag);
      handle.addEventListener("click", function () {
        if (!dragged) setSheet(sheet.dataset.state === "expanded" ? "half" : "expanded");
        dragged = false;
      });
      handle.addEventListener("keydown", function (event) {
        if (!["ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) return;
        event.preventDefault();
        var index = states.indexOf(sheet.dataset.state);
        setSheet(event.key === "Home" ? "hidden" : event.key === "End" ? "expanded" : states[Math.max(0, Math.min(3, index + (event.key === "ArrowUp" ? 1 : -1)))]);
      });
      window.addEventListener("resize", resize);
      if (window.visualViewport) { window.visualViewport.addEventListener("resize", resize); window.visualViewport.addEventListener("scroll", resize); }
      setSheet("collapsed");
    } catch (error) {
      status.textContent = labels.fallback; sheetBody.hidden = false; page.classList.remove("enhanced");
    }
  }
  update();
  page.dataset.ready = "true";
})();
