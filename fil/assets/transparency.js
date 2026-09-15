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
    csv = lines.join("\n");
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

function syncDpwhFilters(range, termIndex) {
  var dpwhFilterContainer = document.getElementById("dpwh-filters");
  var dpwhTermContainer = document.getElementById("dpwh-term-filters");
  if (dpwhFilterContainer) {
    dpwhFilterContainer.querySelectorAll(".filter-pill").forEach(function(b) {
      b.classList.toggle("active", b.getAttribute("data-range") === range);
    });
  }
  if (dpwhTermContainer) {
    dpwhTermContainer.querySelectorAll(".term-pill").forEach(function(b) {
      var idx = parseInt(b.getAttribute("data-term"), 10);
      b.classList.toggle("active", idx === termIndex);
    });
  }
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
  syncDpwhFilters(currentRange, currentMayoralTerm);
  if (window.refreshDpwhMap) {
    var cd = getCustomDateRange();
    window.refreshDpwhMap(currentRange, currentMayoralTerm, cd.from, cd.to);
  }
}

document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll('[data-download]').forEach(function(btn) {
    btn.addEventListener("click", function() {
      downloadTransparencyCSV(this.getAttribute("data-download"));
    });
  });

  var filterContainer = document.getElementById("procurement-filters");
  var termContainer = document.getElementById("mayoral-term-filters");
  var customRangeInline = document.getElementById("custom-range-inline");
  var customApplyBtn = document.getElementById("custom-range-apply");
  var clearTermBtn = document.getElementById("clear-mayoral-term");

  if (filterContainer) {
    filterContainer.addEventListener("click", function(e) {
      var btn = e.target.closest(".filter-pill");
      if (!btn) return;
      var range = btn.getAttribute("data-range");
      filterContainer.querySelectorAll(".filter-pill").forEach(function(b) { b.classList.remove("active"); });
      btn.classList.add("active");
      if (range === "custom") {
        if (customRangeInline) customRangeInline.classList.add("open");
      } else {
        if (customRangeInline) customRangeInline.classList.remove("open");
        updateAll(range, currentMayoralTerm);
      }
    });
  }

  if (termContainer) {
    termContainer.addEventListener("click", function(e) {
      var btn = e.target.closest(".term-pill");
      if (!btn) return;
      termContainer.querySelectorAll(".term-pill").forEach(function(b) { b.classList.remove("active"); });
      btn.classList.add("active");
      var idx = parseInt(btn.getAttribute("data-term"), 10);
      if (clearTermBtn) clearTermBtn.style.display = "inline-block";
      updateAll(currentRange, idx);
    });
  }

  if (customApplyBtn) {
    customApplyBtn.addEventListener("click", function() {
      updateAll("custom", currentMayoralTerm);
    });
  }

  if (clearTermBtn) {
    clearTermBtn.addEventListener("click", function() {
      if (termContainer) {
        termContainer.querySelectorAll(".term-pill").forEach(function(b) { b.classList.remove("active"); });
      }
      clearTermBtn.style.display = "none";
      updateAll(currentRange, null);
    });
  }

  // COA Projects Table
  var projectsBody = document.getElementById("coa-projects-table-body");
  if (projectsBody && window.AUDIT_DATA && window.AUDIT_DATA.infrastructure_projects) {
    var projects = window.AUDIT_DATA.infrastructure_projects;
    var html = "";
    projects.forEach(function(p) {
      var costFormatted = "\u20B1" + (p.cost / 1000000).toFixed(1) + "M";
      var statusClass = p.status === "completed" ? "pill-completed" : "pill-ongoing";
      html += "<tr>";
      html += "<td><strong>" + p.name + "</strong><br><span class='text-xs text-ink-soft'>" + p.description + "</span></td>";
      html += "<td>" + costFormatted + "</td>";
      html += "<td>" + p.year_started + (p.year_completed !== p.year_started ? "\u2013" + p.year_completed : "") + "</td>";
      html += "<td>" + p.category + "</td>";
      html += "<td><span class='pill " + statusClass + "'>" + p.status.charAt(0).toUpperCase() + p.status.slice(1) + "</span></td>";
      html += "</tr>";
    });
    projectsBody.innerHTML = html;
  }

  // Disallowances Chart
  var disallowCanvas = document.getElementById("chart-disallowances");
  if (disallowCanvas && window.AUDIT_DATA && window.AUDIT_DATA.disallowances) {
    var disallowances = window.AUDIT_DATA.disallowances;
    var dLabels = disallowances.map(function(d) { return d.year; });
    var dData = disallowances.map(function(d) { return d.amount / 1000; });
    var dColors = disallowances.map(function(d) {
      return d.status === "under_appeal" ? "#f0c040" : (d.status === "persistent" ? "#d9534f" : "#5cb85c");
    });
    new Chart(disallowCanvas.getContext("2d"), {
      type: "bar",
      data: {
        labels: dLabels,
        datasets: [{
          label: "Disallowances (PHP Thousands)",
          data: dData,
          backgroundColor: dColors,
          borderColor: dColors,
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function(ctx) {
                var item = disallowances[ctx.dataIndex];
                return "\u20B1" + item.amount.toLocaleString() + " (" + item.status.replace("_", " ") + ")";
              }
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: function(v) { return "\u20B1" + v + "K"; }
            }
          }
        }
      }
    });
  }

  // Reform Trackers
  var reformContainer = document.getElementById("reform-trackers-container");
  if (reformContainer && window.AUDIT_DATA && window.AUDIT_DATA.reform_trackers) {
    var trackers = window.AUDIT_DATA.reform_trackers;
    var html = '<div class="grid grid-2">';
    trackers.forEach(function(t) {
      var statusClass = t.status === "resolved" ? "pill-completed" : (t.status === "in_progress" ? "pill-ongoing" : "pill-pending");
      html += '<div class="card">';
      html += '<div class="flex-center mb-12">';
      html += '<span class="pill ' + statusClass + '">' + t.status_label + '</span>';
      html += '<span class="text-sm text-ink-soft">' + t.category + '</span>';
      html += '</div>';
      html += '<h3>' + t.title + '</h3>';
      html += '<p class="text-sm">' + t.description + '</p>';
      if (t.finding_amount > 0) {
        html += '<p class="figure text-lg">\u20B1' + (t.finding_amount / 1000000).toFixed(1) + 'M</p>';
      }
      html += '<div style="margin-top:12px;display:flex;flex-direction:column;gap:8px">';
      t.milestones.forEach(function(m) {
        var icon = m.status === "completed" ? "\u2713" : (m.status === "in_progress" ? "\u25CB" : "\u25CB");
        var color = m.status === "completed" ? "var(--green-deep)" : (m.status === "in_progress" ? "var(--blue)" : "var(--ink-soft)");
        html += '<div style="display:flex;align-items:center;gap:8px;font-size:0.85rem">';
        html += '<span style="color:' + color + ';font-weight:600;min-width:18px">' + icon + '</span>';
        html += '<span>' + m.label;
        if (m.date) html += ' <span class="text-xs text-ink-soft">(' + m.date + ')</span>';
        html += '</span>';
        html += '</div>';
      });
      html += '</div>';
      html += '</div>';
    });
    html += '</div>';
    reformContainer.innerHTML = html;
  }

  // Audit Opinion Chart - add 2025 data point
  var opinionCanvas = document.getElementById("chart-audit-opinion");
  if (opinionCanvas && window.AUDIT_DATA && window.AUDIT_DATA.opinions) {
    var opinions = window.AUDIT_DATA.opinions;
    var oLabels = opinions.map(function(o) { return o.year; });
    var oData = opinions.map(function(o) {
      if (o.opinion === "Unqualified" || o.opinion === "Unmodified") return 3;
      if (o.opinion === "Non-Compliant") return 0;
      return 1;
    });
    var oColors = opinions.map(function(o) {
      if (o.color === "green") return "#16532c";
      if (o.color === "red") return "#d9534f";
      return "#f0c040";
    });
    // Check if chart already exists and update
    if (window._auditOpinionChart) {
      window._auditOpinionChart.data.labels = oLabels;
      window._auditOpinionChart.data.datasets[0].data = oData;
      window._auditOpinionChart.data.datasets[0].backgroundColor = oColors;
      window._auditOpinionChart.update();
    }
  }
});
