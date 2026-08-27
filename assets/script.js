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
  var WEATHER = {
    name: "Mapandan, Pangasinan",
    lat: 16.0300,
    lon: 120.4561,
    timezone: "Asia/Manila",
    days: 3
  };

  var weatherEl = document.getElementById("weather-widget");
  if (weatherEl) {
    var weatherUrl = "https://api.open-meteo.com/v1/forecast?" +
      "latitude=" + WEATHER.lat +
      "&longitude=" + WEATHER.lon +
      "&current=temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m,wind_direction_10m" +
      "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum" +
      "&timezone=" + WEATHER.timezone +
      "&forecast_days=" + WEATHER.days;

    var controller = new AbortController();
    var timeout = setTimeout(function () { controller.abort(); }, 8000);

    fetch(weatherUrl, { signal: controller.signal })
      .then(function (res) {
        if (!res.ok) throw new Error("Weather API error");
        return res.json();
      })
      .then(function (data) {
        clearTimeout(timeout);
        var current = data.current;
        var daily = data.daily;
        var code = current.weather_code;
        var icon = weatherIcon(code);
        var desc = weatherDesc(code);
        var dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
        var windDir = windDirection(current.wind_direction_10m);

        // Format updated timestamp
        var updatedTime = current.time ? new Date(current.time) : new Date();
        var hours = updatedTime.getHours();
        var mins = String(updatedTime.getMinutes()).padStart(2, "0");
        var ampm = hours >= 12 ? "PM" : "AM";
        hours = hours % 12 || 12;
        var updatedStr = hours + ":" + mins + " " + ampm;

        var html = '<div class="weather-location">' + WEATHER.name + '</div>';

        // Current conditions
        html += '<div class="weather-current">';
        html += '<span class="weather-icon">' + icon + '</span>';
        html += '<div>';
        html += '<div class="weather-temp">' + Math.round(current.temperature_2m) + '&deg;C</div>';
        html += '<div class="weather-desc">' + desc + '</div>';
        html += '<div class="weather-feels">Feels like ' + Math.round(current.apparent_temperature) + '&deg;C</div>';
        html += '</div>';
        html += '</div>';

        // Details row
        html += '<div class="weather-details">';
        html += '<span>&#x1F4A7; Humidity ' + current.relative_humidity_2m + '%</span>';
        html += '<span>&#x1F4A8; Wind ' + Math.round(current.wind_speed_10m) + ' km/h ' + windDir + '</span>';
        if (current.precipitation > 0 || (current.rain && current.rain > 0)) {
          var rainMm = current.rain || current.precipitation;
          html += '<span>&#x1F327;&#xFE0F; Rain ' + rainMm + ' mm</span>';
        }
        var rainProb = daily.precipitation_probability_max ? daily.precipitation_probability_max[0] : null;
        if (rainProb !== null && rainProb !== undefined) {
          html += '<span>&#x1F326;&#xFE0F; Rain chance ' + rainProb + '%</span>';
        }
        html += '</div>';

        // 3-day forecast
        html += '<div class="weather-forecast">';
        for (var i = 0; i < WEATHER.days; i++) {
          var d = new Date(daily.time[i]);
          var label = i === 0 ? "Today" : dayNames[d.getDay()];
          html += '<div class="weather-day">';
          html += '<div class="day-name">' + label + '</div>';
          html += '<div class="day-temp">' + Math.round(daily.temperature_2m_min[i]) + '&ndash;' + Math.round(daily.temperature_2m_max[i]) + '&deg;C</div>';
          html += '</div>';
        }
        html += '</div>';

        // Footer: timestamp + attribution
        html += '<div class="weather-footer">';
        html += '<span class="weather-updated">Updated ' + updatedStr + '</span>';
        html += '<span class="weather-source">Powered by Open-Meteo</span>';
        html += '</div>';

        weatherEl.innerHTML = html;
      })
      .catch(function (err) {
        clearTimeout(timeout);
        var msg = "Weather data unavailable.";
        if (err.name === "AbortError") {
          msg = "Weather request timed out.";
        }
        weatherEl.innerHTML = '<div class="weather-error">' + msg +
          ' <a href="https://www.open-meteo.com/" target="_blank" rel="noopener">Try Open-Meteo directly</a></div>' +
          '<div class="weather-pagasa-fallback"><a href="https://www.pagasa.dost.gov.ph/" target="_blank" rel="noopener">View PAGASA Advisories &rarr;</a></div>';
      });
  }

});

// History carousel
document.addEventListener("DOMContentLoaded", function () {
  var track = document.querySelector(".carousel-track");
  if (!track) return;

  var slides = track.querySelectorAll(".carousel-slide");
  var captionText = document.querySelector(".carousel-caption-text");
  var counter = document.querySelector(".carousel-current");
  var prevBtn = document.querySelector(".carousel-prev");
  var nextBtn = document.querySelector(".carousel-next");
  var current = 0;
  var total = slides.length;

  var captions = [
    "Mapandan Town Plaza",
    "Old Mapandan Public Market",
    "Early Municipal Officials",
    "Old Mapandan School",
    "Old Baloling Bridge",
  ];

  function goTo(index) {
    slides[current].classList.remove("active");
    current = (index + total) % total;
    slides[current].classList.add("active");
    if (captionText) captionText.textContent = captions[current] || "";
    if (counter) counter.textContent = current + 1;
  }

  if (prevBtn) prevBtn.addEventListener("click", function () {
    goTo(current - 1);
  });

  if (nextBtn) nextBtn.addEventListener("click", function () {
    goTo(current + 1);
  });

  var region = document.querySelector(".history-carousel");
  if (region) {
    region.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") { goTo(current - 1); e.preventDefault(); }
      if (e.key === "ArrowRight") { goTo(current + 1); e.preventDefault(); }
    });
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

function windDirection(degrees) {
  var dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
  var idx = Math.round(degrees / 22.5) % 16;
  return dirs[idx];
}
