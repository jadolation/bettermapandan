import html
import json
from pathlib import Path

from _build.config import ROOT, SRC_DATA
from _build.templates import compute_asset_base
from _build.locales import t


def _build_dpwh_labels(locale: dict) -> dict:
    return {
        "DPWH_TITLE": t(locale, "transparency.infrastructure_title", "Infrastructure Projects"),
        "DPWH_EYEBROW": t(locale, "transparency.infrastructure_eyebrow", "DPWH &middot; Infrastructure"),
        "DPWH_LEDE": t(locale, "transparency.infrastructure_lede", "DPWH contracts, road and flood-control projects, school buildings, and health facilities in Mapandan."),
        "DPWH_TOTAL_CONTRACTS": t(locale, "transparency.infrastructure_total_contracts", "Total Contracts"),
        "DPWH_TOTAL_VALUE": t(locale, "transparency.infrastructure_total_value", "Total Contract Value"),
        "DPWH_CATEGORY": t(locale, "transparency.infrastructure_category", "Category"),
        "DPWH_STATUS": t(locale, "transparency.infrastructure_status", "Status"),
        "DPWH_CONTRACTOR": t(locale, "transparency.infrastructure_contractor", "Contractor"),
        "DPWH_AMOUNT": t(locale, "transparency.infrastructure_amount", "Amount"),
        "DPWH_DATE": t(locale, "transparency.infrastructure_date", "Date"),
        "DPWH_PROJECT": t(locale, "transparency.infrastructure_project", "Project"),
        "DPWH_AGENCY": t(locale, "transparency.infrastructure_agency", "Implementing Agency"),
        "DPWH_SOURCE": t(locale, "transparency.infrastructure_source", "Source"),
        "DPWH_NO_LOCATION": t(locale, "transparency.infrastructure_no_location", "Projects without coordinates"),
        "DPWH_VIEW_MAP": t(locale, "transparency.infrastructure_view_map", "View on map"),
        "DPWH_FILTER_ALL": t(locale, "transparency.infrastructure_filter_all", "All"),
        "DPWH_COMPLETED": t(locale, "transparency.infrastructure_completed", "Completed"),
        "DPWH_ONGOING": t(locale, "transparency.infrastructure_ongoing", "Ongoing"),
        "DPWH_NOT_STARTED": t(locale, "transparency.infrastructure_not_started", "Not Yet Started"),
        "DPWH_CUSTOM_RANGE": t(locale, "transparency.infrastructure_custom_range", "Custom Range"),
        "DPWH_FROM": t(locale, "transparency.infrastructure_from", "From"),
        "DPWH_TO": t(locale, "transparency.infrastructure_to", "To"),
        "DPWH_AGGREGATED": t(locale, "transparency.infrastructure_aggregated", "Aggregated from published contracts"),
        "DPWH_STATUS_CARD": t(locale, "transparency.infrastructure_status_card", "Status"),
        "DPWH_ACCOMPLISHMENT": t(locale, "transparency.infrastructure_accomplishment", "Accomplishment"),
        "DPWH_MAP": t(locale, "transparency.infrastructure_map", "Map"),
        "DPWH_SOURCE_NOTE": t(locale, "transparency.infrastructure_source_note", "Source: DPWH Transparency Portal — Pangasinan 4th District Engineering Office. Project information, documents, and satellite imagery are continuously being uploaded."),
        "DPWH_SEARCH_PLACEHOLDER": t(locale, "transparency.infrastructure_search_placeholder", "Search projects..."),
        "DPWH_CLOSE": t(locale, "transparency.dash_close", "Close"),
        "TRANSPARENCY_VIEW_TABLE": t(locale, "transparency.dash_view_table", "View full tables"),
    }


def _dpwh_status_class(status: str) -> str:
    s = status.lower()
    if "completed" in s:
        return "pill-completed"
    if "ongoing" in s:
        return "pill-ongoing"
    if "not yet" in s or "pending" in s:
        return "pill-pending"
    return "pill"


def _dpwh_category_icon(category: str) -> str:
    return '<svg class="lucide" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>'


def generate_dpwh(locale: dict, asset_base: str = ".") -> tuple[str, dict, dict]:
    data_path = SRC_DATA / "dpwh.json"
    if not data_path.exists():
        return "", {}, {}

    data = json.loads(data_path.read_text(encoding="utf-8"))
    projects = data.get("projects", [])

    total_value = sum(float(p.get("contract_amount", 0) or 0) for p in projects)
    total_count = len(projects)
    completed = sum(1 for p in projects if "completed" in (p.get("status", "") or "").lower())
    ongoing = sum(1 for p in projects if "ongoing" in (p.get("status", "") or "").lower())
    not_started = sum(1 for p in projects if "not yet" in (p.get("status", "") or "").lower())

    labels = _build_dpwh_labels(locale)

    cards_html = f"""
<div class="grid grid-3 stack-gap-lg mt-24">
  <div class="card">
    <h2>{labels['DPWH_TOTAL_CONTRACTS']}</h2>
    <p class="figure" id="dpwh-count-value">{total_count:,}</p>
    <span class="verification-badge badge-official">{t(locale, 'common.official', 'Official')}</span>
    <span class="source-label">DPWH Transparency Portal</span>
  </div>
  <div class="card">
    <h2>{labels['DPWH_TOTAL_VALUE']}</h2>
    <p class="figure" id="dpwh-value-value">&#8369;{total_value:,.0f}</p>
    <span class="verification-badge badge-verified">{t(locale, 'common.verified', 'Verified')}</span>
    <span class="source-label">{labels['DPWH_AGGREGATED']}</span>
  </div>
  <div class="card">
    <h2>{labels['DPWH_STATUS_CARD']}</h2>
    <p class="figure" id="dpwh-status-value">
      {completed} {labels['DPWH_COMPLETED']} &bull; {ongoing} {labels['DPWH_ONGOING']} &bull; {not_started} {labels['DPWH_NOT_STARTED']}
    </p>
    <span class="verification-badge badge-official">{t(locale, 'common.official', 'Official')}</span>
    <span class="source-label">DPWH Transparency Portal</span>
  </div>
</div>
"""

    projects_json = json.dumps(projects, ensure_ascii=False)

    projects_rows = []
    for p in projects:
        tid = html.escape(p.get("transaction_id", ""))
        name = html.escape(p.get("project_name", ""))
        category = html.escape(p.get("category", ""))
        agency = html.escape(p.get("executing_agency", ""))
        contractor = html.escape(p.get("contractor", "") or "—")
        amount = p.get("contract_amount") or 0
        amount_str = f"&#8369;{float(amount):,.0f}" if amount else "—"
        status = html.escape(p.get("status", "") or "—")
        status_raw = (p.get("status") or "").lower()
        date = html.escape(p.get("actual_completion_date") or p.get("contract_effectivity_date") or "")
        date_raw = p.get("actual_completion_date") or p.get("contract_effectivity_date") or p.get("fiscal_year", "")
        if isinstance(date_raw, int):
            date_raw = f"{date_raw}-01-01"
        acc = p.get("accomplishment_percent") or 0
        acc_str = f"{float(acc):.0f}%" if acc else "—"
        lat = p.get("latitude")
        lng = p.get("longitude")
        has_map = lat is not None and lng is not None
        map_link = f'<a href="https://www.openstreetmap.org/?mlat={lat}&mlon={lng}#map=16/{lat}/{lng}" target="_blank" rel="noopener">{labels["DPWH_VIEW_MAP"]} &rarr;</a>' if has_map else ""

        projects_rows.append(
            f'<tr id="dpwh-project-{tid}" data-project_name="{html.escape(p.get("project_name", ""))}" data-agency="{html.escape(p.get("executing_agency", ""))}" data-contractor="{html.escape(p.get("contractor", "") or "—")}" data-amount="{float(amount):.0f}" data-status="{html.escape(status_raw)}" data-accomplishment="{float(acc):.0f}" data-date="{html.escape(str(date_raw))}">'
            f'<td>{_dpwh_category_icon(category)} {category}</td>'
            f'<td>{name}</td>'
            f'<td>{agency}</td>'
            f'<td>{contractor}</td>'
            f'<td class="num">{amount_str}</td>'
            f'<td><span class="pill {_dpwh_status_class(status)}">{status}</span></td>'
            f'<td class="num">{acc_str}</td>'
            f'<td>{date}</td>'
            f'<td>{map_link}</td>'
            f'</tr>'
        )

    projects_table = "\n".join(projects_rows)

    trigger_label = f"{labels['TRANSPARENCY_VIEW_TABLE']}: DPWH Infrastructure (details)"
    dialog_body = f"""
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<script defer src="{asset_base}/assets/leaflet-map.min.js"></script>
<script>
  window.DPWH_PROJECTS = {projects_json};
</script>
<div id="dpwh-map" class="map-container"></div>
<p id="dpwh-map-fallback" class="source-label hidden">Enable JavaScript to view the project map. All projects are listed in the table below.</p>
<input type="search" id="dpwh-search" placeholder="{labels['DPWH_SEARCH_PLACEHOLDER']}" aria-label="{labels['DPWH_SEARCH_PLACEHOLDER']}" class="form-input mb-24">
<div class="table-wrap">
  <table aria-label="DPWH infrastructure projects" id="dpwh-table">
    <thead>
      <tr>
        <th scope="col" data-column="category">{labels['DPWH_CATEGORY']} <span class="sort-indicator"></span></th>
        <th scope="col" data-column="project_name">{labels['DPWH_PROJECT']} <span class="sort-indicator"></span></th>
        <th scope="col" data-column="executing_agency">{labels['DPWH_AGENCY']} <span class="sort-indicator"></span></th>
        <th scope="col" data-column="contractor">{labels['DPWH_CONTRACTOR']} <span class="sort-indicator"></span></th>
        <th scope="col" data-column="contract_amount">{labels['DPWH_AMOUNT']} <span class="sort-indicator"></span></th>
        <th scope="col" data-column="status">{labels['DPWH_STATUS']} <span class="sort-indicator"></span></th>
        <th scope="col" data-column="accomplishment_percent">{labels['DPWH_ACCOMPLISHMENT']} <span class="sort-indicator"></span></th>
        <th scope="col" data-column="actual_completion_date">{labels['DPWH_DATE']} <span class="sort-indicator"></span></th>
        <th scope="col" data-column="map">{labels['DPWH_MAP']} <span class="sort-indicator"></span></th>
      </tr>
    </thead>
    <tbody>
      {projects_table}
    </tbody>
  </table>
</div>
<script defer src="{asset_base}/assets/dpwh-table.min.js"></script>
<p class="source-label">{labels['DPWH_SOURCE_NOTE']} <a href="https://transparency.dpwh.gov.ph/" target="_blank" rel="noopener">DPWH Transparency Portal</a></p>
"""

    html_content = f"""
{cards_html}

<button type="button" class="btn btn-outline btn-sm" data-open-modal="modal-dpwh">{trigger_label}</button>
<dialog data-modal id="modal-dpwh" aria-label="DPWH Infrastructure (details)">
  <div class="fdp-dialog-head"><strong>DPWH Infrastructure (details)</strong><button type="button" class="btn btn-outline btn-sm" data-close>{labels['DPWH_CLOSE']}</button></div>
  {dialog_body}
</dialog>
"""

    meta = {
        "title": "Infrastructure Projects — BetterMapandan.org",
        "description": "DPWH contracts, road projects, flood control, school buildings, and health facilities in Mapandan, Pangasinan.",
    }
    hero_meta = {
        "hero_eyebrow": labels["DPWH_EYEBROW"],
        "hero_heading": labels["DPWH_TITLE"],
        "hero_lede": labels["DPWH_LEDE"],
    }

    return html_content + '<style>.highlight-project{outline:3px solid var(--green-bright);outline-offset:4px;border-radius:6px;transition:outline .2s}</style>', meta, hero_meta
