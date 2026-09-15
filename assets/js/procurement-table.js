function initProcurementTable() {
  var contracts = window.PROCUREMENT_CONTRACTS || [];
  var pageSize = 20;
  var currentPage = 1;
  var sortCol = "award_date";
  var sortDir = "desc";
  var searchQuery = "";
  var dedupe = false;

  var tableBody = document.querySelector("#procurement-table tbody");
  var pageInfo = document.getElementById("procurement-page-info");
  var pageIndicator = document.getElementById("procurement-page-indicator");
  var searchInput = document.getElementById("procurement-search");
  var csvBtn = document.getElementById("procurement-csv-btn");
  var dupBtn = document.getElementById("procurement-dup-btn");
  var pagination = document.getElementById("procurement-pagination");

  if (!tableBody) return;

  function uniqueOrgs(data) {
    var s = {};
    data.forEach(function(r) { s[r.organization_name || ""] = 1; });
    return Object.keys(s).length;
  }

  function norm(v) {
    return String(v !== undefined ? v : "").toLowerCase().trim();
  }

  function getFilteredSorted() {
    var data = (window._filteredContracts || contracts).slice();
    if (searchQuery) {
      var q = searchQuery.toLowerCase();
      data = data.filter(function(r) {
        return [r.reference_id,r.contract_no,r.title,r.awardee,r.organization_name,r.business_category,r.status,r.area].some(function(v) {
          return String(v).toLowerCase().indexOf(q) > -1;
        });
      });
    }
    if (dedupe) {
      var seen = {};
      data = data.filter(function(r) {
        var key = norm(r.title) + "|" + norm(r.awardee) + "|" + norm(r.amount);
        if (seen[key]) return false;
        seen[key] = true;
        return true;
      });
    }
    data.sort(function(a, b) {
      var va = a[sortCol] !== undefined ? a[sortCol] : "";
      var vb = b[sortCol] !== undefined ? b[sortCol] : "";
      if (sortCol === "amount") {
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
        html += '<span style="padding:0 6px;font-weight:bold;color:var(--ink)">...</span>';
      } else {
        var active = p === current ? ' style="font-weight:bold;background:var(--green-deep);color:#fff;border-color:var(--green-deep)"' : '';
        html += '<button class="btn btn-outline" data-page="' + p + '" style="padding:10px 14px;font-size:0.95rem;min-width:44px"' + active + '>' + p + '</button>';
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
      var r = pageData[i];
      var amt = r.amount !== undefined ? r.amount : 0;
      if (typeof amt !== "number") amt = parseFloat(String(amt).replace(/[^0-9.-]/g, "")) || 0;
      rows.push(
        "<tr>" +
        "<td>" + (r.reference_id !== undefined ? r.reference_id : "") + "</td>" +
        "<td>" + (r.contract_no !== undefined ? r.contract_no : "") + "</td>" +
        "<td>" + (r.title !== undefined ? r.title : "") + "</td>" +
        "<td>" + (r.awardee !== undefined ? r.awardee : "") + "</td>" +
        "<td>" + (r.organization_name !== undefined ? r.organization_name : "") + "</td>" +
        "<td>&#8369;" + amt.toLocaleString() + "</td>" +
        "<td>" + (r.business_category !== undefined ? r.business_category : "") + "</td>" +
        "<td>" + (r.award_date !== undefined ? r.award_date : "") + "</td>" +
        "<td><span class=\"pill\">" + (r.status !== undefined ? r.status : "") + "</span></td>" +
        "</tr>"
      );
    }
    if (!rows.length) {
      rows.push('<tr><td colspan="9">No results</td></tr>');
    }
    tableBody.innerHTML = rows.join("");

    if (pageInfo) {
      var showing = "Showing " + (start + 1) + "-" + Math.min(start + pageSize, filtered.length) + " of " + filtered.length;
      pageInfo.textContent = showing;
    }
    if (pageIndicator) {
      pageIndicator.textContent = currentPage + " / " + totalPages;
    }

    var numberedWrap = document.createElement("span");
    numberedWrap.className = "numbered-pages";
    numberedWrap.style.cssText = "display:inline-flex;gap:6px;align-items:center;flex-wrap:wrap";
    numberedWrap.innerHTML = renderPageNumbers(totalPages, currentPage);
    var existingNumbered = pagination.querySelector(".numbered-pages");
    if (existingNumbered) existingNumbered.remove();
    pagination.insertBefore(numberedWrap, pagination.children[1]);

    document.querySelectorAll("#procurement-table th[data-column]").forEach(function(th) {
      var col = th.getAttribute("data-column");
      if (sortCol === col) {
        th.classList.add(sortDir === "asc" ? "sort-asc" : "sort-desc");
      } else {
        th.classList.remove("sort-asc", "sort-desc");
      }
    });
  }

  window._refreshTable = function() { currentPage = 1; render(); };

  if (searchInput) {
    searchInput.addEventListener("input", function() {
      searchQuery = this.value;
      currentPage = 1;
      render();
    });
  }

  if (csvBtn) {
    csvBtn.addEventListener("click", function() {
      downloadTransparencyCSV("procurement");
    });
  }

  if (dupBtn) {
    var dupOriginal = dupBtn.textContent;
    dupBtn.addEventListener("click", function() {
      dedupe = !dedupe;
      if (dedupe) {
        dupBtn.classList.add("btn-primary");
        dupBtn.textContent = "Showing deduped";
      } else {
        dupBtn.classList.remove("btn-primary");
        dupBtn.textContent = dupOriginal;
      }
      currentPage = 1;
      render();
    });
  }

  document.querySelectorAll("#procurement-table th[data-column]").forEach(function(th) {
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

  if (pagination) {
    pagination.addEventListener("click", function(e) {
      var btn = e.target.closest("button[data-page]");
      if (!btn) return;
      var page = btn.getAttribute("data-page");
      var filtered = getFilteredSorted();
      var totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
      if (page === "prev") {
        if (currentPage > 1) currentPage--;
      } else if (page === "next") {
        if (currentPage < totalPages) currentPage++;
      } else {
        var pn = parseInt(page, 10);
        if (!isNaN(pn)) currentPage = pn;
      }
      render();
    });
  }

  render();
}

document.addEventListener("DOMContentLoaded", function () {
  initProcurementTable();
});
