/* Mapandan DPWH Infrastructure Map — Leaflet + OpenStreetMap */
(function () {
  "use strict";

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
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);

    var bounds = [];

    hasCoords.forEach(function (p) {
      var marker = L.marker([p.latitude, p.longitude]).addTo(map);
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

      marker.on("click", function () {
        var card = document.getElementById("dpwh-project-" + p.transaction_id);
        if (card) {
          card.scrollIntoView({ behavior: "smooth", block: "center" });
          card.classList.add("highlight-project");
          setTimeout(function () {
            card.classList.remove("highlight-project");
          }, 2000);
        }
      });

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
