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

  // Modal dialogs: open/close wiring for full FDP tables
  document.querySelectorAll("[data-fdp-dialog]").forEach(function (btn) {
    var dialog = document.getElementById(btn.getAttribute("data-fdp-dialog"));
    if (!dialog || typeof dialog.showModal !== "function") {
      return;
    }
    btn.addEventListener("click", function () {
      dialog.showModal();
    });
  });
  document.querySelectorAll("dialog.fdp-dialog [data-close]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var dialog = btn.closest("dialog");
      if (dialog) {
        dialog.close();
      }
    });
  });
  document.querySelectorAll("dialog.fdp-dialog").forEach(function (dialog) {
    dialog.addEventListener("click", function (e) {
      if (e.target === dialog) {
        dialog.close();
      }
    });
  });
});
