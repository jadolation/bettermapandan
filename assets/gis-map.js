/* Depends on: Leaflet 1.9.4 (loaded from unpkg before this script) */

/* Better Mapandan GIS Map — Leaflet + injected GeoJSON data */
(function () {
  "use strict";

  var gisMapInitialized = false;

  function escapeHtml(str) {
    return String(str == null ? "" : str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function showFallback() {
    var el = document.getElementById("gis-map");
    if (el) el.style.display = "none";
    var fallback = document.getElementById("gis-map-fallback");
    if (fallback) fallback.style.display = "block";
  }

  function populateBarangayList() {
    var brgays = window.GIS_BARANGAYS && window.GIS_BARANGAYS.features || [];
    var listEl = document.getElementById("gis-barangay-list");
    if (!listEl) return;

    if (!brgays.length) {
      listEl.innerHTML = '<p class="source-label">No barangay data available.</p>';
      return;
    }

    var items = brgays.map(function (f) {
      var p = f.properties;
      var badge = p.verification_status === "source_verified"
        ? '<span class="badge badge-sm badge-official">Verified</span>'
        : '<span class="badge badge-sm badge-review">Pending</span>';
      return '<div class="barangay-list-item">' +
        '<span class="barangay-code">' + escapeHtml(p.gid) + '</span>' +
        '<span class="barangay-name">' + escapeHtml(p.name) + badge + '</span>' +
        '<span class="barangay-pop">Pop. ' + (p.pop2024 || "—") + '</span>' +
        '</div>';
    });

    listEl.innerHTML = '<div class="barangay-list">' + items.join("") + "</div>";
  }

  function filterPublishableFacilities() {
    var facs = window.GIS_FACILITIES && window.GIS_FACILITIES.features || [];
    var publishable = ["source_verified", "field_verified"];
    return facs.filter(function (f) {
      return publishable.indexOf(f.properties.verification_status) !== -1;
    });
  }

  function updateFacilityCount(count) {
    var countEl = document.getElementById("gis-facility-count");
    if (countEl) countEl.textContent = String(count);
  }

  function createLegend(map) {
    var legend = L.control({ position: "bottomright" });

    legend.onAdd = function () {
      var div = L.DomUtil.create("div", "gis-legend");
      div.innerHTML =
        '<h4>Legend</h4>' +
        '<div class="gis-legend-item">' +
        '<span class="gis-legend-swatch gis-legend-rect"></span>' +
        '<span>Approximate extent — not a legal boundary</span>' +
        '</div>' +
        '<div class="gis-legend-item">' +
        '<span class="gis-legend-swatch gis-legend-green"></span>' +
        '<span>Verified facility</span>' +
        '</div>' +
        '<div class="gis-legend-item">' +
        '<span class="gis-legend-swatch gis-legend-orange"></span>' +
        '<span>Pending verification</span>' +
        '</div>' +
        '<div class="gis-legend-item" style="font-size:0.6875rem">' +
        '<span style="flex:1"></span>' +
        '<span>Hazard layers are raster overlays for reference only</span>' +
        '</div>';
      return div;
    };

    legend.addTo(map);
  }

  function initMap() {
    var mapEl = document.getElementById("gis-map");
    if (!mapEl) return;

    if (gisMapInitialized) return;
    gisMapInitialized = true;

    if (typeof L === "undefined") {
      showFallback();
      return;
    }

    var manifest = window.GIS_LAYERS || {};
    var meta = manifest.metadata || {};

    /* default_map_center is stored as [lon, lat] per GeoJSON convention.
       Leaflet's setView expects [lat, lng], so we swap the array order. */
    var center = meta.default_map_center
      ? meta.default_map_center : [120.455, 16.03];
    var zoom = meta.default_zoom ? meta.default_zoom : 14;
    var map = L.map("gis-map").setView([center[1], center[0]], zoom);

    var osmLayer = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    });

    var baseMaps = {
      "OSM": osmLayer,
    };

    /* Municipality extent rectangle — approximate bounds from layers.json
       metadata, NOT a legal boundary. Per AGENTS.md §4.1, we never invent
       spatial data; this dashed rectangle visualizes the data extraction
       extent only. Rendered on its own toggleable "Municipal Extent" layer. */
    var extentLayer = L.layerGroup();
    var bounds = meta.coordinate_bounds;
    if (bounds && bounds.south != null && bounds.west != null &&
        bounds.north != null && bounds.east != null) {
      var rectBounds = L.latLngBounds(
        [bounds.south, bounds.west],
        [bounds.north, bounds.east]
      );
      L.rectangle(rectBounds, {
        color: "#3b82f6",
        weight: 2,
        dashArray: "6,4",
        fill: false,
        clickable: false,
      }).addTo(extentLayer);
    }
    extentLayer.addTo(map);

    /* Municipality extent label — clarifies the rectangle is approximate. */
    var extentLabel = document.createElement("div");
    extentLabel.className = "gis-extent-label";
    extentLabel.innerHTML =
      '<span class="gis-extent-label-inner">Municipal extent (approximate)</span>';
    map.getContainer().appendChild(extentLabel);

    var publishable = filterPublishableFacilities();

    /* Facility layer — only source_verified/field_verified features
       are rendered as green circleMarkers. All 16 features are now
       source_verified, so the layer renders all 16 facilities. */
    var facilityLayer = L.layerGroup();
    publishable.forEach(function (feat) {
      if (feat.geometry && feat.geometry.type === "Point") {
        var coords = feat.geometry.coordinates;
        var props = feat.properties;
        var marker = L.circleMarker([coords[1], coords[0]], {
          radius: 6,
          fillColor: "#2d6b1f",
          color: "#2d6b1f",
          weight: 1,
          opacity: 1,
          fillOpacity: 0.8,
        }).addTo(facilityLayer);
        marker.bindPopup(
          "<strong>" + escapeHtml(props.name) + "</strong><br>" +
          escapeHtml(props.category || "") + "<br>" +
          escapeHtml(props.address || "")
        );
      }
    });
    facilityLayer.addTo(map);

    /* Layer control — OSM base map + toggleable overlays. */
    var overlayMaps = {
      "Municipal Extent": extentLayer,
      "Public Facilities": facilityLayer,
    };
    L.control.layers(baseMaps, overlayMaps, { collapsed: false }).addTo(map);

    /* Legend control explaining symbols and data-status conventions. */
    createLegend(map);

    /* Update the facility count display in the page sidebar. */
    updateFacilityCount(publishable.length);

    /* Non-real-time hazard disclaimer (pinned below the legend). */
    var disclaimer = document.createElement("div");
    disclaimer.className = "gis-disclaimer-popup";
    disclaimer.innerHTML =
      '<div class="source-label" style="margin-top:8px">' +
      '<strong>⚠ Non-real-time data.</strong> Hazard layers are for reference only, ' +
      "not for emergency decisions. Call 911 or local MDRRMO for emergencies." +
      "</div>";
    map.getContainer().appendChild(disclaimer);

    populateBarangayList();
    map.invalidateSize();

    /* Recompute center on window resize (container may have shifted). */
    window.addEventListener("resize", function () {
      if (map) map.invalidateSize();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initMap);
  } else {
    initMap();
  }
})();
