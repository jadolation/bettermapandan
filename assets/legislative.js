function downloadCSV(type) {
  var csv = "";
  if (type === "legislative") {
    var data = window.LEGISLATIVE_CHARTS || {};
    var cats = data.categories || {};
    csv = "Category,Count\n";
    var keys = Object.keys(cats);
    for (var i = 0; i < keys.length; i++) {
      csv += keys[i] + "," + cats[keys[i]] + "\n";
    }
  } else if (type === "ordinances") {
    var rows = window.LEGISLATIVE_ORDINANCES || [];
    if (!rows.length) return;
    var headers = ["number","title","date_enacted","category","sp_review","status","source_url"];
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
  } else if (type === "resolutions") {
    var rows = window.LEGISLATIVE_RESOLUTIONS || [];
    if (!rows.length) return;
    var headers = ["number","title","date_approved","fiscal_value","source_url"];
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
  } else if (type === "executive") {
    var rows = window.LEGISLATIVE_EXECUTIVE || [];
    if (!rows.length) return;
    var headers = ["title","date","authority","description"];
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
  if (!csv) return;
  var blob = new Blob([csv], { type: "text/csv" });
  var a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "mapandan-legislative-" + type + ".csv";
  a.click();
}

function initLegislativeTables() {
  var ordinances = window.LEGISLATIVE_ORDINANCES || [];
  var resolutions = window.LEGISLATIVE_RESOLUTIONS || [];
  var executive = window.LEGISLATIVE_EXECUTIVE || [];

  var tables = {
    ordinances: { data: ordinances, page: 1, sortCol: null, sortDir: "asc", search: "" },
    resolutions: { data: resolutions, page: 1, sortCol: null, sortDir: "asc", search: "" },
    executive: { data: executive, page: 1, sortCol: null, sortDir: "asc", search: "" }
  };

  var searchInput = document.getElementById("legislative-search");
  var csvBtn = document.getElementById("legislative-csv-btn");
  var pagination = document.getElementById("legislative-pagination");
  var pageInfo = document.getElementById("legislative-page-info");
  var pageIndicator = document.getElementById("legislative-page-indicator");

  var ordTable = document.getElementById("ordinances-table");
  var resTable = document.getElementById("resolutions-table");
  var execTable = document.getElementById("executive-table");

  if (!ordTable || !resTable || !execTable) return;

  function getFilteredSorted(type) {
    var t = tables[type];
    var data = t.data.slice();
    var q = (t.search || "").toLowerCase();
    if (q) {
      data = data.filter(function(r) {
        return Object.keys(r).some(function(k) {
          var v = r[k];
          return v !== undefined && v !== null && String(v).toLowerCase().indexOf(q) > -1;
        });
      });
    }
    if (t.sortCol) {
      data.sort(function(a, b) {
        var va = a[t.sortCol] !== undefined ? a[t.sortCol] : "";
        var vb = b[t.sortCol] !== undefined ? b[t.sortCol] : "";
        if (t.sortCol === "fiscal_value") {
          var na = parseFloat(String(va).replace(/[^0-9.-]/g, "")) || 0;
          var nb = parseFloat(String(vb).replace(/[^0-9.-]/g, "")) || 0;
          return t.sortDir === "asc" ? na - nb : nb - na;
        }
        va = String(va);
        vb = String(vb);
        if (va === vb) return 0;
        if (t.sortDir === "asc") return va < vb ? -1 : 1;
        return va > vb ? -1 : 1;
      });
    }
    return data;
  }

  function escapeHtml(s) {
    return String(s !== undefined ? s : "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function buildSourceLink(url) {
    if (url && url.startsWith && url.startsWith("http")) {
      return '<a href="' + escapeHtml(url) + '" target="_blank" rel="noopener">Source &rarr;</a>';
    }
    return "—";
  }

  function formatOrdinanceRow(r) {
    var cat_label = r.category ? r.category.charAt(0).toUpperCase() + r.category.slice(1) : "";
    var status_class = "";
    if (r.status === "enacted") status_class = "pill-enacted";
    else if (r.status === "pending") status_class = "pill-pending";
    var status_text = r.status ? r.status.charAt(0).toUpperCase() + r.status.slice(1) : "";
    return '<tr>' +
      '<td>' + escapeHtml(r.number || "") + '</td>' +
      '<td>' + escapeHtml(r.title || "") + '</td>' +
      '<td>' + escapeHtml(r.date_enacted || "") + '</td>' +
      '<td><span class="category-pill category-' + escapeHtml(r.category || "") + '">' + escapeHtml(cat_label) + '</span></td>' +
      '<td>' + escapeHtml(r.sp_review || "") + '</td>' +
      '<td><span class="pill ' + status_class + '">' + status_text + '</span></td>' +
      '<td>' + buildSourceLink(r.source_url) + '</td>' +
      '</tr>';
  }

  function formatResolutionRow(r) {
    var rawFiscal = r.fiscal_value;
    var fiscal = rawFiscal !== undefined && rawFiscal !== null && String(rawFiscal).trim() !== ""
      ? "₱" + parseFloat(String(rawFiscal).replace(/[^0-9.-]/g, "")).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})
      : "—";
    return '<tr>' +
      '<td>' + escapeHtml(r.number || "") + '</td>' +
      '<td>' + escapeHtml(r.title || "") + '</td>' +
      '<td>' + escapeHtml(r.date_approved || "") + '</td>' +
      '<td>' + fiscal + '</td>' +
      '<td>' + buildSourceLink(r.source_url) + '</td>' +
      '</tr>';
  }

  function formatExecutiveRow(r) {
    var date = r.date ? escapeHtml(r.date) : "—";
    return '<tr>' +
      '<td>' + escapeHtml(r.title || "") + '</td>' +
      '<td>' + date + '</td>' +
      '<td>' + escapeHtml(r.authority || "") + '</td>' +
      '<td>' + escapeHtml(r.description || "") + '</td>' +
      '</tr>';
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

  function renderTable(type, tableEl, formatter) {
    var t = tables[type];
    var filtered = getFilteredSorted(type);
    var totalPages = Math.max(1, Math.ceil(filtered.length / 20));
    if (t.page > totalPages) t.page = totalPages;
    var start = (t.page - 1) * 20;
    var pageData = filtered.slice(start, start + 20);

    var tbody = tableEl.querySelector("tbody");
    var rows = [];
    for (var i = 0; i < pageData.length; i++) {
      rows.push(formatter(pageData[i]));
    }
    if (!rows.length) {
      rows.push('<tr><td colspan="' + tableEl.querySelectorAll("th").length + '">No results</td></tr>');
    }
    tbody.innerHTML = rows.join("");

    tableEl.querySelectorAll("th[data-column]").forEach(function(th) {
      var col = th.getAttribute("data-column");
      if (t.sortCol === col) {
        th.classList.add(t.sortDir === "asc" ? "sort-asc" : "sort-desc");
      } else {
        th.classList.remove("sort-asc", "sort-desc");
      }
    });

    return totalPages;
  }

  function renderAll() {
    var ordFiltered = getFilteredSorted("ordinances");
    var resFiltered = getFilteredSorted("resolutions");
    var execFiltered = getFilteredSorted("executive");

    var ordPages = renderTable("ordinances", ordTable, formatOrdinanceRow);
    var resPages = renderTable("resolutions", resTable, formatResolutionRow);
    var execPages = renderTable("executive", execTable, formatExecutiveRow);
    var totalPages = Math.max(ordPages, resPages, execPages);

    if (tables.ordinances.page > totalPages) {
      tables.ordinances.page = totalPages;
      tables.resolutions.page = totalPages;
      tables.executive.page = totalPages;
      renderTable("ordinances", ordTable, formatOrdinanceRow);
      renderTable("resolutions", resTable, formatResolutionRow);
      renderTable("executive", execTable, formatExecutiveRow);
    }

    var totalFiltered = ordFiltered.length + resFiltered.length + execFiltered.length;
    var cp = tables.ordinances.page;
    var showStart = totalFiltered === 0 ? 0 : ((cp - 1) * 20 + 1);
    var showEnd = Math.min(cp * 20, totalFiltered);

    if (pageInfo) {
      pageInfo.textContent = totalFiltered === 0 ? "No results" : ("Showing " + showStart + "-" + showEnd + " of " + totalFiltered);
    }
    if (pageIndicator) {
      pageIndicator.textContent = cp + " / " + totalPages;
    }

    if (pagination) {
      var numberedWrap = document.createElement("span");
      numberedWrap.className = "numbered-pages";
      numberedWrap.style.cssText = "display:inline-flex;gap:6px;align-items:center;flex-wrap:wrap";
      numberedWrap.innerHTML = renderPageNumbers(totalPages, cp);
      var existing = pagination.querySelector(".numbered-pages");
      if (existing) existing.remove();
      pagination.insertBefore(numberedWrap, pagination.children[1]);
    }
  }

  if (searchInput) {
    searchInput.addEventListener("input", function() {
      var q = this.value;
      tables.ordinances.search = q;
      tables.resolutions.search = q;
      tables.executive.search = q;
      tables.ordinances.page = 1;
      tables.resolutions.page = 1;
      tables.executive.page = 1;
      renderAll();
    });
  }

  if (csvBtn) {
    csvBtn.addEventListener("click", function() {
      downloadCSV("ordinances");
    });
  }

  [ordTable, resTable, execTable].forEach(function(tableEl, idx) {
    var type = ["ordinances", "resolutions", "executive"][idx];
    var ths = tableEl.querySelectorAll("th[data-column]");
    for (var i = 0; i < ths.length; i++) {
      (function(t, col) {
        ths[i].addEventListener("click", function() {
          if (tables[t].sortCol === col) {
            tables[t].sortDir = tables[t].sortDir === "asc" ? "desc" : "asc";
          } else {
            tables[t].sortCol = col;
            tables[t].sortDir = "asc";
          }
          tables[t].page = 1;
          renderAll();
        });
      })(type, ths[i].getAttribute("data-column"));
    }
  });

  if (pagination) {
    pagination.addEventListener("click", function(e) {
      var btn = e.target.closest("button[data-page]");
      if (!btn) return;
      var page = btn.getAttribute("data-page");
      if (page === "prev") {
        if (tables.ordinances.page > 1) tables.ordinances.page--;
      } else if (page === "next") {
        tables.ordinances.page++;
      } else {
        var pn = parseInt(page, 10);
        if (!isNaN(pn)) tables.ordinances.page = pn;
      }
      tables.resolutions.page = tables.ordinances.page;
      tables.executive.page = tables.ordinances.page;
      renderAll();
    });
  }

  renderAll();
}

document.addEventListener("DOMContentLoaded", function () {
  initLegislativeTables();
});

window.addEventListener("load", function () {
  if (typeof Chart === "undefined") return;

  var green = "#4c8a2e";
  var gold = "#e8a917";
  var data = window.LEGISLATIVE_CHARTS || {};

  var catCtx = document.getElementById("chart-legislative-categories");
  if (catCtx && data.categories) {
    var catLabels = Object.keys(data.categories);
    var catValues = catLabels.map(function (k) { return data.categories[k]; });
    new Chart(catCtx, {
      type: "doughnut",
      data: {
        labels: catLabels,
        datasets: [{
          data: catValues,
          backgroundColor: [green, gold, "#16532c", "#2d6b1f", "#6ba34e", "#8fbc5f", "#b3d47a"]
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { position: "right" } }
      }
    });
  }

  var blgfCtx = document.getElementById("chart-blgf-trend");
  if (blgfCtx && data.blgf && data.blgf.length) {
    var blgf = data.blgf;
    var years = blgf.map(function (d) { return d.year; });
    var revenues = blgf.map(function (d) { return d.annual_revenue / 1_000_000; });
    var expenditures = blgf.map(function (d) { return d.total_expenditure / 1_000_000; });
    new Chart(blgfCtx, {
      type: "line",
      data: {
        labels: years,
        datasets: [
          {
            label: "Revenue",
            data: revenues,
            borderColor: green,
            backgroundColor: "rgba(76,138,46,0.1)",
            fill: true,
            tension: 0.2,
            pointRadius: 2,
            pointHoverRadius: 4
          },
          {
            label: "Expenditure",
            data: expenditures,
            borderColor: gold,
            backgroundColor: "rgba(232,169,23,0.1)",
            fill: true,
            tension: 0.2,
            pointRadius: 2,
            pointHoverRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: true } },
        scales: {
          y: { beginAtZero: true },
          x: { ticks: { maxTicksLimit: 12, maxRotation: 0 } }
        }
      }
    });
  }

  var budgetCtx = document.getElementById("chart-budget-growth");
  if (budgetCtx && data.budget && data.budget.length) {
    var budget = data.budget;
    var budgetYears = budget.map(function (d) { return "CY " + d.year; });
    var budgetAmounts = budget.map(function (d) { return d.amount / 1_000_000; });
    new Chart(budgetCtx, {
      type: "bar",
      data: {
        labels: budgetYears,
        datasets: [{
          label: "Annual Budget (PHP Millions)",
          data: budgetAmounts,
          backgroundColor: [green, green, gold, green, green, green, gold]
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true } }
      }
    });
  }
});
