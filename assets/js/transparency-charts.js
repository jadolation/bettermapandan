function tr(text) { return (window.__I18N__ && window.__I18N__[text]) || text; }

document.addEventListener("DOMContentLoaded", function () {
  console.log('[transparency-charts.js] DOMContentLoaded fired');
  console.log('[transparency-charts.js] Chart available:', typeof Chart !== 'undefined');
  
  if (typeof Chart === "undefined") {
    console.error('[transparency-charts.js] Chart.js is not loaded!');
    return;
  }

  function initChart(canvas, config) {
    if (!canvas) {
      console.warn('[transparency-charts.js] Canvas not found');
      return null;
    }
    if (canvas.chart) {
      canvas.chart.destroy();
    }
    try {
      var chart = new Chart(canvas, config);
      console.log('[transparency-charts.js] Chart created on', canvas.id);
      return chart;
    } catch (e) {
      console.error('[transparency-charts.js] Failed to create chart on', canvas.id, e);
      return null;
    }
  }

  var green = "#4c8a2e";
  var gold = "#e8a917";

  // Budget trend
  var budgetCtx = document.getElementById("chart-budget-trend");
  if (budgetCtx) {
    initChart(budgetCtx, {
      type: "bar",
      data: {
        labels: ["CY 2020", "CY 2021", "CY 2022", "CY 2023", "CY 2024", "CY 2025", "CY 2026"],
        datasets: [{
          label: tr("Total Enacted Budget (PHP Millions)"),
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

  var AUDIT = window.AUDIT_DATA || {};

  // Audit opinion — three-state encoding: 1=Unqualified, 2=Qualified, 3=Non-Compliant.
  var auditOpCtx = document.getElementById("chart-audit-opinion");
  if (auditOpCtx && AUDIT.opinions && AUDIT.opinions.length) {
    var opinions = AUDIT.opinions;
    var opinionValue = { "Unqualified": 1, "Unmodified": 1, "Qualified": 2,
                         "Non-Compliant": 3, "Adverse": 3, "Disclaimer": 3 };
    var opinionColor = { "green": green, "gold": gold, "red": "#d9534f" };
    var opinionLabel = {};
    opinions.forEach(function (o) {
      var name = tr(o.opinion || "Unknown");
      if (o.opinion_type === "compliance_audit") name += " (LDRRMF)";
      opinionLabel[o.year] = name;
    });
    initChart(auditOpCtx, {
      type: "bar",
      data: {
        labels: opinions.map(function (o) { return o.year; }),
        datasets: [{
          label: tr("COA Opinion"),
          data: opinions.map(function (o) { return opinionValue[o.opinion] || 0; }),
          backgroundColor: opinions.map(function (o) { return opinionColor[o.color] || gold; })
        }]
      },
      options: {
        responsive: true,
        layout: { padding: { left: 0, right: 0, top: 0, bottom: 0 } },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) { return opinionLabel[ctx.label] || String(ctx.raw); }
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 3.5,
            ticks: {
              stepSize: 1,
              callback: function (value) {
                if (value === 1) return tr("Unqualified");
                if (value === 2) return tr("Qualified");
                if (value === 3) return tr("Non-Compliant");
                return "";
              }
            }
          }
        }
      }
    });
  }

  var FIN = AUDIT.financial_performance || [];
  var REV = AUDIT.revenue_composition || [];

  var assetsCtx = document.getElementById("chart-total-assets");
  if (assetsCtx && FIN.length) {
    initChart(assetsCtx, {
      type: "line",
      data: {
        labels: FIN.map(function (r) { return r.year; }),
        datasets: [{
          label: tr("Total Assets (PHP Millions)"),
          data: FIN.map(function (r) { return (r.total_assets || 0) / 1000000; }),
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

  var incomeExpCtx = document.getElementById("chart-income-expenses");
  if (incomeExpCtx && FIN.length) {
    initChart(incomeExpCtx, {
      type: "line",
      data: {
        labels: FIN.map(function (r) { return r.year; }),
        datasets: [
          {
            label: tr("Income (PHP Millions)"),
            data: FIN.map(function (r) { return (r.income || 0) / 1000000; }),
            borderColor: green,
            backgroundColor: "rgba(76,138,46,0.1)",
            fill: false,
            tension: 0.3
          },
          {
            label: tr("Expenses (PHP Millions)"),
            data: FIN.map(function (r) { return (r.expenses || 0) / 1000000; }),
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

  var revCompCtx = document.getElementById("chart-revenue-composition");
  if (revCompCtx && REV.length) {
    initChart(revCompCtx, {
      type: "bar",
      data: {
        labels: REV.map(function (r) { return r.year; }),
        datasets: [
          {
            label: tr("IRA/NTA (PHP Millions)"),
            data: REV.map(function (r) { return (r.ira || 0) / 1000000; }),
            backgroundColor: green
          },
          {
            label: tr("Local Income (PHP Millions)"),
            data: REV.map(function (r) { return (r.local_income || 0) / 1000000; }),
            backgroundColor: gold
          },
          {
            label: tr("Other (PHP Millions)"),
            data: REV.map(function (r) { return (r.other || 0) / 1000000; }),
            backgroundColor: "#8fbc5f"
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

  var IMPL = AUDIT.implementation_rates || [];
  var implCtx = document.getElementById("chart-implementation-rate");
  if (implCtx && IMPL.length) {
    initChart(implCtx, {
      type: "bar",
      data: {
        labels: IMPL.map(function (r) { return String(r.period).replace("20", "").replace("20", ""); }),
        datasets: [
          {
            label: tr("Implemented"),
            data: IMPL.map(function (r) { return r.implemented || 0; }),
            backgroundColor: green
          },
          {
            label: tr("Partial"),
            data: IMPL.map(function (r) { return r.partial || 0; }),
            backgroundColor: "#8fbc5f"
          },
          {
            label: tr("Not Implemented"),
            data: IMPL.map(function (r) { return r.not_implemented || 0; }),
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
    trendChart = initChart(trendCtx, {
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
    awardeesChart = initChart(awardeesCtx, {
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
    catChart = initChart(catCtx, {
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
});
