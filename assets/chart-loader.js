if (document.querySelector('canvas')) {
  var sc = document.createElement('script');
  sc.src = window.__CONFIG__.assetBase + '/assets/chart.umd.min.js';
  sc.defer = true;
  document.head.appendChild(sc);
}
