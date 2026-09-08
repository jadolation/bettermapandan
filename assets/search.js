document.addEventListener("DOMContentLoaded", function () {
  var input = document.getElementById("search-input");
  var resultsDiv = document.getElementById("search-results");
  var statusDiv = document.getElementById("search-status");
  var statusText = document.getElementById("search-status-text");
  var emptyDiv = document.getElementById("search-empty");
  var browseDiv = document.getElementById("search-browse");
  var params = new URLSearchParams(location.search);
  var query = (params.get("q") || "").trim();

  if (input && query) {
    input.value = query;
  }

  if (!query) {
    statusDiv.style.display = "none";
    browseDiv.style.display = "block";
    return;
  }

  browseDiv.style.display = "none";

  // Load search index and perform search
  // Use correct path for Filipino pages (assets are copied to /fil/assets/)
  var isFil = location.pathname.indexOf("/fil/") !== -1;
  var searchIndexPath = isFil ? "../assets/search-index.json" : "assets/search-index.json";
  fetch(searchIndexPath)
    .then(function (res) { return res.json(); })
    .then(function (index) {
      var q = query.toLowerCase();
      var matches = [];

      index.forEach(function (entry) {
        var titleLower = entry.title.toLowerCase();
        var bodyLower = entry.body.toLowerCase();
        var descLower = entry.description.toLowerCase();
        var score = 0;

        if (titleLower.indexOf(q) !== -1) score += 10;
        if (descLower.indexOf(q) !== -1) score += 5;
        if (bodyLower.indexOf(q) !== -1) score += 2;

        if (score > 0) {
          // Extract snippet around match
          var bodyText = entry.body;
          var idx = bodyLower.indexOf(q);
          var start = Math.max(0, idx - 80);
          var end = Math.min(bodyText.length, idx + q.length + 80);
          var snippet = (start > 0 ? "..." : "") + bodyText.slice(start, end) + (end < bodyText.length ? "..." : "");

          // Determine section anchor for deep-linking
          var resultUrl = entry.url;
          var sectionAnchors = entry.section_anchors;
          if (sectionAnchors && sectionAnchors.length > 0) {
            // Find the section whose start position is closest before the match
            var bestAnchor = sectionAnchors[0].anchor;
            for (var i = 0; i < sectionAnchors.length; i++) {
              if (sectionAnchors[i].pos <= idx) {
                bestAnchor = sectionAnchors[i].anchor;
              }
            }
            resultUrl = entry.url + "#" + bestAnchor;
          }

          matches.push({
            title: entry.title,
            url: resultUrl,
            description: entry.description,
            snippet: snippet,
            score: score
          });
        }
      });

      matches.sort(function (a, b) { return b.score - a.score; });

      if (matches.length === 0) {
        emptyDiv.style.display = "block";
        statusDiv.style.display = "none";
        return;
      }

      // Group by category (first path segment)
      var groups = {};
      matches.forEach(function (m) {
        var parts = m.url.split("/");
        var cat = parts.length > 1 ? parts[0].replace(".html", "") : "Pages";
        cat = cat.charAt(0).toUpperCase() + cat.slice(1);
        if (!groups[cat]) groups[cat] = [];
        groups[cat].push(m);
      });

      var html = "";
      Object.keys(groups).forEach(function (cat) {
        html += '<div class="search-result-group">';
        html += '<h3>' + cat + '</h3>';
        groups[cat].forEach(function (m) {
          html += '<div class="search-result">';
          html += '<h4><a href="' + m.url + '">' + m.title + '</a></h4>';
          html += '<p>' + m.snippet + '</p>';
          html += '</div>';
        });
        html += '</div>';
      });

      resultsDiv.innerHTML = html;
      statusDiv.style.display = "flex";
      statusText.textContent = matches.length + ' result' + (matches.length !== 1 ? 's' : '') + ' for "' + query + '"';
    })
    .catch(function () {
      emptyDiv.style.display = "block";
      emptyDiv.querySelector("h3").textContent = "Search unavailable";
      emptyDiv.querySelector("p").textContent = "The search index could not be loaded. Please try again later.";
    });
});
