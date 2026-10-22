(function () {
  "use strict";
  var FIELDS = ["temperature_2m", "apparent_temperature", "wind_speed_10m", "wind_direction_10m", "precipitation"];
  var UNITS = ["°C", "°C", "km/h", "°", "mm"];
  var TTL = 60 * 60 * 1000;
  var MODES = { temperature: [0, "°C", "#b44a25"], feels: [1, "°C", "#a23e65"], wind: [2, "km/h", "#176c83"], rain: [4, "mm", "#3658b5"] };
  function requestUrl(center) {
    if (!Array.isArray(center) || center.length !== 2 || !center.every(Number.isFinite) || Math.abs(center[0]) > 180 || Math.abs(center[1]) > 90) throw Error("Invalid weather location");
    var url = new URL("https://api.open-meteo.com/v1/forecast");
    url.search = new URLSearchParams({ latitude: center[1], longitude: center[0], hourly: FIELDS.join(","),
      temperature_unit: "celsius", wind_speed_unit: "kmh", precipitation_unit: "mm", timezone: "Asia/Manila", timeformat: "unixtime", forecast_hours: "48" });
    return url.href;
  }
  function normalize(data) {
    if (!data || data.error || !data.hourly || !data.hourly_units || data.hourly_units.time !== "unixtime") throw Error("Invalid weather response");
    var times = data.hourly.time;
    if (!Array.isArray(times) || !times.length || times.length > 72 || times.some(function (t, i) { return !Number.isFinite(t) || t <= 0 || (i && t <= times[i - 1]); })) throw Error("Invalid weather times");
    FIELDS.forEach(function (field, i) {
      if (data.hourly_units[field] !== UNITS[i] || !Array.isArray(data.hourly[field]) || data.hourly[field].length !== times.length) throw Error("Invalid weather units or arrays");
    });
    return times.map(function (time, index) {
      return { time: time * 1000, values: FIELDS.map(function (field, i) {
        var v = data.hourly[field][index];
        return Number.isFinite(v) && !(i >= 2 && v < 0) && !(i === 3 && v > 360) ? v : null;
      }) };
    });
  }
  function windRotation(from) { return (from + 180) % 360; }
  function formatTime(time, lang) {
    return new Intl.DateTimeFormat(lang === "fil" ? "fil-PH" : "en-PH", {
      timeZone: "Asia/Manila", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: true,
    }).format(time) + " PHT";
  }
  function normalizeRadar(data) {
    if (!data || data.host !== "https://tilecache.rainviewer.com" || !data.radar || !Array.isArray(data.radar.past) || !data.radar.past.length || data.radar.past.length > 24) throw Error("Invalid radar response");
    return data.radar.past.map(function (frame, i, frames) {
      if (!Number.isSafeInteger(frame.time) || frame.time <= 0 || frame.time > Date.now() / 1000 + 600 || (i && frame.time <= frames[i - 1].time) || !/^\/v2\/radar\/[a-zA-Z0-9_-]+$/.test(frame.path)) throw Error("Invalid radar frame");
      return { time: frame.time * 1000, url: data.host + frame.path + "/256/{z}/{x}/{y}/2/1_0.png" };
    });
  }
  function attachRadar(map, L, panel, toggle, lang) {
    var picker = document.getElementById("gis-radar-time"), slider = document.getElementById("gis-radar-opacity");
    var output = document.getElementById("gis-radar-opacity-value"), status = document.getElementById("gis-radar-status");
    var play = document.getElementById("gis-radar-play"), playing = false, playbackTimer = null;
    var labels = panel.dataset, frames = [], retrieved = 0, nextRequest = 0, controller = null, timer = null, layer = null, generation = 0;
    var pane = map.createPane("gis-radar"); pane.style.zIndex = "350"; pane.style.pointerEvents = "none";
    function pause() {
      playing = false; clearTimeout(playbackTimer); playbackTimer = null;
      play.textContent = labels.radarPlay; play.setAttribute("aria-pressed", "false");
    }
    function schedule() {
      clearTimeout(playbackTimer);
      if (!playing || document.hidden || !toggle.checked) return;
      // Allow fewer frame requests when zoomed out to respect the provider's tile budget.
      var delay = Math.max(1500, pane.querySelectorAll("img").length * 750);
      playbackTimer = setTimeout(function () {
        var index = frames.findIndex(function (f) { return String(f.time) === picker.value; });
        picker.value = String(frames[(index + 1) % frames.length].time); draw();
      }, delay);
    }
    function clear() { if (layer) { map.removeLayer(layer); layer.off(); layer = null; } }
    function radarStatus() {
      if (!layer) return;
      var bounds = map.getContainer().getBoundingClientRect(), checked = false;
      try {
        var tiles = pane.querySelectorAll("img.leaflet-tile-loaded");
        for (var i = 0; i < tiles.length; i++) {
          var tile = tiles[i], rect = tile.getBoundingClientRect();
          var left = Math.max(rect.left, bounds.left), top = Math.max(rect.top, bounds.top);
          var right = Math.min(rect.right, bounds.right), bottom = Math.min(rect.bottom, bounds.bottom);
          if (right <= left || bottom <= top || !tile.naturalWidth) continue;
          var canvas = document.createElement("canvas"); canvas.width = tile.naturalWidth; canvas.height = tile.naturalHeight;
          var ctx = canvas.getContext("2d", { willReadFrequently: true }); ctx.drawImage(tile, 0, 0);
          var x = Math.floor((left - rect.left) / rect.width * canvas.width), y = Math.floor((top - rect.top) / rect.height * canvas.height);
          var w = Math.min(canvas.width - x, Math.ceil((right - left) / rect.width * canvas.width));
          var h = Math.min(canvas.height - y, Math.ceil((bottom - top) / rect.height * canvas.height));
          var pixels = ctx.getImageData(x, y, w, h).data; checked = true;
          for (var j = 3; j < pixels.length; j += 4) if (pixels[j] > 0) { status.textContent = labels.radarReady; return; }
        }
        status.textContent = checked ? labels.radarEmpty : labels.radarReady;
      } catch (error) { status.textContent = labels.radarReady; }
    }
    function draw() {
      clearTimeout(playbackTimer); clear();
      if (!toggle.checked || !frames.length || Date.now() - frames[frames.length - 1].time > 3600000) { pause(); play.disabled = true; status.textContent = labels.radarUnavailable; return; }
      var frame = frames.find(function (f) { return String(f.time) === picker.value; });
      if (!frame) return;
      status.textContent = labels.loading;
      layer = L.tileLayer(frame.url, { pane: "gis-radar", crossOrigin: true, opacity: Number(slider.value) / 100, maxNativeZoom: 7, maxZoom: 19,
        updateWhenIdle: true, keepBuffer: 1, attribution: '<a href="https://www.rainviewer.com/" target="_blank" rel="noopener">RainViewer</a>' });
      var failed = false;
      layer.on("tileerror", function () { failed = true; pause(); status.textContent = labels.radarUnavailable; });
      layer.on("load", function () { if (!failed) { radarStatus(); schedule(); } });
      layer.addTo(map);
    }
    map.on("moveend", function () { if (layer && !layer.isLoading() && status.textContent !== labels.radarUnavailable) radarStatus(); });
    async function load() {
      if (!toggle.checked || document.hidden || controller) return;
      if (Date.now() - retrieved < 600000 && frames.length) { if (!layer) draw(); return; }
      if (Date.now() < nextRequest) return;
      nextRequest = Date.now() + 60000;
      var id = ++generation, abort = new AbortController(); controller = abort;
      var timeout = setTimeout(function () { abort.abort(); }, 10000);
      status.textContent = labels.loading;
      try {
        var response = await fetch("https://api.rainviewer.com/public/weather-maps.json", { signal: abort.signal, credentials: "omit", redirect: "error" });
        if (id !== generation) return;
        if (response.status === 429 || response.status === 503) nextRequest = Date.now() + 5 * 60000;
        if (!response.ok) throw Error("Radar unavailable");
        var next = normalizeRadar(await response.json());
        if (id !== generation || !toggle.checked) return;
        var previous = picker.value, wasLatest = !frames.length || previous === String(frames[frames.length - 1].time);
        frames = next; retrieved = Date.now(); picker.replaceChildren();
        frames.forEach(function (frame) { var option = document.createElement("option"); option.value = String(frame.time); option.textContent = formatTime(frame.time, lang); picker.appendChild(option); });
        picker.value = !wasLatest && frames.some(function (f) { return String(f.time) === previous; }) ? previous : String(frames[frames.length - 1].time);
        picker.disabled = false; play.disabled = frames.length < 2; draw();
      } catch (error) {
        if (id !== generation) return;
        pause(); clear(); play.disabled = true; picker.disabled = true; status.textContent = labels.radarUnavailable;
      } finally {
        clearTimeout(timeout); if (id === generation) controller = null;
      }
    }
    function tick() {
      if (document.hidden) { pause(); return; }
      if (!toggle.checked) return;
      if (frames.length && Date.now() - frames[frames.length - 1].time > 3600000) { pause(); clear(); play.disabled = true; status.textContent = labels.radarUnavailable; }
      load();
    }
    function stop() { pause(); generation++; if (controller) controller.abort(); controller = null; clearInterval(timer); timer = null; clear(); }
    toggle.addEventListener("change", function () { stop(); if (toggle.checked) { load(); timer = setInterval(tick, 60000); } });
    picker.addEventListener("change", function () { pause(); draw(); });
    play.addEventListener("click", function () {
      if (playing) { pause(); return; }
      if (!toggle.checked || picker.disabled || frames.length < 2) return;
      playing = true; play.textContent = labels.radarPause; play.setAttribute("aria-pressed", "true");
      if (!layer || !layer.isLoading()) schedule();
    });
    map.on("movestart", pause);
    slider.addEventListener("input", function () { output.textContent = slider.value + "%"; if (layer) layer.setOpacity(Number(slider.value) / 100); });
    document.addEventListener("visibilitychange", tick);
    window.addEventListener("pagehide", stop);
    map.on("unload", function () { stop(); document.removeEventListener("visibilitychange", tick); window.removeEventListener("pagehide", stop); });
  }
  function attach(map, L, center) {
    var panel = document.getElementById("gis-weather");
    if (!panel) return;
    var toggle = document.getElementById("gis-weather-enabled"), picker = document.getElementById("gis-weather-time");
    var refresh = document.getElementById("gis-weather-refresh"), status = document.getElementById("gis-weather-status");
    var controls = document.getElementById("gis-weather-controls"), summary = document.getElementById("gis-weather-summary");
    var lang = document.documentElement.lang, labels = panel.dataset;
    var mode = "temperature", cache = null, retrieved = 0, selected = null, controller = null, generation = 0, timer = null, nextRequest = 0;
    var url = requestUrl(center);
    var buttons = Array.from(panel.querySelectorAll("[data-weather-mode]"));
    function node(tag, text, parent) {
      var n = document.createElement(tag); if (text != null) n.textContent = text; if (parent) parent.appendChild(n); return n;
    }
    function available(row) { return row.values[MODES[mode][0]] !== null; }
    function updateTimes() {
      var rows = (cache || []).filter(available);
      picker.replaceChildren();
      rows.forEach(function (row) { var option = node("option", formatTime(row.time, lang), picker); option.value = String(row.time); });
      if (!rows.some(function (row) { return row.time === selected; })) {
        var hour = Math.floor(Date.now() / 3600000) * 3600000;
        var nearest = rows.find(function (row) { return row.time >= hour; }) || rows[rows.length - 1];
        selected = nearest ? nearest.time : null;
      }
      if (selected !== null) picker.value = String(selected);
      picker.disabled = !rows.length;
    }
    function render() {
      summary.replaceChildren(); summary.hidden = true;
      if (!toggle.checked) return;
      if (!cache || Date.now() - retrieved > 2 * TTL) { if (!controller) status.textContent = labels.empty; return; }
      var row = cache.find(function (r) { return r.time === selected; });
      if (!row || !available(row)) { status.textContent = labels.empty; return; }
      var config = MODES[mode], value = row.values[config[0]];
      var valueText = new Intl.NumberFormat(lang === "fil" ? "fil-PH" : "en-PH", { maximumFractionDigits: mode === "rain" ? 1 : 0 }).format(value) + " " + config[1];
      var label = buttons.find(function (b) { return b.dataset.weatherMode === mode; }).textContent;
      summary.style.setProperty("--weather-color", config[2]); summary.hidden = false;
      node("p", labels.area, summary).className = "gis-weather-eyebrow";
      node("h2", label, summary);
      var reading = node("div", valueText, summary); reading.className = "gis-weather-reading";
      if (mode === "wind" && value > 0 && row.values[3] !== null) {
        var arrow = node("span", "↑", reading); arrow.className = "gis-weather-arrow";
        arrow.style.transform = "rotate(" + windRotation(row.values[3]) + "deg)"; arrow.setAttribute("aria-hidden", "true");
        node("p", labels.windFrom + " " + Math.round(row.values[3]) + "°", summary);
      }
      node("p", mode === "rain" ? formatTime(row.time - 3600000, lang) + " – " + formatTime(row.time, lang) : formatTime(row.time, lang), summary);
      node("small", labels.model, summary);
      var source = node("a", "Open-Meteo ↗", summary); source.href = "https://open-meteo.com/"; source.target = "_blank"; source.rel = "noopener";
      node("small", labels.retrieved + " " + formatTime(retrieved, lang), summary);
      var stale = Date.now() - retrieved >= TTL;
      if (stale) node("strong", labels.stale, summary).className = "gis-weather-stale";
      if (!controller) status.textContent = stale ? labels.stale : labels.ready;
    }
    async function load(force) {
      if (!toggle.checked || document.hidden || controller) return;
      if (!force && cache && Date.now() - retrieved < TTL) { updateTimes(); render(); return; }
      if (Date.now() < nextRequest) return;
      nextRequest = Date.now() + 60000;
      var id = ++generation, abort = new AbortController(); controller = abort;
      refresh.disabled = true; panel.setAttribute("aria-busy", "true"); status.textContent = labels.loading;
      var timeout = setTimeout(function () { abort.abort(); }, 10000);
      try {
        var response = await fetch(url, { signal: abort.signal, credentials: "omit", redirect: "error" });
        if (id !== generation) return;
        if (response.status === 429 || response.status === 503) {
          var retry = response.headers.get("Retry-After"), seconds = Number(retry);
          var until = retry && Number.isFinite(seconds) ? Date.now() + seconds * 1000 : Date.parse(retry);
          nextRequest = Math.max(Date.now() + 5 * 60000, Number.isFinite(until) ? until : 0);
        }
        if (!response.ok) throw Error(response.status === 429 ? "limited" : "network");
        var rows = normalize(await response.json());
        if (id !== generation || !toggle.checked) return;
        cache = rows; retrieved = Date.now(); controller = null; updateTimes(); render();
      } catch (error) {
        if (id !== generation || !toggle.checked) return;
        controller = null; render();
        status.textContent = error.message === "limited" ? labels.limited : labels.error;
      } finally {
        clearTimeout(timeout);
        if (id === generation) { controller = null; panel.removeAttribute("aria-busy"); refresh.disabled = Date.now() < nextRequest; }
      }
    }
    function tick() {
      if (!toggle.checked || document.hidden) return;
      refresh.disabled = !!controller || Date.now() < nextRequest;
      if (cache && Date.now() - retrieved >= TTL) render();
      load(false);
    }
    function disable() {
      generation++; if (controller) controller.abort(); controller = null;
      clearInterval(timer); timer = null;
      summary.hidden = true; controls.hidden = true; toggle.checked = false; panel.removeAttribute("aria-busy");
    }
    toggle.addEventListener("change", function () {
      if (!toggle.checked) { disable(); return; }
      controls.hidden = false; updateTimes(); render();
      refresh.disabled = Date.now() < nextRequest;
      timer = setInterval(tick, 15000); load(false);
    });
    buttons.forEach(function (button) { button.addEventListener("click", function () {
      mode = button.dataset.weatherMode;
      buttons.forEach(function (b) { b.setAttribute("aria-pressed", String(b === button)); });
      updateTimes(); render();
    }); });
    picker.addEventListener("change", function () { selected = Number(picker.value); render(); });
    refresh.addEventListener("click", function () { load(true); });
    document.addEventListener("visibilitychange", tick);
    window.addEventListener("pagehide", disable);
    map.on("unload", function () { disable(); document.removeEventListener("visibilitychange", tick); window.removeEventListener("pagehide", disable); });
    attachRadar(map, L, panel, toggle, lang);
    panel.hidden = false;
  }
  var api = { attach: attach, normalizeRadar: normalizeRadar, normalize: normalize, requestUrl: requestUrl, windRotation: windRotation, formatTime: formatTime };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof window !== "undefined") window.MapandanWeather = api;
})();
