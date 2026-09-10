function downloadCSV(type) {
  var csv = "";
  if (type === "population") {
    csv = "Year,Population\n2000,30775\n2007,32905\n2010,34439\n2015,37059\n2020,38058";
  } else if (type === "fiscal") {
    csv = "Fiscal Year,Annual Budget (PHP),AIP/SIP Investment Plan Total (PHP),Notes\n"
        + "CY 2022,,29110389.59,Sum of SB Res. 75-2022 SIP1 + 63-2022 SIP5 + 70-2022 SIP6\n"
        + "CY 2023,,162026344.14,Sum of SB Res. 66-2022 Master AIP + 180-2023 Revision + 184-2023 SIP3\n"
        + "CY 2024,,8871268.42,Sum of SB Res. 287-2024 SIP3 + 344-2024 SIP5\n"
        + "CY 2025,193088074,214861029.79,Budget = SP-approved Jan 6 2025 (SB Res. 299-2024); AIP = Master AIP + SIP1-4\n"
        + "CY 2026,218209788,318209799,\"Budget = SP Res. 438-2026 (confirmed); AIP = SB Res. 83-2025 (UNVERIFIED, see note)\"";
  } else if (type === "barangay") {
    csv = "Barangay,Population 2024\nApaya,1650\nAmanoaoac,1656\nBaloling,4238\nCoral,1405\nGolden,1432\nJimenez,2008\nLambayan,1682\nLuyan,3344\nNilombot,4199\nPias,4827\nPoblacion,3509\nAserda,1414\nPrimicias,2218\nSta. Maria,1585\nTorres,3061";
  }
  var blob = new Blob([csv], { type: "text/csv" });
  var a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "mapandan-" + type + ".csv";
  a.click();
}

document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll('[data-download]').forEach(function(btn) {
    btn.addEventListener("click", function() {
      downloadCSV(this.getAttribute("data-download"));
    });
  });
});

window.addEventListener("load", function () {
  if (typeof Chart === "undefined") return;

  var green = "#4c8a2e";
  var gold = "#e8a917";
  var red = "#b5312a";

  // Population trend
  var popCtx = document.getElementById("chart-population");
  if (popCtx) {
    new Chart(popCtx, {
      type: "line",
      data: {
        labels: ["1995", "2000", "2007", "2010", "2015", "2020", "2024"],
        datasets: [{
          label: "Population",
          data: [27439, 30775, 32905, 34439, 37059, 38058, 38228],
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

  var fiscalCtx = document.getElementById("chart-fiscal");
  if (fiscalCtx) {
    new Chart(fiscalCtx, {
      type: "bar",
      data: {
        labels: ["CY 2020", "CY 2022", "CY 2023", "CY 2024", "CY 2025", "CY 2026"],
        datasets: [
          {
            label: "Annual Budget (PHP Millions)",
            data: [122.4, 173.1, 151.5, 160.8, 193.1, 218.2],
            backgroundColor: [green, gold, green, green, green, gold]
          }
        ]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: true },
          tooltip: {
            callbacks: {
              afterLabel: function(ctx) {
                if (ctx.label === "CY 2026*" && ctx.dataset.label.indexOf("AIP") !== -1) {
                  return "Unverified — see data note above";
                }
                return "";
              }
            }
          }
        },
        scales: { y: { beginAtZero: true } }
      }
    });
  }

  // Population by Barangay
  var brgyCtx = document.getElementById("chart-barangay");
  if (brgyCtx) {
    new Chart(brgyCtx, {
      type: "bar",
      data: {
        labels: ["Pias", "Poblacion", "Baloling", "Nilombot", "Torres", "Luyan", "Jimenez", "Primicias", "Amanoaoac", "Lambayan", "Apaya", "Aserda", "Coral", "Golden", "Sta. Maria"],
        datasets: [{
          label: "Population 2024",
          data: [4827, 3509, 4238, 4199, 3061, 3344, 2008, 2218, 1656, 1682, 1650, 1414, 1405, 1432, 1585],
          backgroundColor: green
        }]
      },
      options: {
        responsive: true,
        indexAxis: "y",
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true } }
      }
    });
  }


  // Barangay Population Comparison (2020 vs 2024)
  var brgyCompCtx = document.getElementById("chart-barangay-comparison");
  if (brgyCompCtx && typeof BARANGAY_COMPARISON !== "undefined") {
    new Chart(brgyCompCtx, {
      type: "bar",
      data: {
        labels: BARANGAY_COMPARISON.names,
        datasets: [
          {
            label: "2020",
            data: BARANGAY_COMPARISON.pop2020,
            backgroundColor: green
          },
          {
            label: "2024",
            data: BARANGAY_COMPARISON.pop2024,
            backgroundColor: "#7cb342"
          }
        ]
      },
      options: {
        responsive: true,
        indexAxis: "y",
        plugins: { legend: { display: true } },
        scales: { x: { beginAtZero: true } }
      }
    });
  }

  // --- Make table rows clickable without showing the URL ---
  document.querySelectorAll('.clickable-row').forEach(function(row) {
    row.addEventListener('click', function(e) {
      // If the user clicks an actual link inside the row, let the link handle it normally
      if (e.target.closest('a')) return;

      var url = this.getAttribute('data-href');
      if (url) {
        window.open(url, '_blank', 'noopener,noreferrer');
      }
    });

    // Accessibility: allow keyboard users to trigger the click with Enter or Space
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
