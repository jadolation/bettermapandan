/* Shared utilities for BetterMapandan transparency and stats pages. */
var MapandanCommon = window.MapandanCommon || {};

MapandanCommon.MAYORAL_TERMS = [
  { start: "2010-06-30", end: "2016-06-29", mayor: "Maximo Calimlim Jr." },
  { start: "2016-06-30", end: "2019-06-29", mayor: "Gerald Glenn L. Tambaoan" },
  { start: "2019-06-30", end: "2022-06-29", mayor: "Anthony C. Penuliar" },
  { start: "2022-06-30", end: "2099-12-31", mayor: "Karl Christian F. Vega" }
];

MapandanCommon.getCustomDateRange = function () {
  var fromEl = document.getElementById("custom-date-from");
  var toEl = document.getElementById("custom-date-to");
  var from = fromEl && fromEl.value ? new Date(fromEl.value) : null;
  var to = toEl && toEl.value ? new Date(toEl.value) : null;
  if (to) to.setHours(23, 59, 59, 999);
  return { from: from, to: to };
};

MapandanCommon.computeCutoff = function (range) {
  if (range === "all" || range === "custom") return null;
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
  } else {
    return null;
  }
  return cutoff;
};

MapandanCommon.filterByMayoralTerm = function (contracts, termIndex) {
  if (termIndex === null || termIndex === undefined) return contracts.slice();
  var term = MapandanCommon.MAYORAL_TERMS[termIndex];
  if (!term) return contracts.slice();
  var from = new Date(term.start);
  var to = new Date(term.end);
  to.setHours(23, 59, 59, 999);
  return contracts.filter(function (c) {
    var dateStr = c.award_date || (c.fiscal_year ? c.fiscal_year + "-01-01" : null);
    if (!dateStr) return false;
    var d = new Date(dateStr);
    return d >= from && d <= to;
  });
};

MapandanCommon.filterByCustomDate = function (projects, dateFrom, dateTo, dateField) {
  if (!dateFrom && !dateTo) return projects;
  return projects.filter(function (p) {
    var dStr = p[dateField] || p.contract_effectivity_date || (p.fiscal_year ? p.fiscal_year + "-01-01" : null);
    if (!dStr) return false;
    var d = new Date(dStr);
    if (dateFrom && d < dateFrom) return false;
    if (dateTo && d > dateTo) return false;
    return true;
  });
};

window.MapandanCommon = MapandanCommon;
