function downloadCSV(type) {
  var csv = "";
  if (type === "budget") {
    csv = "Fiscal Year,Total Enacted Budget (PHP)\nCY 2020,122402454\nCY 2021,129281542\nCY 2022,173142760\nCY 2023,151540728\nCY 2024,160828663\nCY 2025,193088074\nCY 2026,218209788";
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
  { start: "2019-06-30", end: "2022-06-29", mayor: "Anthony \"Dooy\" C. Penuliar" },
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

function updateAll(range, mayoralTermIndex) {
  if (mayoralTermIndex === undefined) mayoralTermIndex = currentMayoralTerm;
  currentMayoralTerm = mayoralTermIndex;
  var byTerm = mayoralTermIndex !== null && mayoralTermIndex !== undefined ? filterByMayoralTerm(allContracts, mayoralTermIndex) : null;
  var base = byTerm !== null ? byTerm : allContracts;
  var filtered = filterByRange(base, range);
  currentRange = range;
  updateMetrics(filtered);
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

  if (window._refreshTable) window._refreshTable();
}

document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll('[data-download]').forEach(function(btn) {
    btn.addEventListener("click", function() {
      downloadCSV(this.getAttribute("data-download"));
    });
  });

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
          backgroundColor: [green, green, gold, green, green, gold, gold]
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true } }
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
  if (filterContainer) {
    filterContainer.addEventListener("click", function(e) {
      var btn = e.target.closest(".filter-pill");
      if (!btn) return;
      filterContainer.querySelectorAll(".filter-pill").forEach(function(b) { b.classList.remove("active"); });
      btn.classList.add("active");
      updateAll(btn.getAttribute("data-range"), currentMayoralTerm);
    });
  }
  if (termContainer) {
    termContainer.addEventListener("click", function(e) {
      var btn = e.target.closest(".term-pill");
      if (!btn) return;
      termContainer.querySelectorAll(".term-pill").forEach(function(b) { b.classList.remove("active"); });
      btn.classList.add("active");
      var idx = parseInt(btn.getAttribute("data-term"), 10);
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
      downloadCSV("procurement");
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
