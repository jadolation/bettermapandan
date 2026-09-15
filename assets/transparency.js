function downloadTransparencyCSV(type) {
  var csv = "";
  if (type === "budget") {
    csv = "Fiscal Year,Total Enacted Budget (PHP)\nCY 2020,122402454\nCY 2021,129281542\nCY 2022,173142760\nCY 2023,151540728\nCY 2024,160828663\nCY 2025,193088074\nCY 2026,218209788";
  } else if (type === "audit-opinions") {
    csv = "Year,Opinion\n2014,Unqualified\n2015,Qualified\n2016,Qualified\n2017,Qualified\n2018,Qualified\n2019,Qualified\n2020,Qualified\n2021,Qualified\n2022,Qualified\n2023,Unqualified\n2024,Qualified";
  } else if (type === "financial-performance") {
    csv = "Year,Income,Expenses,Surplus/Deficit,Source\n2014,71432036,61566073,9865963,COA AAR\n2015,81052292,67593459,13458833,COA AAR\n2016,88255537,78852072,9403465,COA AAR\n2017,99989387,95214375,4775012,COA AAR\n2018,106700000,97500000,9200000,COA AAR\n2019,116100000,106800000,9300000,COA AAR\n2020,128331255,131058342,6552809,COA AAR\n2021,144503846,133834650,10669196,COA AAR\n2022,180618300,166571000,14047290,COA AAR\n2023,159409832,168264248,-8854416,COA AAR\n2024,173759470,183574901,-9815431,COA AAR";
  } else if (type === "implementation-rates") {
    csv = "Period,Implemented,Partial,Not Implemented,Rate\n2014 to 2015,6,0,1,86%\n2015 to 2016,6,1,1,75%\n2016 to 2017,6,4,4,43%\n2017 to 2018,7,4,5,44%\n2018 to 2019,9,7,4,45%\n2019 to 2020,18,0,6,75%\n2020 to 2021,10,0,11,48%\n2021 to 2022,12,0,16,43%\n2022 to 2023,11,0,20,35%\n2023 to 2024,14,0,23,38%";
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

function filterByRange(contracts, range) {
  if (range === "all") return contracts.slice();
  if (range === "custom") {
    var dates = getCustomDateRange();
    return filterByCustomDate(contracts, dates.from, dates.to);
  }
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
    return contracts.slice();
  }
  return contracts.filter(function(c) {
    if (!c.award_date) return false;
    var d = new Date(c.award_date);
    return d >= cutoff;
  });
}

var mayoralTerms = [
  { start: "2010-06-30", end: "2016-06-29", mayor: "Maximo Calimlim Jr." },
  { start: "2016-06-30", end: "2019-06-29", mayor: "Gerald Glenn L. Tambaoan" },
  { start: "2019-06-30", end: "2022-06-29", mayor: "Anthony C. Penuliar" },
  { start: "2022-06-30", end: "2099-12-31", mayor: "Karl Christian F. Vega" }
];
var currentMayoralTerm = null;

function filterByMayoralTerm(contracts, termIndex) {
  if (termIndex === null || termIndex === undefined) return contracts.slice();
  var term = mayoralTerms[termIndex];
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
  var fromEl = document.getElementById("custom-date-from");
  var toEl = document.getElementById("custom-date-to");
  var from = fromEl && fromEl.value ? new Date(fromEl.value) : null;
  var to = toEl && toEl.value ? new Date(toEl.value) : null;
  if (to) to.setHours(23, 59, 59, 999);
  return { from: from, to: to };
}

function filterByCustomDate(projects, dateFrom, dateTo) {
  if (!dateFrom && !dateTo) return projects;
  return projects.filter(function(p) {
    var dStr = p.actual_completion_date || p.contract_effectivity_date || (p.fiscal_year ? p.fiscal_year + "-01-01" : null);
    if (!dStr) return false;
    var d = new Date(dStr);
    if (dateFrom && d < dateFrom) return false;
    if (dateTo && d > dateTo) return false;
    return true;
  });
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
    var termStarts = ["2010-06-30","2016-06-30","2019-06-30","2022-06-30"];
    var termEnds = ["2016-06-29","2019-06-29","2022-06-29","2099-12-31"];
    var tFrom = new Date(termStarts[mayoralTermIndex]);
    var tTo = new Date(termEnds[mayoralTermIndex]);
    tTo.setHours(23,59,59,999);
    dpwhFiltered = dpwhFiltered.filter(function(p) {
      var dStr = p.actual_completion_date || p.contract_effectivity_date || (p.fiscal_year ? p.fiscal_year + "-01-01" : null);
      if (!dStr) return false;
      var d = new Date(dStr);
      return d >= tFrom && d <= tTo;
    });
  }
  if (range && range !== "all" && range !== "custom") {
    var now = new Date();
    var cutoff;
    if (range === "30d") cutoff = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 30);
    else if (range === "3m") cutoff = new Date(now.getFullYear(), now.getMonth() - 3, now.getDate());
    else if (range === "6m") cutoff = new Date(now.getFullYear(), now.getMonth() - 6, now.getDate());
    else if (range === "1y") cutoff = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
    else if (range === "3y") cutoff = new Date(now.getFullYear() - 3, now.getMonth(), now.getDate());
    if (cutoff) {
      dpwhFiltered = dpwhFiltered.filter(function(p) {
        var dStr = p.actual_completion_date || p.contract_effectivity_date || (p.fiscal_year ? p.fiscal_year + "-01-01" : null);
        if (!dStr) return false;
        return new Date(dStr) >= cutoff;
      });
    }
  }
  if (range === "custom") {
    var customDates = getCustomDateRange();
    dpwhFiltered = filterByCustomDate(dpwhFiltered, customDates.from, customDates.to);
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

  initProcurementTable();
});

window.addEventListener("load", function () {
  if (typeof Chart === "undefined") return;

  var green = "#4c8a2e";
  var gold = "#e8a917";

  var budgetCtx = document.getElementById("chart-budget-trend");
  if (budgetCtx) {
    new Chart(budgetCtx, {
      type: "bar",
      data: {
        labels: ["CY 2020", "CY 2021", "CY 2022", "CY 2023", "CY 2024", "CY 2025", "CY 2026"],
        datasets: [{
          label: "Total Enacted Budget (PHP Millions)",
          data: [122.40, 129.28, 173.14, 151.54, 160.83, 193.09, 218.21],
          backgroundColor: [green, green, green, green, green, green, green]
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true } }
      }
    });
  }

  // Audit Opinion Timeline Chart
  var auditOpCtx = document.getElementById("chart-audit-opinion");
  if (auditOpCtx) {
    new Chart(auditOpCtx, {
      type: "bar",
      data: {
        labels: ["2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024"],
        datasets: [{
          label: "Audit Opinion (1=Unqualified, 2=Qualified)",
          data: [1, 2, 2, 2, 2, 2, 2, 2, 2, 1, 2],
          backgroundColor: [green, gold, gold, gold, gold, gold, gold, gold, gold, green, gold]
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function(ctx) {
                return ctx.raw === 1 ? "Unqualified (Clean)" : "Qualified";
              }
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 3,
            ticks: {
              callback: function(value) {
                if (value === 1) return "Unqualified";
                if (value === 2) return "Qualified";
                return "";
              }
            }
          }
        }
      }
    });
  }

  // Total Assets Growth Chart
  var assetsCtx = document.getElementById("chart-total-assets");
  if (assetsCtx) {
    new Chart(assetsCtx, {
      type: "line",
      data: {
        labels: ["2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024"],
        datasets: [{
          label: "Total Assets (PHP Millions)",
          data: [115.0, 130.5, 243.6, 243.6, 292.9, 298.3, 257.1, 289.1, 578.5, 563.5, 555.4],
          borderColor: green,
          backgroundColor: "rgba(76,138,46,0.1)",
          fill: true,
          tension: 0.3
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: false } }
      }
    });
  }

  // Income vs Expenses Chart
  var incomeExpCtx = document.getElementById("chart-income-expenses");
  if (incomeExpCtx) {
    new Chart(incomeExpCtx, {
      type: "line",
      data: {
        labels: ["2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024"],
        datasets: [
          {
            label: "Income (PHP Millions)",
            data: [71.4, 81.1, 88.3, 100.0, 106.7, 116.1, 128.3, 144.5, 180.6, 159.4, 173.8],
            borderColor: green,
            backgroundColor: "rgba(76,138,46,0.1)",
            fill: false,
            tension: 0.3
          },
          {
            label: "Expenses (PHP Millions)",
            data: [61.6, 67.6, 78.9, 95.2, 97.5, 107.3, 131.1, 133.8, 166.6, 168.3, 183.6],
            borderColor: gold,
            backgroundColor: "rgba(232,169,23,0.1)",
            fill: false,
            tension: 0.3
          }
        ]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: true } },
        scales: { y: { beginAtZero: false } }
      }
    });
  }

  // Revenue Composition Chart
  var revCompCtx = document.getElementById("chart-revenue-composition");
  if (revCompCtx) {
    new Chart(revCompCtx, {
      type: "bar",
      data: {
        labels: ["2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024"],
        datasets: [
          {
            label: "IRA/NTA (PHP Millions)",
            data: [67.5, 73.4, 78.5, 86.3, 90.8, 103.0, 110.9, 118.0, 142.0, 128.0, 135.0],
            backgroundColor: green
          },
          {
            label: "Local Income (PHP Millions)",
            data: [8.1, 8.5, 9.2, 9.9, 10.4, 9.1, 8.4, 14.5, 22.5, 18.5, 22.0],
            backgroundColor: gold
          }
        ]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: true } },
        scales: {
          x: { stacked: true },
          y: { stacked: true, beginAtZero: true }
        }
      }
    });
  }

  // Implementation Rate Chart
  var implCtx = document.getElementById("chart-implementation-rate");
  if (implCtx) {
    new Chart(implCtx, {
      type: "bar",
      data: {
        labels: ["14→15", "15→16", "16→17", "17→18", "18→19", "19→20", "20→21", "21→22", "22→23", "23→24"],
        datasets: [
          {
            label: "Implemented",
            data: [6, 6, 6, 7, 9, 18, 10, 12, 11, 14],
            backgroundColor: green
          },
          {
            label: "Partial",
            data: [0, 1, 4, 4, 7, 0, 0, 0, 0, 0],
            backgroundColor: "#8fbc5f"
          },
          {
            label: "Not Implemented",
            data: [1, 1, 4, 5, 4, 6, 11, 16, 20, 23],
            backgroundColor: gold
          }
        ]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: true } },
        scales: {
          x: { stacked: true },
          y: { stacked: true, beginAtZero: true }
        }
      }
    });
  }

  allContracts = (window.PROCUREMENT_CONTRACTS || []).slice();
  window._filteredContracts = allContracts;
  var procurement = window.PROCUREMENT_DATA || {};

  var trendCtx = document.getElementById("chart-procurement-trend");
  if (trendCtx) {
    var monthly = procurement.monthly || [];
    trendChart = new Chart(trendCtx, {
      type: "line",
      data: {
        labels: monthly.map(function (d) { return d.month; }),
        datasets: [{
          label: "Contract Amount (PHP Millions)",
          data: monthly.map(function (d) { return d.total / 1000000; }),
          borderColor: green,
          backgroundColor: "rgba(76,138,46,0.1)",
          fill: true,
          tension: 0.2,
          pointRadius: 2,
          pointHoverRadius: 4
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true },
          x: { ticks: { maxTicksLimit: 12, maxRotation: 0 } }
        }
      }
    });
  }

  var awardeesCtx = document.getElementById("chart-procurement-awardees");
  if (awardeesCtx) {
    var awardees = procurement.awardees || [];
    var awardeeColors = ["#16532c","#2d6b1f","#4c8a2e","#6ba34e","#8fbc5f","#b3d47a","#d4e89e","#e8f3b8","#f0c040","#f6ecc9"];
    awardeesChart = new Chart(awardeesCtx, {
      type: "bar",
      data: {
        labels: awardees.map(function (d) { return d.name; }),
        datasets: [{
          label: "Total Contract Value (PHP)",
          data: awardees.map(function (d) { return d.total; }),
          backgroundColor: awardees.map(function (_, i) {
            return awardeeColors[i % awardeeColors.length];
          })
        }]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true } }
      }
    });
  }

  var catCtx = document.getElementById("chart-procurement-categories");
  if (catCtx) {
    var cats = window.PROCUREMENT_CATEGORIES || [];
    var catTotal = cats.reduce(function (s, d) { return s + d.total; }, 0);
    var catColors = ["#16532c","#2d6b1f","#4c8a2e","#6ba34e","#8fbc5f","#b3d47a","#d4e89e","#e8f3b8","#f0c040","#f6ecc9","#16532c","#2d6b1f","#4c8a2e"];
    catChart = new Chart(catCtx, {
      type: "doughnut",
      data: {
        labels: cats.map(function (d) { return d.name; }),
        datasets: [{
          data: cats.map(function (d) { return d.total; }),
          backgroundColor: cats.map(function (_, i) {
            return catColors[i % catColors.length];
          }),
          borderColor: "#fff",
          borderWidth: 2,
          cutout: "65%"
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        layout: { padding: { left: 20, right: 20 } },
        plugins: { legend: { display: false } }
      }
    });

    var legendEl = document.getElementById("category-legend");
    if (legendEl) {
      var html = '<div style="display:flex;flex-direction:column;gap:6px">';
      cats.forEach(function (d, i) {
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

  var filterContainer = document.getElementById("procurement-filters");
  var termContainer = document.getElementById("mayoral-term-filters");
  var customRangeInline = document.getElementById("custom-range-inline");
  var clearTermBtn = document.getElementById("clear-mayoral-term");
  var dpwhFilterContainer = document.getElementById("dpwh-filters");
  var dpwhTermContainer = document.getElementById("dpwh-term-filters");

  function syncDpwhFilters(range, termIndex) {
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
  if (dpwhFilterContainer) {
    dpwhFilterContainer.addEventListener("click", function(e) {
      var btn = e.target.closest(".filter-pill");
      if (!btn) return;
      dpwhFilterContainer.querySelectorAll(".filter-pill").forEach(function(b) { b.classList.remove("active"); });
      btn.classList.add("active");
      var range = btn.getAttribute("data-range");
      if (filterContainer) {
        filterContainer.querySelectorAll(".filter-pill").forEach(function(b) {
          b.classList.toggle("active", b.getAttribute("data-range") === range);
        });
      }
      updateAll(range, currentMayoralTerm);
    });
  }
  if (dpwhTermContainer) {
    dpwhTermContainer.addEventListener("click", function(e) {
      var btn = e.target.closest(".term-pill");
      if (!btn) return;
      dpwhTermContainer.querySelectorAll(".term-pill").forEach(function(b) { b.classList.remove("active"); });
      btn.classList.add("active");
      var idx = parseInt(btn.getAttribute("data-term"), 10);
      if (termContainer) {
        termContainer.querySelectorAll(".term-pill").forEach(function(b) {
          var bidx = parseInt(b.getAttribute("data-term"), 10);
          b.classList.toggle("active", bidx === idx);
        });
      }
      updateAll(currentRange, idx);
    });
  }


  document.querySelectorAll('.clickable-row').forEach(function(row) {
    row.addEventListener('click', function(e) {
      if (e.target.closest('a')) return;
      var url = this.getAttribute('data-href');
      if (url) {
        window.open(url, '_blank', 'noopener,noreferrer');
      }
    });
    row.setAttribute('tabindex', '0');
    row.setAttribute('role', 'link');
    row.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        this.click();
      }
    });
  });
});

function initProcurementTable() {
  var contracts = window.PROCUREMENT_CONTRACTS || [];
  var pageSize = 20;
  var currentPage = 1;
  var sortCol = "award_date";
  var sortDir = "desc";
  var searchQuery = "";
  var dedupe = false;

  var tableBody = document.querySelector("#procurement-table tbody");
  var pageInfo = document.getElementById("procurement-page-info");
  var pageIndicator = document.getElementById("procurement-page-indicator");
  var searchInput = document.getElementById("procurement-search");
  var csvBtn = document.getElementById("procurement-csv-btn");
  var dupBtn = document.getElementById("procurement-dup-btn");
  var pagination = document.getElementById("procurement-pagination");

  if (!tableBody) return;

  function uniqueOrgs(data) {
    var s = {};
    data.forEach(function(r) { s[r.organization_name || ""] = 1; });
    return Object.keys(s).length;
  }

  function norm(v) {
    return String(v !== undefined ? v : "").toLowerCase().trim();
  }

  function getFilteredSorted() {
    var data = (window._filteredContracts || contracts).slice();
    if (searchQuery) {
      var q = searchQuery.toLowerCase();
      data = data.filter(function(r) {
        return [r.reference_id,r.contract_no,r.title,r.awardee,r.organization_name,r.business_category,r.status,r.area].some(function(v) {
          return String(v).toLowerCase().indexOf(q) > -1;
        });
      });
    }
    if (dedupe) {
      var seen = {};
      data = data.filter(function(r) {
        var key = norm(r.title) + "|" + norm(r.awardee) + "|" + norm(r.amount);
        if (seen[key]) return false;
        seen[key] = true;
        return true;
      });
    }
    data.sort(function(a, b) {
      var va = a[sortCol] !== undefined ? a[sortCol] : "";
      var vb = b[sortCol] !== undefined ? b[sortCol] : "";
      if (sortCol === "amount") {
        var na = parseFloat(String(va).replace(/[^0-9.-]/g, "")) || 0;
        var nb = parseFloat(String(vb).replace(/[^0-9.-]/g, "")) || 0;
        return sortDir === "asc" ? na - nb : nb - na;
      }
      va = String(va);
      vb = String(vb);
      if (va === vb) return 0;
      if (sortDir === "asc") return va < vb ? -1 : 1;
      return va > vb ? -1 : 1;
    });
    return data;
  }

  function renderPageNumbers(totalPages, current) {
    var html = "";
    var pages = [];
    if (totalPages <= 7) {
      for (var i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1);
      if (current > 3) pages.push("...");
      var start = Math.max(2, current - 1);
      var end = Math.min(totalPages - 1, current + 1);
      if (current <= 3) end = Math.min(totalPages - 1, 4);
      if (current >= totalPages - 2) start = Math.max(2, totalPages - 3);
      for (var i = start; i <= end; i++) pages.push(i);
      if (current < totalPages - 2) pages.push("...");
      pages.push(totalPages);
    }
    for (var i = 0; i < pages.length; i++) {
      var p = pages[i];
      if (p === "...") {
        html += '<span style="padding:0 6px;font-weight:bold;color:var(--ink)">...</span>';
      } else {
        var active = p === current ? ' style="font-weight:bold;background:var(--green-deep);color:#fff;border-color:var(--green-deep)"' : '';
        html += '<button class="btn btn-outline" data-page="' + p + '" style="padding:10px 14px;font-size:0.95rem;min-width:44px"' + active + '>' + p + '</button>';
      }
    }
    return html;
  }

  function render() {
    var filtered = getFilteredSorted();
    var totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
    if (currentPage > totalPages) currentPage = totalPages;
    var start = (currentPage - 1) * pageSize;
    var pageData = filtered.slice(start, start + pageSize);

    var rows = [];
    for (var i = 0; i < pageData.length; i++) {
      var r = pageData[i];
      var amt = r.amount !== undefined ? r.amount : 0;
      if (typeof amt !== "number") amt = parseFloat(String(amt).replace(/[^0-9.-]/g, "")) || 0;
      rows.push(
        "<tr>" +
        "<td>" + (r.reference_id !== undefined ? r.reference_id : "") + "</td>" +
        "<td>" + (r.contract_no !== undefined ? r.contract_no : "") + "</td>" +
        "<td>" + (r.title !== undefined ? r.title : "") + "</td>" +
        "<td>" + (r.awardee !== undefined ? r.awardee : "") + "</td>" +
        "<td>" + (r.organization_name !== undefined ? r.organization_name : "") + "</td>" +
        "<td>&#8369;" + amt.toLocaleString() + "</td>" +
        "<td>" + (r.business_category !== undefined ? r.business_category : "") + "</td>" +
        "<td>" + (r.award_date !== undefined ? r.award_date : "") + "</td>" +
        "<td><span class=\"pill\">" + (r.status !== undefined ? r.status : "") + "</span></td>" +
        "</tr>"
      );
    }
    if (!rows.length) {
      rows.push('<tr><td colspan="9">No results</td></tr>');
    }
    tableBody.innerHTML = rows.join("");

    if (pageInfo) {
      var showing = "Showing " + (start + 1) + "-" + Math.min(start + pageSize, filtered.length) + " of " + filtered.length;
      pageInfo.textContent = showing;
    }
    if (pageIndicator) {
      pageIndicator.textContent = currentPage + " / " + totalPages;
    }

    var numberedWrap = document.createElement("span");
    numberedWrap.className = "numbered-pages";
    numberedWrap.style.cssText = "display:inline-flex;gap:6px;align-items:center;flex-wrap:wrap";
    numberedWrap.innerHTML = renderPageNumbers(totalPages, currentPage);
    var existingNumbered = pagination.querySelector(".numbered-pages");
    if (existingNumbered) existingNumbered.remove();
    pagination.insertBefore(numberedWrap, pagination.children[1]);

    document.querySelectorAll("#procurement-table th[data-column]").forEach(function(th) {
      var col = th.getAttribute("data-column");
      if (sortCol === col) {
        th.classList.add(sortDir === "asc" ? "sort-asc" : "sort-desc");
      } else {
        th.classList.remove("sort-asc", "sort-desc");
      }
    });
  }

  window._refreshTable = function() { currentPage = 1; render(); };

  if (searchInput) {
    searchInput.addEventListener("input", function() {
      searchQuery = this.value;
      currentPage = 1;
      render();
    });
  }

  if (csvBtn) {
    csvBtn.addEventListener("click", function() {
      downloadTransparencyCSV("procurement");
    });
  }

  if (dupBtn) {
    var dupOriginal = dupBtn.textContent;
    dupBtn.addEventListener("click", function() {
      dedupe = !dedupe;
      if (dedupe) {
        dupBtn.classList.add("btn-primary");
        dupBtn.textContent = "Showing deduped";
      } else {
        dupBtn.classList.remove("btn-primary");
        dupBtn.textContent = dupOriginal;
      }
      currentPage = 1;
      render();
    });
  }

  document.querySelectorAll("#procurement-table th[data-column]").forEach(function(th) {
    th.addEventListener("click", function() {
      var col = this.getAttribute("data-column");
      if (sortCol === col) {
        sortDir = sortDir === "asc" ? "desc" : "asc";
      } else {
        sortCol = col;
        sortDir = "asc";
      }
      currentPage = 1;
      render();
    });
  });

  if (pagination) {
    pagination.addEventListener("click", function(e) {
      var btn = e.target.closest("button[data-page]");
      if (!btn) return;
      var page = btn.getAttribute("data-page");
      var filtered = getFilteredSorted();
      var totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
      if (page === "prev") {
        if (currentPage > 1) currentPage--;
      } else if (page === "next") {
        if (currentPage < totalPages) currentPage++;
      } else {
        var pn = parseInt(page, 10);
        if (!isNaN(pn)) currentPage = pn;
      }
      render();
    });
  }

  render();
}
