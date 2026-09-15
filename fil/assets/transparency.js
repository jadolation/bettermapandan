/* Depends on: assets/js/common.js */

function downloadTransparencyCSV(type) {
  var csv = "";
  var data = window.TRANSPARENCY_CSV_DATA || {};
  if (type === "budget") {
    csv = data.budget || "";
  } else if (type === "audit-opinions") {
    csv = data["audit-opinions"] || "";
  } else if (type === "financial-performance") {
    csv = data["financial-performance"] || "";
  } else if (type === "implementation-rates") {
    csv = data["implementation-rates"] || "";
  } else if (type === "procurement") {
    var rows = window._filteredContracts || window.PROCUREMENT_CONTRACTS || [];
    if (!rows.length) return;
    var headers = ["reference_id","contract_no","title","awardee","organization_name","amount","business_category","award_date","status"];
    var lines = [headers.join(",")];
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      var vals = headers.map(function(h) {
        var v = r[h] !== undefined ? String(r[h]) : "";
        return '"' + v.replace(/"/g, '""') + '"';
      });
      lines.push(vals.join(","));
    }
    csv = lines.join("
");
  }
  var blob = new Blob([csv], { type: "text/csv" });
  var a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "mapandan-" + type + ".csv";
  a.click();
}

var trendChart, awardeesChart, catChart;
var allContracts = [];
var currentRange = "all";
var currentMayoralTerm = null;

function filterByRange(contracts, range) {
  if (range === "all") return contracts.slice();
  if (range === "custom") {
    var dates = getCustomDateRange();
    return filterByCustomDate(contracts, dates.from, dates.to);
  }
  var cutoff = MapandanCommon.computeCutoff(range);
  if (cutoff) {
    return contracts.filter(function(c) {
      if (!c.award_date) return false;
      var d = new Date(c.award_date);
      return d >= cutoff;
    });
  }
  return contracts.slice();
}

function filterByMayoralTerm(contracts, termIndex) {
  if (termIndex === null || termIndex === undefined) return contracts.slice();
  var term = MapandanCommon.MAYORAL_TERMS[termIndex];
  if (!term) return contracts.slice();
  var from = new Date(term.start);
  var to = new Date(term.end);
  to.setHours(23, 59, 59, 999);
  return contracts.filter(function(c) {
    if (!c.award_date) return false;
    var d = new Date(c.award_date);
    return d >= from && d <= to;
  });
}

function rebuildMonthly(contracts) {
  var byMonth = {};
  contracts.forEach(function(c) {
    if (!c.award_date) return;
    var m = c.award_date.slice(0, 7);
    byMonth[m] = (byMonth[m] || 0) + (c.amount || 0);
  });
  var result = Object.keys(byMonth).sort().map(function(m) {
    return { month: m, total: byMonth[m] };
  });
  return result;
}

function rebuildAwardees(contracts) {
  var byAwardee = {};
  contracts.forEach(function(c) {
    var name = (c.awardee || "Unknown").trim();
    if (!byAwardee[name]) byAwardee[name] = 0;
    byAwardee[name] += c.amount || 0;
  });
  return Object.keys(byAwardee)
    .map(function(name) { return { name: name, total: byAwardee[name] }; })
    .sort(function(a, b) { return b.total - a.total; })
    .slice(0, 10);
}

function rebuildCategories(contracts) {
  var byCat = {};
  contracts.forEach(function(c) {
    var cat = c.business_category || "Other";
    if (!cat) cat = "Other";
    byCat[cat] = (byCat[cat] || 0) + (c.amount || 0);
  });
  return Object.keys(byCat)
    .map(function(name) { return { name: name, total: byCat[name] }; })
    .sort(function(a, b) { return b.total - a.total; });
}

function fmtDateRange(contracts) {
  var dates = contracts.filter(function(c) { return c.award_date; }).map(function(c) { return c.award_date; });
  if (!dates.length) return "";
  dates.sort();
  var minD = dates[0], maxD = dates[dates.length - 1];
  var months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  function fmt(ds) {
    var parts = ds.split("-");
    return months[parseInt(parts[1], 10) - 1] + " " + parts[0];
  }
  return fmt(minD) + " \u2013 " + fmt(maxD);
}

function updateMetrics(contracts) {
  var total = contracts.reduce(function(s, c) { return s + (c.amount || 0); }, 0);
  var count = contracts.length;
  var avg = count > 0 ? total / count : 0;
  var cats = {};
  contracts.forEach(function(c) {
    var cat = c.business_category || "Other";
    if (!cat) cat = "Other";
    cats[cat] = true;
  });
  var uniqueCats = Object.keys(cats).length;

  var elTotal = document.getElementById("metric-total-value");
  var elAvg = document.getElementById("metric-average-value");
  var elCount = document.getElementById("metric-contracts-value");
  var elCats = document.getElementById("metric-categories-value");
  if (elTotal) elTotal.innerHTML = "₱" + total.toLocaleString("en-PH", { maximumFractionDigits: 0 });
  if (elAvg) elAvg.innerHTML = "₱" + avg.toLocaleString("en-PH", { maximumFractionDigits: 0 });
  if (elCount) elCount.textContent = count.toLocaleString();
  if (elCats) elCats.textContent = uniqueCats.toLocaleString();
}

function getCustomDateRange() {
  return MapandanCommon.getCustomDateRange();
}

function filterByCustomDate(projects, dateFrom, dateTo) {
  return MapandanCommon.filterByCustomDate(projects, dateFrom, dateTo, "actual_completion_date");
}

function updateDpwhCards(filtered) {
  var count = filtered.length;
  var total = filtered.reduce(function(s, p) { return s + (p.contract_amount || 0); }, 0);
  var completed = 0, ongoing = 0, notStarted = 0;
  filtered.forEach(function(p) {
    var st = (p.status || "").toLowerCase();
    if (st.indexOf("completed") !== -1) completed++;
    else if (st.indexOf("ongoing") !== -1) ongoing++;
    else if (st.indexOf("not yet") !== -1) notStarted++;
  });

  var elCount = document.getElementById("dpwh-count-value");
  var elValue = document.getElementById("dpwh-value-value");
  var elStatus = document.getElementById("dpwh-status-value");
  if (elCount) elCount.textContent = count.toLocaleString();
  if (elValue) elValue.innerHTML = "\u20B1" + total.toLocaleString("en-PH", { maximumFractionDigits: 0 });
  if (elStatus) elStatus.innerHTML = completed + " Completed \u2022 " + ongoing + " Ongoing \u2022 " + notStarted + " Not Started";
}

function filterDpwhTable(filtered) {
  var table = document.getElementById("dpwh-table");
  if (!table) return;
  var visibleIds = {};
  filtered.forEach(function(p) { visibleIds["dpwh-project-" + p.transaction_id] = true; });
  var rows = table.querySelectorAll("tbody tr");
  rows.forEach(function(row) {
    row.style.display = visibleIds[row.id] ? "" : "none";
  });
}

function updateAll(range, mayoralTermIndex) {
  if (mayoralTermIndex === undefined) mayoralTermIndex = currentMayoralTerm;
  currentMayoralTerm = mayoralTermIndex;
  var byTerm = mayoralTermIndex !== null && mayoralTermIndex !== undefined ? filterByMayoralTerm(allContracts, mayoralTermIndex) : null;
  var base = byTerm !== null ? byTerm : allContracts;
  var filtered = filterByRange(base, range);
  currentRange = range;
  updateMetrics(filtered);

  var dpwhProjects = window.DPWH_PROJECTS || [];
  var dpwhFiltered = dpwhProjects.slice();
  if (mayoralTermIndex !== null && mayoralTermIndex !== undefined) {
    var term = MapandanCommon.MAYORAL_TERMS[mayoralTermIndex];
    if (term) {
      var tFrom = new Date(term.start);
      var tTo = new Date(term.end);
      tTo.setHours(23, 59, 59, 999);
      dpwhFiltered = dpwhFiltered.filter(function(p) {
        var dStr = p.actual_completion_date || p.contract_effectivity_date || (p.fiscal_year ? p.fiscal_year + "-01-01" : null);
        if (!dStr) return false;
        var d = new Date(dStr);
        return d >= tFrom && d <= tTo;
      });
    }
  }
  if (range && range !== "all" && range !== "custom") {
    var cutoff = MapandanCommon.computeCutoff(range);
    if (cutoff) {
      dpwhFiltered = dpwhFiltered.filter(function(p) {
        var dStr = p.actual_completion_date || p.contract_effectivity_date || (p.fiscal_year ? p.fiscal_year + "-01-01" : null);
        if (!dStr) return false;
        return new Date(dStr) >= cutoff;
      });
    }
  }
  if (range === "custom") {
    var customDates = MapandanCommon.getCustomDateRange();
    dpwhFiltered = MapandanCommon.filterByCustomDate(dpwhFiltered, customDates.from, customDates.to, "actual_completion_date");
  }
  updateDpwhCards(dpwhFiltered);
  filterDpwhTable(dpwhFiltered);
  window._filteredContracts = filtered;

  var monthly = rebuildMonthly(filtered);
  var awardees = rebuildAwardees(filtered);
  var cats = rebuildCategories(filtered);

  if (trendChart) {
    trendChart.data.labels = monthly.map(function(d) { return d.month; });
    trendChart.data.datasets[0].data = monthly.map(function(d) { return d.total / 1000000; });
    trendChart.update();
  }

  if (awardeesChart) {
    awardeesChart.data.labels = awardees.map(function(d) { return d.name; });
    awardeesChart.data.datasets[0].data = awardees.map(function(d) { return d.total; });
    awardeesChart.update();
  }

  if (catChart) {
    catChart.data.labels = cats.map(function(d) { return d.name; });
    catChart.data.datasets[0].data = cats.map(function(d) { return d.total; });
    catChart.update();

    var catTotal = cats.reduce(function(s, d) { return s + d.total; }, 0);
    var catColors = ["#16532c","#2d6b1f","#4c8a2e","#6ba34e","#8fbc5f","#b3d47a","#d4e89e","#e8f3b8","#f0c040","#f6ecc9","#16532c","#2d6b1f","#4c8a2e"];
    var legendEl = document.getElementById("category-legend");
    if (legendEl) {
      var html = '<div style="display:flex;flex-direction:column;gap:6px">';
      cats.forEach(function(d, i) {
        var pct = catTotal > 0 ? ((d.total / catTotal) * 100).toFixed(1) : "0.0";
        var amount = "\u20B1" + d.total.toLocaleString("en-PH", { maximumFractionDigits: 0 });
        var color = catColors[i % catColors.length];
        html += '<div style="display:flex;align-items:center;gap:8px;font-size:0.95rem;color:#333">';
        html += '<span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:' + color + ';flex-shrink:0"></span>';
        html += '<span style="flex:1;min-width:0">' + d.name + '</span>';
        html += '<span style="white-space:nowrap;font-weight:600">' + amount + '</span>';
        html += '<span style="white-space:nowrap;color:#666;width:52px;text-align:right">' + pct + '%</span>';
        html += '</div>';
      });
      html += '</div>';
      legendEl.innerHTML = html;
    }
  }

  var toolbarCount = document.getElementById("toolbar-count");
  var toolbarTotal = document.getElementById("toolbar-total");
  var toolbarDateRange = document.getElementById("toolbar-daterange");
  if (toolbarCount) toolbarCount.textContent = filtered.length.toLocaleString();
  var totalAmt = filtered.reduce(function(s, c) { return s + (c.amount || 0); }, 0);
  if (toolbarTotal) toolbarTotal.innerHTML = "\u20B1" + totalAmt.toLocaleString("en-PH", { maximumFractionDigits: 0 });
  if (toolbarDateRange) toolbarDateRange.textContent = fmtDateRange(filtered);
  var trendSub = document.getElementById("chart-trend-subtitle");
  var awardSub = document.getElementById("chart-awardees-subtitle");
  var catSub = document.getElementById("chart-categories-subtitle");
  var rangeText = fmtDateRange(filtered);
  var totalText = filtered.reduce(function(s, c) { return s + (c.amount || 0); }, 0);
  if (trendSub) {
    var trendLabel = trendSub.textContent.split(" • ")[0];
    trendSub.textContent = trendLabel + " • " + rangeText;
  }
  if (awardSub) {
    var awardLabel = awardSub.textContent.split(" • ")[0];
    awardSub.textContent = awardLabel + " • " + rangeText;
  }
  if (catSub) {
    catSub.innerHTML = "Total: \u20B1" + totalText.toLocaleString("en-PH", { maximumFractionDigits: 0 }) + " &bull; " + rangeText;
  }

  if (window._refreshTable) window._refreshTable();
  if (window.refreshDpwhMap) window.refreshDpwhMap(currentRange, currentMayoralTerm, customDates.from, customDates.to);
}

document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll('[data-download]').forEach(function(btn) {
    btn.addEventListener("click", function() {
      downloadTransparencyCSV(this.getAttribute("data-download"));
    });
  });

  var customRangeInline = document.getElementById("custom-range-inline");
  var customApplyBtn = document.getElementById("custom-range-apply");
  var clearTermBtn = document.getElementById("clear-mayoral-term");

  if (customApplyBtn) {
    customApplyBtn.addEventListener("click", function() {
      updateAll("custom", currentMayoralTerm);
    });
  }

  if (clearTermBtn) {
    clearTermBtn.addEventListener("click", function() {
      termContainer.querySelectorAll(".term-pill").forEach(function(b) { b.classList.remove("active"); });
      clearTermBtn.style.display = "none";
      updateAll(currentRange, null);
    });
  }
});
