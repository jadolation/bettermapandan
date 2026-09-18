/* dashboard-tabs.js — Transparency dashboard interactions */
(function () {
  'use strict';

  function setActiveTab() {
    var path = location.pathname;
    document.querySelectorAll('.transparency-tabs .tab-btn').forEach(function (btn) {
      var href = btn.getAttribute('href');
      var isActive = href && path === href.replace(/\/$/, '');
      btn.classList.toggle('active', isActive);
      btn.setAttribute('aria-current', isActive ? 'true' : 'false');
    });
  }

  document.addEventListener('DOMContentLoaded', setActiveTab);

  // View toggle (table vs card)
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.view-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var view = this.getAttribute('data-view');
        document.querySelectorAll('.view-btn').forEach(function (b) {
          b.classList.toggle('active', b === btn);
        });
        var container = document.getElementById('records-container');
        if (container) {
          container.classList.toggle('table-view', view === 'table');
          container.classList.toggle('card-view', view === 'card');
        }
      });
    });

    // Restore view preference
    var pref = localStorage.getItem('transparency-view');
    if (pref) {
      document.querySelectorAll('.view-btn').forEach(function (b) {
        b.classList.toggle('active', b.getAttribute('data-view') === pref);
      });
      var container = document.getElementById('records-container');
      if (container) {
        container.classList.add(pref === 'card' ? 'card-view' : 'table-view');
      }
    }
  });

  // CSV export utility
  window.exportToCSV = function (records, filename) {
    if (!records || !records.length) return;
    var headers = Object.keys(records[0]);
    var lines = [headers.join(',')];
    records.forEach(function (r) {
      lines.push(headers.map(function (h) {
        var v = r[h] == null ? '' : String(r[h]);
        return '"' + v.replace(/"/g, '""') + '"';
      }).join(','));
    });
    var blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename || 'export.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Export button wiring
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-export-csv]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var dataset = this.getAttribute('data-export-csv');
        var rows = [];
        if (dataset && window[dataset]) {
          rows = Array.isArray(window[dataset]) ? window[dataset] : [window[dataset]];
        }
        exportToCSV(rows, (dataset || 'export') + '.csv');
      });
    });
  });

  // Dynamic sticky top for transparency tabs
  function updateStickyTabsTop() {
    var header = document.querySelector('.site-header');
    var tabs = document.querySelector('.transparency-tabs');
    if (!header || !tabs) return;

    var headerHeight = header.offsetHeight;
    var emergencyHeight = 44;
    var stickyTop = emergencyHeight + headerHeight;

    tabs.style.top = stickyTop + 'px';
  }

  document.addEventListener('DOMContentLoaded', updateStickyTabsTop);
  window.addEventListener('resize', updateStickyTabsTop);

})();
