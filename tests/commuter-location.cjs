"use strict";
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
// Exercise the runtime's pure helper without starting a DOM or Leaflet.
const source = fs.readFileSync(require('node:path').join(__dirname, '../assets/commuter-map.js'), 'utf8');
const helper = vm.runInNewContext('(' + source.match(/function stationLocation\(feature\) \{[\s\S]*?\n  \}/)[0] + ')', { URLSearchParams });
test('Point validation rejects missing, coerced, nonfinite and malformed coordinates', () => {
  for (const geometry of [null, {}, { type: 'LineString', coordinates: [1, 2] },
    ...[[], [1], new Array(2), [1, 2, 3], ['', 2], ['1', 2], [true, 2], [null, 2], [NaN, 2], [Infinity, 2], [1, -Infinity], [181, 0], [0, 91], [-181, 0], [0, -91]].map(coordinates => ({ type: 'Point', coordinates }))]) {
    assert.equal(helper({ geometry }), null, JSON.stringify(geometry));
  }
  assert.equal(helper(null), null);
});
test('exact lat/lon URLs preserve precision, boundaries and omit origin and tracking', () => {
  for (const coordinates of [[120.4524123456789, 16.0266123456789], [180, 90], [-180, -90], [0, 0]]) {
    const location = helper({ geometry: { type: 'Point', coordinates } });
    const coordinate = [coordinates[1], coordinates[0]].join(',');
    assert.equal(location.view, 'https://www.google.com/maps/search/?' + new URLSearchParams({ api: '1', query: coordinate }));
    assert.equal(location.walking, 'https://www.google.com/maps/dir/?' + new URLSearchParams({ api: '1', destination: coordinate, travelmode: 'walking' }));
  }
});
