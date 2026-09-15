from collections import Counter
import html
import json
import re
from pathlib import Path

from _build.config import ROOT, SRC_DATA, SRC_TEMPLATES
from _build.locales import t
from _build.templates import fill, compute_url, compute_asset_base, FRONT_MATTER_RE


def generate_legislative(locale: dict, is_fil: bool) -> tuple[str, dict, dict]:
    """Generate legislative page HTML. Returns (html, metadata, hero_meta) for SEO."""
    data_path = SRC_DATA / "legislative.json"
    try:
        template = (SRC_TEMPLATES / "legislative.html").read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(f"ERROR: Template file not found: {SRC_TEMPLATES / 'legislative.html'}")

    match = FRONT_MATTER_RE.match(template)
    if match:
        meta_block, _ = match.groups()
        hero_meta = {}
        for line in meta_block.splitlines():
            key, _, value = line.partition(":")
            key = key.strip()
            if key in ("hero_eyebrow", "hero_heading", "hero_lede"):
                hero_meta[key] = value.strip()
    else:
        hero_meta = {}

    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"ERROR: Malformed JSON in {data_path}: {e}")

    filled = _fill_legislative_template(template, data, locale, is_fil)
    return filled, {
        "title": t(locale, "legislative.ord_title", "Municipal ordinances") + " — BetterMapandan.org",
        "description": t(locale, "legislative.ord_desc", "Ordinances, resolutions, and executive issuances for the Municipality of Mapandan."),
    }, hero_meta


def _fill_legislative_template(template: str, data: dict, locale: dict, is_fil: bool = False) -> str:
    fiscal_cards = _build_fiscal_cards(data.get("fiscal", []))
    trend_cards = _build_trend_cards(data.get("legislative_trends", []))
    process_steps = _build_process_steps(data.get("legislative_process", []))
    chart_data = _build_chart_data(data)
    chart_json = json.dumps(chart_data, ensure_ascii=False)
    ord_json = json.dumps(data.get("ordinances", []), ensure_ascii=False)
    res_json = json.dumps(data.get("resolutions", []), ensure_ascii=False)
    exec_json = json.dumps(data.get("executive_issuances", []), ensure_ascii=False)

    gw = data.get("governance_framework", {})
    asset_base = compute_asset_base(Path("legislative/index.html"), is_fil)

    return fill(template, {
        "ASSET_BASE": asset_base,
        "HISTORY": gw.get("history", ""),
        "MUNICIPAL_CLASS": gw.get("municipal_class", ""),
        "LAND_AREA": gw.get("land_area", ""),
        "BARANGAYS": str(gw.get("barangays", "")),
        "FISCAL_CARDS": "\n      ".join(fiscal_cards),
        "TRENDS_CARDS": "\n      ".join(trend_cards),
        "PROCESS_STEPS": "\n      ".join(process_steps),
        "LEGISLATIVE_ORDINANCES_JSON": ord_json,
        "LEGISLATIVE_RESOLUTIONS_JSON": res_json,
        "LEGISLATIVE_EXECUTIVE_JSON": exec_json,
        "LEGISLATIVE_CHARTS_JSON": chart_json,
        ** _build_legislative_labels(locale),
    })


def _build_legislative_labels(locale: dict) -> dict:
    return {
        "LEG_FRAMEWORK_EYEBROW": t(locale, "legislative.framework_eyebrow", "Framework"),
        "LEG_FRAMEWORK_TITLE": t(locale, "legislative.framework_title", "Local governance & statutory origins"),
        "LEG_LEGAL_BASIS": t(locale, "legislative.legal_basis", "Legal Basis"),
        "LEG_LEGAL_BASIS_DESC": t(locale, "legislative.legal_basis_desc", ""),
        "LEG_HISTORICAL_ORIGINS": t(locale, "legislative.historical_origins", "Historical Origins"),
        "LEG_MUNICIPAL_CLASS": t(locale, "legislative.municipal_class", "Municipal Class"),
        "LEG_LAND_AREA": t(locale, "legislative.land_area", "Land Area"),
        "LEG_BARANGAYS": t(locale, "legislative.barangays_count", "Barangays"),
        "LEG_ORD_EYEBROW": t(locale, "legislative.ord_eyebrow", "Database"),
        "LEG_ORD_TITLE": t(locale, "legislative.ord_title", "Municipal ordinances"),
        "LEG_ORD_DESC": t(locale, "legislative.ord_desc", ""),
        "LEG_ORD_NO": t(locale, "legislative.ord_no", "Ordinance No."),
        "LEG_ORD_TITLE_COL": t(locale, "legislative.ord_title_col", "Title"),
        "LEG_ORD_DATE": t(locale, "legislative.ord_date", "Date"),
        "LEG_ORD_CATEGORY": t(locale, "legislative.ord_category", "Category"),
        "LEG_ORD_SP_REVIEW": t(locale, "legislative.ord_sp_review", "SP Review"),
        "LEG_ORD_STATUS": t(locale, "legislative.ord_status", "Status"),
        "LEG_ORD_SOURCE": t(locale, "legislative.ord_source", "Source"),
        "LEG_RES_EYEBROW": t(locale, "legislative.res_eyebrow", "Resolutions"),
        "LEG_RES_TITLE": t(locale, "legislative.res_title", "Resolutions & investment plans"),
        "LEG_RES_DESC": t(locale, "legislative.res_desc", ""),
        "LEG_RES_NO": t(locale, "legislative.res_no", "Resolution No."),
        "LEG_RES_TITLE_COL": t(locale, "legislative.res_title_col", "Title"),
        "LEG_RES_DATE": t(locale, "legislative.res_date", "Date Approved"),
        "LEG_RES_FISCAL": t(locale, "legislative.res_fiscal", "Fiscal Impact"),
        "LEG_RES_SOURCE": t(locale, "legislative.res_source", "Source"),
        "LEG_EXEC_EYEBROW": t(locale, "legislative.exec_eyebrow", "Executive"),
        "LEG_EXEC_TITLE": t(locale, "legislative.exec_title", "Executive issuances"),
        "LEG_EXEC_DESC": t(locale, "legislative.exec_desc", ""),
        "LEG_EXEC_NAME": t(locale, "legislative.exec_name", "Title"),
        "LEG_EXEC_DATE": t(locale, "legislative.exec_date", "Date"),
        "LEG_EXEC_AUTHORITY": t(locale, "legislative.exec_authority", "Authority"),
        "LEG_EXEC_DESC_COL": t(locale, "legislative.exec_desc_col", "Description"),
        "LEG_BUDGET_TITLE": t(locale, "legislative.budget_title", "Municipal budget"),
        "LEG_BUDGET_DESC": t(locale, "legislative.budget_desc", ""),
        "LEG_TRENDS_TITLE": t(locale, "legislative.trends_title", "Legislative trends"),
        "LEG_TRENDS_DESC": t(locale, "legislative.trends_desc", ""),
        "LEG_SEARCH_PLACEHOLDER": t(locale, "legislative.search_placeholder", "Search all tables..."),
        "LEG_SEARCH_LABEL": t(locale, "legislative.search_label", "Search legislative documents"),
        "LEG_CSV_BTN": t(locale, "legislative.csv_btn", "CSV"),
        "LEG_PAGE_INFO": t(locale, "legislative.page_info", "Showing 1-20 of 0"),
        "LEG_PREV": t(locale, "legislative.prev", "Prev"),
        "LEG_NEXT": t(locale, "legislative.next", "Next"),
        "LEG_FISCAL_EYEBROW": t(locale, "legislative.fiscal_eyebrow", "Fiscal"),
        "LEG_ORD_CATEGORIES": t(locale, "legislative.ord_categories", "Ordinance Categories"),
        "LEG_ORD_CATEGORIES_DESC": t(locale, "legislative.ord_categories_desc", "Breakdown by category"),
        "LEG_REVENUE_VS_EXPENDITURE": t(locale, "legislative.revenue_vs_expenditure", "Revenue vs Expenditure"),
        "LEG_BLGF_DATA": t(locale, "legislative.blgf_data", "BLGF fiscal data 2020–2025"),
        "LEG_BUDGET_GROWTH": t(locale, "legislative.budget_growth", "Budget Growth"),
        "LEG_BUDGET_GROWTH_DESC": t(locale, "legislative.budget_growth_desc", "Annual budget growth 2020–2026"),
        "LEG_VIEW_FISCAL": t(locale, "legislative.view_fiscal", "View detailed fiscal data"),
        "LEG_ANALYSIS_EYEBROW": t(locale, "legislative.analysis_eyebrow", "Analysis"),
        "LEG_PIPELINE_EYEBROW": t(locale, "legislative.pipeline_eyebrow", "Pipeline"),
        "LEG_PIPELINE_TITLE": t(locale, "legislative.pipeline_title", "Legislative pipeline"),
        "LEG_PIPELINE_DESC": t(locale, "legislative.pipeline_desc", "The legislative pipeline under the Local Government Code of 1991."),
        "LEG_ORDINANCE": t(locale, "legislative.ordinance", "Ordinance"),
        "LEG_ORDINANCE_DESC": t(locale, "legislative.ordinance_desc", ""),
        "LEG_RESOLUTION": t(locale, "legislative.resolution", "Resolution"),
        "LEG_RESOLUTION_DESC": t(locale, "legislative.resolution_desc", ""),
        "LEG_KEY_DISTINCTION": t(locale, "legislative.key_distinction", "Key Distinction"),
        "LEG_ORD_VS_RESOLUTION": t(locale, "legislative.ord_vs_resolution", "Ordinance vs. Resolution"),
        "LEG_ORD_VS_RESOLUTION_DESC": t(locale, "legislative.ord_vs_resolution_desc", "Under the Local Government Code of 1991, the Sangguniang Bayan enacts two types of legislative measures:"),
    }


def _build_ordinance_rows(ordinances: list, category_labels: dict) -> list:
    rows = []
    for o in ordinances:
        cat_label = category_labels.get(o.get("category", ""), o.get("category", "").title())
        status_class = _get_status_class(o.get("status", ""))
        status_text = o.get("status", "").title()
        source = _build_source_link(o.get("source_url", ""))
        cat_class = html.escape(o.get("category", ""))
        rows.append(
            f'<tr>'
            f'<td>{html.escape(o.get("number", ""))}</td>'
            f'<td>{html.escape(o.get("title", ""))}</td>'
            f'<td>{html.escape(o.get("date_enacted", ""))}</td>'
            f'<td><span class="category-pill category-{cat_class}">{html.escape(cat_label)}</span></td>'
            f'<td>{html.escape(o.get("sp_review", ""))}</td>'
            f'<td><span class="pill {status_class}">{status_text}</span></td>'
            f'<td>{source}</td>'
            f'</tr>'
        )
    return rows


def _build_resolution_rows(resolutions: list) -> list:
    rows = []
    for r in resolutions:
        fiscal = _format_fiscal_value(r.get("fiscal_value"), decimals=2)
        res_source = _build_source_link(r.get("source_url", ""))
        rows.append(
            f'<tr>'
            f'<td>{html.escape(r.get("number", ""))}</td>'
            f'<td>{html.escape(r.get("title", ""))}</td>'
            f'<td>{html.escape(r.get("date_approved", ""))}</td>'
            f'<td>{fiscal}</td>'
            f'<td>{res_source}</td>'
            f'</tr>'
        )
    return rows


def _build_executive_rows(issuances: list) -> list:
    rows = []
    for e in issuances:
        date = html.escape(e.get("date", "")) if e.get("date") else "—"
        rows.append(
            f'<tr>'
            f'<td>{html.escape(e.get("title", ""))}</td>'
            f'<td>{date}</td>'
            f'<td>{html.escape(e.get("authority", ""))}</td>'
            f'<td>{html.escape(e.get("description", ""))}</td>'
            f'</tr>'
        )
    return rows


def _build_fiscal_cards(fiscal_data: list) -> list:
    cards = []
    for fc in fiscal_data:
        amount = fc.get("amount", 0)
        if amount >= 1_000_000:
            amount_str = f'₱{amount / 1_000_000:,.1f}M'
        else:
            amount_str = f'₱{amount:,.0f}'
        type_label = fc.get("type", "").replace("_", " ").title()
        cards.append(
            f'<div class="card fiscal-card">'
            f'<h3>{html.escape(type_label)}</h3>'
            f'<p class="figure">{amount_str}</p>'
            f'<p class="source-label">{html.escape(fc.get("period", ""))}</p>'
            f'<p>{html.escape(fc.get("scope", ""))}</p>'
            f'<span class="source-label">{html.escape(fc.get("legislative_basis", ""))}</span>'
            f'</div>'
        )
    return cards


def _build_trend_cards(trends: list) -> list:
    cards = []
    for i, tr in enumerate(trends, 1):
        bullets_html = "".join(f'<li>{html.escape(b)}</li>' for b in tr.get("bullets", []))
        ordinances = tr.get("ordinances", [])
        refs = " · ".join(html.escape(o) for o in ordinances)
        cards.append(
            f'<div class="trend-step">'
            f'<div class="n">{i}</div>'
            f'<div class="trend-body">'
            f'<h3>{html.escape(tr.get("title", ""))}</h3>'
            f'<ul class="trend-bullets">{bullets_html}</ul>'
            f'<span class="trend-refs">{refs}</span>'
            f'</div>'
            f'</div>'
        )
    return cards


def _build_process_steps(process_list: list) -> list:
    steps = []
    total = len(process_list)
    for s in process_list:
        step_num = s.get("step", 1)
        final_class = ' final' if step_num == total else ''
        steps.append(
            f'<div class="step{final_class}">'
            f'<div class="n">{step_num}</div>'
            f'<h3>{html.escape(s.get("title", ""))}</h3>'
            f'<p>{html.escape(s.get("description", ""))}</p>'
            f'</div>'
        )
    return steps


def _build_chart_data(data: dict) -> dict:
    ordinances = data.get("ordinances", [])
    cat_counts = dict(Counter(o.get("category", "other") for o in ordinances))
    blgf = data.get("blgf_fiscal_data", [])
    annual_budgets = [b for b in data.get("fiscal", []) if b.get("type") == "annual_budget"]
    budget = []
    for b in annual_budgets:
        year = None
        period = b.get("period", "")
        m = re.search(r"20\d{2}", period)
        if m:
            year = int(m.group())
        budget.append({"year": year, "amount": b.get("amount")})
    return {"categories": cat_counts, "blgf": blgf, "budget": budget}


def _format_fiscal_value(value, decimals=0) -> str:
    if value is None:
        return "—"
    try:
        if decimals == 0:
            return f'₱{int(value):,}'
        return f'₱{float(value):,.{decimals}f}'
    except (ValueError, TypeError):
        return "—"


def _get_status_class(status: str) -> str:
    if status == "enacted":
        return "pill-enacted"
    if status == "pending":
        return "pill-pending"
    return "pill"


def _build_source_link(url: str) -> str:
    if url and url.startswith(("http://", "https://")):
        return f'<a href="{html.escape(url)}" target="_blank" rel="noopener">Source &rarr;</a>'
    return "—"
