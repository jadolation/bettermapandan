document.addEventListener("DOMContentLoaded", function () {
  var input = document.getElementById("service-filter-input");
  var grid = document.getElementById("service-category-grid");
  var noResults = document.getElementById("service-no-results");
  if (!input || !grid) return;

  var cards = grid.querySelectorAll(".service-category-card");
  var params = new URLSearchParams(location.search);
  var initialQuery = (params.get("q") || "").trim();

  if (initialQuery && input) {
    input.value = initialQuery;
  }

  function filterServices() {
    var q = input.value.toLowerCase().trim();
    var anyVisible = false;

    cards.forEach(function (card) {
      var h3 = card.querySelector("h3");
      var desc = card.querySelector("p");
      var links = card.querySelectorAll(".service-link");
      var catName = h3 ? h3.textContent.toLowerCase() : "";
      var catDesc = desc ? desc.textContent.toLowerCase() : "";
      var catMatch = !q || catName.indexOf(q) !== -1 || catDesc.indexOf(q) !== -1;
      var visibleLinks = 0;

      links.forEach(function (link) {
        var linkText = link.textContent.toLowerCase();
        var linkMatch = !q || linkText.indexOf(q) !== -1 || catMatch;
        link.style.display = linkMatch ? "" : "none";
        if (linkMatch) visibleLinks++;
      });

      var cardVisible = catMatch || visibleLinks > 0;
      card.style.display = cardVisible ? "" : "none";
      if (cardVisible) anyVisible = true;
    });

    noResults.style.display = anyVisible ? "none" : "block";
  }

  input.addEventListener("input", filterServices);

  if (initialQuery) {
    filterServices();
  }
});
