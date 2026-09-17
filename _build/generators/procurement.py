import html
import json
from pathlib import Path

from _build.config import ROOT, SRC_DATA
from _build.locales import t


def _build_procurement_labels(locale: dict) -> dict:
    return {
        "PROC_EYEBROW": t(locale, "procurement.eyebrow", ""),
        "PROC_TITLE": t(locale, "procurement.title", ""),
        "PROC_UNIQUE_CATEGORIES": t(locale, "procurement.unique_categories", "Unique Categories"),
        "PROC_TOTAL_SPEND": t(locale, "procurement.total_spend", "Total Contract Value"),
        "PROC_AVERAGE_COST": t(locale, "procurement.average_cost", "Average Cost"),
        "PROC_CONTRACTS": t(locale, "procurement.contracts", "Contracts"),
        "PROC_CATEGORY": t(locale, "procurement.category", "Category"),
        "PROC_AMOUNT": t(locale, "procurement.amount", "Amount"),
        "PROC_STATUS": t(locale, "procurement.status", "Status"),
        "PROC_AWARDEE": t(locale, "procurement.awardee", "Awardee"),
        "PROC_DATE": t(locale, "procurement.date", "Date"),
        "PROC_REF_NO": t(locale, "procurement.ref_no", "Reference No."),
        "PROC_CONTRACT_NO": t(locale, "procurement.contract_no", "Contract No."),
        "PROC_TITLE_COL": t(locale, "procurement.title_col", "Title"),
        "PROC_ORGANIZATION_COL": t(locale, "procurement.organization_col", "Organization"),
        "PROC_TIME_FRAME": t(locale, "procurement.time_frame", "Time Frame"),
        "PROC_FILTER_ALL": t(locale, "procurement.filter_all", "All"),
        "PROC_FILTER_30D": t(locale, "procurement.filter_30d", "Last 30 days"),
        "PROC_FILTER_3M": t(locale, "procurement.filter_3m", "Last 3 months"),
        "PROC_FILTER_6M": t(locale, "procurement.filter_6m", "Last 6 months"),
        "PROC_FILTER_1Y": t(locale, "procurement.filter_1y", "Last 1 year"),
        "PROC_FILTER_3Y": t(locale, "procurement.filter_3y", "Last 3 years"),
        "PROC_FILTER_CUSTOM": t(locale, "procurement.filter_custom", "Custom"),
        "PROC_APPLY": t(locale, "procurement.apply", "Apply"),
        "PROC_MAYORAL_TERM": t(locale, "procurement.mayoral_term", "Mayoral Term"),
        "PROC_TERM_CALIMLIM": t(locale, "procurement.term_calimlim", "Maximo Calimlim Jr."),
        "PROC_TERM_TAMBAON": t(locale, "procurement.term_tambaoan", "Gerald Glenn L. Tambaoan"),
        "PROC_TERM_PENULIAR": t(locale, "procurement.term_penuliar", "Anthony C. Penuliar"),
        "PROC_TERM_VEGA": t(locale, "procurement.term_vega", "Karl Christian F. Vega"),
        "PROC_CLEAR": t(locale, "procurement.clear", "Clear"),
        "PROC_SEARCH_PLACEHOLDER": t(locale, "procurement.search_placeholder", "Search contracts..."),
        "PROC_SHOWING_X_OF_Y": t(locale, "procurement.showing_x_of_y", "Showing 1-20 of {n}"),
        "PROC_DOWNLOAD_CSV": t(locale, "procurement.download_csv", "CSV"),
        "PROC_REMOVE_DUPLICATES": t(locale, "procurement.remove_duplicates", "Remove duplicate contracts"),
        "PROC_RESULTS_COUNT": t(locale, "procurement.results_count", "Results"),
        "PROC_MONTHLY_TREND_TITLE": t(locale, "procurement.monthly_trend_title", ""),
        "PROC_MONTHLY_TREND_DESC": t(locale, "procurement.monthly_trend_desc", ""),
        "PROC_TOP_AWARDEES_TITLE": t(locale, "procurement.top_awardees_title", ""),
        "PROC_TOP_AWARDEES_DESC": t(locale, "procurement.top_awardees_desc", ""),
        "PROC_SOURCE_PHILGEPS": t(locale, "procurement.source_philgeps", "Source: PhilGEPS"),
        "PROC_SOURCE_AGGREGATOR": t(locale, "procurement.source_aggregator", "Aggregated via: BetterGov.ph"),
        "PROC_PER_CONTRACT": t(locale, "procurement.per_contract", "Per contract"),
        "PROC_VERIFIED": t(locale, "common.verified", "Verified"),
        "PROC_OFFICIAL": t(locale, "common.official", "Official"),
    }


def _build_procurement_metric_cards(locale: dict, metrics: dict) -> str:
    """Build the 4 metric cards for the procurement dashboard."""
    total_amount = metrics.get("total_amount", 0)
    contract_count = metrics.get("contract_count", 0)
    average_cost = metrics.get("average_cost", 0)
    unique_categories = metrics.get("unique_categories", 0)

    return (
        f'      <div class="card" id="metric-categories">\n'
        f'        <h2>{t(locale, "procurement.unique_categories", "Unique Categories")}</h2>\n'
        f'        <p class="figure" id="metric-categories-value">{unique_categories:,}</p>\n'
        f'        <span class="verification-badge badge-official">{t(locale, "common.official", "Official")}</span>\n'
        f'        <span class="source-label">{t(locale, "procurement.category", "Category")}</span>\n'
        f'      </div>\n'
        f'      <div class="card" id="metric-total">\n'
        f'        <h2>{t(locale, "procurement.total_spend", "Total Contract Value")}</h2>\n'
        f'        <p class="figure" id="metric-total-value">&#8369;{total_amount:,.0f}</p>\n'
        f'        <span class="verification-badge badge-official">{t(locale, "common.official", "Official")}</span>\n'
        f'        <span class="source-label">{t(locale, "procurement.source_philgeps", "Source: PhilGEPS")}</span>\n'
        f'      </div>\n'
        f'      <div class="card" id="metric-average">\n'
        f'        <h2>{t(locale, "procurement.average_cost", "Average Cost")}</h2>\n'
        f'        <p class="figure" id="metric-average-value">&#8369;{average_cost:,.0f}</p>\n'
        f'        <span class="verification-badge badge-verified">{t(locale, "common.verified", "Verified")}</span>\n'
        f'        <span class="source-label">{t(locale, "procurement.per_contract", "Per contract")}</span>\n'
        f'      </div>\n'
        f'      <div class="card" id="metric-contracts">\n'
        f'        <h2>{t(locale, "procurement.contracts", "Contracts")}</h2>\n'
        f'        <p class="figure" id="metric-contracts-value">{contract_count:,}</p>\n'
        f'        <span class="verification-badge badge-verified">{t(locale, "common.verified", "Verified")}</span>\n'
        f'        <span class="source-label">{t(locale, "procurement.source_aggregator", "Aggregated via: BetterGov.ph")}</span>\n'
        f'      </div>'
    )


def _build_procurement_charts(locale: dict, date_range: str, total_amount: int, contract_count: int) -> str:
    """Build the charts section (trend, awardees, categories)."""
    return (
        f'    <div class="grid grid-2 stack-gap-lg mt-24">\n'
        f'      <div class="card">\n'
        f'        <h3>{t(locale, "procurement.monthly_trend_title", "")}</h3>\n'
        f'        <p class="source-label source-label--flush" id="chart-trend-subtitle">{t(locale, "procurement.monthly_trend_desc", "")} &bull; {date_range}</p>\n'
        f'        <canvas id="chart-procurement-trend" height="220" role="img" aria-label="Monthly procurement trend"></canvas>\n'
        f'      </div>\n'
        f'      <div class="card">\n'
        f'        <h3>{t(locale, "procurement.top_awardees_title", "")}</h3>\n'
        f'        <p class="source-label source-label--flush" id="chart-awardees-subtitle">{t(locale, "procurement.top_awardees_desc", "")} &bull; {date_range}</p>\n'
        f'        <canvas id="chart-procurement-awardees" height="220" role="img" aria-label="Top 10 awardees"></canvas>\n'
        f'      </div>\n'
        f'    </div>\n'
        f'    <div class="card mt-24">\n'
        f'      <h3>Procurement by Category</h3>\n'
        f'      <p class="source-label source-label--flush">Total spend by business category</p>\n'
        f'      <p class="chart-categories-subtitle" id="chart-categories-subtitle">Total: &#8369;{total_amount:,.0f} &bull; {date_range}</p>\n'
        f'      <div class="chart-categories-wrap">\n'
        f'        <div class="chart-categories-inner">\n'
        f'          <canvas id="chart-procurement-categories" height="200" role="img" aria-label="Procurement by business category"></canvas>\n'
        f'        </div>\n'
        f'      </div>\n'
        f'      <div id="category-legend" class="mt-16"></div>\n'
        f'    </div>\n'
    )


def _build_procurement_table(locale: dict, contract_count: int, total_amount: int, date_range: str, search_placeholder: str, showing_x_of_y: str, download_csv: str, remove_duplicates: str) -> str:
    """Build the procurement table, toolbar, and pagination."""
    return (
        f'      <div class="procurement-toolbar mt-24">\n'
        f'        <div class="procurement-toolbar-stats">\n'
        f'          <span class="stat-label">{t(locale, "procurement.results_count", "Results")}</span>\n'
        f'          <span class="stat-value" id="toolbar-count">{contract_count:,}</span>\n'
        f'          <span class="stat-divider">&bull;</span>\n'
        f'          <span class="stat-value" id="toolbar-total">&#8369;{total_amount:,.0f}</span>\n'
        f'          <span class="stat-divider">&bull;</span>\n'
        f'          <span class="stat-value" id="toolbar-daterange">{date_range}</span>\n'
        f'        </div>\n'
        f'        <div class="procurement-toolbar-actions">\n'
        f'          <input type="search" id="procurement-search" placeholder="{search_placeholder}" aria-label="{search_placeholder}">\n'
        f'          <button class="btn btn-outline" id="procurement-dup-btn">{remove_duplicates}</button>\n'
        f'          <button class="btn btn-outline" id="procurement-csv-btn">{download_csv}</button>\n'
        f'        </div>\n'
        f'      </div>\n'
        f'      <div class="table-wrap">\n'
        f'        <table aria-label="Procurement contracts" id="procurement-table">\n'
        f'          <thead>\n'
        f'            <tr>\n'
        f'              <th scope="col" class="sortable" data-column="reference_id">{t(locale, "procurement.ref_no", "Reference No.")} <span class="sort-indicator"></span></th>\n'
        f'              <th scope="col" class="sortable" data-column="contract_no">{t(locale, "procurement.contract_no", "Contract No.")} <span class="sort-indicator"></span></th>\n'
        f'              <th scope="col" class="sortable" data-column="title">{t(locale, "procurement.title_col", "Title")} <span class="sort-indicator"></span></th>\n'
        f'              <th scope="col" class="sortable" data-column="awardee">{t(locale, "procurement.awardee", "")} <span class="sort-indicator"></span></th>\n'
        f'              <th scope="col" class="sortable" data-column="organization_name">{t(locale, "procurement.organization_col", "Organization")} <span class="sort-indicator"></span></th>\n'
        f'              <th scope="col" class="sortable" data-column="amount">{t(locale, "procurement.amount", "")} <span class="sort-indicator"></span></th>\n'
        f'              <th scope="col" class="sortable" data-column="business_category">{t(locale, "procurement.category", "")} <span class="sort-indicator"></span></th>\n'
        f'              <th scope="col" class="sortable" data-column="award_date">{t(locale, "procurement.date", "")} <span class="sort-indicator"></span></th>\n'
        f'              <th scope="col" class="sortable" data-column="status">{t(locale, "procurement.status", "")} <span class="sort-indicator"></span></th>\n'
        f'            </tr>\n'
        f'          </thead>\n'
        f'          <tbody>\n'
        f'          </tbody>\n'
        f'        </table>\n'
        f'      </div>\n'
        f'      <div class="procurement-pagination-wrap">\n'
        f'        <span class="source-label" id="procurement-page-info">{showing_x_of_y}</span>\n'
        f'        <div id="procurement-pagination">\n'
        f'          <button class="btn btn-outline" data-page="prev">&laquo; Prev</button>\n'
        f'          <span class="source-label" id="procurement-page-indicator">1 / 1</span>\n'
        f'          <button class="btn btn-outline" data-page="next">Next &raquo;</button>\n'
        f'        </div>\n'
        f'      </div>\n'
    )


def _build_procurement_scripts(monthly_json: str, awardees_json: str, contracts_json: str, categories_json: str, orgs_json: str, total_amount: int, date_range: str, license_str: str, mayoral_terms_json: str = "") -> str:
    """Build the inline scripts and styles for the procurement dashboard."""
    mayoral_terms_line = f"      window.MAYORAL_TERMS = {mayoral_terms_json};\n" if mayoral_terms_json else ""
    return (
        f'    <p class="source-label">Source: PhilGEPS | Aggregated via: BetterGov.ph | License: {html.escape(license_str)}</p>\n'
        f'    <script>\n'
        f'      window.PROCUREMENT_DATA = {{ monthly: {monthly_json}, awardees: {awardees_json} }};\n'
        f'      window.PROCUREMENT_CONTRACTS = {contracts_json};\n'
        f'      window.PROCUREMENT_CATEGORIES = {categories_json};\n'
        f'      window.PROCUREMENT_ORGS = {orgs_json};\n'
        f'      window.PROCUREMENT_TOTAL = {total_amount};\n'
        f'      window.PROCUREMENT_DATE_RANGE = {json.dumps(date_range)};\n'
        f'{mayoral_terms_line}'
        f'    </script>\n'
        f'    <style>\n'
        f'      #procurement-table th.sort-asc .sort-indicator::after {{ content: " ▲"; }}\n'
        f'      #procurement-table th.sort-desc .sort-indicator::after {{ content: " ▼"; }}\n'
        f'    </style>\n'
    )


def generate_procurement(locale: dict) -> tuple[str, dict, dict]:
    """Generate procurement dashboard HTML. Returns (html, metadata, hero_meta)."""
    data_path = SRC_DATA / "procurement.json"
    if not data_path.exists():
        return "", {}, {}

    data = json.loads(data_path.read_text(encoding="utf-8"))
    metrics = data.get("metrics", {})
    contracts = data.get("contracts", [])
    monthly_trend = data.get("monthly_trend", [])
    top_awardees = data.get("top_awardees", [])

    total_amount = metrics.get("total_amount", 0)
    contract_count = metrics.get("contract_count", 0)
    license_str = metrics.get("license", "")

    metric_cards = _build_procurement_metric_cards(locale, metrics)

    monthly_json = json.dumps(monthly_trend, ensure_ascii=False)
    awardees_json = json.dumps(top_awardees, ensure_ascii=False)
    contracts_json = json.dumps(contracts, ensure_ascii=False)

    cat_totals = {}
    org_totals = {}
    for c in contracts:
        cat = c.get("business_category", "Other") or "Other"
        cat_totals[cat] = cat_totals.get(cat, 0.0) + (c.get("amount", 0) or 0)
        org = c.get("organization_name", "Unknown") or "Unknown"
        if org not in org_totals:
            org_totals[org] = {"count": 0, "total": 0.0}
        org_totals[org]["count"] += 1
        org_totals[org]["total"] += c.get("amount", 0) or 0

    date_range = ""
    award_dates = [c.get("award_date", "") for c in contracts if c.get("award_date")]
    if award_dates:
        min_date = min(award_dates)
        max_date = max(award_dates)
        from datetime import datetime as _dt
        from datetime import timezone
        def _fmt_date(ds):
            try:
                return _dt.strptime(ds, "%Y-%m-%d").replace(tzinfo=timezone.utc).strftime("%b %Y")
            except Exception:
                return ds
        date_range = f"{_fmt_date(min_date)} \u2013 {_fmt_date(max_date)}"

    categories_list = sorted(
        [{"name": k, "total": v} for k, v in cat_totals.items()],
        key=lambda x: x["total"],
        reverse=True,
    )
    orgs_list = sorted(
        [{"name": k, "count": v["count"], "total": v["total"]} for k, v in org_totals.items()],
        key=lambda x: x["total"],
        reverse=True,
    )
    categories_json = json.dumps(categories_list, ensure_ascii=False)
    orgs_json = json.dumps(orgs_list, ensure_ascii=False)

    search_placeholder = t(locale, "procurement.search_placeholder", "Search contracts...")
    showing_x_of_y = t(locale, "procurement.showing_x_of_y", "Showing 1-20 of {n}").replace("{n}", str(contract_count))
    download_csv = t(locale, "procurement.download_csv", "CSV")
    remove_duplicates = t(locale, "procurement.remove_duplicates", "Remove duplicate contracts")

    charts_html = _build_procurement_charts(locale, date_range, total_amount, contract_count)
    table_html = _build_procurement_table(locale, contract_count, total_amount, date_range, search_placeholder, showing_x_of_y, download_csv, remove_duplicates)
    # Mayoral terms: single source is src/data/mayoral-terms.json.
    # Rollover rule: when a new mayor takes office, close the incumbent row
    # with its real end date and append a new row with "end": null.
    # A null end means "incumbent" — JS treats it as today (see common.js).
    terms_path = SRC_DATA / "mayoral-terms.json"
    mayoral_terms = json.loads(terms_path.read_text(encoding="utf-8"))
    mayoral_terms_json = json.dumps(mayoral_terms, ensure_ascii=False)
    scripts_html = _build_procurement_scripts(monthly_json, awardees_json, contracts_json, categories_json, orgs_json, total_amount, date_range, license_str, mayoral_terms_json)

    proc_html = (
        f'    <div class="section-head">\n'
        f'      <div class="section-eyebrow">{t(locale, "procurement.eyebrow", "")}</div>\n'
        f'      <h2>{t(locale, "procurement.title", "")}</h2>\n'
        f'      <p>Municipality of Mapanda &mdash; {contract_count:,} contracts totaling &#8369;{total_amount:,.0f}. Data from PhilGEPS via BetterGov.ph Open Data Portal.</p>\n'
        f'    </div>\n'
        f'    <div class="filter-row">\n'
        f'      <div class="filter-section">\n'
        f'        <div class="filter-section-head">{t(locale, "procurement.time_frame", "Time Frame")}</div>\n'
        f'        <div class="filter-pills" id="procurement-filters">\n'
        f'          <button class="filter-pill active" data-range="all">{t(locale, "procurement.filter_all", "All")}</button>\n'
        f'          <button class="filter-pill" data-range="30d">{t(locale, "procurement.filter_30d", "Last 30 days")}</button>\n'
        f'          <button class="filter-pill" data-range="3m">{t(locale, "procurement.filter_3m", "Last 3 months")}</button>\n'
        f'          <button class="filter-pill" data-range="6m">{t(locale, "procurement.filter_6m", "Last 6 months")}</button>\n'
        f'          <button class="filter-pill" data-range="1y">{t(locale, "procurement.filter_1y", "Last 1 year")}</button>\n'
        f'          <button class="filter-pill" data-range="3y">{t(locale, "procurement.filter_3y", "Last 3 years")}</button>\n'
        f'          <button class="filter-pill filter-pill-custom" data-range="custom">{t(locale, "procurement.filter_custom", "Custom")}</button>\n'
        f'        </div>\n'
        f'        <div class="custom-range-inline" id="custom-range-inline">\n'
        f'          <label>{t(locale, "transparency.infrastructure_from", "From")}</label>\n'
        f'          <input type="date" id="custom-date-from" />\n'
        f'          <label>{t(locale, "transparency.infrastructure_to", "To")}</label>\n'
        f'          <input type="date" id="custom-date-to" />\n'
        f'          <button class="btn btn-primary btn-sm" id="custom-range-apply">{t(locale, "procurement.apply", "Apply")}</button>\n'
        f'        </div>\n'
        f'      </div>\n'
        f'      <div class="filter-section">\n'
        f'        <div class="filter-section-head">{t(locale, "procurement.mayoral_term", "Mayoral Term")}</div>\n'
        f'        <div class="filter-pills" id="mayoral-term-filters">\n'
        f'          <button class="term-pill" data-term="0">{t(locale, "procurement.term_calimlim", "Maximo Calimlim Jr.")}</button>\n'
        f'          <button class="term-pill" data-term="1">{t(locale, "procurement.term_tambaoan", "Gerald Glenn L. Tambaoan")}</button>\n'
        f'          <button class="term-pill" data-term="2">{t(locale, "procurement.term_penuliar", "Anthony C. Penuliar")}</button>\n'
        f'          <button class="term-pill" data-term="3">{t(locale, "procurement.term_vega", "Karl Christian F. Vega")}</button>\n'
        f'          <button class="filter-clear hidden" id="clear-mayoral-term">{t(locale, "procurement.clear", "Clear")} &times;</button>\n'
        f'        </div>\n'
        f'      </div>\n'
        f'    </div>\n'
         f'    <div class="grid grid-4 stack-gap-lg mt-24">\n'
        f'      {metric_cards}\n'
        f'    </div>\n'
        f'    {charts_html}\n'
        f'    {table_html}\n'
        f'    {scripts_html}\n'
    )

    return proc_html, {
        "title": t(locale, "procurement.title", "Government Contracts") + " — BetterMapandan.org",
        "description": f"Mapandan procurement records: {contract_count:,} contracts totaling ₱{total_amount:,.0f}.",
    }, {}


def generate_homepage_procurement_data() -> str:
    data_path = SRC_DATA / "procurement.json"
    if not data_path.exists():
        return "{\"monthly\":[],\"awardees\":[]}"
    data = json.loads(data_path.read_text(encoding="utf-8"))
    contracts = data.get("contracts", [])
    
    monthly = {}
    for c in contracts:
        if c.get("award_date"):
            m = c["award_date"][:7]
            monthly[m] = monthly.get(m, 0) + (c.get("amount") or 0)
    monthly_list = [{"month": k, "total": v} for k, v in sorted(monthly.items())]
    
    awardees = {}
    for c in contracts:
        name = (c.get("awardee") or "Unknown").strip()
        awardees[name] = awardees.get(name, 0) + (c.get("amount") or 0)
    awardees_list = sorted(
        [{"name": k, "total": v} for k, v in awardees.items()],
        key=lambda x: x["total"],
        reverse=True
    )[:10]
    
    return json.dumps({"monthly": monthly_list, "awardees": awardees_list}, ensure_ascii=False)


def generate_homepage_dpwh_data() -> str:
    data_path = SRC_DATA / "dpwh.json"
    if not data_path.exists():
        return "[]"
    data = json.loads(data_path.read_text(encoding="utf-8"))
    return json.dumps(data.get("projects", []), ensure_ascii=False)
