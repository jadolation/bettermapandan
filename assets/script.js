// Better Mapandan — shared site behavior (no frameworks, no dead ends)

document.addEventListener("DOMContentLoaded", function () {
  var toggle = document.querySelector(".nav-toggle");
  var links = document.querySelector(".nav-links");

  if (toggle && links) {
    toggle.addEventListener("click", function () {
      var isOpen = links.classList.toggle("open");
      toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });

    links.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", function () {
        links.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  // Mark the current page in the nav
  var here = location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".nav-links a").forEach(function (a) {
    var target = a.getAttribute("href");
    if (target === here || (here === "" && target === "index.html")) {
      a.setAttribute("aria-current", "page");
    }
  });

  // Search: highlight matching rows on services.html when ?q= is present
  var params = new URLSearchParams(location.search);
  var query = (params.get("q") || "").trim().toLowerCase();
  if (query && here === "services.html") {
    var rows = document.querySelectorAll("table tbody tr");
    var matched = [];
    rows.forEach(function (row) {
      var text = row.textContent.toLowerCase();
      if (text.indexOf(query) !== -1) {
        row.style.background = "#f6ecc9";
        matched.push(row);
      }
    });
    if (matched.length > 0) {
      matched[0].scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  // Weather widget — Open-Meteo API (free, no API key)
  var weatherEl = document.getElementById("weather-widget");
  if (weatherEl) {
    var lat = 16.0;
    var lon = 120.4;
    var weatherUrl = "https://api.open-meteo.com/v1/forecast?latitude=" + lat + "&longitude=" + lon + "&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=Asia/Manila&forecast_days=3";

    fetch(weatherUrl)
      .then(function (res) { return res.json(); })
      .then(function (data) {
        var current = data.current;
        var daily = data.daily;
        var code = current.weather_code;
        var icon = weatherIcon(code);
        var desc = weatherDesc(code);
        var dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

        var html = '<div class="weather-current">';
        html += '<span class="weather-icon">' + icon + '</span>';
        html += '<div>';
        html += '<div class="weather-temp">' + Math.round(current.temperature_2m) + '&deg;C</div>';
        html += '<div class="weather-desc">' + desc + '</div>';
        html += '</div>';
        html += '</div>';
        html += '<div class="weather-details">';
        html += '<span>Humidity: ' + current.relative_humidity_2m + '%</span>';
        html += '<span>Wind: ' + Math.round(current.wind_speed_10m) + ' km/h</span>';
        html += '</div>';
        html += '<div class="weather-forecast">';
        for (var i = 0; i < 3; i++) {
          var d = new Date(daily.time[i]);
          html += '<div class="weather-day">';
          html += '<div class="day-name">' + dayNames[d.getDay()] + '</div>';
          html += '<div class="day-temp">' + Math.round(daily.temperature_2m_min[i]) + '&ndash;' + Math.round(daily.temperature_2m_max[i]) + '&deg;C</div>';
          html += '</div>';
        }
        html += '</div>';
        html += '<div class="weather-source">Source: Open-Meteo API</div>';
        weatherEl.innerHTML = html;
      })
      .catch(function () {
        weatherEl.innerHTML = '<div class="weather-error">Weather data unavailable. <a href="https://open-meteo.com/" target="_blank" rel="noopener">Visit Open-Meteo</a></div>';
      });
  }

  // Interactive map — Leaflet + OpenStreetMap
  var mapEl = document.getElementById("map");
  if (mapEl && typeof L !== "undefined") {
    var map = L.map("map").setView([16.0, 120.4], 13);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 18
    }).addTo(map);

    // Barangay markers
    var barangays = [
      { name: "Bacnar", lat: 16.005, lon: 120.395, pop: 4064 },
      { name: "Baloling", lat: 15.995, lon: 120.385, pop: 1403 },
      { name: "East Centre", lat: 16.002, lon: 120.405, pop: 773 },
      { name: "Gilotongan", lat: 15.998, lon: 120.410, pop: 1135 },
      { name: "Luyan (South Centre)", lat: 15.990, lon: 120.395, pop: 2767 },
      { name: "Parangao", lat: 16.010, lon: 120.415, pop: 1171 },
      { name: "Poblacion", lat: 16.000, lon: 120.400, pop: 3452 },
      { name: "Pogo", lat: 16.008, lon: 120.380, pop: 1107 },
      { name: "Primicias", lat: 15.992, lon: 120.415, pop: 2218 },
      { name: "Santa Maria", lat: 16.012, lon: 120.390, pop: 1585 },
      { name: "Torres", lat: 15.988, lon: 120.405, pop: 3061 }
    ];

    var barangayLayer = L.layerGroup();
    barangays.forEach(function (b) {
      L.circleMarker([b.lat, b.lon], {
        radius: 6, fillColor: "#4c8a2e", color: "#16532c", weight: 1, fillOpacity: 0.8
      }).bindPopup("<strong>" + b.name + "</strong><br/>Population: " + b.pop.toLocaleString()).addTo(barangayLayer);
    });
    barangayLayer.addTo(map);

    // Facility markers
    var facilities = [
      { name: "Municipal Hall", lat: 16.001, lon: 120.401, icon: "🏛️" },
      { name: "Mapandan Community Hospital", lat: 16.003, lon: 120.398, icon: "🏥" },
      { name: "Rural Health Unit", lat: 15.999, lon: 120.402, icon: "🏥" },
      { name: "PNP Station", lat: 16.000, lon: 120.397, icon: "🚔" },
      { name: "BFP Station", lat: 15.998, lon: 120.399, icon: "🚒" },
      { name: "Town Plaza", lat: 16.0005, lon: 120.4005, icon: "🌳" },
      { name: "Public Market", lat: 16.0015, lon: 120.399, icon: "🏪" }
    ];

    var facilityLayer = L.layerGroup();
    facilities.forEach(function (f) {
      L.marker([f.lat, f.lon], {
        icon: L.divIcon({ className: "map-marker", html: '<span style="font-size:20px">' + f.icon + '</span>', iconSize: [24, 24], iconAnchor: [12, 12] })
      }).bindPopup("<strong>" + f.name + "</strong>").addTo(facilityLayer);
    });
    facilityLayer.addTo(map);

    // Layer control
    L.control.layers(null, {
      "Barangays": barangayLayer,
      "Facilities": facilityLayer
    }, { collapsed: false }).addTo(map);
  }
});

// Weather code helpers
function weatherIcon(code) {
  var icons = { 0: "\u2600\uFE0F", 1: "\uD83C\uDF24\uFE0F", 2: "\u26C5", 3: "\u2601\uFE0F", 45: "\uD83C\uDF2B\uFE0F", 48: "\uD83C\uDF2B\uFE0F", 51: "\uD83C\uDF26\uFE0F", 53: "\uD83C\uDF26\uFE0F", 55: "\uD83C\uDF27\uFE0F", 61: "\uD83C\uDF27\uFE0F", 63: "\uD83C\uDF27\uFE0F", 65: "\uD83C\uDF27\uFE0F", 71: "\u2744\uFE0F", 73: "\u2744\uFE0F", 75: "\u2744\uFE0F", 80: "\uD83C\uDF26\uFE0F", 81: "\uD83C\uDF27\uFE0F", 82: "\uD83C\uDF27\uFE0F", 95: "\u26C8\uFE0F", 96: "\u26C8\uFE0F", 99: "\u26C8\uFE0F" };
  return icons[code] || "\uD83C\uDF24\uFE0F";
}

function weatherDesc(code) {
  var descs = { 0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Rime fog", 51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle", 61: "Light rain", 63: "Moderate rain", 65: "Heavy rain", 71: "Light snow", 73: "Moderate snow", 75: "Heavy snow", 80: "Light showers", 81: "Moderate showers", 82: "Violent showers", 95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Severe thunderstorm" };
  return descs[code] || "Unknown";
}
