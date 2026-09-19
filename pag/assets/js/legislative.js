function initLegislativeTable() {
  var ordinances = window.LEGISLATIVE_ORDINANCES || [];
  var resolutions = window.LEGISLATIVE_RESOLUTIONS || [];
  var executive = window.LEGISLATIVE_EXECUTIVE || [];
  var pageSize = 20;
  var currentPage = 1;
  var sortCol = "date_enacted";
  var sortDir = "desc";
  var searchQuery = "";

  var searchInput = document.getElementById("legislative-search");
  var csvBtn = document.getElementById("legislative-csv-btn");
  var pageInfo = document.getElementById("legislative-page-info");
  var pageIndicator = document.getElementById("legislative-page-indicator");
  var pagination = document.getElementById("legislative-pagination");

  function norm(v) {
    return String(v !== undefined ? v : "").toLowerCase().trim();
  }

  function getFilteredSorted(data) {
    var result = data.slice();
    if (searchQuery) {
      var q = searchQuery.toLowerCase();
      result = result.filter(function(r) {
        return Object.values(r).some(function(v) {
          return String(v).toLowerCase().indexOf(q) > -1;
        });
      });
    }
    result.sort(function(a, b) {
      var va = a[sortCol] !== undefined ? a[sortCol] : "";
      var vb = b[sortCol] !== undefined ? b[sortCol] : "";
      if (sortCol === "fiscal_value") {
        var na = parseFloat(String(va).replace(/[^0-9.-]/g, "")) || 0;
        var nb = parseFloat(String(vb).replace(/[^0-9.-]/g, "")) || 0;
        return sortDir === "asc" ? na - nb : nb - na;
      }
      va = String(va);
      vb = String(vb);
      if (va === vb) return 0;
      return sortDir === "asc" ? (va < vb ? -1 : 1) : (va > vb ? -1 : 1);
    });
    return result;
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

  function renderOrdinances() {
    var filtered = getFilteredSorted(ordinances);
    renderTable("#ordinances-table tbody", filtered, function(o) {
      return "<tr>" +
        "<td>" + (o.number !== undefined ? o.number : "") + "</td>" +
        "<td>" + (o.title !== undefined ? o.title : "") + "</td>" +
        "<td>" + (o.date_enacted !== undefined ? o.date_enacted : "") + "</td>" +
        "<td>" + (o.category !== undefined ? o.category : "") + "</td>" +
        "<td>" + (o.sp_review !== undefined ? o.sp_review : "") + "</td>" +
        "<td><span class=\"pill\">" + (o.status !== undefined ? o.status : "") + "</span></td>" +
        "<td>" + (o.source_url ? '<a href="' + o.source_url + '" target="_blank" rel="noopener">Source &rarr;</a>' : "—") + "</td>" +
        "</tr>";
    });
  }

  function renderResolutions() {
    var filtered = getFilteredSorted(resolutions);
    renderTable("#resolutions-table tbody", filtered, function(r) {
      var fiscal = r.fiscal_value ? "₱" + parseFloat(r.fiscal_value).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) : "—";
      return "<tr>" +
        "<td>" + (r.number !== undefined ? r.number : "") + "</td>" +
        "<td>" + (r.title !== undefined ? r.title : "") + "</td>" +
        "<td>" + (r.date_approved !== undefined ? r.date_approved : "") + "</td>" +
        "<td>" + fiscal + "</td>" +
        "<td>" + (r.source_url ? '<a href="' + r.source_url + '" target="_blank" rel="noopener">Source &rarr;</a>' : "—") + "</td>" +
        "</tr>";
    });
  }

  function renderExecutive() {
    var filtered = getFilteredSorted(executive);
    renderTable("#executive-table tbody", filtered, function(e) {
      return "<tr>" +
        "<td>" + (e.title !== undefined ? e.title : "") + "</td>" +
        "<td>" + (e.date !== undefined ? e.date : "—") + "</td>" +
        "<td>" + (e.authority !== undefined ? e.authority : "") + "</td>" +
        "<td>" + (e.description !== undefined ? e.description : "") + "</td>" +
        "</tr>";
    });
  }

  function renderTable(selector, filtered, rowBuilder) {
    var tbody = document.querySelector(selector);
    if (!tbody) return;
    var totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
    if (currentPage > totalPages) currentPage = totalPages;
    var start = (currentPage - 1) * pageSize;
    var pageData = filtered.slice(start, start + pageSize);

    var rows = [];
    for (var i = 0; i < pageData.length; i++) {
      rows.push(rowBuilder(pageData[i]));
    }
    if (!rows.length) {
      rows.push('<tr><td colspan="' + (tbody.querySelectorAll("th").length || 5) + '">No results</td></tr>');
    }
    tbody.innerHTML = rows.join("");

    if (pageInfo) {
      var showing = "Showing " + (start + 1) + "-" + Math.min(start + pageSize, filtered.length) + " of " + filtered.length;
      pageInfo.textContent = showing;
    }
    if (pageIndicator) {
      pageIndicator.textContent = currentPage + " / " + totalPages;
    }

    var numberedWrap = document.createElement("span");
    numberedWrap.className = "numbered-pages";
    numberedWrap.innerHTML = renderPageNumbers(totalPages, currentPage);
    var existingNumbered = pagination.querySelector(".numbered-pages");
    if (existingNumbered) existingNumbered.remove();
    pagination.insertBefore(numberedWrap, pagination.children[1]);

    document.querySelectorAll("th[data-column]").forEach(function(th) {
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
      renderOrdinances();
      renderResolutions();
      renderExecutive();
    });
  }

  if (csvBtn) {
    csvBtn.addEventListener("click", function() {
      downloadTransparencyCSV("legislative");
    });
  }

  ["ordinances-table", "resolutions-table", "executive-table"].forEach(function(tableId) {
    document.querySelectorAll("#" + tableId + " th[data-column]").forEach(function(th) {
      th.addEventListener("click", function() {
        var col = this.getAttribute("data-column");
        if (sortCol === col) {
          sortDir = sortDir === "asc" ? "desc" : "asc";
        } else {
          sortCol = col;
          sortDir = "asc";
        }
        currentPage = 1;
        if (tableId === "ordinances-table") renderOrdinances();
        else if (tableId === "resolutions-table") renderResolutions();
        else renderExecutive();
      });
    });
  });

  if (pagination) {
    pagination.addEventListener("click", function(e) {
      var btn = e.target.closest("button[data-page]");
      if (!btn) return;
      var page = btn.getAttribute("data-page");
      var totalCount = ordinances.length + resolutions.length + executive.length;
      var totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
      if (page === "prev") {
        if (currentPage > 1) currentPage--;
      } else if (page === "next") {
        if (currentPage < totalPages) currentPage++;
      } else {
        var pn = parseInt(page, 10);
        if (!isNaN(pn)) currentPage = pn;
      }
      renderOrdinances();
      renderResolutions();
      renderExecutive();
    });
  }

  renderOrdinances();
  renderResolutions();
  renderExecutive();
}

document.addEventListener("DOMContentLoaded", function () {
  initLegislativeTable();
});
