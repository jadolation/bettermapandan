"""FDP disclosures generator — renders DILG Full Disclosure Policy filings."""
import html
import json
import re

from _build.config import SRC_DATA
from _build.locales import t


def _build_fdp_labels(locale: dict) -> dict:
    return {
        "FDP_EYEBROW": t(locale, "transparency.fdp_eyebrow", "Full Disclosure"),
        "FDP_TITLE": t(locale, "transparency.fdp_title", "DILG Disclosure Filings"),
        "FDP_LEDE": t(locale, "transparency.fdp_lede", ""),
        "FDP_SOURCE": t(locale, "transparency.fdp_source", ""),
        "FDP_LATEST": t(locale, "transparency.fdp_latest", "Latest filing"),
        "FDP_OLDER": t(locale, "transparency.fdp_older", "Older filings"),
        "FDP_NIL": t(locale, "transparency.fdp_nil", "Nil filing — nothing to report for this period."),
        "FDP_UNDATED": t(locale, "transparency.fdp_undated", "Undated snapshot"),
        "FDP_APP_TITLE": t(locale, "transparency.fdp_app_title", "Annual Procurement Plan"),
        "FDP_GAD_TITLE": t(locale, "transparency.fdp_gad_title", "Gender and Development Report"),
        "FDP_ARCHIVE_TITLE": t(locale, "transparency.fdp_archive_title", "Browse older filings"),
        "FDP_COLLECTIONS_TITLE": t(locale, "transparency.fdp_collections_title", "Themed collections"),
    }


def _peso(value) -> str:
    if value is None:
        return "&mdash;"
    text = f"{value:,.2f}"
    if text.endswith(".00"):
        text = text[:-3]
    return f"&#8369;{text}"


def _pct(value) -> str:
    if value is None:
        return "&mdash;"
    if value <= 1:
        return f"{value * 100:.1f}%"
    return f"{value:.1f}%"


def _esc(text) -> str:
    return html.escape(str(text) if text is not None else "")


def _period_label(period: str, undated_label: str) -> str:
    if not period or period == "undated":
        return undated_label
    match = period.split("-")
    if len(match) == 2 and match[1].startswith("Q"):
        return f"Q{match[1][1:]} {match[0]}"
    return period


def _find_row(rows: list, *prefixes):
    for row in rows:
        label = str(row.get("label", "")).lower()
        for prefix in prefixes:
            if label.startswith(prefix.lower()):
                return row
    return None


def _sre_cards(sre: dict) -> tuple:
    income = _find_row(sre.get("rows", []), "total current operating")
    nta = _find_row(sre.get("rows", []), "national tax allotm")
    local = _find_row(sre.get("rows", []), "local sources")
    return income, nta, local


def _metric_cards(cards: list) -> str:
    out = ['<div class="grid grid-4 stack-gap-lg mt-24">']
    for value, label in cards:
        out.append(
            '<div class="card"><p class="figure text-lg">{}</p>'
            '<p class="note-inline">{}</p></div>'.format(value, _esc(label))
        )
    out.append("</div>")
    return "\n".join(out)


def _money_table(headers: list, rows: list) -> str:
    out = ['<div class="table-wrap"><table>']
    out.append("<thead><tr>" + "".join(f"<th scope='col'>{h}</th>" for h in headers) + "</tr></thead>")
    out.append("<tbody>")
    for cells in rows:
        out.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def _sortable_money_table(table_id, search_id, headers, rows, search_placeholder="", data_columns=None):
    if data_columns is None:
        data_columns = [str(i) for i in range(len(headers))]
    out = ['<input type="search" id="' + search_id + '" placeholder="' + _esc(search_placeholder) + '" class="form-input mb-24">']
    out.append('<div class="table-wrap"><table aria-label="" id="' + table_id + '">')
    out.append("<thead><tr>" + "".join(
        f"<th scope='col' class='sortable' data-column='{_esc(col)}'>{_esc(h)} <span class='sort-indicator'></span></th>"
        for h, col in zip(headers, data_columns)
    ) + "</tr></thead>")
    out.append("<tbody>")
    for cells in rows:
        out.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def _dialog(dialog_id: str, title: str, body_html: str, close_label: str) -> str:
    """Accessible modal wrapper for full FDP tables."""
    return (
        f'<dialog class="fdp-dialog" id="{dialog_id}" aria-label="{title}">'
        f'<div class="fdp-dialog-head"><strong>{title}</strong>'
        f'<button type="button" class="btn btn-outline btn-sm" data-close>{close_label}</button></div>'
        f"{body_html}"
        "</dialog>"
    )


def _render_period_cards(period: str, data: dict, labels: dict) -> str:
    """Visible metric cards for one quarterly filing period."""
    parts = []
    title = _period_label(period, labels["FDP_UNDATED"])
    sre = next((r for r in data.get("sre", []) if r.get("period") == period), None)
    sef = next((r for r in data.get("sef", []) if r.get("period") == period), None)
    ldrrmf = next((r for r in data.get("ldrrmf", []) if r.get("period") == period), None)
    dev = [r for r in data.get("dev_fund", []) if r.get("period") == period]
    bids = next((r for r in data.get("bids", []) if r.get("period") == period), None)

    cards = []
    if sre:
        income, _, _ = _sre_cards(sre)
        if income:
            cards.append((_peso(income.get("general_fund")), f"Total receipts, General Fund ({title})"))
    if sef and sef.get("balance") is not None:
        cards.append((_peso(sef["balance"]), f"SEF balance ({title})"))
    if ldrrmf and ldrrmf.get("totals", {}).get("unutilized") is not None:
        cards.append((_peso(ldrrmf["totals"]["unutilized"]), f"LDRRMF unutilized ({title})"))
    n_bids = 0
    if bids:
        n_bids = len(bids.get("civil_works", [])) + len(bids.get("goods", []))
        cards.append((str(n_bids), f"Bids awarded ({title})"))
    n_proj = sum(len(d.get("projects", [])) for d in dev)
    if n_proj:
        cards.append((str(n_proj), f"Development fund projects ({title})"))
    if cards:
        parts.append(_metric_cards(cards[:4]))
    return "\n".join(parts)


def _render_period_tables(period: str, data: dict, labels: dict) -> str:
    """Full tables for one quarterly filing period (lives inside a dialog)."""
    parts = []
    title = _period_label(period, labels["FDP_UNDATED"])
    slug = re.sub(r"[^a-z0-9]+", "-", period.lower()).strip("-") or "undated"
    sre = next((r for r in data.get("sre", []) if r.get("period") == period), None)
    sef = next((r for r in data.get("sef", []) if r.get("period") == period), None)
    ldrrmf = next((r for r in data.get("ldrrmf", []) if r.get("period") == period), None)
    cash = next((r for r in data.get("cash_flows", []) if r.get("period") == period), None)
    adv = next((r for r in data.get("cash_advances", []) if r.get("period") == period), None)
    trust = next((r for r in data.get("trust_fund", []) if r.get("period") == period), None)
    lgsf = next((r for r in data.get("lgsf", []) if r.get("period") == period), None)
    dev = [r for r in data.get("dev_fund", []) if r.get("period") == period]
    bids = next((r for r in data.get("bids", []) if r.get("period") == period), None)

    if sre:
        tl_any = any(r.get("trust_liability") for r in sre["rows"])
        headers = ["Particulars", "Target", "General Fund", "SEF", "Trust Fund"] + (["Trust Liability"] if tl_any else [])
        data_cols = ["particulars", "target", "general_fund", "sef", "trust_fund"] + (["trust_liability"] if tl_any else [])
        rows = []
        for r in sre["rows"]:
            cells = [f"<strong>{_esc(r['label'])}</strong>" if r["label"].isupper() else _esc(r["label"]),
                     _peso(r.get("target")), _peso(r.get("general_fund")),
                     _peso(r.get("sef")), _peso(r.get("trust_fund"))]
            if tl_any:
                cells.append(_peso(r.get("trust_liability")))
            rows.append(cells)
        parts.append(f"<h3 class='mt-24'>Statement of Receipts &amp; Expenditures ({_esc(title)})</h3>")
        parts.append(_sortable_money_table("sre-table-" + slug, "sre-search-" + slug, headers, rows, "Search SRE...", data_cols))

    if sef:
        parts.append(f"<h3 class='mt-24'>Special Education Fund ({_esc(title)})</h3>")
        parts.append(_metric_cards([(_peso(sef.get("receipt")), "SEF receipts"),
                                    (_peso(sef.get("subtotal")), "Disbursed"),
                                    (_peso(sef.get("balance")), "Balance")]))
        if sef.get("items"):
            parts.append(_sortable_money_table("sef-table-" + slug, "sef-search-" + slug,
                                               ["Item", "Amount"],
                                               [[_esc(i["label"]), _peso(i["amount"])] for i in sef["items"]],
                                               "Search SEF items...",
                                               ["item", "amount"]))

    if ldrrmf:
        totals = ldrrmf.get("totals", {})
        parts.append(f"<h3 class='mt-24'>Disaster Fund Utilization ({_esc(title)})</h3>")
        parts.append(_metric_cards([(_peso(totals.get("available")), "Available"),
                                    (_peso(totals.get("utilization")), "Utilized"),
                                    (_peso(totals.get("unutilized")), "Unutilized")]))
        items = [u for u in ldrrmf.get("utilization", [])
                 if (u.get("total") or 0) != 0 or (u.get("qrf") or 0) != 0]
        if items:
            parts.append(_sortable_money_table("ldrrmf-table-" + slug, "ldrrmf-search-" + slug,
                                               ["Utilization", "QRF", "Total"],
                                               [[_esc(u["label"]), _peso(u.get("qrf")), _peso(u.get("total"))] for u in items],
                                               "Search disaster fund...",
                                               ["utilization", "qrf", "total"]))

    if dev:
        dev_idx = [0]
        for rec in dev:
            if not rec.get("projects"):
                continue
            dev_idx[0] += 1
            parts.append(f"<h3 class='mt-24'>20% Development Fund Projects ({_esc(title)})</h3>")
            rows = [[_esc(p["project"]), _esc(p["location"]), _peso(p.get("cost")),
                     _pct(p.get("pct")), _peso(p.get("incurred"))] for p in rec["projects"]]
            totals = rec.get("totals") or {}
            if totals.get("cost") is not None:
                rows.append(["<strong>Total</strong>", "", f"<strong>{_peso(totals.get('cost'))}</strong>",
                             f"<strong>{_pct(totals.get('pct'))}</strong>",
                             f"<strong>{_peso(totals.get('incurred'))}</strong>"])
            parts.append(_sortable_money_table("devfund-table-" + slug + "-" + str(dev_idx[0]),
                                               "devfund-search-" + slug + "-" + str(dev_idx[0]),
                                               ["Project", "Location", "Cost", "Completion", "Incurred"], rows,
                                               "Search development fund...",
                                               ["project", "location", "cost", "completion", "incurred"]))

    if bids:
        parts.append(f"<h3 class='mt-24'>Bids Awarded ({_esc(title)})</h3>")
        bid_idx = [0]
        bid_parts = []
        for kind, label in (("civil_works", "Civil Works"), ("goods", "Goods"), ("consulting", "Consulting")):
            items = bids.get(kind, [])
            if items:
                bid_idx[0] += 1
                bid_parts.append(_sortable_money_table("bids-table-" + slug + "-" + str(bid_idx[0]),
                                                       "bids-search-" + slug + "-" + str(bid_idx[0]),
                                                       [label, "ABC", "Winning Bidder", "Bid Amount"],
                                                       [[_esc(b.get("project") or b.get("ref", "")), _peso(b.get("abc")),
                                                         _esc(b.get("bidder")), _peso(b.get("bid_amount"))] for b in items],
                                                       "Search bids...",
                                                       ["project", "abc", "bidder", "bid_amount"]))
            else:
                bid_parts.append(f"<p class='note-inline'>{label}: {labels['FDP_NIL']}</p>")
        parts.append("<div class='mt-24'></div>".join(bid_parts))

    if adv:
        parts.append(f"<h3 class='mt-24'>Unliquidated Cash Advances ({_esc(title)})</h3>")
        if adv.get("status") == "nil" or not adv.get("debtors"):
            parts.append(f"<p class='note-inline'>{labels['FDP_NIL']}</p>")
        else:
            parts.append(_money_table(
                ["Debtor", "Balance", "Granted", "Purpose"],
                [[_esc(d["debtor"]), _peso(d.get("balance")),
                  _esc(d.get("date_granted")), _esc(d.get("purpose"))] for d in adv["debtors"]]))

    if trust:
        parts.append(f"<h3 class='mt-24'>Trust Fund Programs ({_esc(title)})</h3>")
        if trust.get("status") == "nil" or not trust.get("items"):
            parts.append(f"<p class='note-inline'>{labels['FDP_NIL']}</p>")
        else:
            parts.append(_money_table(
                ["Program", "Location", "Cost", "Completion"],
                [[_esc(t["program"]), _esc(t["location"]), _peso(t.get("cost")),
                  _esc(t.get("completion"))] for t in trust["items"]]))
    if lgsf and (lgsf.get("status") == "nil" or not lgsf.get("items")):
        parts.append(f"<h3 class='mt-24'>Local Government Support Fund ({_esc(title)})</h3>")
        parts.append(f"<p class='note-inline'>{labels['FDP_NIL']}</p>")

    if cash and cash.get("key"):
        key = cash["key"]
        parts.append(f"<h3 class='mt-24'>Cash Flows ({_esc(title)})</h3>")
        parts.append(_metric_cards([(_peso(key.get("net_operating")), "Net operating cash"),
                                    (_peso(key.get("net_investing")), "Net investing cash"),
                                    (_peso(key.get("net_financing")), "Net financing cash"),
                                    (_peso(key.get("ending")), "Cash at end of period")]))
    return "\n".join(parts)


def _themed_dialog(slug: str, heading: str, count_line: str, body_html: str, labels: dict) -> str:
    """One themed dialog group for standalone FDP tables, rendered as a card."""
    dialog_id = f"fdp-dialog-{slug}"
    return "\n".join([
        f"<div class='card fdp-archive-card' id='fdp-collection-{slug}' data-nav-label='{_esc(heading)}'>",
        f"<h3>{heading}</h3>",
        f"<p class='note-inline'>{count_line}</p>",
        f'<button type="button" class="btn btn-outline btn-sm" data-fdp-dialog="{dialog_id}">'
        f'{labels["DASH_VIEW_TABLE"]}</button>',
        _dialog(dialog_id, heading, body_html, labels["DASH_CLOSE"]),
        "</div>",
    ])


def _render_standalone(data: dict, labels: dict) -> str:
    parts = []
    budgets = sorted(data.get("budget", []), key=lambda r: str(r.get("period", "")), reverse=True)
    if budgets:
        inner = []
        for rec in budgets:
            inner.append("<h3>Annual Budget by Office ({})</h3>".format(_esc(_period_label(rec["period"], labels["FDP_UNDATED"]))))
            inner.append(_money_table(
                ["Office", "Personnel", "MOOE", "Capital Outlay", "Proposed Total"],
                [[_esc(o["office"]), _peso(o.get("ps")), _peso(o.get("mooe")),
                  _peso(o.get("co")), _peso(o.get("proposed"))] for o in rec["offices"]]))
        n_off = sum(len(r["offices"]) for r in budgets)
        parts.append(_themed_dialog("budget", "Annual Budget by Office",
                                    f"{len(budgets)} filing(s) · {n_off} office rows",
                                    "\n".join(inner), labels))

    loans = {}
    for loan in data.get("indebtedness", []):
        key = loan.get("loan", "")
        if key not in loans or str(loan.get("report_date", "")) > str(loans[key].get("report_date", "")):
            loans[key] = loan
    if loans:
        rows = []
        for name in sorted(loans):
            items = loans[name].get("items", {})
            amount = next((v for k, v in items.items() if "amount approved" in k.lower()), "")
            purpose = next((v for k, v in items.items() if "purpose" in k.lower()), "")
            rows.append([_esc(name), _esc(purpose), _esc(amount),
                         _esc(loans[name].get("report_date", ""))])
        parts.append(_themed_dialog("debt", "Indebtedness",
                                    f"{len(loans)} loan facilities (latest statements)",
                                    _money_table(["Loan", "Purpose", "Approved", "Reported"], rows), labels))

    if data.get("manpower"):
        inner = []
        for mp in data.get("manpower", []):
            inner.append("<h3>Manpower Complement ({})</h3>".format(
                _esc(_period_label(mp.get("period", ""), labels["FDP_UNDATED"]))))
            if mp.get("note"):
                inner.append(f"<p class='note-inline'>{_esc(mp['note'])}</p>")
            rows = [[_esc(i["class"]), _esc(i.get("count")), _peso(i.get("amount"))] for i in mp.get("items", [])]
            total = mp.get("total") or {}
            if total.get("count") is not None:
                rows.append(["<strong>Total</strong>", f"<strong>{_esc(total.get('count'))}</strong>",
                             f"<strong>{_peso(total.get('amount'))}</strong>"])
            inner.append(_money_table(["Appointment", "Count", "Salaries"], rows))
        parts.append(_themed_dialog("workforce", "Workforce history",
                                    f"{len(data.get('manpower', []))} snapshots",
                                    "\n".join(inner), labels))

    proc_inner = []
    for spp in data.get("spp", []):
        with_items = [o for o in spp.get("offices", []) if o.get("items")]
        if with_items:
            proc_inner.append("<h3>Supplemental Procurement ({})</h3>".format(
                _esc(_period_label(spp.get("period", ""), labels["FDP_UNDATED"]))))
            for office in with_items:
                proc_inner.append(_money_table(
                    [office["office"], "End User", "Mode", "Amount"],
                    [[_esc(i["project"]), _esc(i.get("end_user")),
                      _esc(i.get("mode")), _peso(i.get("amount"))] for i in office["items"]]))
        if spp.get("summary"):
            proc_inner.append("<h3>Supplemental Procurement Summary ({})</h3>".format(
                _esc(_period_label(spp.get("period", ""), labels["FDP_UNDATED"]))))
            proc_inner.append(_money_table(
                ["Office", "Head", "Total Cost"],
                [[_esc(s.get("office", "")), _esc(s.get("head", "")),
                  _peso(s.get("total"))] for s in spp["summary"]]))
    for app in data.get("app", []):
        if app.get("form") == "app_summary":
            if app.get("summary"):
                proc_inner.append("<h3>{} ({})</h3>".format(
                    labels["FDP_APP_TITLE"],
                    _esc(_period_label(app.get("period", ""), labels["FDP_UNDATED"]))))
                proc_inner.append(_money_table(
                    ["Office", "Head", "Total Cost"],
                    [[_esc(s.get("office", "")), _esc(s.get("head", "")),
                      _peso(s.get("total"))] for s in app["summary"]]))
            continue
        if not app.get("items"):
            continue
        proc_inner.append("<h3>{}: {} ({})</h3>".format(
            labels["FDP_APP_TITLE"], _esc(app.get("office", "")),
            _esc(_period_label(app.get("period", ""), labels["FDP_UNDATED"]))))
        proc_inner.append(_money_table(
            ["Item", "End User", "Mode", "Total"],
            [[_esc(i["project"]), _esc(i.get("end_user")),
              _esc(i.get("mode")), _peso(i.get("total"))] for i in app["items"]]))
    if proc_inner:
        n_tables = sum(1 for _ in re.finditer(r"<table", "\n".join(proc_inner)))
        parts.append(_themed_dialog("proc-plans", "Procurement Plans",
                                    f"{n_tables} tables (supplemental + annual plans)",
                                    "\n".join(proc_inner), labels))

    if data.get("gad"):
        gad_inner = []
        for gad in data.get("gad", []):
            gad_inner.append("<h3>{} ({})</h3>".format(
                labels["FDP_GAD_TITLE"],
                _esc(_period_label(gad.get("period", ""), labels["FDP_UNDATED"]))))
            totals = gad.get("totals", {})
            if totals:
                gad_inner.append(_metric_cards([(_peso(totals.get("lgu_budget")), "Total LGU budget"),
                                                (_peso(totals.get("gad_budget")), "GAD budget")]))
            if gad.get("entries"):
                gad_inner.append(_money_table(
                    ["Issue", "Program", "Result", "Budget"],
                    [[_esc(e["issue"]), _esc(e.get("program")),
                      _esc(e.get("result")), _peso(e.get("budget"))] for e in gad["entries"]]))
        parts.append(_themed_dialog("gad", "Gender and Development",
                                    f"{len(data.get('gad', []))} report(s)",
                                    "\n".join(gad_inner), labels))

    fund_inner = []
    for fund in data.get("fund_matrix", []):
        fund_inner.append("<h3>{} ({})</h3>".format(
            _esc(fund.get("fund", "")), _esc(_period_label(fund.get("period", ""), labels["FDP_UNDATED"]))))
        fund_inner.append(_money_table(
            ["Office", "Personnel", "MOOE", "Capital", "Non-Office", "Total"],
            [[_esc(o["office"]), _peso(o.get("ps")), _peso(o.get("mooe")),
              _peso(o.get("co")), _peso(o.get("non_office")), _peso(o.get("total"))]
             for o in fund.get("offices", [])]))
    for spa in data.get("spa", []):
        fund_inner.append("<h3>{} ({})</h3>".format(
            _esc(spa.get("fund", "")), _esc(_period_label(spa.get("period", ""), labels["FDP_UNDATED"]))))
        fund_inner.append(_money_table(
            ["Project", "Past", "Current", "Proposed"],
            [[_esc(i["project"]), _peso(i.get("past")),
              _peso(i.get("current")), _peso(i.get("proposed"))] for i in spa.get("items", [])]))
    if fund_inner:
        parts.append(_themed_dialog("funds", "Fund Matrices & Special Appropriations",
                                    "General Fund, Economic Enterprise, development, non-office & calamity funds",
                                    "\n".join(fund_inner), labels))
    return "\n".join(parts)



def _quarter_figures(period: str, data: dict):
    """Three headline figures for a compact quarter row."""
    sre = next((r for r in data.get("sre", []) if r.get("period") == period), None)
    sef = next((r for r in data.get("sef", []) if r.get("period") == period), None)
    ldrrmf = next((r for r in data.get("ldrrmf", []) if r.get("period") == period), None)
    receipts = None
    if sre:
        income, _, _ = _sre_cards(sre)
        receipts = (income or {}).get("general_fund")
    return (receipts,
            (sef or {}).get("balance"),
            ((ldrrmf or {}).get("totals", {}) or {}).get("unutilized"))


def _quarter_dialog(period: str, data: dict, labels: dict) -> str:
    """Full cards + tables for one quarter, wrapped in a modal dialog."""
    slug = re.sub(r"[^a-z0-9]+", "-", period.lower()).strip("-") or "undated"
    dialog_id = f"fdp-dialog-{slug}"
    body = "\n".join([_render_period_cards(period, data, labels),
                       _render_period_tables(period, data, labels)])
    if not body.strip():
        return ""
    return (
        f'<button type="button" class="btn btn-outline btn-sm" data-fdp-dialog="{dialog_id}">'
        f'{labels["DASH_VIEW_TABLE"]}: {_esc(_period_label(period, labels["FDP_UNDATED"]))}</button>'
        + _dialog(dialog_id, _period_label(period, labels["FDP_UNDATED"]),
                  body, labels["DASH_CLOSE"])
    )


def generate_fdp(locale: dict) -> str:
    """Render the FDP disclosures section for the transparency page."""
    path = SRC_DATA / "fdp_disclosures.json"
    if not path.exists():
        return ""
    data = json.loads(path.read_text(encoding="utf-8"))
    labels = {**_build_fdp_labels(locale), **_build_dashboard_labels(locale)}
    retrieved = data.get("meta", {}).get("retrieved", "")

    periods = sorted({r.get("period", "undated")
                      for key in ("sre", "sef", "ldrrmf", "cash_flows", "cash_advances",
                                  "trust_fund", "lgsf", "dev_fund", "bids")
                      for r in data.get(key, []) if r.get("period") and r.get("period") != "undated"},
                     reverse=True)
    out = ['<section class="section" id="fdp-disclosures">', '<div class="wrap">',
           '<div class="section-head">',
           f'<div class="section-eyebrow">{labels["FDP_EYEBROW"]}</div>',
           f'<h2>{labels["FDP_TITLE"]}</h2>',
           f'<p>{labels["FDP_LEDE"]}</p>',
           "</div>"]
    def _period_block(period: str, heading: str) -> list:
        slug = re.sub(r"[^a-z0-9]+", "-", period.lower()).strip("-") or "undated"
        dialog_id = f"fdp-dialog-{slug}"
        block = [heading, _render_period_cards(period, data, labels)]
        tables = _render_period_tables(period, data, labels)
        if tables.strip():
            block.append(f'<button type="button" class="btn btn-outline btn-sm" data-fdp-dialog="{dialog_id}">'
                         f'{labels["DASH_VIEW_TABLE"]}: {_esc(_period_label(period, labels["FDP_UNDATED"]))}</button>')
            block.append(_dialog(dialog_id, _period_label(period, labels["FDP_UNDATED"]),
                                 tables, labels["DASH_CLOSE"]))
        return block

    if periods:
        latest = periods[0]
        out.append(f"<h3 id=\"fdp-latest\">{labels['FDP_LATEST']}: {_esc(_period_label(latest, labels['FDP_UNDATED']))}</h3>")
        out.append('<div class="fdp-latest">')
        out.append(_render_period_cards(latest, data, labels))
        out.append(_render_period_tables(latest, data, labels))
        out.append("</div>")
        by_year = {}
        for period in periods[1:]:
            year = period.split("-")[0] if "-" in period else period
            by_year.setdefault(year, []).append(period)
        out.append(f"<h3 id=\"fdp-archive\">{labels['FDP_ARCHIVE_TITLE']}</h3>")
        out.append('<div class="grid grid-3">')
        for year in sorted(by_year, reverse=True):
            n_q = len(by_year[year])
            out.append("<div class='card fdp-archive-card'"
                       f" id='fdp-archive-{year}' data-nav-label='{year}'>"
                       f"<div class='section-eyebrow'>{year}</div>"
                       f"<p class='note-inline'>{n_q} quarter(s)</p>")
            for period in by_year[year]:
                receipts, sef_bal, ld_unutil = _quarter_figures(period, data)
                out.append(
                    "<div class='quarter-row'><strong>{}</strong>"
                    "<span>Receipts {} · SEF {} · LDRRMF {}</span></div>".format(
                        _esc(_period_label(period, labels["FDP_UNDATED"])),
                        _peso(receipts), _peso(sef_bal), _peso(ld_unutil)))
                out.append(_quarter_dialog(period, data, labels))
            out.append("</div>")
        out.append("</div>")
    standalone = _render_standalone(data, labels)
    if standalone.strip():
        out.append(f"<h3 id=\"fdp-collections\">{labels['FDP_COLLECTIONS_TITLE']}</h3>")
        out.append('<div class="grid grid-3">')
        out.append(standalone)
        out.append("</div>")
    if retrieved:
        out.append(f"<p class='source-label'>{labels['FDP_SOURCE']} DILG Full Disclosure Policy Portal &mdash; retrieved {retrieved}.</p>")
    out.append("</div></section>")
    return "\n".join(out)


def _build_dashboard_labels(locale: dict) -> dict:
    keys = ["eyebrow", "title", "lede", "kpi_receipts", "kpi_expenditures",
            "kpi_sef", "kpi_ldrrmf", "kpi_cash", "kpi_projects", "kpi_bids",
            "rev_title", "exp_title", "trend_title", "funds_title",
            "cash_title", "brgy_title", "bids_title", "view_table", "close",
            "computed", "source", "view_table", "close"]
    return {"DASH_" + k.upper(): t(locale, f"transparency.dash_{k}", "") for k in keys}


def _bar(share: float, label: str) -> str:
    share = max(0.0, min(100.0, share or 0))
    return (
        "<div class='util-bar' role='img' aria-label='{} {:.1f}%'>"
        "<div class='util-fill' style='width:{:.1f}%'></div></div>"
    ).format(_esc(label), share, share)


def generate_fdp_dashboard(locale: dict) -> str:
    """Server-rendered fiscal dashboard: KPI cards, chart shells, bars, tables."""
    from _build.generators.fdp_analytics import generate_fdp_summary
    path = SRC_DATA / "fdp_disclosures.json"
    if not path.exists():
        return ""
    summary = generate_fdp_summary()
    labels = _build_dashboard_labels(locale)
    latest = summary["latest_period"]
    period_label = _period_label(latest, "")
    kpis = summary["kpis"]
    src = f"{labels['DASH_SOURCE']} {period_label}"

    out = ['<section class="section" id="fiscal-dashboard">', '<div class="wrap">',
           '<div class="section-head">',
           f'<div class="section-eyebrow">{labels["DASH_EYEBROW"]}</div>',
           f'<h2>{labels["DASH_TITLE"]}</h2>',
           f'<p>{labels["DASH_LEDE"]}</p>',
           "</div>"]

    kpi_defs = [(_peso(kpis.get("receipts")), labels["DASH_KPI_RECEIPTS"]),
                (_peso(kpis.get("expenditures")), labels["DASH_KPI_EXPENDITURES"]),
                (_peso(kpis.get("sef_balance")), labels["DASH_KPI_SEF"]),
                (_peso(kpis.get("ldrrmf_unutilized")), labels["DASH_KPI_LDRRMF"]),
                (_peso(kpis.get("cash_ending")), labels["DASH_KPI_CASH"]),
                (_esc(kpis.get("projects")), labels["DASH_KPI_PROJECTS"]),
                (_esc(kpis.get("bids")), labels["DASH_KPI_BIDS"])]
    out.append('<div class="grid grid-4 stack-gap-lg">')
    for value, label in kpi_defs:
        out.append(f'<div class="card"><p class="figure text-lg">{value}</p>'
                   f'<p class="note-inline">{label} ({period_label})</p>'
                   f'<span class="source-label">{src}</span></div>')
    out.append("</div>")

    out.append('<div class="grid grid-2">')
    out.append(f'<div class="card"><h3 id="fiscal-revenue">{labels["DASH_REV_TITLE"]} ({period_label})</h3>'
               '<canvas id="chart-fdp-revenue" height="220" role="img"></canvas>'
               f'<p class="note-inline">NTA {summary["revenue"].get("nta_share")}% '
               f'({labels["DASH_COMPUTED"]})</p></div>')
    out.append(f'<div class="card"><h3 id="fiscal-expenditure">{labels["DASH_EXP_TITLE"]} ({period_label})</h3>'
               '<canvas id="chart-fdp-expenditure" height="220" role="img"></canvas></div>')
    out.append("</div>")

    out.append('<div class="card mt-24">'
               f'<h3 id="fiscal-trend">{labels["DASH_TREND_TITLE"]}</h3>'
               '<canvas id="chart-fdp-trend" height="200" role="img"></canvas>'
               f'<p class="note-inline">Quarterly flows derived by differencing year-to-date filings '
               f'({labels["DASH_COMPUTED"]})</p></div>')

    funds = summary["funds"]
    sef_hist = funds["sef"]
    ld_hist = funds["ldrrmf"]
    if sef_hist or ld_hist:
        out.append('<div class="card mt-24">'
                   f'<h3 id="fiscal-funds">{labels["DASH_FUNDS_TITLE"]} ({period_label})</h3>')
        if sef_hist:
            last = sef_hist[-1]
            out.append(f"<p>SEF {_peso(last.get('balance'))}</p>"
                       + _bar(last.get("rate"), "SEF"))
        if ld_hist:
            last = ld_hist[-1]
            out.append(f"<p>LDRRMF {_peso(last.get('unutilized'))}</p>"
                       + _bar(last.get("rate"), "LDRRMF"))
        out.append("</div>")

    cash = summary["cash"]
    if cash:
        out.append('<div class="card mt-24">'
                   f'<h3 id="fiscal-cash">{labels["DASH_CASH_TITLE"]} ({period_label})</h3>'
                   f'<p>Operating {_peso(cash.get("net_operating"))} · '
                   f'Investing {_peso(cash.get("net_investing"))} · '
                   f'Financing {_peso(cash.get("net_financing"))} → '
                   f'Ending {_peso(cash.get("ending"))}</p></div>')

    brgy = summary["barangay"]["dist"]
    if brgy:
        out.append('<div class="card mt-24">'
                   f'<h3 id="fiscal-barangay">{labels["DASH_BRGY_TITLE"]} ({period_label})</h3>'
                   '<canvas id="chart-fdp-barangay" height="240" role="img"></canvas></div>')

    bids_hist = summary["bids"]
    if bids_hist:
        last = bids_hist[-1]
        out.append('<div class="card mt-24">'
                   f'<h3 id="fiscal-bids">{labels["DASH_BIDS_TITLE"]} ({period_label})</h3>'
                   f'<p>ABC {_peso(last.get("abc"))} → awarded {_peso(last.get("awarded"))} · '
                   f'saved {_peso(last.get("savings"))} ({last.get("rate")}%, '
                   f'{labels["DASH_COMPUTED"]})</p></div>')

    out.append(f"<p class='source-label'>{src} &mdash; retrieved {summary.get('retrieved', '')}.</p>")
    out.append("</div></section>")
    return "\n".join(out)
