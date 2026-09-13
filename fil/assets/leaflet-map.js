/* Mapandan DPWH Infrastructure Map — Leaflet + OpenStreetMap */
(function () {
  "use strict";

  function getMarkerColor(status) {
    if (status === "Completed") return "#22c55e";
    if (status === "Ongoing") return "#eab308";
    if (status === "Not Yet Started") return "#ef4444";
    return "#3b82f6";
  }

  function createMarkerIcon(color) {
    return L.divIcon({
      className: "dpwh-marker",
      html:
        "<svg width=\"24\" height=\"36\" viewBox=\"0 0 24 36\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\">" +
        "<path d=\"M12 0C5.373 0 0 5.373 0 12c0 8.5 12 24 12 24S24 20.5 24 12C24 5.373 18.627 0 12 0z\" fill=\"" +
        color +
        "\"/>" +
        "<circle cx=\"12\" cy=\"12\" r=\"6\" fill=\"white\"/>" +
        "</svg>",
      iconSize: [24, 36],
      iconAnchor: [12, 36],
      popupAnchor: [0, -36],
    });
  }

  function initMap() {
    var projects = window.DPWH_PROJECTS || [];
    var hasCoords = projects.filter(function (p) {
      return p.latitude != null && p.longitude != null;
    });

    if (!hasCoords.length) {
      var el = document.getElementById("dpwh-map");
      if (el) el.style.display = "none";
      var fallback = document.getElementById("dpwh-map-fallback");
      if (fallback) fallback.style.display = "block";
      return;
    }

    var map = L.map("dpwh-map").setView([16.035, 120.45], 13);

    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors",
      maxZoom: 19,
    }).addTo(map);

    var bounds = [];

    hasCoords.forEach(function (p) {
      var color = getMarkerColor(p.status);
      var marker = L.marker([p.latitude, p.longitude], {
        icon: createMarkerIcon(color),
      }).addTo(map);
      var popup =
        "<strong>" +
        escapeHtml(p.project_name) +
        "</strong><br>" +
        escapeHtml(p.category) + "<br>" +
        "Contractor: " + escapeHtml(p.contractor || "—") + "<br>" +
        "Amount: ₱" + Number(p.contract_amount || 0).toLocaleString() + "<br>" +
        "Status: " + escapeHtml(p.status || "—") + "<br>" +
        "Accomplishment: " + (p.accomplishment_percent || 0) + "%";
      marker.bindPopup(popup);

      bounds.push([p.latitude, p.longitude]);
    });

    if (bounds.length > 1) {
      map.fitBounds(bounds, { padding: [40, 40] });
    }
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initMap);
  } else {
    initMap();
  }
})();
