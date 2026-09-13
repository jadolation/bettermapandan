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

  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function getProjectDate(p) {
    if (p.actual_completion_date) return p.actual_completion_date;
    if (p.fiscal_year) return p.fiscal_year + "-01-01";
    return null;
  }

  function filterDpwhProjects(projects, range, termIndex) {
    var filtered = projects.slice();
    if (termIndex !== null && termIndex !== undefined) {
      var terms = [
        { start: "2010-06-30", end: "2016-06-29" },
        { start: "2016-06-30", end: "2019-06-29" },
        { start: "2019-06-30", end: "2022-06-29" },
        { start: "2022-06-30", end: "2099-12-31" }
      ];
      var term = terms[termIndex];
      if (term) {
        var from = new Date(term.start);
        var to = new Date(term.end);
        to.setHours(23, 59, 59, 999);
        filtered = filtered.filter(function (p) {
          var dStr = getProjectDate(p);
          if (!dStr) return false;
          var d = new Date(dStr);
          return d >= from && d <= to;
        });
      }
    }
    if (range && range !== "all") {
      var now = new Date();
      var cutoff;
      if (range === "30d") {
        cutoff = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 30);
      } else if (range === "3m") {
        cutoff = new Date(now.getFullYear(), now.getMonth() - 3, now.getDate());
      } else if (range === "6m") {
        cutoff = new Date(now.getFullYear(), now.getMonth() - 6, now.getDate());
      } else if (range === "1y") {
        cutoff = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
      } else if (range === "3y") {
        cutoff = new Date(now.getFullYear() - 3, now.getMonth(), now.getDate());
      }
      if (cutoff) {
        filtered = filtered.filter(function (p) {
          var dStr = getProjectDate(p);
          if (!dStr) return false;
          return new Date(dStr) >= cutoff;
        });
      }
    }
    return filtered;
  }

  function renderMarkers(projects) {
    var map = window._dpwhMap;
    if (!map) return;
    if (window._dpwhMarkers) {
      window._dpwhMarkers.forEach(function (m) { map.removeLayer(m); });
    }
    window._dpwhMarkers = [];
    var bounds = [];
    var coords = projects.filter(function (p) {
      return p.latitude != null && p.longitude != null;
    });
    coords.forEach(function (p) {
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
      window._dpwhMarkers.push(marker);
      bounds.push([p.latitude, p.longitude]);
    });
    if (bounds.length > 1) {
      map.fitBounds(bounds, { padding: [40, 40] });
    } else if (bounds.length === 1) {
      map.setView(bounds[0], 14);
    }
  }

  window.refreshDpwhMap = function (range, termIndex) {
    var projects = window.DPWH_PROJECTS || [];
    var filtered = filterDpwhProjects(projects, range, termIndex);
    renderMarkers(filtered);
  };

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

    window._dpwhMap = L.map("dpwh-map").setView([16.035, 120.45], 13);

    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors",
      maxZoom: 19,
    }).addTo(window._dpwhMap);

    renderMarkers(hasCoords);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initMap);
  } else {
    initMap();
  }
})();
