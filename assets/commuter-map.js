(function () {
  "use strict";
  var page = document.getElementById("commuter-page");
  if (!page) return;
  var data = JSON.parse(document.getElementById("commuter-data").textContent);
  var labels = data.labels;
  var sheet = document.getElementById("commuter-sheet");
  var cards = Array.from(page.querySelectorAll(".transport-card"));
  var search = document.getElementById("commuter-search");
  var filter = document.getElementById("commuter-type");
  var status = document.getElementById("commuter-map-status");
  var markers = new Map();
  var lines = new Map();
  var map;
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
    document.getElementById("commuter-info-title").textContent = labels[id];
    var body = document.getElementById("commuter-info-body");
    body.replaceChildren();
    Array.from(card.children).forEach(function (child) {
      if (child.tagName !== "H3" && child.tagName !== "BUTTON") body.appendChild(child.cloneNode(true));
    });
    sheet.open = true;
    if (map) map.panTo([feature.geometry.coordinates[1], feature.geometry.coordinates[0]], {
      animate: !window.matchMedia("(prefers-reduced-motion: reduce)").matches
    });
    if (focus) document.getElementById("commuter-info").focus({ preventScroll: true });
  }
  function update() {
    var count = 0;
    cards.forEach(function (card) {
      var visible = (!filter.value || card.dataset.type === filter.value) &&
        card.textContent.toLocaleLowerCase().includes(search.value.trim().toLocaleLowerCase());
      card.hidden = !visible;
      if (visible) count++;
      var marker = markers.get(card.dataset.id);
      if (map && marker) {
        if (visible && !map.hasLayer(marker)) marker.addTo(map);
        else if (!visible && map.hasLayer(marker)) map.removeLayer(marker);
      }
    });
    document.getElementById("commuter-count").textContent = labels.results + ": " + count;
  }
  page.querySelector(".commuter-controls").hidden = false;
  cards.forEach(function (card) {
    var button = card.querySelector("button");
    button.hidden = false;
    button.setAttribute("aria-pressed", "false");
    button.addEventListener("click", function () {
      select(data.features.find(function (feature) { return feature.properties.id === card.dataset.id; }), true);
    });
  });
  search.addEventListener("input", update);
  filter.addEventListener("change", update);
  document.getElementById("commuter-reset").addEventListener("click", function () {
    search.value = ""; filter.value = ""; update();
    lines.forEach(function (line) { if (map.hasLayer(line)) map.removeLayer(line); });
    page.querySelectorAll(".candidate-toggle").forEach(function (input) { input.checked = false; });
    if (map) map.fitBounds(data.features.map(function (feature) { return [feature.geometry.coordinates[1], feature.geometry.coordinates[0]]; }), { padding: [32, 32], maxZoom: 14 });
  });
  if (window.L) {
    try {
      map = L.map("commuter-map", { scrollWheelZoom: false });
      map.fitBounds(data.features.map(function (feature) { return [feature.geometry.coordinates[1], feature.geometry.coordinates[0]]; }), { padding: [32, 32], maxZoom: 14 });
      var tiles = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors', maxZoom: 19
      });
      status.textContent = labels.loading;
      var tileFailed = false;
      tiles.on("tileerror", function () { tileFailed = true; status.textContent = labels.tiles_failed; });
      tiles.on("load", function () { if (!tileFailed) status.textContent = labels.ready; });
      tiles.addTo(map);
      data.features.forEach(function (feature) {
        var props = feature.properties;
        var marker = L.marker([feature.geometry.coordinates[1], feature.geometry.coordinates[0]], {
          title: labels[props.id], alt: labels[props.id], keyboard: true,
          icon: L.divIcon({ className: "transport-marker transport-icon-" + props.transport_type,
             html: '<span class="transport-dot" aria-hidden="true"></span>', iconSize: [44, 44], iconAnchor: [22, 22] })
        }).addTo(map);
        marker.on("click", function () { select(feature, true); });
        marker.getElement().addEventListener("keydown", function (event) {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            event.stopPropagation();
            select(feature, true);
          }
        });
        markers.set(props.id, marker);
      });
      var controls = document.getElementById("commuter-lines");
      controls.hidden = false;
      [["minibus", "mini-mapandan-dagupan-outbound", "mini-dagupan-mapandan-return"],
       ["jeepney", "jeep-mapandan-mangaldan", "jeep-mangaldan-mapandan"]].forEach(function (corridor, index) {
        var direction = 1;
        var group = document.createElement("fieldset");
        group.className = "passenger-geometry";
        var legend = document.createElement("legend");
        legend.textContent = labels[corridor[0]];
        group.appendChild(legend);
        var label = document.createElement("label");
        var input = document.createElement("input");
        input.type = "checkbox"; input.className = "candidate-toggle";
        input.setAttribute("aria-controls", "commuter-map");
        label.appendChild(input);
        var directionLabel = document.createElement("span");
        directionLabel.setAttribute("aria-live", "polite");
        label.appendChild(directionLabel);
        group.appendChild(label);
        var swap = document.createElement("button");
        swap.type = "button"; swap.className = "candidate-swap";
        swap.textContent = labels.swap;
        swap.setAttribute("aria-controls", "commuter-map");
        group.appendChild(swap);
        var note = document.createElement("p");
        note.textContent = labels.unavailable;
        note.setAttribute("role", "status");
        group.appendChild(note);
        controls.appendChild(group);
        corridor.slice(1).forEach(function (id) {
          var shape = data.shapes.find(function (item) { return item.properties.pattern_id === id; });
          if (shape) lines.set(id, L.geoJSON(shape, { style: { color: ["#185da3", "#a74608"][index], weight: 4, dashArray: "10 7" } }));
        });
        function render(fit) {
          corridor.slice(1).forEach(function (id) {
            var old = lines.get(id);
            if (old && map.hasLayer(old)) map.removeLayer(old);
          });
          var id = corridor[direction];
          var line = lines.get(id);
          input.dataset.pattern = id;
          directionLabel.textContent = labels[id];
          input.disabled = !line;
          note.hidden = !!line;
          if (input.checked && line) {
            line.addTo(map);
            if (fit) map.fitBounds(line.getBounds(), { padding: [32, 32], maxZoom: 16, animate: false });
          }
        }
        input.addEventListener("change", function () { render(input.checked); });
        swap.addEventListener("click", function () {
          direction = direction === 1 ? 2 : 1;
          render(input.checked);
        });
        render(false);
      });
      map.attributionControl.addAttribution('Road geometry: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | <a href="https://www.openstreetmap.org/fixthemap">Fix the map</a>');
      if (window.matchMedia("(max-width: 719px)").matches) sheet.open = false;
    } catch (error) {
      status.textContent = labels.fallback;
      sheet.open = true;
    }
  }
  update();
  page.dataset.ready = "true";
})();
