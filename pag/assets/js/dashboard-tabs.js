/* dashboard-tabs.js — Transparency section nav (pills + mobile select) */
(function () {
  "use strict";

  // Normalize: strip /fil prefix + trailing slash for comparison.
  function normPath(path) {
    return path.replace(/^\/fil(?=\/|$)/, "") || "/";
  }

  function syncFromPath() {
    var path = normPath(location.pathname);
    // Pills: safety net (server already renders active + aria-current).
    document.querySelectorAll(".transparency-tabs .tab-btn").forEach(function (btn) {
      var href = btn.getAttribute("href");
      if (!href) return;
      var isActive = normPath(href) === path || normPath(href + "/") === path;
      btn.classList.toggle("active", isActive);
      if (isActive) {
        btn.setAttribute("aria-current", "page");
      } else {
        btn.removeAttribute("aria-current");
      }
    });
    // Select: reflect current section (server pre-selects; fix up on FIL/edge paths).
    var select = document.getElementById("transparency-section-select");
    if (select) {
      var matched = false;
      Array.prototype.forEach.call(select.options, function (opt) {
        var isCurrent = normPath(opt.value) === path || normPath(opt.value + "/") === path;
        if (isCurrent && !matched) {
          opt.selected = true;
          matched = true;
        }
      });
    }
  }

  function bindSelect() {
    var select = document.getElementById("transparency-section-select");
    if (!select || select.hasAttribute("data-tabs-bound")) return;
    select.setAttribute("data-tabs-bound", "true");
    select.addEventListener("change", function () {
      if (select.value) window.location.href = select.value;
    });
  }

  // Dock the mobile dropdown bar directly below the sticky header.
  // Uses the header's live viewport geometry each frame instead of a
  // sampled height sum, so ticker reflow, font swaps, and menu open/close
  // can never leave a stale gap. Falls back to measured heights when the
  // header isn't rendered (or getBoundingClientRect is unavailable).
  var scrollQueued = false;

  function updateTabsTop() {
    var bar = document.querySelector(".emergency-bar");
    var header = document.querySelector(".site-header");
    if (!bar || !header) return;
    var top = bar.offsetHeight + header.offsetHeight;
    if (header.getBoundingClientRect) {
      var bottom = header.getBoundingClientRect().bottom;
      if (bottom > 0) top = bottom;
    }
    document.documentElement.style.setProperty("--transparency-tabs-top", top + "px");
  }

  function queueTabsTop() {
    if (scrollQueued) return;
    scrollQueued = true;
    window.requestAnimationFrame(function () {
      scrollQueued = false;
      updateTabsTop();
    });
  }

  function init() {
    syncFromPath();
    bindSelect();
    updateTabsTop();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
  window.addEventListener("resize", updateTabsTop);
  window.addEventListener("orientationchange", updateTabsTop);
  window.addEventListener("scroll", queueTabsTop, { passive: true });
  window.addEventListener("load", updateTabsTop);
  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", updateTabsTop);
  }
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(updateTabsTop);
  }
})();
