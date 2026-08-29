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
    var target = a.getAttribute("href").split("/").pop();
    if (target === here || (here === "" && target === "index.html")) {
      a.setAttribute("aria-current", "page");
    }
  });

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

// History accordions
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".accordion-toggle").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var content = btn.nextElementSibling;
      var expanded = btn.getAttribute("aria-expanded") === "true";
      btn.setAttribute("aria-expanded", String(!expanded));
      if (expanded) {
        content.hidden = true;
        btn.textContent = "Read more";
      } else {
        content.hidden = false;
        btn.textContent = "Show less";
      }
    });
  });
});

// History population chart
document.addEventListener("DOMContentLoaded", function () {
  var ctx = document.getElementById("chart-history-population");
  if (!ctx) return;

  new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["1903", "1918", "1939", "1948", "1960", "1970", "1980", "1990", "2000", "2010", "2020", "2024"],
      datasets: [{
        label: "Population",
        data: [4198, 6049, 7286, 9836, 13065, 16653, 20094, 25622, 30775, 34077, 38058, 38228],
        backgroundColor: "rgba(76,138,46,0.6)",
        borderColor: "#4c8a2e",
        borderWidth: 1,
        borderRadius: 3
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true },
        x: { grid: { display: false } }
      }
    }
  });
});

// Barangay history modal
document.addEventListener("DOMContentLoaded", function () {
  var barangays = {
    "Torres": { pop2024: "3,061", pop2020: "3,112", landUse: "Historical settlement / farming", history: "Torres was the first seat of Mapandan, established when the municipality was created in 1887. The area was associated with a church where Fr. Jose Torres served as parish priest. The community once contained several sitios &mdash; Primicias, Luyan, Lambayan, and Jimenez &mdash; that later developed into separate barangays. Torres&rsquo;s position near the southern boundary led to the eventual transfer of the municipal center to Poblacion.", source: "Municipality of Mapandan, Barangay Torres History" },
    "Golden": { pop2024: "1,432", pop2020: "1,399", landUse: "Agricultural / micro-commercial", history: "Golden was formerly known as Amanoaoac North, a sitio of Amanoaoac. Named after the Golden Distillery that operated after liberation, the community underwent substantial development including road improvement, waterworks, school construction, and cooperative organization. In 1972, Golden was recognized as a SEATO/PACD Model Village, with the award presented at Malaca&ntilde;ang on September 8, 1972. It became a separate barangay in 1967.", source: "Municipality of Mapandan, Barangay Golden History" },
    "Sta. Maria (Luyan North)": { pop2024: "1,585", pop2020: "1,270", landUse: "Agricultural", history: "Sta. Maria was formerly part of Luyan, developed from former hacienda land. After World War II, tenants gained opportunities to own the land they had been farming. The community developed as an independent barrio in 1965, with agricultural development driven by the area&rsquo;s fertile land and the community&rsquo;s transition from tenant farming to land ownership.", source: "Municipality of Mapandan, Barangay Sta. Maria History" },
    "Coral": { pop2024: "1,405", pop2020: "1,389", landUse: "Agricultural", history: "Coral&rsquo;s name originates from the stone coral (animal enclosure) built during the Spanish era to protect livestock from disease. The barangay was created through a series of official actions: Municipal Council Resolution No. 87 (May 4, 1972), Provincial Board Resolution No. 155 (August 10, 1972), and Proclamation No. 11 (April 25, 1973), followed by a special election for barangay officials on May 6, 1973.", source: "Municipality of Mapandan, Barangay Coral History" },
    "Poblacion": { pop2024: "3,509", pop2020: "3,622", landUse: "Administrative / central commercial zone", history: "Poblacion became the municipal center after the transfer from Torres. Much of the land was owned by the Aquino family, with Leon Hilario Aquino encouraging settlement by subdividing land into uniform lots. Today it houses the Municipal Hall, Sangguniang Bayan, Municipal Trial Court, and Mapandan National High School &mdash; the administrative and commercial heart of the municipality.", source: "Municipality of Mapandan, Barangay Poblacion History" },
    "Luyan (Luyan South)": { pop2024: "3,344", pop2020: "3,730", landUse: "Agri-tourism / culinary agriculture", history: "Luyan&rsquo;s history traces back to 18th-century oral accounts. The community has historical relationships with Torres, Aserda, and Sta. Maria. An elementary school was developed in 1990, marking a significant milestone in the community&rsquo;s educational infrastructure. Today, Luyan is highlighted in regional DOT farm-to-table culinary circuits for its agri-tourism programs.", source: "Municipality of Mapandan, Barangay Luyan History" },
    "Amanoaoac": { pop2024: "1,656", pop2020: "1,636", landUse: "Agricultural / crop farming", history: "One of the original barrios when Mapandan was established in 1887. The name Amanoaoac has local linguistic origins, and the community shares historical ties with Golden, which was formerly a sitio called Amanoaoac North. The barangay has maintained its agricultural character throughout its history.", source: "Municipality of Mapandan, Barangay Amanoaoac History" },
    "Apaya": { pop2024: "1,650", pop2020: "1,467", landUse: "Agricultural / livestock production", history: "One of the original barrios of Mangaldan that became part of Mapandan in 1887. Apaya is one of the major historical barrios, with relationships to Coral, Golden, and Poblacion. The community has maintained its agricultural and livestock production character over more than a century.", source: "Municipality of Mapandan, Barangay Apaya History" },
    "Aserda": { pop2024: "1,414", pop2020: "1,108", landUse: "Agricultural", history: "Aserda is one of Mapandan&rsquo;s 15 barangays, with historical ties to neighboring Luyan. The community has developed primarily as an agricultural area, contributing to Mapandan&rsquo;s identity as a rice-growing municipality.", source: "Municipality of Mapandan, Municipal Profile" },
    "Baloling": { pop2024: "4,238", pop2020: "4,393", landUse: "Mixed agricultural / residential", history: "One of the original barrios when Mapandan was established in 1887, Baloling is one of the municipality&rsquo;s more populous barangays. The community has a mixed agricultural and residential character, reflecting its growth over more than 130 years.", source: "Municipality of Mapandan, Municipal Profile" },
    "Jimenez": { pop2024: "2,008", pop2020: "1,995", landUse: "Agricultural", history: "Jimenez is one of the sitios that were originally part of Barangay Torres before developing into a separate community. The barangay has maintained its agricultural character throughout its history.", source: "Municipality of Mapandan, Barangay Torres History" },
    "Lambayan": { pop2024: "1,682", pop2020: "1,756", landUse: "Agricultural / rice production", history: "Lambayan was originally one of the sitios of Barangay Torres before becoming a separate community. The barangay is known for its rice production, contributing to Mapandan&rsquo;s agricultural economy.", source: "Municipality of Mapandan, Barangay Torres History" },
    "Nilombot": { pop2024: "4,199", pop2020: "4,411", landUse: "Residential / commercial outer fringe", history: "Nilombot&rsquo;s name has local origins tied to the area&rsquo;s former landscape. The community has developed from agricultural roots into a residential and commercial area on Mapandan&rsquo;s outer fringe, reflecting the municipality&rsquo;s growth.", source: "Municipality of Mapandan, Barangay Nilombot History" },
    "Pias": { pop2024: "4,827", pop2020: "4,699", landUse: "High-density residential / farming", history: "Pias is one of Mapandan&rsquo;s most populous barangays. The community combines high-density residential areas with active farming, reflecting the transition from purely agricultural to mixed-use land character.", source: "Municipality of Mapandan, Municipal Profile" },
    "Primicias": { pop2024: "2,218", pop2020: "2,071", landUse: "Agricultural", history: "Primicias was originally one of the sitios of Barangay Torres before developing into a separate community. The barangay has maintained its agricultural character throughout its development.", source: "Municipality of Mapandan, Barangay Torres History" }
  };

  var grid = document.getElementById("barangay-grid");
  if (!grid) return;

  var order = [
    "Torres", "Poblacion", "Baloling", "Pias", "Nilombot",
    "Luyan (Luyan South)", "Jimenez", "Lambayan", "Amanoaoac", "Apaya",
    "Aserda", "Coral", "Golden", "Primicias", "Sta. Maria (Luyan North)"
  ];

  order.forEach(function (name) {
    var d = barangays[name];
    if (!d) return;
    var card = document.createElement("div");
    card.className = "barangay-card";
    card.setAttribute("tabindex", "0");
    card.setAttribute("role", "button");
    card.setAttribute("aria-label", name + " \u2014 " + d.pop2024 + " residents, " + d.landUse + ". Read history.");
    card.innerHTML = "<h4>" + name + '</h4><div class="barangay-card-meta"><span class="barangay-card-pop">' + d.pop2024 + '</span><span class="barangay-card-landuse">' + d.landUse + '</span></div>';
    card.addEventListener("click", function () { openBarangayModal(name, d); });
    card.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openBarangayModal(name, d); }
    });
    grid.appendChild(card);
  });

  function openBarangayModal(name, data) {
    var overlay = document.createElement("div");
    overlay.className = "barangay-modal-overlay";
    overlay.innerHTML =
      '<div class="barangay-modal" role="dialog" aria-label="' + name + ' history">' +
      '<button class="barangay-modal-close" aria-label="Close">&times;</button>' +
      "<h3>" + name + "</h3>" +
      "<p><strong>2024 Population:</strong> " + data.pop2024 +
      " &middot; <strong>2020 Population:</strong> " + data.pop2020 +
      " &middot; <strong>Land Use:</strong> " + data.landUse + "</p>" +
      "<p>" + data.history + "</p>" +
      '<p class="source-cite">Source: ' + data.source + "</p>" +
      "</div>";

    document.body.appendChild(overlay);
    requestAnimationFrame(function () { overlay.classList.add("open"); });

    var closeBtn = overlay.querySelector(".barangay-modal-close");
    function close() {
      overlay.classList.remove("open");
      setTimeout(function () { overlay.remove(); }, 200);
    }
    closeBtn.addEventListener("click", close);
    overlay.addEventListener("click", function (e) { if (e.target === overlay) close(); });
    document.addEventListener("keydown", function handler(e) {
      if (e.key === "Escape") { close(); document.removeEventListener("keydown", handler); }
    });
    closeBtn.focus();
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
