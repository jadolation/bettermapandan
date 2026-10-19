/* Depends on Leaflet 1.9.4. Public facilities are gated by the Python build. */
(function () {
  "use strict";

  function escapeHtml(value) {
    return String(value == null ? "" : value).replace(/&/g, "&amp;")
      .replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function validPoint(coords) {
    return Array.isArray(coords) && coords.length === 2 &&
      coords.every(function (n) { return typeof n === "number" && Number.isFinite(n); }) &&
      Math.abs(coords[0]) <= 180 && Math.abs(coords[1]) <= 90;
  }

  function initMap() {
    var el = document.getElementById("gis-map");
    if (!el || el.dataset.initialized) return;
    el.dataset.initialized = "true";
    var messages = document.getElementById("gis-page").dataset;
    var fallback = document.getElementById("gis-map-fallback");
    var status = document.getElementById("gis-map-status");
    function message(key) { return messages[key] || ""; }
    function fail(key) {
      fallback.hidden = false;
      status.textContent = message(key);
    }
    if (typeof L === "undefined") {
      el.hidden = true;
      fail("libraryError");
      return;
    }

    try {
      var meta = (window.GIS_LAYERS || {}).metadata || {};
      var center = validPoint(meta.default_map_center) ? meta.default_map_center : [120.455, 16.03];
      var zoom = Number.isFinite(meta.default_zoom) && meta.default_zoom >= 0 && meta.default_zoom <= 19
        ? meta.default_zoom : 14;
      var map = L.map("gis-map").setView([center[1], center[0]], zoom);
      var tiles = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      });
      var tileFailed = false;
      tiles.on("tileerror", function () {
        tileFailed = true;
        fail("tileError");
      });
      tiles.on("load", function () {
        if (!tileFailed) {
          status.textContent = message("ready");
          fallback.hidden = true;
        }
      });
      tiles.addTo(map);

      var overlays = {};
      var bounds = meta.coordinate_bounds;
      if (bounds && validPoint([bounds.west, bounds.south]) &&
          validPoint([bounds.east, bounds.north]) && bounds.south < bounds.north && bounds.west < bounds.east) {
        var extent = L.layerGroup().addTo(map);
        L.rectangle([[bounds.south, bounds.west], [bounds.north, bounds.east]], {
          color: "#3b82f6", weight: 2, dashArray: "6,4", fill: false, interactive: false,
        }).addTo(extent);
        overlays[message("extent")] = extent;
      }

      // Validate defensively, but never substitute the canonical candidate inventory.
      var candidates = (window.GIS_FACILITIES || {}).features;
      var groups = new Map();
      var count = 0;
      (Array.isArray(candidates) ? candidates : []).forEach(function (feature) {
        if (!feature || feature.type !== "Feature" || !feature.properties || !feature.geometry ||
            feature.geometry.type !== "Point" || !validPoint(feature.geometry.coordinates)) return;
        var props = feature.properties;
        if (["source_verified", "field_verified"].indexOf(props.verification_status) === -1 ||
            typeof props.name !== "string" || !props.name.trim()) return;
        var coords = feature.geometry.coordinates;
        var key = JSON.stringify(coords);
        if (!groups.has(key)) groups.set(key, { coords: coords, records: [] });
        groups.get(key).records.push(props);
        count += 1;
      });

      var facilities = L.layerGroup().addTo(map);
      groups.forEach(function (group) {
        var popup = group.records.length > 1 ? "<p>" + escapeHtml(message("shared")) + "</p>" : "";
        popup += "<ul>" + group.records.map(function (props) {
          var method = {
            source_reported: props.location_precision === "approximate" ? "approximateSource" : "sourceReported",
            plus_code_cell_center: "cellCenter", polygon_centroid: "centroid", field_observation: "fieldPosition",
          }[props.coordinate_method];
          var provenance = props.provenance || {};
          var source = typeof provenance.source === "string" ? provenance.source : "";
          var url = typeof provenance.source_url === "string" && /^https?:\/\//i.test(provenance.source_url)
            ? provenance.source_url : null;
          return "<li><strong>" + escapeHtml(props.name) + "</strong><br>" +
            escapeHtml(props.category) + "<br>" + escapeHtml(props.address) + "<br>" +
            escapeHtml(message(method || "unknownPrecision")) + "<br>" +
            escapeHtml(message("source")) + ": " + (url ? '<a href="' + escapeHtml(url) + '">' +
              escapeHtml(source) + "</a>" : escapeHtml(source)) + "<br>" +
            escapeHtml(message("checked")) + ": " + escapeHtml(provenance.last_verified) + "</li>";
        }).join("") + "</ul>";
        L.circleMarker([group.coords[1], group.coords[0]], {
          radius: 7, fillColor: "#2d6b1f", color: "#2d6b1f", weight: 1, fillOpacity: 0.8,
        }).addTo(facilities).bindPopup(popup);
      });
      overlays[message("facilities")] = facilities;
      var baseMaps = {};
      baseMaps[message("basemap")] = tiles;
      L.control.layers(baseMaps, overlays, { collapsed: true }).addTo(map);
      var controls = map.getContainer();
      [[".leaflet-control-zoom-in", "zoomIn"], [".leaflet-control-zoom-out", "zoomOut"],
        [".leaflet-control-layers-toggle", "layers"]].forEach(function (entry) {
        var control = controls.querySelector(entry[0]);
        if (control) {
          control.title = message(entry[1]);
          control.setAttribute("aria-label", message(entry[1]));
        }
      });
      document.getElementById("gis-facility-count").textContent = String(count);
      document.getElementById("gis-marker-count").textContent = String(groups.size);
      document.getElementById("gis-facility-empty").hidden = count !== 0;
      map.invalidateSize();
      window.addEventListener("resize", function () { map.invalidateSize(); });
    } catch (error) {
      fail("mapError");
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initMap);
  else initMap();
})();
