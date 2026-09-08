function downloadCSV(type) {
  var csv = "";
  if (type === "budget") {
    csv = "Fiscal Year,Total Enacted Budget (PHP)\nCY 2020,122402454\nCY 2021,129281542\nCY 2022,173142760\nCY 2023,151540728\nCY 2024,160828663\nCY 2025,193088074\nCY 2026,218209788";
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
