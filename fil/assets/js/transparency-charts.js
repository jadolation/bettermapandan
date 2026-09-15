document.addEventListener("DOMContentLoaded", function () {
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
});
