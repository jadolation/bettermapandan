window.addEventListener("load", function () {
  if (typeof Chart === "undefined") return;

  var green = "#4c8a2e";
  var gold = "#e8a917";
  var greenDark = "#16532c";
  var greenMid = "#2d6b1f";
  var greenLight = "#6ba34e";
  var greenPale = "#8fbc5f";
  var greenPalest = "#b3d47a";
  var data = window.SERVICES_ANALYTICS || {};

  function sortedEntries(obj) {
    var entries = Object.entries(obj || {});
    entries.sort(function (a, b) { return b[1] - a[1]; });
    return entries;
  }

  function makePalette(n) {
    var palette = [green, gold, greenDark, greenMid, greenLight, greenPale, greenPalest, "#3a7a20", "#c9b458", "#4e9e3d"];
    var colors = [];
    for (var i = 0; i < n; i++) {
      colors.push(palette[i % palette.length]);
    }
    return colors;
  }

  var catCtx = document.getElementById("chart-services-categories");
  if (catCtx && data.categories) {
    var catEntries = sortedEntries(data.categories);
    var catLabels = catEntries.map(function (e) { return e[0]; });
    var catValues = catEntries.map(function (e) { return e[1]; });
    new Chart(catCtx, {
      type: "bar",
      data: {
        labels: catLabels,
        datasets: [{
          label: "Services",
          data: catValues,
          backgroundColor: makePalette(catLabels.length)
        }]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true, ticks: { stepSize: 1 } } }
      }
    });
  }

  var officeCtx = document.getElementById("chart-services-offices");
  if (officeCtx && data.offices) {
    var officeEntries = sortedEntries(data.offices);
    var officeLabels = officeEntries.map(function (e) { return e[0]; });
    var officeValues = officeEntries.map(function (e) { return e[1]; });
    new Chart(officeCtx, {
      type: "bar",
      data: {
        labels: officeLabels,
        datasets: [{
          label: "Services",
          data: officeValues,
          backgroundColor: makePalette(officeLabels.length)
        }]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true, ticks: { stepSize: 1 } } }
      }
    });
  }

  var classCtx = document.getElementById("chart-services-classifications");
  if (classCtx && data.classifications) {
    var classLabels = Object.keys(data.classifications);
    var classValues = classLabels.map(function (k) { return data.classifications[k]; });
    new Chart(classCtx, {
      type: "doughnut",
      data: {
        labels: classLabels,
        datasets: [{
          data: classValues,
          backgroundColor: [green, gold]
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { position: "right" } }
      }
    });
  }

  var modeCtx = document.getElementById("chart-services-delivery-modes");
  if (modeCtx && data.delivery_modes) {
    var modeEntries = sortedEntries(data.delivery_modes);
    var modeLabels = modeEntries.map(function (e) { return e[0]; });
    var modeValues = modeEntries.map(function (e) { return e[1]; });
    new Chart(modeCtx, {
      type: "doughnut",
      data: {
        labels: modeLabels,
        datasets: [{
          data: modeValues,
          backgroundColor: makePalette(modeLabels.length)
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { position: "right" } }
      }
    });
  }

  var feesSummary = document.getElementById("services-fees-summary");
  if (feesSummary && data.fees) {
    var avg = data.fees.average || 0;
    var freeCount = data.fees.free || 0;
    var paidCount = data.fees.paid || 0;
    feesSummary.innerHTML =
      '<div style="font-size:1.5rem;font-weight:700;color:' + green + '">&#x20B1;' + avg.toLocaleString("en-PH", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + '</div>' +
      '<div><strong>Average fee</strong> across ' + paidCount + ' paid service' + (paidCount !== 1 ? 's' : '') + '</div>' +
      '<div><span style="color:' + green + ';font-weight:600">' + freeCount + ' free</span> &middot; <span style="font-weight:600">' + paidCount + ' paid</span></div>';
  }
});
