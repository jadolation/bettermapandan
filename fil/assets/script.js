// Better Mapandan — shared site behavior (no frameworks, no dead ends)

// Language persistence — saves preference to localStorage
function switchLang(lang) {
  localStorage.setItem("bettermapandan_lang", lang);
}

function getCurrentLang() {
  return location.pathname.indexOf("/fil/") !== -1 ? "fil" : "en";
}

document.addEventListener("DOMContentLoaded", function () {
  var toggle = document.querySelector(".nav-toggle");
  var links = document.querySelector(".nav-links");

  if (toggle && links) {
    toggle.addEventListener("click", function () {
      var isOpen = links.classList.toggle("open");
      toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
      if (isOpen) {
        var firstLink = links.querySelector("a");
        if (firstLink) firstLink.focus();
      }
    });

    links.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", function () {
        links.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      });
    });

    links.addEventListener("keydown", function (e) {
      if (e.key === "Tab") {
        var focusable = links.querySelectorAll("a[href], button");
        if (focusable.length === 0) return;
        var first = focusable[0];
        var last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
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
        html += '<span class="weather-icon"><i data-lucide="' + icon + '"></i></span>';
        html += '<div>';
        html += '<div class="weather-temp">' + Math.round(current.temperature_2m) + '&deg;C</div>';
        html += '<div class="weather-desc">' + desc + '</div>';
        html += '<div class="weather-feels">Feels like ' + Math.round(current.apparent_temperature) + '&deg;C</div>';
        html += '</div>';
        html += '</div>';

        // Details row
        html += '<div class="weather-details">';
        html += '<span><i data-lucide="droplet"></i> Humidity ' + current.relative_humidity_2m + '%</span>';
        html += '<span><i data-lucide="wind"></i> Wind ' + Math.round(current.wind_speed_10m) + ' km/h ' + windDir + '</span>';
        if (current.precipitation > 0 || (current.rain && current.rain > 0)) {
          var rainMm = current.rain || current.precipitation;
          html += '<span><i data-lucide="cloud-rain"></i> Rain ' + rainMm + ' mm</span>';
        }
        var rainProb = daily.precipitation_probability_max ? daily.precipitation_probability_max[0] : null;
        if (rainProb !== null && rainProb !== undefined) {
          html += '<span><i data-lucide="cloud-drizzle"></i> Rain chance ' + rainProb + '%</span>';
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
        clearTimeout(timeout);
        if (typeof lucide !== "undefined") lucide.createIcons({ nodes: [weatherEl] });
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

  // Initialize all Lucide icons on the page
  if (typeof lucide !== "undefined") lucide.createIcons();

});

// History carousel
document.addEventListener("DOMContentLoaded", function () {
  var track = document.querySelector(".carousel-track");
  if (!track) return;

  var slides = track.querySelectorAll(".carousel-slide");
  var counter = document.querySelector(".carousel-current");
  var prevBtn = document.querySelector(".carousel-prev");
  var nextBtn = document.querySelector(".carousel-next");
  var current = 0;
  var total = slides.length;

  function goTo(index) {
    slides[current].classList.remove("active");
    current = (index + total) % total;
    slides[current].classList.add("active");
    if (counter) counter.textContent = current + 1;
  }

  if (prevBtn) prevBtn.addEventListener("click", function () {
    goTo(current - 1);
    resetAuto();
  });

  if (nextBtn) nextBtn.addEventListener("click", function () {
    goTo(current + 1);
    resetAuto();
  });

  var region = document.querySelector(".history-carousel");
  if (region) {
    region.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") { goTo(current - 1); resetAuto(); e.preventDefault(); }
      if (e.key === "ArrowRight") { goTo(current + 1); resetAuto(); e.preventDefault(); }
    });
  }

  // Auto-advance carousel every 5 seconds, pause on hover
  var autoTimer = null;
  function startAuto() {
    stopAuto();
    autoTimer = setInterval(function () { goTo(current + 1); }, 5000);
  }
  function stopAuto() {
    if (autoTimer) { clearInterval(autoTimer); autoTimer = null; }
  }
  function resetAuto() { stopAuto(); startAuto(); }
  if (region) {
    region.addEventListener("mouseenter", stopAuto);
    region.addEventListener("mouseleave", startAuto);
    region.addEventListener("touchstart", stopAuto, { passive: true });
    region.addEventListener("touchend", function () { setTimeout(startAuto, 3000); }, { passive: true });
  }
  startAuto();
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
  // BARANGAY_DATA is loaded from assets/barangay-data.js (generated from barangays.json)
  var barangays = typeof BARANGAY_DATA !== "undefined" ? BARANGAY_DATA : [];
  var byName = {};
  barangays.forEach(function (b) { byName[b.name] = b; });

  var grid = document.getElementById("barangay-grid");
  if (!grid) return;

  var order = [
    "Torres", "Poblacion", "Baloling", "Pias", "Nilombot",
    "Luyan (Luyan South)", "Jimenez", "Lambayan", "Amanoaoac", "Apaya",
    "Aserda", "Coral", "Golden", "Primicias", "Sta. Maria (Luyan North)"
  ];

  order.forEach(function (name) {
    var d = byName[name];
    if (!d) return;
    var card = document.createElement("div");
    card.className = "barangay-card";
    card.setAttribute("tabindex", "0");
    card.setAttribute("role", "button");
    card.setAttribute("aria-label", name + " \u2014 " + d.pop2024 + " residents, " + d.landUse + ". Read history.");
    card.innerHTML = "<h4>" + name + '</h4><div class="barangay-card-meta"><span class="barangay-card-pop">' + d.pop2024 + '</span><span class="barangay-card-landuse">' + d.landUse + '</span>' + (d.punong ? '<span class="barangay-card-punong">' + d.punong + '</span>' : '') + '</div>';
    card.addEventListener("click", function () { openBarangayModal(name, d); });
    card.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openBarangayModal(name, d); }
    });
    grid.appendChild(card);
  });

  function openBarangayModal(name, data) {
    var previouslyFocused = document.activeElement;

    // Contact info — show Facebook and Phone separately
    var contactHtml = "";
    if (data.facebook) {
      contactHtml += '<p><strong>Facebook:</strong> <a href="' + data.facebook + '" target="_blank" rel="noopener">Barangay Page</a></p>';
    }
    if (data.phone && data.phone.toUpperCase() !== "N/A") {
      contactHtml += '<p><strong>Phone:</strong> <a href="tel:' + data.phone.replace(/\s/g, "") + '">' + data.phone + '</a></p>';
    } else if (data.phone) {
      contactHtml += '<p><strong>Phone:</strong> N/A</p>';
    }

    // Kagawads
    var kagawadHtml = "";
    var kagawads = data.kagawads || [];
    if (kagawads.length > 0) {
      kagawadHtml = '<p><strong>Kagawads:</strong></p><ul style="margin:0 0 12px 20px; padding:0">';
      kagawads.forEach(function (k) {
        kagawadHtml += "<li>" + k + "</li>";
      });
      kagawadHtml += "</ul>";
    }

    // Officials list (Secretary, Treasurer, SK Chair)
    var officialsHtml = "";
    var officials = data.officials || [];
    if (officials.length > 0) {
      officialsHtml = '<table class="barangay-officials"><thead><tr><th>Position</th><th>Name</th></tr></thead><tbody>';
      officials.forEach(function (off) {
        officialsHtml += "<tr><td>" + off.position + "</td><td>" + off.name + "</td></tr>";
      });
      officialsHtml += "</tbody></table>";
    }

    var overlay = document.createElement("div");
    overlay.className = "barangay-modal-overlay";

    var modalDiv = document.createElement("div");
    modalDiv.className = "barangay-modal";
    modalDiv.setAttribute("role", "dialog");
    modalDiv.setAttribute("aria-modal", "true");
    modalDiv.setAttribute("aria-label", name + " profile");

    var closeBtn = document.createElement("button");
    closeBtn.className = "barangay-modal-close";
    closeBtn.setAttribute("aria-label", "Close");
    closeBtn.innerHTML = "&times;";
    modalDiv.appendChild(closeBtn);

    var titleEl = document.createElement("h3");
    titleEl.textContent = name;
    modalDiv.appendChild(titleEl);

    var popEl = document.createElement("p");
    popEl.innerHTML = "<strong>2024 Population:</strong> " + data.pop2024 +
      " &middot; <strong>2020 Population:</strong> " + data.pop2020 +
      " &middot; <strong>Land Use:</strong> " + data.landUse;
    modalDiv.appendChild(popEl);

    if (data.punong) {
      var punongEl = document.createElement("p");
      punongEl.innerHTML = "<strong>Punong Barangay:</strong> " + data.punong;
      modalDiv.appendChild(punongEl);
    }

    if (contactHtml) {
      var contactDiv = document.createElement("div");
      contactDiv.innerHTML = contactHtml;
      modalDiv.appendChild(contactDiv);
    }

    if (kagawadHtml) {
      var kagawadDiv = document.createElement("div");
      kagawadDiv.innerHTML = kagawadHtml;
      modalDiv.appendChild(kagawadDiv);
    }

    if (officialsHtml) {
      var officialsDiv = document.createElement("div");
      officialsDiv.innerHTML = officialsHtml;
      modalDiv.appendChild(officialsDiv);
    }

    var historyEl = document.createElement("p");
    historyEl.textContent = data.history;
    modalDiv.appendChild(historyEl);

    var sourceEl = document.createElement("p");
    sourceEl.className = "source-cite";
    sourceEl.textContent = "Source: " + data.source;
    modalDiv.appendChild(sourceEl);

    var actionsDiv = document.createElement("div");
    actionsDiv.className = "barangay-modal-actions";
    var reportLink = document.createElement("a");
    reportLink.className = "btn btn-outline";
    reportLink.href = "support/report.html?barangay=" + encodeURIComponent(name);
    reportLink.textContent = "Report or update information";
    actionsDiv.appendChild(reportLink);
    modalDiv.appendChild(actionsDiv);

    overlay.appendChild(modalDiv);

    document.body.appendChild(overlay);
    requestAnimationFrame(function () { overlay.classList.add("open"); });

    closeBtn = overlay.querySelector(".barangay-modal-close");
    function close() {
      overlay.classList.remove("open");
      setTimeout(function () { overlay.remove(); }, 200);
      if (previouslyFocused && previouslyFocused.focus) previouslyFocused.focus();
    }
    closeBtn.addEventListener("click", close);
    overlay.addEventListener("click", function (e) { if (e.target === overlay) close(); });
    document.addEventListener("keydown", function handler(e) {
      if (e.key === "Escape") { close(); document.removeEventListener("keydown", handler); }
      if (e.key === "Tab") {
        var modal = overlay.querySelector(".barangay-modal");
        var focusable = modal.querySelectorAll('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])');
        if (focusable.length === 0) return;
        var first = focusable[0];
        var last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    });
    closeBtn.focus();
  }
});

// Weather code helpers
function weatherIcon(code) {
  var icons = { 0: "sun", 1: "sun", 2: "cloud-sun", 3: "cloud", 45: "cloud-fog", 48: "cloud-fog", 51: "cloud-drizzle", 53: "cloud-drizzle", 55: "cloud-rain", 61: "cloud-rain", 63: "cloud-rain", 65: "cloud-rain-heavy", 71: "snowflake", 73: "snowflake", 75: "snowflake", 80: "cloud-drizzle", 81: "cloud-rain", 82: "cloud-rain-heavy", 95: "cloud-lightning", 96: "cloud-lightning", 99: "cloud-lightning" };
  return icons[code] || "cloud-sun";
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

// Feedback widget
var feedback = document.getElementById("service-feedback");
if (feedback) {
  var feedbackService = document.querySelector(".hero h1");
  var serviceName = feedbackService ? feedbackService.textContent.trim() : "";
  var feedbackKey = "feedback_" + serviceName.replace(/[^a-z0-9]/gi, "_");
  if (localStorage.getItem(feedbackKey)) {
    feedback.querySelector(".feedback-buttons").style.display = "none";
    feedback.querySelector(".feedback-thanks").style.display = "block";
  }
  feedback.querySelectorAll("button").forEach(function(btn) {
    btn.addEventListener("click", function() {
      localStorage.setItem(feedbackKey, btn.getAttribute("data-helpful"));
      feedback.querySelector(".feedback-buttons").style.display = "none";
      feedback.querySelector(".feedback-thanks").style.display = "block";
    });
  });
}

// Language suggestion banner — shows once per session if user has a stored preference
// that differs from the current page language
(function() {
  var banner = document.getElementById("lang-banner");
  if (!banner) return;

  var stored = localStorage.getItem("bettermapandan_lang");
  var current = getCurrentLang();

  // Don't show if no preference stored or already on preferred language
  if (!stored || stored === current) return;

  // Don't show if already dismissed this session
  if (sessionStorage.getItem("lang_banner_dismissed")) return;

  // Build banner content
  var isEnPage = current === "en";
  var switchLabel = isEnPage ? "Filipino" : "English";
  var switchUrl;
  if (isEnPage) {
    // EN page → link to FIL version
    switchUrl = "/fil" + location.pathname;
  } else {
    // FIL page → link to EN version
    switchUrl = location.pathname.replace("/fil/", "/");
  }
  switchUrl += location.search + location.hash;

  var msgLabel = isEnPage
    ? "Mababasa rin ito sa Filipino"
    : "This page is also available in English";

  banner.innerHTML =
    '<div class="lang-banner-inner">' +
    '<span class="lang-banner-msg">' + msgLabel + '</span>' +
    '<a href="' + switchUrl + '" class="lang-banner-btn" onclick="switchLang(\'' + stored + '\')">Switch to ' + switchLabel + '</a>' +
    '<button class="lang-banner-dismiss" aria-label="Dismiss">&times;</button>' +
    '</div>';

  banner.style.display = "block";

  // Dismiss handler
  banner.querySelector(".lang-banner-dismiss").addEventListener("click", function() {
    banner.style.display = "none";
    sessionStorage.setItem("lang_banner_dismissed", "1");
  });
})();
