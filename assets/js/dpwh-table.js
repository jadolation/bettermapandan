function initDPWHTable() {
  var projects = window.DPWH_PROJECTS || [];
  var pageSize = 20;
  var currentPage = 1;
  var sortCol = "date";
  var sortDir = "desc";
  var searchQuery = "";

  var tableBody = document.querySelector("#dpwh-table tbody");
  var searchInput = document.getElementById("dpwh-search");

  if (!tableBody) return;

  function norm(v) {
    return String(v !== undefined ? v : "").toLowerCase().trim();
  }

  function getFilteredSorted() {
    var data = projects.slice();
    if (searchQuery) {
      var q = searchQuery.toLowerCase();
      data = data.filter(function(r) {
        return [r.category, r.project_name, r.executing_agency, r.contractor, r.status, r.actual_completion_date, r.contract_effectivity_date].some(function(v) {
          return String(v).toLowerCase().indexOf(q) > -1;
        });
      });
    }
    data.sort(function(a, b) {
      var va = a[sortCol] !== undefined ? a[sortCol] : "";
      var vb = b[sortCol] !== undefined ? b[sortCol] : "";
      if (sortCol === "amount" || sortCol === "accomplishment") {
        var na = parseFloat(String(va).replace(/[^0-9.-]/g, "")) || 0;
        var nb = parseFloat(String(vb).replace(/[^0-9.-]/g, "")) || 0;
        return sortDir === "asc" ? na - nb : nb - na;
      }
      va = String(va);
      vb = String(vb);
      if (va === vb) return 0;
      return sortDir === "asc" ? (va < vb ? -1 : 1) : (va > vb ? -1 : 1);
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
        html += '<span class="page-ellipsis">...</span>';
      } else {
        var active = p === current ? ' btn-active' : '';
        html += '<button class="btn btn-outline' + active + '" data-page="' + p + '">' + p + '</button>';
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
      var p = pageData[i];
      var amount = p.contract_amount || 0;
      var amount_str = "₱" + parseFloat(amount).toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0}) if amount else "—";
      var acc = p.accomplishment_percent || 0;
      var acc_str = parseFloat(acc).toFixed(0) + "%" if acc else "—";
      var date = p.actual_completion_date || p.contract_effectivity_date || "—";
      var lat = p.latitude, lng = p.longitude;
      var map_link = "";
      if (lat !== undefined && lng !== undefined) {
        map_link = '<a href="https://www.openstreetmap.org/?mlat=' + lat + '&mlon=' + lng + '#map=16/' + lat + '/' + lng + '" target="_blank" rel="noopener">View map &rarr;</a>';
      }
      rows.push(
        "<tr>" +
        "<td>" + (p.category !== undefined ? p.category : "") + "</td>" +
        "<td>" + (p.project_name !== undefined ? p.project_name : "") + "</td>" +
        "<td>" + (p.executing_agency !== undefined ? p.executing_agency : "") + "</td>" +
        "<td>" + (p.contractor !== undefined ? p.contractor : "—") + "</td>" +
        "<td class=\"num\">" + amount_str + "</td>" +
        "<td><span class=\"pill\">" + (p.status !== undefined ? p.status : "") + "</span></td>" +
        "<td class=\"num\">" + acc_str + "</td>" +
        "<td>" + date + "</td>" +
        "<td>" + map_link + "</td>" +
        "</tr>"
      );
    }
    if (!rows.length) {
      rows.push('<tr><td colspan="9">No results</td></tr>');
    }
    tableBody.innerHTML = rows.join("");

    document.querySelectorAll("#dpwh-table th[data-column]").forEach(function(th) {
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
      currentPage = 1;
      render();
    });
  }

  document.querySelectorAll("#dpwh-table th[data-column]").forEach(function(th) {
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

  render();
}

document.addEventListener("DOMContentLoaded", function () {
  initDPWHTable();
});
