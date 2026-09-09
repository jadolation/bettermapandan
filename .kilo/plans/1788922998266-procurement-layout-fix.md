# Procurement Layout Fix Plan

## Problem
1. Pagination buttons are invisible/hidden - they only appear on highlight
2. Search bar layout is broken - results text and controls are not properly aligned
3. Buttons use `.btn-ghost` which has white text/border for dark backgrounds, making them invisible on the light procurement section

## Root Cause
- `.btn-ghost` CSS: `background: transparent; border-color: rgba(255,255,255,0.55); color: #fff;` — designed for dark backgrounds
- The procurement section has a light background, so white text/border buttons are invisible
- The flex layout uses `align-items: stretch` which causes height mismatches
- The results text and controls are in separate flex containers that wrap poorly

## Fix Required

### 1. `build.py` — `generate_procurement()` controls layout (around line 1548)
Replace the current controls row:

```html
<div style="display:flex;justify-content:space-between;align-items:stretch;gap:12px;flex-wrap:wrap;margin-bottom:12px">
  <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
    <strong>Results</strong> 277 | ₱470,203,285
  </div>
  <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
    <input type="search" id="procurement-search" ... style="padding:8px 12px;...;min-width:220px">
    <button class="btn btn-ghost" ...>Remove duplicate contracts</button>
    <button class="btn btn-ghost" ...>CSV</button>
  </div>
</div>
```

With this:
```html
<div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:12px">
  <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
    <strong style="font-size:0.95rem">Results:</strong>
    <span style="font-size:0.95rem">277 | ₱470,203,285</span>
  </div>
  <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
    <input type="search" id="procurement-search" placeholder="Search contracts..." aria-label="Search contracts..." style="padding:10px 14px;font-size:0.95rem;border:1.5px solid var(--line);border-radius:var(--radius);min-width:240px">
    <button class="btn btn-outline" id="procurement-dup-btn" style="padding:10px 14px;font-size:0.95rem">Remove duplicate contracts</button>
    <button class="btn btn-outline" id="procurement-csv-btn" style="padding:10px 14px;font-size:0.95rem">CSV</button>
  </div>
</div>
```

Key changes:
- Change `align-items: stretch` to `align-items: center`
- Wrap "Results" count and amount in a `<span>` with consistent font-size
- Change buttons from `btn-ghost` to `btn-outline` (visible on light backgrounds)
- Increase search input padding and min-width
- Increase button padding

### 2. `build.py` — pagination buttons styling (around line 1580)
Change pagination buttons from `btn-ghost` to `btn-outline`:

```html
<button class="btn btn-outline" data-page="prev" style="padding:10px 14px;font-size:0.95rem">&laquo; Prev</button>
<span class="source-label" id="procurement-page-indicator">1 / 1</span>
<button class="btn btn-outline" data-page="next" style="padding:10px 14px;font-size:0.95rem">Next &raquo;</button>
```

### 3. `assets/transparency.js` — `renderPageNumbers()` (around line 205)
Update the numbered page button styles to be visible:

```javascript
function renderPageNumbers(totalPages, current) {
  var html = "";
  var pages = [];
  if (totalPages <= 7) {
    for (var i = 1; i <= totalPages; i++) pages.push(i);
  } else {
    pages.push(1);
    if (current > 3) pages.push("...");
    var start = Math.max(2, current - 1);
    var end = Math.min(totalPages - 1, current + 1);
    if (current <= 3) end = Math.min(totalPages - 1, 4);
    if (current >= totalPages - 2) start = Math.max(2, totalPages - 3);
    for (var i = start; i <= end; i++) pages.push(i);
    if (current < totalPages - 2) pages.push("...");
    pages.push(totalPages);
  }
  for (var i = 0; i < pages.length; i++) {
    var p = pages[i];
    if (p === "...") {
      html += '<span style="padding:0 6px;font-weight:bold;color:var(--ink)">...</span>';
    } else {
      var active = p === current ? ' style="font-weight:bold;background:var(--green-deep);color:#fff;border-color:var(--green-deep)"' : '';
      html += '<button class="btn btn-outline" data-page="' + p + '" style="padding:10px 14px;font-size:0.95rem;min-width:44px"' + active + '>' + p + '</button>';
    }
  }
  return html;
}
```

Key changes:
- Use `btn-outline` class instead of `btn-ghost`
- Active state: dark green background with white text
- Ellipsis uses `color:var(--ink)` for visibility
- Consistent padding and min-width with other controls

### 4. `assets/transparency.js` — pagination container insertion (around line 286)
Ensure the numbered pages wrapper inserts correctly:

```javascript
var numberedWrap = document.createElement("span");
numberedWrap.className = "numbered-pages";
numberedWrap.style.cssText = "display:inline-flex;gap:6px;align-items:center;flex-wrap:wrap";
numberedWrap.innerHTML = renderPageNumbers(totalPages, currentPage);
var existingNumbered = pagination.querySelector(".numbered-pages");
if (existingNumbered) existingNumbered.remove();
pagination.insertBefore(numberedWrap, pagination.children[1]);
```

Change `display:flex` to `display:inline-flex` so it flows inline with Prev/Next.

## Validation
After rebuild, verify:
1. Search bar is visible with clear border and adequate width
2. Results text "277 | ₱470,203,285" is on the same row as search bar on desktop
3. On mobile, results and controls stack cleanly
4. Pagination Prev/Next buttons are visible with green outline
5. Numbered page buttons appear between Prev/Next and are clickable
6. Active page number has dark green background
7. All buttons have consistent padding and font size

## Files to Modify
- `build.py` — lines ~1548-1584 (controls layout and pagination button classes)
- `assets/transparency.js` — lines ~205-231 (renderPageNumbers styles), ~286-292 (numbered wrapper display)
