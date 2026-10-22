document.addEventListener("DOMContentLoaded", function () {
  if (typeof Chart === "undefined") {
    return;
  }

  function initChart(canvas, config) {
    if (!canvas) {
      return null;
    }
    if (canvas.chart) {
      canvas.chart.destroy();
    }
    try {
      var chart = new Chart(canvas, config);
      canvas.chart = chart;
      return chart;
    } catch (e) {
      return null;
    }
  }

  var data = window.FDP_SUMMARY || {};
  if (!data.latest_period) {
    return;
  }

  var green = "#4c8a2e";
  var gold = "#e8a917";
  var red = "#c0392b";
  var blue = "#3b82f6";
  var M = 1000000;

  function millions(value) {
    return value == null ? null : Math.round(value / M * 100) / 100;
  }

  // Revenue composition doughnut (latest quarter)
  var revCtx = document.getElementById("chart-fdp-revenue");
  if (revCtx && data.revenue) {
    var detail = data.revenue.detail || {};
    var taxKeys = Object.keys(detail).filter(function (k) {
      return /real property|business|other taxes/i.test(k);
    });
    var nonTaxKeys = Object.keys(detail).filter(function (k) {
      return !/real property|business|other taxes/i.test(k);
    });
    var taxTotal = taxKeys.reduce(function (s, k) { return s + (detail[k] || 0); }, 0);
    var nonTaxTotal = nonTaxKeys.reduce(function (s, k) { return s + (detail[k] || 0); }, 0);
    initChart(revCtx, {
      type: "doughnut",
      data: {
        labels: ["Tax revenue", "Non-tax revenue", "National Tax Allotment", "Other external"],
        datasets: [{
          data: [millions(taxTotal), millions(nonTaxTotal),
                 millions(data.revenue.nta), millions(data.revenue.other_external)],
          backgroundColor: [green, gold, blue, "#95a5a6"]
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { position: "bottom" } }
      }
    });
  }

  // Spending by function, horizontal bars (latest quarter)
  var expCtx = document.getElementById("chart-fdp-expenditure");
  if (expCtx && data.expenditure && data.expenditure.items) {
    var expLabels = Object.keys(data.expenditure.items);
    initChart(expCtx, {
      type: "bar",
      data: {
        labels: expLabels.map(function (l) {
          return l.length > 28 ? l.slice(0, 27) + "…" : l;
        }),
        datasets: [{
          label: "General Fund spending (PHP Millions)",
          data: expLabels.map(function (l) { return millions(data.expenditure.items[l]); }),
          backgroundColor: green
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

  // Receipts vs expenditures quarterly flows (differenced YTD filings)
  var trendCtx = document.getElementById("chart-fdp-trend");
  if (trendCtx && data.trend) {
    initChart(trendCtx, {
      type: "line",
      data: {
        labels: data.trend.map(function (p) { return p.period; }),
        datasets: [
          {
            label: "Receipts (PHP Millions)",
            data: data.trend.map(function (p) { return millions(p.receipts); }),
            borderColor: green,
            backgroundColor: "rgba(76,138,46,0.1)",
            fill: false,
            tension: 0.3
          },
          {
            label: "Expenditures (PHP Millions)",
            data: data.trend.map(function (p) { return millions(p.expenditures); }),
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

  // Development investment by barangay, horizontal bars (latest quarter).
  // All 15 barangays shown; zero-investment bars render red to flag gaps.
  var brgyCtx = document.getElementById("chart-fdp-barangay");
  if (brgyCtx && data.barangay && data.barangay.dist) {
    var slugs = ["amanoaoac", "apaya", "aserda", "baloling", "coral", "golden",
                 "jimenez", "lambayan", "luyan", "nilombot", "pias", "poblacion",
                 "primicias", "sta-maria", "torres"];
    slugs.sort(function (a, b) {
      var va = (data.barangay.dist[a] || {}).investment || 0;
      var vb = (data.barangay.dist[b] || {}).investment || 0;
      return vb - va;
    });
    initChart(brgyCtx, {
      type: "bar",
      data: {
        labels: slugs.map(function (s) { return s.replace(/-/g, " "); }),
        datasets: [{
          label: "Investment (PHP Millions)",
          data: slugs.map(function (s) { return millions(((data.barangay.dist[s] || {}).investment) || 0); }),
          backgroundColor: slugs.map(function (s) {
            return ((data.barangay.dist[s] || {}).investment || 0) > 0 ? green : red;
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

  // Modal dialogs: open/close wiring for all data tables site-wide.
  // Supports both the FDP attributes ([data-fdp-dialog] + dialog.fdp-dialog)
  // and the generic pair ([data-open-modal] + dialog[data-modal]).
  document.querySelectorAll("[data-fdp-dialog], [data-open-modal]").forEach(function (btn) {
    var id = btn.getAttribute("data-fdp-dialog") || btn.getAttribute("data-open-modal");
    var dialog = document.getElementById(id);
    if (!dialog || typeof dialog.showModal !== "function") {
      return;
    }
    btn.addEventListener("click", function () {
      dialog.showModal();
    });
  });
  document.querySelectorAll("dialog.fdp-dialog [data-close], dialog[data-modal] [data-close]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var dialog = btn.closest("dialog");
      if (dialog) {
        dialog.close();
      }
    });
  });
  document.querySelectorAll("dialog.fdp-dialog, dialog[data-modal]").forEach(function (dialog) {
    dialog.addEventListener("click", function (e) {
      if (e.target === dialog) {
        dialog.close();
      }
    });
  });
  function renderSortableTable(table) {
    var sortCol = table.getAttribute("data-sort-col") || "";
    var sortDir = table.getAttribute("data-sort-dir") || "asc";
    var searchQuery = (table.getAttribute("data-search") || "").toLowerCase();

    var originalRows = table.getAttribute("data-original-rows");
    if (originalRows === null) {
      var tbody = table.querySelector("tbody");
      originalRows = Array.from(tbody.querySelectorAll("tr")).map(function(tr) {
        return tr.outerHTML;
      }).join("|||SPLIT|||");
      table.setAttribute("data-original-rows", originalRows);
    } else {
      var tbody = table.querySelector("tbody");
      tbody.innerHTML = originalRows.split("|||SPLIT|||").join("");
    }

    var rows = Array.from(table.querySelectorAll("tbody tr"));
    var headers = Array.from(table.querySelectorAll("thead th"));
    var data = rows.map(function(row) {
      var cells = Array.from(row.querySelectorAll("td"));
      return { cells: Array.from(cells).map(function(c) { return c.textContent.trim(); }), row: row };
    });

    if (searchQuery) {
      data = data.filter(function(r) {
        return r.cells.some(function(v) {
          return String(v).toLowerCase().indexOf(searchQuery) > -1;
        });
      });
    }

    if (sortCol) {
      var colIndex = headers.findIndex(function(h) { return h.getAttribute("data-column") === sortCol; });
      if (colIndex < 0) colIndex = 0;
      data.sort(function(a, b) {
        var va = colIndex < a.cells.length ? a.cells[colIndex] : "";
        var vb = colIndex < b.cells.length ? b.cells[colIndex] : "";
        var na = parseFloat(String(va).replace(/[^0-9.\-\u20B1,]/g, "")) || 0;
        var nb = parseFloat(String(vb).replace(/[^0-9.\-\u20B1,]/g, "")) || 0;
        var aIsNum = !isNaN(na) && String(va).match(/^[0-9.,\-\u20B1]+$/);
        var bIsNum = !isNaN(nb) && String(vb).match(/^[0-9.,\-\u20B1]+$/);
        if (aIsNum && bIsNum) {
          return sortDir === "asc" ? na - nb : nb - na;
        }
        va = String(va).toLowerCase();
        vb = String(vb).toLowerCase();
        if (va === vb) return 0;
        return sortDir === "asc" ? (va < vb ? -1 : 1) : (va > vb ? -1 : 1);
      });
    }

    var tbody = table.querySelector("tbody");
    tbody.innerHTML = "";
    if (!data.length) {
      var noResults = document.createElement("tr");
      noResults.innerHTML = '<td colspan="99">No results</td>';
      tbody.appendChild(noResults);
    } else {
      data.forEach(function(item) {
        tbody.appendChild(item.row);
      });
    }

    headers.forEach(function(th) {
      var col = th.getAttribute("data-column");
      if (sortCol === col) {
        th.classList.add(sortDir === "asc" ? "sort-asc" : "sort-desc");
      } else {
        th.classList.remove("sort-asc", "sort-desc");
      }
    });
  }

  function findTableFromSearchInput(input) {
    var th = input.closest("th.sortable[data-column]");
    if (th) {
      var table = th.closest("table");
      if (table) return table;
    }
    var dialog = input.closest("dialog");
    if (dialog) {
      var found = dialog.querySelector("th.sortable[data-column]");
      if (found) return found.closest("table");
    }
    var section = input.closest("section");
    if (section) {
      var found = section.querySelector("th.sortable[data-column]");
      if (found) return found.closest("table");
    }
    var card = input.closest(".card");
    if (card) {
      var found = card.querySelector("th.sortable[data-column]");
      if (found) return found.closest("table");
    }
    var wrap = input.closest(".table-wrap");
    if (wrap) {
      var found = wrap.querySelector("th.sortable[data-column]");
      if (found) return found.closest("table");
    }
    var parent = input.parentElement;
    if (parent) {
      var found = parent.querySelector("th.sortable[data-column]");
      if (found) return found.closest("table");
    }
    return null;
  }

  function initGenericTableControls() {
    var skipIds = ["procurement-table", "dpwh-table", "coa-projects-table"];
    var seen = {};
    document.querySelectorAll("th.sortable[data-column]").forEach(function(th) {
      var table = th.closest("table");
      if (!table || skipIds.indexOf(table.id) !== -1) return;
      if (seen[table.id]) return;
      seen[table.id] = true;
      table.setAttribute("data-sort-col", "");
      table.setAttribute("data-sort-dir", "asc");
      table.setAttribute("data-search", "");
      renderSortableTable(table);
    });

    document.addEventListener("click", function(e) {
      var th = e.target.closest("th.sortable[data-column]");
      if (!th) return;
      var table = th.closest("table");
      if (!table) return;
      if (skipIds.indexOf(table.id) !== -1) return;

      var sortCol = table.getAttribute("data-sort-col") || "";
      var sortDir = table.getAttribute("data-sort-dir") || "asc";
      var col = th.getAttribute("data-column");

      if (sortCol === col) {
        sortDir = sortDir === "asc" ? "desc" : "asc";
      } else {
        sortCol = col;
        sortDir = "asc";
      }

      table.setAttribute("data-sort-col", sortCol);
      table.setAttribute("data-sort-dir", sortDir);
      renderSortableTable(table);
    });

    document.addEventListener("input", function(e) {
      if (e.target.tagName !== "INPUT" || e.target.type !== "search") return;
      var table = findTableFromSearchInput(e.target);
      if (!table) return;
      if (skipIds.indexOf(table.id) !== -1) return;
      table.setAttribute("data-search", e.target.value);
      renderSortableTable(table);
    });
  }

  initGenericTableControls();

});
