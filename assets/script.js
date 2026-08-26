// Better Mapandan — shared site behavior (no frameworks, no dead ends)

document.addEventListener("DOMContentLoaded", function () {
  var toggle = document.querySelector(".nav-toggle");
  var links = document.querySelector(".nav-links");

  if (toggle && links) {
    toggle.addEventListener("click", function () {
      var isOpen = links.classList.toggle("open");
      toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });

    links.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", function () {
        links.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  // Mark the current page in the nav
  var here = location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".nav-links a").forEach(function (a) {
    var target = a.getAttribute("href");
    if (target === here || (here === "" && target === "index.html")) {
      a.setAttribute("aria-current", "page");
    }
  });

  // Search: highlight matching rows on services.html when ?q= is present
  var params = new URLSearchParams(location.search);
  var query = (params.get("q") || "").trim().toLowerCase();
  if (query && here === "services.html") {
    var rows = document.querySelectorAll("table tbody tr");
    var matched = [];
    rows.forEach(function (row) {
      var text = row.textContent.toLowerCase();
      if (text.indexOf(query) !== -1) {
        row.style.background = "#f6ecc9";
        matched.push(row);
      }
    });
    if (matched.length > 0) {
      matched[0].scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }
});
