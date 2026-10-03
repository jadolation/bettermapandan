/* project-explorer.js — Transparency Project Explorer.
   Index-first search over project/contractor/audit/fund indexes;
   full entity detail lazy-loaded only on card expand.
   Labels distinguish SOURCE REPORTED facts from MATCHED and CALCULATED ones. */
(function () {
  "use strict";

  function base() {
    if (window.__CONFIG__ && window.__CONFIG__.assetBase) return window.__CONFIG__.assetBase;
    return location.pathname.indexOf("/fil/") !== -1 || location.pathname.indexOf("/pag/") !== -1 ? "../.." : ".";
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function peso(n) {
    if (n == null || n === "") return "—";
    return "₱" + Number(n).toLocaleString("en-PH", { maximumFractionDigits: 0 });
  }

  function levelLabel(level) {
    if (level === "explicit") return "Confirmed";
    if (level === "strong") return "Strong match";
    if (level === "probable" || level === "possible") return "Possible match";
    return "No linked record";
  }

  var store = { projects: [], contractors: [], audits: [], funds: [], edges: [] };
  var detailCache = {};
  var entityCache = null;
  var view = "projects";
  var NOUNS = { projects: "projects", contractors: "contractors", audits: "audit findings", funds: "funds" };

  function coverage(p) {
    var n = 0;
    ["dilg", "philgeps", "dpwh", "coa"].forEach(function (k) { if (p.sources[k]) n++; });
    return n;
  }

  function trail(p) {
    var strength = p.link_strength || {};
    function chip(key, name, present, level) {
      var cls, text;
      if (!present) { cls = "trail-off"; text = name + ": no linked record"; }
      else if (level) { cls = "trail-linked"; text = name + ": " + levelLabel(level); }
      else { cls = "trail-on"; text = name + ": reported"; }
      return '<span class="' + cls + '" title="' + esc(text) + '">' + esc(name) + "</span>";
    }
    return '<div class="source-trail" aria-label="Source coverage">' +
      chip("dilg", "DILG", p.sources.dilg) +
      chip("philgeps", "PhilGEPS", p.sources.philgeps, strength.philgeps) +
      chip("dpwh", "DPWH", p.sources.dpwh) +
      chip("coa", "COA", p.sources.coa) +
      "</div>";
  }

  function projectCard(p) {
    var cov = coverage(p);
    return '<div class="card explorer-card" data-id="' + esc(p.id) + '">' +
      '<div class="explorer-card-head">' +
      '<div class="explorer-card-title">' +
      '<h3>' + esc(p.name) + '</h3>' +
      '<p class="source-label">' + esc(p.year || "") +
      (p.barangay && p.barangay.length ? " · " + esc(p.barangay.join(", ")) : "") +
      " · " + esc(p.type || "") + "</p>" +
      "</div>" +
      '<button type="button" class="btn btn-outline" data-expand="' + esc(p.id) + '" aria-expanded="false">Evidence</button>' +
      "</div>" +
      trail(p) +
      '<div class="explorer-detail" hidden></div></div>';
  }

  function edgeEvidence(pid) {
    return store.edges.filter(function (e) {
      return e.to === "contract:" + pid || e.from === "project:" + pid;
    });
  }

  function renderDetail(box, id) {
    if (detailCache[id]) {
      box.innerHTML = detailCache[id];
      box.hidden = false;
      return;
    }
    function entities() {
      if (entityCache) return Promise.resolve(entityCache);
      return Promise.all([
        fetch(base() + "/assets/data/entity-projects.json").then(function (r) {
          if (!r.ok) throw new Error("detail unavailable");
          return r.json();
        }),
        fetch(base() + "/assets/data/entity-contracts.json").then(function (r) {
          return r.ok ? r.json() : [];
        }).catch(function () { return []; })
      ]).then(function (all) {
        entityCache = { projects: all[0], contracts: all[1] };
        return entityCache;
      });
    }
    entities().then(function (cache) {
      var p = null, i;
      for (i = 0; i < cache.projects.length; i++) {
        if (cache.projects[i].project_id === id) { p = cache.projects[i]; break; }
      }
      if (!p) throw new Error("not found");
      var byId = {};
      cache.contracts.forEach(function (c) { byId[c.contract_id] = c; });
      var html = "<h4>What the sources say</h4><dl>";
      (p.provenance || []).forEach(function (pr) {
        html += "<dt>" + esc(pr.source) + "</dt><dd>" + esc(pr.record_id || "") +
          (pr.document ? " · " + esc(typeof pr.document === "string" ? pr.document : "multiple files") : "") +
          (pr.verification_method ? " · manually verified" : "") + "</dd>";
      });
      html += "</dl>";
      var edges = edgeEvidence(id).filter(function (e) { return e.type === "has_contract"; });
      if (edges.length) {
        html += "<h4>How we linked these</h4>";
        edges.forEach(function (e) {
          var cid = String(e.to).split(":")[1];
          var c = byId[cid] || {};
          html += '<p><strong>' + esc(levelLabel(e.confidence)) + '</strong> — contract ' + esc(cid);
          if (c.awardee_name) html += ' · ' + esc(c.awardee_name);
          if (c.award_amount) html += ' · ' + peso(c.award_amount);
          html += "</p><ul>" + e.evidence.map(function (v) {
            var t = String(v);
            if (t.indexOf("rule_") === 0) t = "Matched by " + t;
            return "<li>" + esc(t) + "</li>";
          }).join("") + "</ul>";
        });
      } else {
        html += "<h4>How we linked these</h4>" +
          "<p class=\"source-label\">No linked record — this project appears in a single source.</p>";
      }
      var money = [];
      (p.reported_costs || []).forEach(function (v) { money.push("DILG disclosed " + peso(v)); });
      edges.forEach(function (e) {
        var c = byId[String(e.to).split(":")[1]];
        if (c && c.award_amount) money.push("PhilGEPS contract " + peso(c.award_amount));
      });
      if (p.contract_amount) money.push("DPWH contract " + peso(p.contract_amount));
      if (money.length) {
        html += "<h4>Financial records</h4><ul>" + money.map(function (v) {
          return "<li>" + esc(v) + " (SOURCE REPORTED)</li>";
        }).join("") + "</ul>";
      }
      html += "<h4>Audit</h4>" +
        '<p class="source-label">No directly linked COA finding. Findings link only where a report explicitly names the project.</p>';
      detailCache[id] = html;
      box.innerHTML = html;
      box.hidden = false;
    }).catch(function () {
      box.innerHTML = '<p class="source-label">Detail unavailable offline.</p>';
      box.hidden = false;
    });
  }

  function current() {
    var q = (document.getElementById("explorer-search").value || "").toLowerCase();
    var brgy = document.getElementById("explorer-barangay").value;
    var year = document.getElementById("explorer-year").value;
    var type = document.getElementById("explorer-type").value;
    var cov = document.getElementById("explorer-coverage").value;
    var out = store.projects.filter(function (p) {
      if (q && (p.name + " " + p.id).toLowerCase().indexOf(q) === -1) return false;
      if (brgy && (p.barangay || []).indexOf(brgy) === -1) return false;
      if (year && String(p.year) !== year) return false;
      if (type && p.type !== type) return false;
      if (cov && coverage(p) < Number(cov)) return false;
      return true;
    }).map(projectCard);
    var box = document.getElementById("explorer-results");
    box.innerHTML = out.length ? out.join("") :
      '<p class="source-label">No matches. Try a different search or filter.</p>';
    document.getElementById("explorer-count").textContent =
      out.length + " project" + (out.length === 1 ? "" : "s");
  }

  function fillFilters() {
    var brgys = {}, years = {}, types = {};
    store.projects.forEach(function (p) {
      (p.barangay || []).forEach(function (b) { brgys[b] = 1; });
      if (p.year) years[p.year] = 1;
      if (p.type) types[p.type] = 1;
    });
    function fill(id, vals) {
      var sel = document.getElementById(id);
      Object.keys(vals).sort().forEach(function (v) {
        var o = document.createElement("option");
        o.value = v; o.textContent = v; sel.appendChild(o);
      });
    }
    fill("explorer-barangay", brgys); fill("explorer-year", years); fill("explorer-type", types);
  }

  function init() {
    var root = document.getElementById("explorer-results");
    if (!root || root.hasAttribute("data-explorer-bound")) return;
    root.setAttribute("data-explorer-bound", "true");
    var b = base();
    fetch(b + "/assets/data/project-index.json").then(function (r) { return r.json(); }).then(function (projects) {
      store.projects = projects;
      return fetch(b + "/assets/data/entity-relationships.json").then(function (r) {
        return r.ok ? r.json() : [];
      }).catch(function () { return []; });
    }).then(function (rels) {
      store.edges = rels;
      fillFilters();
      current();
    }).catch(function () {
      root.innerHTML = '<p class="source-label">Index unavailable offline.</p>';
    });
    document.getElementById("explorer-search").addEventListener("input", current);
    ["explorer-barangay", "explorer-year", "explorer-type", "explorer-coverage"].forEach(function (id) {
      document.getElementById(id).addEventListener("change", current);
    });
    root.addEventListener("click", function (ev) {
      var btn = ev.target.closest ? ev.target.closest("[data-expand]") : null;
      if (!btn) return;
      var card = btn.closest ? btn.closest(".explorer-card") : btn.parentElement;
      var box = card.querySelector(".explorer-detail");
      var open = btn.getAttribute("aria-expanded") === "true";
      btn.setAttribute("aria-expanded", String(!open));
      if (open) { box.hidden = true; return; }
      renderDetail(box, btn.getAttribute("data-expand"));
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else { init(); }
})();
