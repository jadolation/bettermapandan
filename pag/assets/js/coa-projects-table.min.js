function initCOAProjectsTable() {
  var projects = [];
  var attempts = 0;
  var maxAttempts = 50;
  function tryInit() {
    if (window.AUDIT_DATA && window.AUDIT_DATA.infrastructure_projects) {
      projects = window.AUDIT_DATA.infrastructure_projects;
      buildTable();
    } else if (attempts < maxAttempts) {
      attempts++;
      setTimeout(tryInit, 50);
    }
  }
  function buildTable() {
    var sortCol = "cost";
    var sortDir = "desc";
    var searchQuery = "";

    var tableBody = document.querySelector("#coa-projects-table tbody");
    var searchInput = document.getElementById("coa-projects-search");

    if (!tableBody) return;

    function getFilteredSorted() {
      var data = projects.slice();
      if (searchQuery) {
        var q = searchQuery.toLowerCase();
        data = data.filter(function(r) {
          return [r.name, r.description, r.category, r.status, r.source].some(function(v) {
            return String(v).toLowerCase().indexOf(q) > -1;
          });
        });
      }
      data.sort(function(a, b) {
        var va = a[sortCol] !== undefined ? a[sortCol] : "";
        var vb = b[sortCol] !== undefined ? b[sortCol] : "";
        if (sortCol === "cost") {
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

    function render() {
      var filtered = getFilteredSorted();
      var rows = [];
      for (var i = 0; i < filtered.length; i++) {
        var p = filtered[i];
        var cost = p.cost || 0;
        var costStr = "₱" + parseFloat(cost).toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0});
        var yearStr = p.year_started + (p.year_completed !== p.year_started ? "–" + p.year_completed : "");
        var statusClass = p.status === "completed" ? "pill-completed" : "pill-ongoing";
        rows.push(
          "<tr>" +
          "<td><strong>" + (p.name !== undefined ? p.name : "") + "</strong><br><span class='text-xs text-ink-soft'>" + (p.description !== undefined ? p.description : "") + "</span></td>" +
          "<td>" + costStr + "</td>" +
          "<td>" + yearStr + "</td>" +
          "<td>" + (p.category !== undefined ? p.category : "") + "</td>" +
          "<td><span class='pill " + statusClass + "'>" + (p.status !== undefined ? p.status.charAt(0).toUpperCase() + p.status.slice(1) : "") + "</span></td>" +
          "</tr>"
        );
      }
      if (!rows.length) {
        rows.push('<tr><td colspan="5">No results</td></tr>');
      }
      tableBody.innerHTML = rows.join("");

      document.querySelectorAll("#coa-projects-table th[data-column]").forEach(function(th) {
        var col = th.getAttribute("data-column");
        if (sortCol === col) {
          th.classList.add(sortDir === "asc" ? "sort-asc" : "sort-desc");
        } else {
          th.classList.remove("sort-asc", "sort-desc");
        }
      });
    }

    if (searchInput) {
      searchInput.addEventListener("input", function() {
        searchQuery = this.value;
        render();
      });
    }

    document.querySelectorAll("#coa-projects-table th[data-column]").forEach(function(th) {
      th.addEventListener("click", function() {
        var col = this.getAttribute("data-column");
        if (sortCol === col) {
          sortDir = sortDir === "asc" ? "desc" : "asc";
        } else {
          sortCol = col;
          sortDir = "asc";
        }
        render();
      });
    });

    render();
  }
  tryInit();
}

document.addEventListener("DOMContentLoaded", function () {
  initCOAProjectsTable();
});
