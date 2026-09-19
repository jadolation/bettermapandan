/* section-nav.js — Dual-mode in-page section navigation.
   Desktop: IntersectionObserver scrollspy + collapsible sidebar.
   Mobile (<=720px): press-and-hold the right edge (~800ms) to reveal a
   named submenu; it stays visible only while held — sliding highlights a
   row and releasing over it smooth-scrolls (CSS scroll-behavior) there. */
(function () {
  "use strict";

  var HOLD_MS = 800;
  var EDGE_PX = 30;
  var MOVE_PX = 24;
  var mq = window.matchMedia ? window.matchMedia("(max-width: 720px)") : null;

  function isMobile() {
    return mq ? mq.matches : window.innerWidth <= 720;
  }

  /* ---------- Sticky offset (mirrors dashboard-tabs.js pattern) ---------- */

  function updateNavTop() {
    var bar = document.querySelector(".emergency-bar");
    var header = document.querySelector(".site-header");
    if (!bar || !header) return;
    var top = bar.offsetHeight + header.offsetHeight + 16;
    document.documentElement.style.setProperty("--section-nav-top", top + "px");
  }

  /* ---------- Desktop scrollspy ---------- */

  function setActive(id) {
    var links = document.querySelectorAll(".section-nav a[data-section]");
    Array.prototype.forEach.call(links, function (a) {
      var on = a.getAttribute("data-section") === id;
      a.classList.toggle("active", on);
      if (on) {
        a.setAttribute("aria-current", "true");
      } else {
        a.removeAttribute("aria-current");
      }
    });
    // Mirror the current section onto the mobile hold-menu rows.
    var dots = document.querySelectorAll(".edge-dot[data-target]");
    Array.prototype.forEach.call(dots, function (d) {
      d.classList.toggle("active", d.getAttribute("data-target") === id);
    });
  }

  function initScrollspy() {
    var sections = document.querySelectorAll(".page-with-nav-body section[id]");
    if (!sections.length) return;
    if (typeof IntersectionObserver === "undefined") {
      initScrollFallback(sections);
      return;
    }
    var current = null;
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) current = e.target.id;
        });
        if (current) setActive(current);
      },
      { rootMargin: "-25% 0px -65% 0px", threshold: 0 }
    );
    Array.prototype.forEach.call(sections, function (s) {
      observer.observe(s);
    });
  }

  function initScrollFallback(sections) {
    var ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () {
        var probe = window.scrollY + window.innerHeight * 0.3;
        var id = null;
        Array.prototype.forEach.call(sections, function (s) {
          if (s.offsetTop <= probe) id = s.id;
        });
        if (id) setActive(id);
        ticking = false;
      });
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  /* ---------- Sidebar collapse + sub-groups ---------- */

  function initCollapse() {
    var wrap = document.querySelector(".page-with-nav");
    var btn = document.querySelector(".section-nav-toggle");
    if (!wrap || !btn) return;
    var list = document.getElementById("section-nav-list");
    function apply(collapsed) {
      wrap.classList.toggle("nav-collapsed", collapsed);
      btn.setAttribute("aria-expanded", String(!collapsed));
      var label = btn.querySelector("span");
      if (label) {
        label.textContent = collapsed ? btn.getAttribute("data-show-label") : btn.getAttribute("data-hide-label");
      }
      if (list) list.hidden = false;
      try {
        localStorage.setItem("bettermapandan_section_nav", collapsed ? "collapsed" : "open");
      } catch (e) { /* private mode */ }
    }
    var stored = null;
    try {
      stored = localStorage.getItem("bettermapandan_section_nav");
    } catch (e) { /* private mode */ }
    if (stored === "collapsed") apply(true);
    btn.addEventListener("click", function () {
      apply(!wrap.classList.contains("nav-collapsed"));
    });
    var subs = document.querySelectorAll(".section-nav-sub-toggle");
    Array.prototype.forEach.call(subs, function (sub) {
      sub.addEventListener("click", function () {
        var expanded = sub.getAttribute("aria-expanded") === "true";
        sub.setAttribute("aria-expanded", String(!expanded));
        var panel = null;
        var split = sub.closest(".section-nav-split");
        if (split) {
          panel = split.parentElement.querySelector(".section-nav-sub-sub");
        } else {
          panel = sub.nextElementSibling;
        }
        if (panel) panel.hidden = expanded;
        if (sub.hasAttribute("data-show-label")) {
          sub.setAttribute(
            "aria-label",
            expanded ? sub.getAttribute("data-show-label") : sub.getAttribute("data-hide-label")
          );
        }
      });
    });
  }

  /* ---------- Mobile edge-hold nav ---------- */

  var edgeNav = null;
  var holdTimer = null;
  var holdId = null;
  var startX = 0;
  var startY = 0;

  function openEdge() {
    if (!edgeNav || !isMobile()) return;
    edgeNav.classList.add("open");
  }

  function closeEdge() {
    if (!edgeNav) return;
    edgeNav.classList.remove("open");
    var tips = edgeNav.querySelectorAll(".tip-on");
    Array.prototype.forEach.call(tips, function (d) {
      d.classList.remove("tip-on");
    });
  }

  function dotFromPoint(x, y) {
    var el = document.elementFromPoint(x, y);
    if (!el) return null;
    if (el.classList && el.classList.contains("edge-dot")) return el;
    if (el.parentElement && el.parentElement.classList.contains("edge-dot")) return el.parentElement;
    return null;
  }

  function showTip(dot) {
    if (!edgeNav) return;
    var dots = edgeNav.querySelectorAll(".edge-dot");
    Array.prototype.forEach.call(dots, function (d) {
      d.classList.toggle("tip-on", d === dot);
    });
  }

  function goTo(dot) {
    var id = dot.getAttribute("data-target");
    if (id) window.location.hash = id;
    closeEdge();
  }

  function initEdge() {
    edgeNav = document.querySelector(".edge-nav");
    if (!edgeNav) return;
    var dots = edgeNav.querySelectorAll(".edge-dot");

    document.addEventListener(
      "touchstart",
      function (ev) {
        if (!isMobile() || edgeNav.classList.contains("open")) return;
        var t = ev.changedTouches[0];
        if (window.innerWidth - t.clientX > EDGE_PX) return;
        if (t.target.closest && t.target.closest(".edge-nav")) return;
        holdId = t.identifier;
        startX = t.clientX;
        startY = t.clientY;
        clearTimeout(holdTimer);
        holdTimer = setTimeout(function () {
          openEdge();
          holdTimer = null;
        }, HOLD_MS);
      },
      { passive: true }
    );

    document.addEventListener(
      "touchmove",
      function (ev) {
        if (holdTimer) {
          var t = ev.changedTouches[0];
          if (t.identifier !== holdId) return;
          if (Math.abs(t.clientX - startX) > MOVE_PX || Math.abs(t.clientY - startY) > MOVE_PX) {
            clearTimeout(holdTimer);
            holdTimer = null;
          }
        } else if (edgeNav.classList.contains("open")) {
          var m = ev.changedTouches[0];
          var dot = dotFromPoint(m.clientX, m.clientY);
          if (dot) showTip(dot);
        }
      },
      { passive: true }
    );

    document.addEventListener("touchend", function (ev) {
      if (holdTimer) {
        clearTimeout(holdTimer);
        holdTimer = null;
        return;
      }
      if (!edgeNav.classList.contains("open")) return;
      // Taps on the edge tab are owned by its toggle handler below.
      if (ev.target.closest && ev.target.closest(".edge-tab")) return;
      var t = ev.changedTouches[0];
      var dot = dotFromPoint(t.clientX, t.clientY);
      if (dot) {
        goTo(dot);
      } else {
        closeEdge();
      }
    });

    document.addEventListener("touchcancel", function () {
      clearTimeout(holdTimer);
      holdTimer = null;
    });

    // Discoverable fallback: tap the edge tab toggles; click works for
    // mouse users and automated tests.
    var tab = edgeNav.querySelector(".edge-tab");
    if (tab) {
      tab.addEventListener("click", function () {
        if (edgeNav.classList.contains("open")) {
          closeEdge();
        } else {
          openEdge();
        }
      });
    }
    Array.prototype.forEach.call(dots, function (dot) {
      dot.addEventListener("click", function () {
        goTo(dot);
      });
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") closeEdge();
    });
  }

  function init() {
    if (document.querySelector("[data-section-nav-bound]")) return;
    document.documentElement.setAttribute("data-section-nav-bound", "true");
    updateNavTop();
    initScrollspy();
    initCollapse();
    initEdge();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
  window.addEventListener("resize", updateNavTop);
  window.addEventListener("orientationchange", updateNavTop);
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(updateNavTop);
  }
})();
