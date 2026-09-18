"""FDP disclosures generator — renders DILG Full Disclosure Policy filings."""
import html
import json

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
    out = ['<div class="grid grid-4 stack-gap-lg" style="margin-top:20px">']
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


def _render_period(period: str, data: dict, labels: dict, retrieved: str) -> str:
    """Render one quarterly filing period across all form groups."""
    parts = []
    title = _period_label(period, labels["FDP_UNDATED"])
    sre = next((r for r in data.get("sre", []) if r.get("period") == period), None)
    sef = next((r for r in data.get("sef", []) if r.get("period") == period), None)
    ldrrmf = next((r for r in data.get("ldrrmf", []) if r.get("period") == period), None)
    cash = next((r for r in data.get("cash_flows", []) if r.get("period") == period), None)
    adv = next((r for r in data.get("cash_advances", []) if r.get("period") == period), None)
    trust = next((r for r in data.get("trust_fund", []) if r.get("period") == period), None)
    lgsf = next((r for r in data.get("lgsf", []) if r.get("period") == period), None)
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

    if sre:
        tl_any = any(r.get("trust_liability") for r in sre["rows"])
        headers = ["Particulars", "Target", "General Fund", "SEF", "Trust Fund"] + (["Trust Liability"] if tl_any else [])
        rows = []
        for r in sre["rows"]:
            cells = [f"<strong>{_esc(r['label'])}</strong>" if r["label"].isupper() else _esc(r["label"]),
                     _peso(r.get("target")), _peso(r.get("general_fund")),
                     _peso(r.get("sef")), _peso(r.get("trust_fund"))]
            if tl_any:
                cells.append(_peso(r.get("trust_liability")))
            rows.append(cells)
        parts.append(f"<h3>Statement of Receipts &amp; Expenditures ({_esc(title)})</h3>")
        parts.append(_money_table(headers, rows))

    if sef:
        parts.append(f"<h3>Special Education Fund ({_esc(title)})</h3>")
        parts.append(_metric_cards([(_peso(sef.get("receipt")), "SEF receipts"),
                                    (_peso(sef.get("subtotal")), "Disbursed"),
                                    (_peso(sef.get("balance")), "Balance")]))
        if sef.get("items"):
            parts.append(_money_table(["Item", "Amount"],
                                       [[_esc(i["label"]), _peso(i["amount"])] for i in sef["items"]]))

    if ldrrmf:
        totals = ldrrmf.get("totals", {})
        parts.append(f"<h3>Disaster Fund Utilization ({_esc(title)})</h3>")
        parts.append(_metric_cards([(_peso(totals.get("available")), "Available"),
                                    (_peso(totals.get("utilization")), "Utilized"),
                                    (_peso(totals.get("unutilized")), "Unutilized")]))
        items = [u for u in ldrrmf.get("utilization", [])
                 if (u.get("total") or 0) != 0 or (u.get("qrf") or 0) != 0]
        if items:
            parts.append(_money_table(["Utilization", "QRF", "Total"],
                                       [[_esc(u["label"]), _peso(u.get("qrf")), _peso(u.get("total"))] for u in items]))

    if dev:
        for rec in dev:
            if not rec.get("projects"):
                continue
            parts.append(f"<h3>20% Development Fund Projects ({_esc(title)})</h3>")
            parts.append(_money_table(
                ["Project", "Location", "Cost", "Status", "Completion"],
                [[_esc(p["project"]), _esc(p["location"]), _peso(p.get("cost")),
                  _esc(p.get("status")), _pct(p.get("pct"))] for p in rec["projects"]]))

    if bids:
        parts.append(f"<h3>Bids Awarded ({_esc(title)})</h3>")
        for kind, label in (("civil_works", "Civil Works"), ("goods", "Goods"), ("consulting", "Consulting")):
            items = bids.get(kind, [])
            if items:
                parts.append(_money_table(
                    [label, "ABC", "Winning Bidder", "Bid Amount"],
                    [[_esc(b.get("project") or b.get("ref", "")), _peso(b.get("abc")),
                      _esc(b.get("bidder")), _peso(b.get("bid_amount"))] for b in items]))
            else:
                parts.append(f"<p class='note-inline'>{label}: {labels['FDP_NIL']}</p>")

    if adv:
        parts.append(f"<h3>Unliquidated Cash Advances ({_esc(title)})</h3>")
        if adv.get("status") == "nil" or not adv.get("debtors"):
            parts.append(f"<p class='note-inline'>{labels['FDP_NIL']}</p>")
        else:
            parts.append(_money_table(
                ["Debtor", "Balance", "Granted", "Purpose"],
                [[_esc(d["debtor"]), _peso(d.get("balance")),
                  _esc(d.get("date_granted")), _esc(d.get("purpose"))] for d in adv["debtors"]]))

    if trust:
        parts.append(f"<h3>Trust Fund Programs ({_esc(title)})</h3>")
        if trust.get("status") == "nil" or not trust.get("items"):
            parts.append(f"<p class='note-inline'>{labels['FDP_NIL']}</p>")
        else:
            parts.append(_money_table(
                ["Program", "Location", "Cost", "Completion"],
                [[_esc(t["program"]), _esc(t["location"]), _peso(t.get("cost")),
                  _esc(t.get("completion"))] for t in trust["items"]]))
    if lgsf and (lgsf.get("status") == "nil" or not lgsf.get("items")):
        parts.append(f"<h3>Local Government Support Fund ({_esc(title)})</h3>")
        parts.append(f"<p class='note-inline'>{labels['FDP_NIL']}</p>")

    if cash and cash.get("key"):
        key = cash["key"]
        parts.append(f"<h3>Cash Flows ({_esc(title)})</h3>")
        parts.append(_metric_cards([(_peso(key.get("net_operating")), "Net operating cash"),
                                    (_peso(key.get("net_investing")), "Net investing cash"),
                                    (_peso(key.get("net_financing")), "Net financing cash"),
                                    (_peso(key.get("ending")), "Cash at end of period")]))
    return "\n".join(parts)


def _render_standalone(data: dict, labels: dict) -> str:
    parts = []
    budgets = sorted(data.get("budget", []), key=lambda r: str(r.get("period", "")), reverse=True)
    if budgets:
        latest = budgets[0]
        parts.append("<h3>Annual Budget by Office ({})</h3>".format(_esc(_period_label(latest["period"], labels["FDP_UNDATED"]))))
        parts.append(_money_table(
            ["Office", "Personnel", "MOOE", "Capital Outlay", "Proposed Total"],
            [[_esc(o["office"]), _peso(o["ps"]), _peso(o["mooe"]),
              _peso(o["co"]), _peso(o["proposed"])] for o in latest["offices"]]))
        for older in budgets[1:]:
            parts.append("<details><summary>Budget {}</summary>".format(_esc(_period_label(older["period"], labels["FDP_UNDATED"]))))
            parts.append(_money_table(
                ["Office", "Personnel", "MOOE", "Capital Outlay", "Proposed Total"],
                [[_esc(o["office"]), _peso(o["ps"]), _peso(o["mooe"]),
                  _peso(o["co"]), _peso(o["proposed"])] for o in older["offices"]]))
            parts.append("</details>")

    loans = {}
    for loan in data.get("indebtedness", []):
        key = loan.get("loan", "")
        if key not in loans or str(loan.get("report_date", "")) > str(loans[key].get("report_date", "")):
            loans[key] = loan
    if loans:
        parts.append("<h3>Indebtedness (latest statements)</h3>")
        rows = []
        for name in sorted(loans):
            items = loans[name].get("items", {})
            amount = next((v for k, v in items.items() if "amount approved" in k.lower()), "")
            purpose = next((v for k, v in items.items() if "purpose" in k.lower()), "")
            rows.append([_esc(name), _esc(purpose), _esc(amount),
                         _esc(loans[name].get("report_date", ""))])
        parts.append(_money_table(["Loan", "Purpose", "Approved", "Reported"], rows))

    for mp in data.get("manpower", []):
        parts.append("<h3>Manpower Complement ({})</h3>".format(
            _esc(_period_label(mp.get("period", ""), labels["FDP_UNDATED"]))))
        if mp.get("note"):
            parts.append(f"<p class='note-inline'>{_esc(mp['note'])}</p>")
        rows = [[_esc(i["class"]), _esc(i.get("count")), _peso(i.get("amount"))] for i in mp.get("items", [])]
        total = mp.get("total") or {}
        if total.get("count") is not None:
            rows.append(["<strong>Total</strong>", f"<strong>{_esc(total.get('count'))}</strong>",
                         f"<strong>{_peso(total.get('amount'))}</strong>"])
        parts.append(_money_table(["Appointment", "Count", "Salaries"], rows))

    for spp in data.get("spp", []):
        with_items = [o for o in spp.get("offices", []) if o.get("items")]
        if with_items:
            parts.append("<h3>Supplemental Procurement ({})</h3>".format(
                _esc(_period_label(spp.get("period", ""), labels["FDP_UNDATED"]))))
            for office in with_items:
                parts.append(_money_table(
                    [office["office"], "End User", "Mode", "Amount"],
                    [[_esc(i["project"]), _esc(i.get("end_user")),
                      _esc(i.get("mode")), _peso(i.get("amount"))] for i in office["items"]]))
    for app in data.get("app", []):
        if app.get("form") == "app_summary":
            if app.get("summary"):
                parts.append("<h3>{} ({})</h3>".format(
                    labels["FDP_APP_TITLE"],
                    _esc(_period_label(app.get("period", ""), labels["FDP_UNDATED"]))))
                parts.append(_money_table(
                    ["Office", "Head", "Total Cost"],
                    [[_esc(s.get("office", "")), _esc(s.get("head", "")),
                      _peso(s.get("total"))] for s in app["summary"]]))
            continue
        if not app.get("items"):
            continue
        parts.append("<h3>{}: {} ({})</h3>".format(
            labels["FDP_APP_TITLE"], _esc(app.get("office", "")),
            _esc(_period_label(app.get("period", ""), labels["FDP_UNDATED"]))))
        parts.append(_money_table(
            ["Item", "End User", "Mode", "Total"],
            [[_esc(i["project"]), _esc(i.get("end_user")),
              _esc(i.get("mode")), _peso(i.get("total"))] for i in app["items"]]))
    for gad in data.get("gad", []):
        parts.append("<h3>{} ({})</h3>".format(
            labels["FDP_GAD_TITLE"],
            _esc(_period_label(gad.get("period", ""), labels["FDP_UNDATED"]))))
        totals = gad.get("totals", {})
        if totals:
            parts.append(_metric_cards([(_peso(totals.get("lgu_budget")), "Total LGU budget"),
                                        (_peso(totals.get("gad_budget")), "GAD budget")]))
        if gad.get("entries"):
            parts.append(_money_table(
                ["Issue", "Program", "Result", "Budget"],
                [[_esc(e["issue"]), _esc(e.get("program")),
                  _esc(e.get("result")), _peso(e.get("budget"))] for e in gad["entries"]]))
    for fund in data.get("fund_matrix", []):
        parts.append("<h3>{} ({})</h3>".format(
            _esc(fund.get("fund", "")), _esc(_period_label(fund.get("period", ""), labels["FDP_UNDATED"]))))
        parts.append(_money_table(
            ["Office", "Personnel", "MOOE", "Capital", "Non-Office", "Total"],
            [[_esc(o["office"]), _peso(o.get("ps")), _peso(o.get("mooe")),
              _peso(o.get("co")), _peso(o.get("non_office")), _peso(o.get("total"))]
             for o in fund.get("offices", [])]))
    for spa in data.get("spa", []):
        parts.append("<h3>{} ({})</h3>".format(
            _esc(spa.get("fund", "")), _esc(_period_label(spa.get("period", ""), labels["FDP_UNDATED"]))))
        parts.append(_money_table(
            ["Project", "Past", "Current", "Proposed"],
            [[_esc(i["project"]), _peso(i.get("past")),
              _peso(i.get("current")), _peso(i.get("proposed"))] for i in spa.get("items", [])]))
    return "\n".join(parts)


def generate_fdp(locale: dict) -> str:
    """Render the FDP disclosures section for the transparency page."""
    path = SRC_DATA / "fdp_disclosures.json"
    if not path.exists():
        return ""
    data = json.loads(path.read_text(encoding="utf-8"))
    labels = _build_fdp_labels(locale)
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
    if periods:
        latest = periods[0]
        out.append(f"<h3>{labels['FDP_LATEST']}: {_esc(_period_label(latest, labels['FDP_UNDATED']))}</h3>")
        out.append(_render_period(latest, data, labels, retrieved))
        for period in periods[1:]:
            out.append("<details class='mt-8'><summary><strong>{}: {}</strong></summary>".format(
                labels["FDP_OLDER"], _esc(_period_label(period, labels["FDP_UNDATED"]))))
            out.append(_render_period(period, data, labels, retrieved))
            out.append("</details>")
    undated_periods = sorted({r.get("period", "undated")
                              for key in ("sre", "sef", "ldrrmf", "cash_flows", "cash_advances",
                                          "trust_fund", "lgsf", "dev_fund", "bids")
                              for r in data.get(key, []) if r.get("period") == "undated"})
    for period in undated_periods:
        out.append("<details class='mt-8'><summary><strong>{}</strong></summary>".format(labels["FDP_UNDATED"]))
        out.append(_render_period(period, data, labels, retrieved))
        out.append("</details>")
    out.append(_render_standalone(data, labels))
    if retrieved:
        out.append(f"<p class='source-label'>{labels['FDP_SOURCE']} DILG Full Disclosure Policy Portal &mdash; retrieved {retrieved}.</p>")
    out.append("</div></section>")
    return "\n".join(out)
