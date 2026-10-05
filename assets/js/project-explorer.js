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
    if (level === "explicit") return "Confirmed match";
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
    function chip(key, name, present, level) {
      var cls, state;
      if (!present) { cls = "trail-off"; state = "No match"; }
      else if (level) { cls = "trail-linked"; state = levelLabel(level); }
      else { cls = "trail-on"; state = "Reported"; }
      var text = name + ": " + state.toLowerCase();
      return '<span class="' + cls + '" title="' + esc(text) + '">' + esc(name) +
        ' · ' + esc(state) + "</span>";
    }
    return '<div class="source-trail" aria-label="Source coverage">' +
      chip("dilg", "DILG", p.sources.dilg) +
      chip("philgeps", "PhilGEPS", p.sources.philgeps, bestLevel(p)) +
      chip("dpwh", "DPWH", p.sources.dpwh) +
      chip("coa", "COA", p.sources.coa) +
      "</div>";
  }

  function projectCard(p) {
    var cov = coverage(p);
    var links = linkCountsText(p);
    return '<div class="card explorer-card" data-id="' + esc(p.id) + '">' +
      '<div class="explorer-card-head">' +
      '<div class="explorer-card-title">' +
      '<h3>' + esc(p.name) + '</h3>' +
      '<p class="source-label">' + esc(p.year || "") +
      (p.barangay && p.barangay.length ? " · " + esc(p.barangay.join(", ")) : "") +
      " · " + esc(typeLabel(p.type)) + "</p>" +
      '<p class="source-label">Records found in ' + cov + " of 4 sources" +
      (links ? " · " + esc(links) : "") + "</p>" +
      "</div>" +
      '<button type="button" class="btn btn-outline" data-expand="' + esc(p.id) + '" aria-expanded="false">Evidence</button>' +
      "</div>" +
      trail(p) +
      '<div class="explorer-detail" hidden></div></div>';
  }

  function humanEvidence(evidence) {
    var map = {
      "same reference id": "The DILG and PhilGEPS records use the same reference ID.",
      "same project title": "The records describe the same project title.",
      "similar project title": "The project titles are closely similar.",
      "same barangay": "The records name the same barangay.",
      "same fiscal year": "The records fall in the same fiscal year.",
      "same contractor": "The records name the same contractor.",
      "matching amount": "The reported amounts agree within tolerance."
    };
    return evidence.filter(function (v) {
      return String(v).indexOf("rule_") !== 0;
    }).map(function (v) {
      return map[String(v)] || String(v);
    });
  }

  function techRule(evidence) {
    for (var i = 0; i < evidence.length; i++) {
      if (String(evidence[i]).indexOf("rule_") === 0) return String(evidence[i]);
    }
    return "";
  }
  function edgeEvidence(pid) {
    return store.edges.filter(function (e) {
      return e.to === "contract:" + pid || e.from === "project:" + pid;
    });
  }

  function chainContracts(pid) {
    // Project -> Contract via direct has_contract, or via
    // has_bid -> resulted_in chain. Returns [{edge, bid, via}].
    var out = [], seen = {};
    store.edges.forEach(function (e) {
      if (e.type === "has_contract" && e.from === "project:" + pid) {
        var cid = String(e.to).split(":")[1];
        if (!seen[cid]) { seen[cid] = 1; out.push({ edge: e, bid: null, cid: cid }); }
      }
    });
    store.edges.forEach(function (e) {
      if (e.type !== "has_bid" || e.from !== "project:" + pid) return;
      var bidId = String(e.to).split(":")[1];
      store.edges.forEach(function (r) {
        if (r.type === "resulted_in" && String(r.from).split(":")[1] === bidId) {
          var cid = String(r.to).split(":")[1];
          if (!seen[cid]) {
            seen[cid] = 1;
            out.push({ edge: r, bid: { id: bidId, link: e }, cid: cid });
          }
        }
      });
    });
    return out;
  }

  function renderDetail(box, id) {
    if (detailCache[id]) {
      box.innerHTML = detailCache[id];
      box.hidden = false;
      return;
    }
    function entities() {
      if (entityCache) return Promise.resolve(entityCache);
      function get(url, fallback) {
        return fetch(base() + url).then(function (r) {
          if (!r.ok) throw new Error("detail unavailable");
          return r.json();
        }).catch(function () { return fallback; });
      }
      return Promise.all([
        get("/assets/data/entity-projects.json", null),
        get("/assets/data/entity-contracts.json", []),
        get("/assets/data/contractor-index.json", []),
        get("/assets/data/entity-bids.json", [])
      ]).then(function (all) {
        if (!all[0]) throw new Error("not found");
        entityCache = { projects: all[0], contracts: all[1], contractors: all[2], bids: all[3] };
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
      var bidsById = {};
      (cache.bids || []).forEach(function (b) { bidsById[b.bid_id] = b; });
      var contractorsById = {};
      (cache.contractors || []).forEach(function (c) { contractorsById[c.id] = c; });
      var links = chainContracts(id);
      var edges = links.map(function (l) { return l.edge; });
      var html = "";
      if (p.project_type === "dpwh_infrastructure") {
        html += '<p class="source-label">DPWH record — manually verified from the official DPWH Transparency Portal.</p>';
      }
      html += "<h4>What the sources say</h4><dl>";
      var dilgRows = [];
      (p.provenance || []).forEach(function (pr) {
        var role = pr.record_role ? " · " + esc(String(pr.record_role).replace(/_/g, " ")) : "";
        var asof = pr.source_as_of ? " · as of " + esc(pr.source_as_of) : "";
        var row = "<dt>" + esc(pr.source) + "</dt><dd>" + esc(pr.record_id || "") +
          (pr.document ? " · " + esc(typeof pr.document === "string" ? pr.document : "multiple files") : "") +
          (pr.verification_method ? " · manually verified" : "") + role + asof + "</dd>";
        if (pr.source === "DILG-FDP" && (p.provenance || []).filter(function (q) {
          return q.source === "DILG-FDP";
        }).length > 1) {
          dilgRows.push(row);
        } else {
          html += row;
        }
      });
      if (dilgRows.length) {
        var periods = (p.provenance || []).filter(function (q) {
          return q.source === "DILG-FDP" && q.source_as_of;
        }).map(function (q) { return String(q.source_as_of); });
        var span = periods.length ? " (" + esc(periods[0]) +
          (periods.length > 1 ? "–" + esc(periods[periods.length - 1]) : "") + ")" : "";
        html += "<dt>DILG-FDP</dt><dd>Reported in " + dilgRows.length + " quarterly filings" +
          span + '<details class="tech-details"><summary>Reporting periods</summary><dl>' +
          dilgRows.join("") + "</dl></details></dd>";
      }
      links.forEach(function (l) {
        var c = byId[l.cid] || {};
        if (!c.contract_id) return;
        if (l.bid) {
          var b = bidsById[l.bid.id] || {};
          html += "<dt>DILG-FDP</dt><dd>Bid " + esc(l.bid.id) +
            (b.project ? " · " + esc(String(b.project).slice(0, 60)) : "") +
            (b.bidder ? " · " + esc(b.bidder) : "") + "</dd>";
        }
        html += "<dt>PhilGEPS</dt><dd>Contract " + esc(c.contract_id) +
          (c.awardee_name ? " · " + esc(c.awardee_name) : "") +
          (c.award_date ? " · awarded " + esc(c.award_date) : "") + "</dd>";
      });
      html += "</dl>";
      if (links.length) {
        html += "<h4>How we linked these</h4>";
        links.forEach(function (l) {
          var e = l.edge;
          var cid = l.cid;
          var c = byId[cid] || {};
          html += "<p><strong>" + esc(levelLabel(e.confidence)) + "</strong> — contract " + esc(cid);
          if (c.awardee_name) html += " · " + esc(c.awardee_name);
          if (c.award_amount) html += " · " + peso(c.award_amount);
          html += "</p>";
          if (l.bid) {
            html += '<p class="source-label">Via DILG bid ' + esc(l.bid.id) + ".</p>";
          }
          var ctr = contractorsById[c.awardee_id] || null;
          if (ctr) {
            html += '<p class="source-label">Contractor: ' + esc(ctr.name) + " · " +
              ctr.contracts + " PhilGEPS contract records indexed · total values represented " +
              peso(ctr.total) + "</p>";
          }
          html += "<ul>" +
            humanEvidence(e.evidence).map(function (t) {
              return "<li>" + esc(t) + "</li>";
            }).join("") + "</ul>";
          var rule = techRule(e.evidence);
          html += '<details class="tech-details"><summary>Technical details</summary>' +
            "<p>Relationship " + esc(e.id) + " · confidence " + esc(e.confidence) +
            (rule ? " · " + esc(rule) : "") +
            (e.match_path ? " · via " + esc(String(e.match_path).replace(/-/g, " ")) : "") + "</p></details>";
        });
      } else {
        html += "<h4>How we linked these</h4>" +
          "<p class=\"source-label\">No linked record — this project appears in a single source.</p>";
      }
      var money = [];
      var costs = p.reported_costs || [];
      if (costs.length > 1 && costs.every(function (v) { return v === costs[0]; })) {
        money.push({ text: "Allocation: " + peso(costs[0]) + " (reported in " + costs.length +
          " quarterly filings — same appropriation, do not sum)", reported: true });
      } else {
        costs.forEach(function (v) { money.push({ text: "Allocation (DILG disclosed): " + peso(v), reported: true }); });
      }
      edges.forEach(function (e) {
        var c = byId[String(e.to).split(":")[1]];
        if (c && c.award_amount) money.push({ text: "Award (PhilGEPS contract): " + peso(c.award_amount), reported: true });
      });
      if (p.contract_amount) money.push({ text: "Contract (DPWH): " + peso(p.contract_amount), reported: true });
      if (money.length) {
        html += "<h4>Financial references</h4><ul>" + money.map(function (m) {
          return "<li>" + esc(m.text) + " (SOURCE REPORTED)</li>";
        }).join("") + "</ul>" +
          "<p class=\"source-label\">These are source-reported amounts from different records and are not automatically equivalent.</p>";
      }
      html += "<h4>COA references</h4>" +
        '<p class="source-label">No directly linked COA finding was identified. Better Mapandan links findings to projects only when the COA report explicitly identifies the project.</p>';
      detailCache[id] = html;
      box.innerHTML = html;
      box.hidden = false;
    }).catch(function () {
      box.innerHTML = '<p class="source-label">Detail unavailable offline.</p>';
      box.hidden = false;
    });
  }

  var TYPE_LABELS = {
    lgu_development: "LGU development",
    dpwh_infrastructure: "DPWH infrastructure"
  };

  function typeLabel(t) {
    return TYPE_LABELS[t] || String(t || "").replace(/_/g, " ").replace(/\b\w/g, function (c) {
      return c.toUpperCase();
    });
  }

  var TYPE_LABELS = {
    lgu_development: "LGU development",
    dpwh_infrastructure: "DPWH infrastructure"
  };

  function typeLabel(t) {
    if (TYPE_LABELS[t]) return TYPE_LABELS[t];
    return String(t || "").replace(/_/g, " ").replace(/\b\w/g, function (c) {
      return c.toUpperCase();
    });
  }

  var LEVEL_RANK = { explicit: 3, strong: 2, probable: 1, possible: 0 };

  function relSummary(p) {
    return p.relationship_summary || { confirmed: 0, strong: 0, probable: 0, possible: 0 };
  }

  function bestLevel(p) {
    var s = relSummary(p);
    if (s.confirmed) return "explicit";
    if (s.strong) return "strong";
    if (s.probable) return "probable";
    if (s.possible) return "possible";
    return null;
  }

  function linkCountsText(p) {
    var s = relSummary(p);
    var parts = [];
    if (s.confirmed) parts.push(s.confirmed + " confirmed");
    if (s.strong) parts.push(s.strong + " strong");
    if (s.probable) parts.push(s.probable + " probable");
    if (s.possible) parts.push(s.possible + " possible");
    return parts.join(" · ");
  }

  function defaultSort(a, b) {
    // Default order: multi-coverage projects first (coverage desc),
    // then newest (year desc, undated last), then name, then id.
    // Applied only when no search query is active; typed queries keep
    // match order so results don't reshuffle while searching.
    var covDiff = coverage(b) - coverage(a);
    if (covDiff) return covDiff;
    var ya = parseInt(a.year, 10) || -1, yb = parseInt(b.year, 10) || -1;
    if (yb !== ya) return yb - ya;
    var na = String(a.name || ""), nb = String(b.name || "");
    if (na < nb) return -1;
    if (na > nb) return 1;
    if (a.id < b.id) return -1;
    if (a.id > b.id) return 1;
    return 0;
  }

  function current() {
    var rawQ = document.getElementById("explorer-search").value || "";
    var q = rawQ.toLowerCase();
    var brgy = document.getElementById("explorer-barangay").value;
    var year = document.getElementById("explorer-year").value;
    var type = document.getElementById("explorer-type").value;
    var cov = document.getElementById("explorer-coverage").value;
    var match = document.getElementById("explorer-match").value;
    var out = store.projects.filter(function (p) {
      if (q && (p.name + " " + p.id).toLowerCase().indexOf(q) === -1) return false;
      if (brgy && (p.barangay || []).indexOf(brgy) === -1) return false;
      if (year && String(p.year) !== year) return false;
      if (type && p.type !== type) return false;
      if (cov && coverage(p) < Number(cov)) return false;
      if (match) {
        var best = bestLevel(p);
        var need = LEVEL_RANK[match];
        var have = best ? LEVEL_RANK[best] : -1;
        if (need === undefined || have < need) return false;
      }
      return true;
    });
    if (!rawQ.trim()) out.sort(defaultSort);
    var cards = out.map(projectCard);
    var box = document.getElementById("explorer-results");
    box.innerHTML = cards.length ? cards.join("") :
      '<p class="source-label">No matches. Try a different search or filter.</p>';
    document.getElementById("explorer-count").textContent =
      cards.length + " project" + (cards.length === 1 ? "" : "s");
  }

  function fillFilters() {
    var brgys = {}, years = {}, types = {};
    store.projects.forEach(function (p) {
      (p.barangay || []).forEach(function (b) { brgys[b] = 1; });
      if (p.year) years[p.year] = 1;
      if (p.type) types[p.type] = 1;
    });
    function fill(id, vals, labelFn) {
      var sel = document.getElementById(id);
      Object.keys(vals).sort().forEach(function (v) {
        var o = document.createElement("option");
        o.value = v; o.textContent = labelFn ? labelFn(v) : v; sel.appendChild(o);
      });
    }
    fill("explorer-barangay", brgys); fill("explorer-year", years); fill("explorer-type", types, typeLabel);
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
    ["explorer-barangay", "explorer-year", "explorer-type", "explorer-coverage", "explorer-match"].forEach(function (id) {
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
