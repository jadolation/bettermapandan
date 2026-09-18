"""FDP analytics — quarterly deltas, barangay normalization, dashboard summary.

FDP filings report year-to-date cumulative figures, so flow charts must use
differenced quarters (Q2 minus Q1), never sums across quarters in one year.
"""
import json
import re

from _build.config import SRC_DATA

BARANGAY_SLUGS = [
    "amanoaoac", "apaya", "aserda", "baloling", "coral", "golden",
    "jimenez", "lambayan", "luyan", "nilombot", "pias", "poblacion",
    "primicias", "sta-maria", "torres",
]
MUNICIPAL_WIDE = "municipal-wide"
MUNICIPAL_MARKERS = ("mapandan, pangasinan", "entire mapandan", "mapandan")


def normalize_barangay(location: str):
    """Map a free-text FDP location to a barangay slug, municipal-wide, or None."""
    if not location:
        return None
    text = location.strip().lower().rstrip(".")
    text = re.sub(r"^(brgy|barangay)\.?\s*", "", text)
    text = re.sub(r",?\s*mapandan\.?\s*$", "", text).strip().rstrip(".")
    text = re.sub(r",?\s*pang\.?\s*$", "", text).strip().rstrip(".")
    if not text or text in MUNICIPAL_MARKERS or "entire mapandan" in text:
        return MUNICIPAL_WIDE
    key = re.sub(r"[\s.]+", "-", text).strip("-")
    if key in BARANGAY_SLUGS:
        return key
    nospace = key.replace("-", "")
    for slug in BARANGAY_SLUGS:
        if slug.replace("-", "") == nospace:
            return slug
    return None


def _load():
    path = SRC_DATA / "fdp_disclosures.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _dated(records: list) -> list:
    """Records with real YYYY-QN periods, sorted chronologically."""
    return sorted(
        (r for r in records if r.get("year") and r.get("quarter")),
        key=lambda r: (r["year"], r["quarter"]),
    )


def _sre_row(sre: dict, *prefixes):
    for row in sre.get("rows", []):
        label = str(row.get("label", "")).lower()
        for prefix in prefixes:
            if label.startswith(prefix.lower()):
                return row
    return {}


def quarterly_deltas() -> list:
    """Per-quarter GF receipt/expenditure FLOWS derived from YTD filings."""
    data = _load()
    by_year: dict = {}
    for rec in _dated([r for r in data.get("sre", []) if r.get("sheet") == "sre_report"]):
        income = _sre_row(rec, "total current operating income")
        expend = _sre_row(rec, "total current operating expenditures")
        by_year.setdefault(rec["year"], {})[rec["quarter"]] = {
            "receipts": income.get("general_fund"),
            "expenditures": expend.get("general_fund"),
        }
    series = []
    for year in sorted(by_year):
        prev = None
        for quarter in sorted(by_year[year]):
            values = by_year[year][quarter]
            flow = {}
            for field in ("receipts", "expenditures"):
                current = values.get(field)
                if current is None:
                    flow[field] = None
                elif prev and prev.get(field) is not None and quarter > 1:
                    flow[field] = round(current - prev[field], 2)
                else:
                    flow[field] = current
            series.append({"period": f"{year}-Q{quarter}", **flow})
            prev = values
    return series


def revenue_composition(period: str) -> dict:
    """Latest-period receipt breakdown: local tax/non-tax detail + NTA."""
    data = _load()
    rec = next((r for r in data.get("sre", [])
                if r.get("period") == period and r.get("sheet") == "sre_report"), None)
    if not rec:
        return {}
    rows = rec.get("rows", [])
    income = _sre_row(rec, "total current operating income")
    total = income.get("general_fund") or 0
    groups = {}
    for row in rows:
        label = str(row.get("label", ""))
        low = label.lower()
        if low.startswith(("real property tax", "tax on business", "other taxes",
                            "regulatory fees", "service/user charges",
                            "receipts from economic", "other receipts")):
            groups[label] = row.get("general_fund") or 0
    nta = _sre_row(rec, "national tax allotm").get("general_fund") or 0
    other_ext = _sre_row(rec, "other shares from national").get("general_fund") or 0
    local_total = _sre_row(rec, "local sources").get("general_fund") or 0
    return {"total": total, "detail": groups, "nta": nta, "other_external": other_ext,
            "local_total": local_total,
            "nta_share": round(nta / total * 100, 1) if total else None,
            "local_share": round(local_total / total * 100, 1) if total else None}


def expenditure_by_function(period: str) -> dict:
    """Latest-period GF spending across the 7 statutory functions."""
    data = _load()
    rec = next((r for r in data.get("sre", [])
                if r.get("period") == period and r.get("sheet") == "sre_report"), None)
    if not rec:
        return {}
    functions = ["general public servi", "education, culture",
                 "health, nutrition", "labor and employment",
                 "housing and community", "social services", "economic services",
                 "debt service"]
    out, total = {}, 0.0
    for row in rec.get("rows", []):
        label = str(row.get("label", ""))
        if "principal" in label.lower():
            continue  # debt principal lives outside operating expenditures
        for prefix in functions:
            if label.lower().startswith(prefix):
                value = row.get("general_fund") or 0
                out[label] = value
                total += value
    total = round(total, 2)
    return {"items": out, "total": total,
            "shares": {k: round(v / total * 100, 1) if total else 0 for k, v in out.items()}}


def funds_history() -> dict:
    """SEF/LDRRMF utilization rates across dated filings."""
    data = _load()
    sef, ldrrmf = [], []
    for rec in _dated(data.get("sef", [])):
        receipt, balance = rec.get("receipt"), rec.get("balance")
        sef.append({"period": rec["period"], "receipt": receipt, "balance": balance,
                    "rate": round((receipt - balance) / receipt * 100, 1)
                    if receipt else None})
    for rec in _dated(data.get("ldrrmf", [])):
        totals = rec.get("totals", {})
        available, utilized = totals.get("available"), totals.get("utilization")
        ldrrmf.append({"period": rec["period"], "available": available,
                       "utilized": utilized, "unutilized": totals.get("unutilized"),
                       "rate": round(utilized / available * 100, 1) if available else None})
    return {"sef": sef, "ldrrmf": ldrrmf}


def cash_bridge(period: str) -> dict:
    data = _load()
    rec = next((r for r in data.get("cash_flows", []) if r.get("period") == period), {})
    return rec.get("key", {})


def barangay_distribution(period: str) -> dict:
    """Per-barangay project counts + investment for one filing period."""
    data = _load()
    rec = next((r for r in data.get("dev_fund", []) if r.get("period") == period), None)
    dist, unmatched = {}, []
    for proj in (rec or {}).get("projects", []):
        slug = normalize_barangay(proj.get("location", ""))
        if slug is None:
            unmatched.append(proj.get("location", ""))
            continue
        slot = dist.setdefault(slug, {"projects": 0, "investment": 0.0})
        slot["projects"] += 1
        slot["investment"] += proj.get("cost") or 0
    return {"dist": dist, "unmatched": sorted(set(unmatched))}


def bids_savings() -> list:
    """ABC vs awarded totals and savings rate per dated filing."""
    data = _load()
    out = []
    for rec in _dated(data.get("bids", [])):
        abc = awarded = 0.0
        for bid in rec.get("civil_works", []) + rec.get("goods", []):
            abc += bid.get("abc") or 0
            awarded += bid.get("bid_amount") or 0
        out.append({"period": rec["period"], "abc": abc, "awarded": awarded,
                    "savings": round(abc - awarded, 2),
                    "rate": round((abc - awarded) / abc * 100, 2) if abc else None,
                    "count": len(rec.get("civil_works", [])) + len(rec.get("goods", []))})
    return out


def latest_period() -> str:
    data = _load()
    periods = [r.get("period") for g in ("sre", "sef", "ldrrmf", "bids", "dev_fund")
               for r in data.get(g, []) if r.get("period") and r.get("period") != "undated"]
    return max(periods) if periods else ""


def generate_fdp_summary() -> dict:
    """Slim build-time payload for the dashboard (tens of KB, not the 1.3MB file)."""
    data = _load()
    latest = latest_period()
    sef_latest = next((r for r in _dated(data.get("sef", [])) if r.get("period") == latest), {})
    ld_latest = next((r for r in data.get("ldrrmf", []) if r.get("period") == latest), {})
    cash = cash_bridge(latest)
    comp = revenue_composition(latest)
    exp = expenditure_by_function(latest)
    brgy = barangay_distribution(latest)
    def _r2(value):
        return round(value, 2) if isinstance(value, float) else value

    return {
        "latest_period": latest,
        "retrieved": data.get("meta", {}).get("retrieved", ""),
        "kpis": {
            "receipts": _r2(comp.get("total")),
            "expenditures": _r2(exp.get("total")),
            "sef_balance": sef_latest.get("balance"),
            "ldrrmf_unutilized": (ld_latest.get("totals", {}) or {}).get("unutilized"),
            "cash_ending": cash.get("ending"),
            "projects": sum(v["projects"] for v in brgy["dist"].values()),
            "bids": (bids_savings() or [{}])[-1].get("count") if bids_savings() else None,
        },
        "trend": quarterly_deltas(),
        "revenue": comp,
        "expenditure": exp,
        "funds": funds_history(),
        "cash": cash,
        "barangay": brgy,
        "bids": bids_savings(),
    }
