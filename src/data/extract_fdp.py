"""Extract DILG Full Disclosure Policy filings for Mapandan into fdp_disclosures.json.

Reads per-sheet CSVs in datasets/fdp-csv/<year>/*.csv (generated from the
FDP workbooks by src/data/fdp_to_csv.py; one CSV per worksheet, sheet name
in the filename after "__"), normalizes them into quarterly records, and
writes src/data/fdp_disclosures.json for the site generators.

Sheet routing is by filename suffix, with content-sniffing for ambiguous
Sheet1 files. Amounts arrive as comma-quoted text; dates as ISO strings.

Usage: python3 src/data/extract_fdp.py
"""
import csv
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.data._utils import write_json

CACHE_DIR = Path("datasets/fdp-csv")
OUTPUT = Path("src/data/fdp_disclosures.json")

CERTIFY_RE = re.compile(r"we hereby certify", re.I)
CODE_RE = re.compile(r"^\d-\d{2}-\d{2}-\d{3}$")


def to_float(value):
    """Coerce FDP money cells (floats, comma text, 'P 1,234', N/A) to float/None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    text = re.sub(r"^(p|php|₱)\s*", "", text, flags=re.I).strip()
    if text in ("", "-", "N/A", "n/a", "NONE", "none", "not yet started"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def clean_text(value):
    if value is None:
        return ""
    text = str(value).strip()
    return re.sub(r"\s+", " ", text)


def read_rows(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return [[c for c in row] for row in csv.reader(fh)]


def sheet_of(path: Path) -> str:
    """Sheet identifier from '<workbook>__<Sheet>.csv' filename."""
    stem = path.stem
    return stem.split("__", 1)[1] if "__" in stem else stem


def workbook_of(path: Path) -> str:
    stem = path.stem
    return stem.split("__", 1)[0] if "__" in stem else stem


def parse_year_quarter(ws, rows):
    """FDP header blocks carry CALENDAR YEAR / QUARTER cells or 'Period Covered:'."""
    year, quarter = None, None
    for row in rows[:10]:
        cells = [clean_text(c) for c in row]
        joined = " ".join(cells)
        if "period covered" in joined.lower():
            match = re.search(r"Q([1-4])\s*,?\s*(20\d{2})", joined, re.I)
            if match:
                quarter, year = int(match.group(1)), int(match.group(2))
        for i, cell in enumerate(cells):
            rest = [c for c in cells[i + 1:] if c]
            if cell.lower() == "calendar year:" and rest:
                try:
                    year = int(float(rest[0]))
                except ValueError:
                    pass
            if cell.lower() == "quarter:" and rest:
                try:
                    quarter = int(float(rest[0]))
                except ValueError:
                    pass
    return year, quarter


def period_key(year, quarter):
    if year and quarter:
        return f"{year}-Q{quarter}"
    if year:
        return str(year)
    return "undated"


def first_number(row, start=0):
    for cell in row[start:]:
        value = to_float(cell)
        if value is not None:
            return value
    return None


def last_number(row):
    for cell in reversed(row):
        value = to_float(cell)
        if value is not None:
            return value
    return None


def split_date(value):
    """Normalize '2026-02-10 00:00:00' text (or datetime) to YYYY-MM-DD."""
    if value is None:
        return ""
    text = clean_text(value)
    match = re.match(r"(\d{4}-\d{2}-\d{2})", text)
    return match.group(1) if match else text


# ----------------------------------------------------------------------------
# Form parsers (rows = list of string lists; each returns a record or None)
# ----------------------------------------------------------------------------

def parse_sre(rows, form="sre"):
    year, quarter = parse_year_quarter(None, rows)
    header_idx = next((i for i, r in enumerate(rows)
                       if clean_text(r[0]).lower().startswith("particulars")
                       or (len(r) > 1 and clean_text(r[1]).lower().startswith("particulars"))), None)
    if header_idx is None:
        return None
    p = 0 if clean_text(rows[header_idx][0]).lower().startswith("particulars") else 1
    records = []
    for row in rows[header_idx + 1:]:
        label = clean_text(row[p]) if len(row) > p else ""
        if not label:
            continue
        nums = [to_float(c) for c in row[p + 1:]]
        vals = [v for v in nums if v is not None]
        if not vals:
            continue
        while len(vals) < 5:
            vals.append(None)
        records.append({"label": label, "target": vals[0], "general_fund": vals[1],
                        "sef": vals[2], "trust_fund": vals[3], "trust_liability": vals[4]})
    if not records:
        return None
    return {"form": form, "period": period_key(year, quarter), "year": year,
            "quarter": quarter, "rows": records}


def parse_sef(rows):
    year, quarter = parse_year_quarter(None, rows)
    receipt, items, subtotal, balance = None, [], None, None
    in_items = False
    for row in rows:
        a = clean_text(row[0]) if len(row) > 0 else ""
        low = a.lower()
        if low.startswith("receipt from sef"):
            receipt = last_number(row)
            in_items = True
            continue
        if low.startswith("sub"):
            subtotal = last_number(row)
            in_items = False
            continue
        if low.startswith("balance"):
            balance = last_number(row)
            in_items = False
            continue
        if CERTIFY_RE.search(a) or "hereby certify" in " ".join(clean_text(c) for c in row).lower():
            in_items = False
            continue
        if in_items:
            b = clean_text(row[1]) if len(row) > 1 else ""
            amount = last_number(row)
            if b and amount is not None:
                items.append({"label": b, "amount": amount})
    return {"form": "sef", "period": period_key(year, quarter), "year": year,
            "quarter": quarter, "receipt": receipt, "items": items,
            "subtotal": subtotal, "balance": balance}


def parse_ldrrmf(rows):
    year, quarter = parse_year_quarter(None, rows)
    sources, utilization = [], []
    section = None
    for row in rows:
        a = clean_text(row[0]) if len(row) > 0 else ""
        low = a.lower()
        if low.startswith("a. sources of funds"):
            section = "sources"
            continue
        if low.startswith("b. utilization"):
            section = "util"
            continue
        if CERTIFY_RE.search(a):
            break
        if section == "sources" and a:
            qrf = to_float(row[1]) if len(row) > 1 else None
            mit = to_float(row[2]) if len(row) > 2 else None
            total = to_float(row[6]) if len(row) > 6 else None
            if qrf is not None or mit is not None or total is not None:
                sources.append({"label": a, "qrf": qrf, "mitigation": mit, "total": total})
        elif section == "util" and a and not low.startswith("total utilization") and not low.startswith("unutilized"):
            qrf = to_float(row[1]) if len(row) > 1 else None
            total = to_float(row[6]) if len(row) > 6 else None
            if qrf not in (None, 0) or total not in (None, 0):
                utilization.append({"label": a, "qrf": qrf, "total": total})
    totals = {}
    for row in rows:
        a = clean_text(row[0]).lower() if len(row) > 0 else ""
        if a.startswith("total utilization"):
            totals["utilization"] = last_number(row)
        elif a.startswith("unutilized balance"):
            totals["unutilized"] = last_number(row)
        elif a.startswith("total funds avail"):
            totals["available"] = last_number(row)
    if not sources and not utilization:
        return None
    return {"form": "ldrrmf", "period": period_key(year, quarter), "year": year,
            "quarter": quarter, "sources": sources, "utilization": utilization,
            "totals": totals}


def parse_scf(rows):
    year, quarter = parse_year_quarter(None, rows)
    section, entries, key = None, [], {}
    for row in rows:
        cells = [clean_text(c) for c in row]
        a = cells[0] if cells else ""
        if a.lower().startswith("cash flows from"):
            section = re.sub(r"cash flows from\s*", "", a, flags=re.I).strip() or section
            continue
        if CERTIFY_RE.search(a):
            break
        label = next((c for c in cells[:4] if c), "")
        if not label:
            continue
        value = first_number(cells[4:])
        low = label.lower()
        entries.append({"label": label, "section": section, "value": value})
        if low.startswith("net cash from operating"):
            key["net_operating"] = value
        elif low.startswith("net cash from investing"):
            key["net_investing"] = value
        elif low.startswith("net cash from financ"):
            key["net_financing"] = value
        elif low.startswith("net increase in cash"):
            key["net_increase"] = value
        elif low.startswith("cash at beginning"):
            key["beginning"] = value
        elif low.startswith("cash at the end"):
            key["ending"] = value
    if not entries:
        return None
    return {"form": "cash_flows", "period": period_key(year, quarter), "year": year,
            "quarter": quarter, "key": key, "rows": entries}


def parse_uca(rows):
    year, quarter = parse_year_quarter(None, rows)
    debtors, total, started = [], None, False
    for row in rows:
        a = clean_text(row[0]) if len(row) > 0 else ""
        if a.lower().startswith("name of debtor"):
            started = True
            continue
        if not started:
            continue
        if CERTIFY_RE.search(a):
            break
        if a.lower().startswith("total"):
            total = first_number(row[1:])
            continue
        if not a or a.upper() in ("NONE", "N/A"):
            continue
        debtors.append({"debtor": a,
                        "balance": to_float(row[1]) if len(row) > 1 else None,
                        "date_granted": split_date(row[2]) if len(row) > 2 else "",
                        "purpose": clean_text(row[3]) if len(row) > 3 else ""})
    if not debtors and total in (None, 0):
        return {"form": "cash_advances", "period": period_key(year, quarter),
                "year": year, "quarter": quarter, "status": "nil",
                "debtors": [], "total": 0}
    return {"form": "cash_advances", "period": period_key(year, quarter),
            "year": year, "quarter": quarter, "debtors": debtors, "total": total}


def parse_trust(rows, suffix):
    year, quarter = parse_year_quarter(None, rows)
    form = "trust_fund" if suffix == "6a" else "lgsf"
    header_idx = next((i for i, r in enumerate(rows)
                       if clean_text(r[0]).lower().startswith(("program or project", "fund source"))), None)
    items = []
    if header_idx is not None:
        for row in rows[header_idx + 2:]:
            cells = [clean_text(c) for c in row]
            a = cells[0] if cells else ""
            if CERTIFY_RE.search(" ".join(cells)) or "certified correct" in " ".join(cells).lower():
                break
            if not a or a.upper() in ("N/A", "NONE"):
                continue
            items.append({"program": a,
                          "location": cells[1] if len(cells) > 1 else "",
                          "cost": to_float(row[2]) if len(row) > 2 else None,
                          "started": split_date(row[3]) if len(row) > 3 else "",
                          "completion": split_date(row[4]) if len(row) > 4 else "",
                          "progress": cells[5] if len(cells) > 5 else ""})
    if not items:
        return {"form": form, "period": period_key(year, quarter), "year": year,
                "quarter": quarter, "status": "nil", "items": []}
    return {"form": form, "period": period_key(year, quarter), "year": year,
            "quarter": quarter, "items": items}


def parse_dfu_rows(rows):
    """Parse one DFU quarter-sheet: returns (year, quarter, projects, totals)."""
    year, quarter = parse_year_quarter(None, rows)
    header_idx = next((i for i, r in enumerate(rows)
                       if clean_text(r[0]).lower().startswith("program or")), None)
    projects, totals = [], {}
    if header_idx is not None:
        for row in rows[header_idx + 2:]:
            a = clean_text(row[0]) if len(row) > 0 else ""
            if CERTIFY_RE.search(a) or a.lower().startswith("we hereby"):
                break
            if not a:
                continue
            if a.upper() == "TOTAL":
                nums = [to_float(c) for c in row[1:]]
                nums = [v for v in nums if v is not None]
                if nums:
                    totals = {"cost": nums[0] if len(nums) > 0 else None,
                              "pct": nums[1] if len(nums) > 1 else None,
                              "incurred": nums[2] if len(nums) > 2 else None}
                continue
            if a.lower() in ("social development", "econimic development", "economic development"):
                continue
            nums = [to_float(c) for c in row[3:]]
            nums = [v for v in nums if v is not None]
            cost = to_float(row[2]) if len(row) > 2 else None
            pct = incurred = None
            if len(nums) >= 2:
                pct, incurred = nums[-2], nums[-1]
            elif len(nums) == 1:
                incurred = nums[0]
            if cost is None and pct is None and incurred is None:
                continue
            projects.append({"project": a,
                             "location": clean_text(row[1]) if len(row) > 1 else "",
                             "cost": cost,
                             "started": split_date(row[3]) if len(row) > 3 else "",
                             "completion": split_date(row[4]) if len(row) > 4 else "",
                             "pct": pct, "incurred": incurred})
    return year, quarter, projects, totals


def parse_bids_rows(rows):
    """Parse one 10a/10b/10c sheet: returns list of bids."""
    header_idx = next((i for i, r in enumerate(rows)
                       if "reference" in clean_text(r[1]).lower() or "reference" in clean_text(r[0]).lower()), None)
    bids = []
    if header_idx is not None:
        for row in rows[header_idx + 2:]:
            cells = [clean_text(c) for c in row]
            if CERTIFY_RE.search(" ".join(cells)) or cells[0].lower().startswith("we hereby"):
                break
            if not cells[1] or cells[1].upper() in ("N/A", "NONE"):
                continue
            bids.append({"ref": cells[1],
                         "project": clean_text(row[2]) if len(row) > 2 else "",
                         "abc": to_float(row[3]) if len(row) > 3 else None,
                         "location": clean_text(row[4]) if len(row) > 4 else "",
                         "bidder": clean_text(row[5]) if len(row) > 5 else "",
                         "bid_amount": to_float(row[7]) if len(row) > 7 else None,
                         "award_date": split_date(row[8]) if len(row) > 8 else ""})
    return bids


def parse_manpower(rows):
    year, quarter = parse_year_quarter(None, rows)
    items, total = [], None
    for row in rows:
        a = clean_text(row[0]) if len(row) > 0 else ""
        b = clean_text(row[1]) if len(row) > 1 else ""
        label = b or a
        low = label.lower()
        if low.startswith(("permanent", "contractual", "job order", "casual", "grand total")):
            count = to_float(row[2]) if len(row) > 2 else None
            amount = to_float(row[4]) if len(row) > 4 else None
            if low.startswith("grand total"):
                total = {"count": count, "amount": amount}
            else:
                items.append({"class": label, "count": count, "amount": amount})
    if not items:
        return None
    return {"form": "manpower", "period": period_key(year, quarter) if year else "undated",
            "year": year, "quarter": quarter, "items": items, "total": total,
            "note": None if year else "Snapshot date not stated in filing"}


def parse_sipb_rows(rows, loan):
    items, report_date = {}, ""
    for row in rows:
        a = clean_text(row[0]) if len(row) > 0 else ""
        b = clean_text(row[1]) if len(row) > 1 else ""
        c = clean_text(row[2]) if len(row) > 2 else ""
        if a.isdigit() and b:
            items[b] = c
            if b.lower().startswith("date of report"):
                report_date = c
    if not items:
        return None
    return {"loan": loan, "report_date": report_date, "items": items}


def _detect_budget_year(rows, fallback=None):
    for row in rows[:14]:
        joined = " ".join(clean_text(c) for c in row)
        match = re.search(r"[Bb][Uu][Dd][Gg][Ee][Tt]\s+[Yy][Ee][Aa][Rr]\s+(20\d{2})", joined)
        if match:
            return int(match.group(1))
        match = re.search(r"[Ff][Ii][Ss][Cc][Aa][Ll]\s+[Yy][Ee][Aa][Rr]\s+(20\d{2})", joined)
        if match:
            return int(match.group(1))
    return fallback


def parse_lbp2(rows, year):
    offices, current = [], None
    for row in rows:
        cells = [clean_text(c) for c in row]
        office_cell = next((c for c in cells if c.lower().startswith("office:")), "")
        if office_cell:
            current = {"office": re.sub(r"^office:\s*", "", office_cell, flags=re.I),
                       "ps": 0.0, "mooe": 0.0, "co": 0.0, "proposed": 0.0, "lines": 0}
            offices.append(current)
            continue
        if current is None:
            continue
        code = clean_text(row[1]) if len(row) > 1 else ""
        if not CODE_RE.match(code):
            continue
        prop = last_number(row[2:])
        if prop is None:
            continue
        current["lines"] += 1
        current["proposed"] += prop
        if code.startswith("5-01"):
            current["ps"] += prop
        elif code.startswith("5-02"):
            current["mooe"] += prop
        else:
            current["co"] += prop
    offices = [o for o in offices if o["lines"] > 0]
    if not offices:
        return None
    for o in offices:
        for k in ("ps", "mooe", "co", "proposed"):
            o[k] = round(o[k], 2)
    return {"offices": offices,
            "totals": {k: round(sum(o[k] for o in offices), 2) for k in ("ps", "mooe", "co", "proposed")}}


def parse_budget_sheet(rows, sheet, year):
    """LBP-2-style sheets aggregate by office; all others capture labeled rows."""
    has_account_code = any(len(r) > 1 and "account code" in clean_text(r[1]).lower() for r in rows[:16])
    if has_account_code:
        result = parse_lbp2(rows, year)
        if result:
            result.update({"form": "budget", "sheet": sheet,
                           "period": str(year) if year else "undated", "year": year, "quarter": None})
            return result
        # Summary-style sheet (e.g. Form 1b): account codes but no offices.
        # Fall through to generic labeled-row capture below.
    captured = []
    for row in rows:
        label = clean_text(row[0]) if len(row) > 0 else ""
        if not label or len(label) > 120:
            continue
        low = label.lower()
        if low.startswith(("office:", "object of", "particip", "region", "province", "city",
                            "municipality", "mapandan", "general fund", "lbp form", "budget of",
                            "programmed", "statement of", "comparative", "appropriations for")):
            continue
        if CERTIFY_RE.search(label):
            continue
        vals = [to_float(c) for c in row[1:]]
        vals = [v for v in vals if v is not None]
        if vals:
            captured.append({"label": label, "values": vals})
    if not captured:
        return None
    return {"form": "budget_book", "sheet": sheet,
            "period": str(year) if year else "undated", "year": year,
            "quarter": None, "rows": captured}


def parse_fund_matrix(rows):
    """Office × PS/MOOE/CO appropriation matrix (General Fund, Economic Enterprise)."""
    fund, offices = "", []
    for row in rows[:6]:
        a = clean_text(row[0]) if len(row) > 0 else ""
        if a and not fund and not a.lower().startswith(("region", "province", "city", "municipality", "mapandan")):
            fund = a
    header_idx = next((i for i, r in enumerate(rows)
                       if clean_text(r[0]).lower() == "office"), None)
    if header_idx is None:
        return None
    for row in rows[header_idx + 1:]:
        a = clean_text(row[0]) if len(row) > 0 else ""
        if not a or a.lower().startswith(("office", "total", "certified")):
            continue
        if CERTIFY_RE.search(a):
            break
        nums = [to_float(c) for c in row[1:]]
        nums = [v for v in nums if v is not None]
        while len(nums) < 5:
            nums.append(None)
        offices.append({"office": a, "ps": nums[0], "mooe": nums[1], "co": nums[2],
                        "non_office": nums[3], "total": nums[4]})
    if not offices:
        return None
    return {"form": "fund_matrix", "fund": fund or "General Fund", "year": None,
            "quarter": None, "period": "undated", "offices": offices}


def parse_spa(rows):
    """Special-purpose appropriation project lists (20% DF, Non-Office, Calamity)."""
    fund, items = "", []
    for row in rows[:6]:
        a = clean_text(row[0]) if len(row) > 0 else ""
        if a and not fund and not a.lower().startswith(("region", "province", "city", "municipality", "mapandan")):
            fund = a
    header_idx = next((i for i, r in enumerate(rows)
                       if "office of expenditure" in clean_text(r[0]).lower()
                       or "procurement" in clean_text(r[0]).lower() and "account" in clean_text(r[1]).lower()), None)
    if header_idx is None:
        for i, r in enumerate(rows):
            joined = " ".join(clean_text(c) for c in r).lower()
            if "account" in joined and "code" in joined:
                header_idx = i
                break
    if header_idx is None:
        return None
    for row in rows[header_idx + 1:]:
        a = clean_text(row[0]) if len(row) > 0 else ""
        if not a or a.lower().startswith(("special purpose", "total")):
            continue
        if CERTIFY_RE.search(a):
            break
        nums = [to_float(c) for c in row[1:]]
        nums = [v for v in nums if v is not None]
        if not nums and not a:
            continue
        while len(nums) < 3:
            nums.append(None)
        items.append({"project": a, "code": clean_text(row[1]) if len(row) > 1 else "",
                      "past": nums[0], "current": nums[1], "proposed": nums[2]})
    if not items:
        return None
    return {"form": "spa", "fund": fund, "year": None, "quarter": None,
            "period": "undated", "items": items}


def parse_spp_rows(rows, office):
    header_idx = next((i for i, r in enumerate(rows)
                       if "code (pap)" in clean_text(r[0]).lower()), None)
    items = []
    if header_idx is not None:
        for row in rows[header_idx + 2:]:
            cells = [clean_text(c) for c in row]
            if CERTIFY_RE.search(" ".join(cells)):
                break
            if len(cells) < 2 or not cells[1] or cells[1].upper() in ("N/A", "NONE", "TOTAL"):
                continue
            amount = next((to_float(c) for c in reversed(cells) if to_float(c) is not None), None)
            items.append({"project": cells[1], "end_user": cells[2] if len(cells) > 2 else "",
                          "mode": cells[4] if len(cells) > 4 else "", "amount": amount})
    return items


def parse_app_rows(rows):
    """Annual Procurement Plan per-office sheet."""
    office, year, items = "", None, []
    for row in rows[:10]:
        cells = [clean_text(c) for c in row]
        for i, cell in enumerate(cells):
            rest = [c for c in cells[i + 1:] if c]
            if cell.lower().startswith("office") and "department" in cell.lower() and rest:
                office = rest[0]
            if cell.lower() == "calendar year:" and rest:
                try:
                    year = int(float(rest[0]))
                except ValueError:
                    pass
    header_idx = next((i for i, r in enumerate(rows)
                       if clean_text(r[0]).lower().startswith("code (pap)")), None)
    if header_idx is not None:
        for row in rows[header_idx + 2:]:
            cells = [clean_text(c) for c in row] + [""] * 14
            if CERTIFY_RE.search(" ".join(cells)) or cells[0].lower().startswith("we hereby"):
                break
            if not cells[1] or cells[1].upper() in ("N/A", "NONE", "TOTAL"):
                continue
            items.append({"code": cells[0], "project": cells[1],
                          "end_user": cells[2], "early": cells[3], "mode": cells[4],
                          "schedule": " / ".join(c for c in cells[5:9] if c),
                          "source": cells[9], "total": to_float(cells[10]),
                          "mooe": to_float(cells[11]), "co": to_float(cells[12]),
                          "remarks": cells[13]})
    return office, year, items


# ----------------------------------------------------------------------------
# Router + driver
# ----------------------------------------------------------------------------

def head_text(rows, n=12):
    return " ".join(clean_text(c) for r in rows[:n] for c in r).lower()


def classify_csv(path: Path) -> str:
    """Route a per-sheet CSV by filename suffix, with content sniffing fallback."""
    sheet = sheet_of(path).lower()
    if sheet in ("sre_report",):
        return "sre"
    if sheet in ("soe_report",):
        return "soe"
    if "sef" in sheet:
        return "sef"
    if "ldrrmfu" in sheet:
        return "ldrrmf"
    if "scf" in sheet:
        return "scf"
    if "uca" in sheet:
        return "uca"
    if "6a" in sheet and "tfu" in sheet:
        return "trust6a"
    if "6b" in sheet and "tfu" in sheet:
        return "trust6b"
    if "dfu" in sheet or re.match(r"q[1-4]_20\d\d$", sheet):
        return "dfu"
    if "10a" in sheet:
        return "bids_cw"
    if "10b" in sheet:
        return "bids_gs"
    if "10c" in sheet:
        return "bids_cs"
    if "term_loan" in sheet:
        return "sipb"
    if "app_summary" in sheet or ("4b" in sheet and "14b" not in sheet):
        return "app_summary"
    if sheet.startswith("app_"):
        return "app"
    if any(k in sheet for k in ("lbp", "lpb", "final", "comparative", "budget_per_dept")):
        if "lpb_2" in sheet:
            return "spa"
        return "lbp"
    if "spp" in sheet or "14b" in sheet:
        return "spp_sheet"
    if "form_1a" in sheet or "form_1b" in sheet:
        return "lbp"
    return "sniff"


def sniff_kind(rows) -> str:
    """Content-sniff ambiguous sheets (Sheet1, bare numbers, office names)."""
    head = head_text(rows)
    if "annual procurement plan" in head and "by office" in head:
        return "app"
    if "annual procurement plan" in head and "summary" in head:
        return "app_summary"
    if "supplemental procurement" in head:
        return "spp_sheet"
    if "programmed appropriation" in head:
        return "lbp"
    if "statement of indebtedness" in head:
        return "sipb"
    if "manpower complement" in head or "human resource complement" in head:
        return "manpower_sheet"
    if "gender and development" in head:
        return "gad"
    if "general fund" in head and "personal" in head and "mooe" in head:
        return "fund_matrix"
    if "economic enterprise" in head and "personal" in head:
        return "fund_matrix"
    if "20% development fund" in head or "calamity" in head or "non-office" in head or "non office" in head:
        if "office of expenditure" in head:
            return "spa"
    if "sre_report" in head or "statement of receipts and expe" in head:
        return "sre"
    if "statement of expenditures" in head:
        return "soe"
    return "unknown"


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if not CACHE_DIR.exists():
        sys.exit(f"missing {CACHE_DIR}")
    files = sorted(CACHE_DIR.rglob("*.csv"))
    print(f"found {len(files)} csv files")

    groups = {"sre": [], "sef": [], "ldrrmf": [], "cash_flows": [], "cash_advances": [],
              "trust_fund": [], "lgsf": [], "dev_fund": [], "bids": [], "manpower": [],
              "indebtedness": [], "budget": [], "budget_book": [], "spp": [],
              "app": [], "gad": [], "fund_matrix": [], "spa": []}
    bids_parts = {}
    skipped, errors = [], []

    for path in files:
        try:
            rows = read_rows(path)
        except (OSError, csv.Error, UnicodeDecodeError) as exc:
            errors.append(f"{path}: {type(exc).__name__}: {exc}")
            continue
        if not any(any(clean_text(c) for c in r) for r in rows):
            skipped.append(f"{path}: empty")
            continue
        if "data_validation" in sheet_of(path).lower():
            continue  # dropdown-list helper sheet, not a filing
        kind = classify_csv(path)
        if kind in ("sniff", "unknown"):
            sniffed = sniff_kind(rows)
            kind = sniffed if sniffed != "unknown" else "unknown"
        if kind == "manpower_sheet":
            rec = parse_manpower(rows)
            if rec:
                rec["source_file"] = f"datasets/fdp-csv/{path.parent.name}/{path.name}"
                groups["manpower"].append(rec)
            else:
                skipped.append(f"{path}: manpower unparsed")
        elif kind in ("sre", "soe"):
            rec = parse_sre(rows, form="sre" if kind == "sre" else "soe")
            if rec:
                rec["sheet"] = sheet_of(path)
                rec["source_file"] = f"datasets/fdp-csv/{path.parent.name}/{path.name}"
                groups["sre"].append(rec)
            else:
                skipped.append(f"{path}: {kind} unparsed")
        elif kind == "sef":
            rec = parse_sef(rows)
            rec["source_file"] = f"datasets/fdp-csv/{path.parent.name}/{path.name}"
            groups["sef"].append(rec)
        elif kind == "ldrrmf":
            rec = parse_ldrrmf(rows)
            if rec:
                rec["source_file"] = f"datasets/fdp-csv/{path.parent.name}/{path.name}"
                groups["ldrrmf"].append(rec)
            else:
                skipped.append(f"{path}: ldrrmf unparsed")
        elif kind == "scf":
            rec = parse_scf(rows)
            if rec:
                rec["source_file"] = f"datasets/fdp-csv/{path.parent.name}/{path.name}"
                groups["cash_flows"].append(rec)
            else:
                skipped.append(f"{path}: scf unparsed")
        elif kind == "uca":
            rec = parse_uca(rows)
            rec["source_file"] = f"datasets/fdp-csv/{path.parent.name}/{path.name}"
            groups["cash_advances"].append(rec)
        elif kind in ("trust6a", "trust6b"):
            rec = parse_trust(rows, "6a" if kind == "trust6a" else "6b")
            rec["source_file"] = f"datasets/fdp-csv/{path.parent.name}/{path.name}"
            groups[rec["form"]].append(rec)
        elif kind == "dfu":
            year, quarter, projects, totals = parse_dfu_rows(rows)
            rec = {"form": "dev_fund", "period": period_key(year, quarter), "year": year,
                   "quarter": quarter, "projects": projects, "totals": totals,
                   "source_file": f"datasets/fdp-csv/{path.parent.name}/{path.name}"}
            groups["dev_fund"].append(rec)
        elif kind in ("bids_cw", "bids_gs", "bids_cs"):
            bids = parse_bids_rows(rows)
            year, quarter = parse_year_quarter(None, rows)
            key = (workbook_of(path), year, quarter)
            slot = bids_parts.setdefault(key, {"civil_works": [], "goods": [], "consulting": []})
            slot[{"bids_cw": "civil_works", "bids_gs": "goods", "bids_cs": "consulting"}[kind]] = bids
            slot["year"], slot["quarter"] = year, quarter
            slot["source_file"] = f"datasets/fdp-csv/{path.parent.name}/{workbook_of(path)}"
        elif kind == "sipb":
            loan = sheet_of(path).replace("_", " ").strip()
            rec = parse_sipb_rows(rows, loan)
            if rec:
                rec["source_file"] = f"datasets/fdp-csv/{path.parent.name}/{path.name}"
                groups["indebtedness"].append(rec)
            else:
                skipped.append(f"{path}: sipb unparsed")
        elif kind == "lbp":
            try:
                default_year = int(path.parent.name)
            except ValueError:
                default_year = None
            rec = parse_budget_sheet(rows, sheet_of(path), default_year)
            if rec:
                rec["source_file"] = f"datasets/fdp-csv/{path.parent.name}/{path.name}"
                groups[rec["form"]].append(rec)
            else:
                skipped.append(f"{path}: lbp unparsed")
        elif kind == "spp_sheet":
            office = ""
            for row in rows[:10]:
                cells = [clean_text(c) for c in row]
                for i, cell in enumerate(cells):
                    if cell.lower() == "office:" and i + 1 < len(cells):
                        office = cells[i + 1]
            year, _ = parse_year_quarter(None, rows)
            items = parse_spp_rows(rows, office)
            summary = "summary" in sheet_of(path).lower() or "14b" in sheet_of(path).lower()
            if summary:
                items_out = []
                for row in rows:
                    a = clean_text(row[0]) if len(row) > 0 else ""
                    if a.upper().startswith("OFFICE OF"):
                        items_out.append({"office": a,
                                          "total": to_float(row[4]) if len(row) > 4 else None})
                if items_out:
                    groups["spp"].append({"form": "spp", "period": str(year) if year else "undated",
                                          "year": year, "quarter": None, "offices": [],
                                          "summary": items_out,
                                          "source_file": f"datasets/fdp-csv/{path.parent.name}/{path.name}"})
            elif office or items:
                groups["spp"].append({"form": "spp", "period": str(year) if year else "undated",
                                      "year": year, "quarter": None,
                                      "offices": [{"office": office, "items": items}] if office else [],
                                      "summary": [],
                                      "source_file": f"datasets/fdp-csv/{path.parent.name}/{path.name}"})
        elif kind == "app":
            office, year, items = parse_app_rows(rows)
            if office or items:
                groups["app"].append({"form": "app", "period": str(year) if year else "undated",
                                      "year": year, "quarter": None, "office": office,
                                      "sheet": office or "unknown",
                                      "items": items,
                                      "source_file": f"datasets/fdp-csv/{path.parent.name}/{path.name}"})
            else:
                skipped.append(f"{path}: app unparsed")
        elif kind == "app_summary":
            year, _ = parse_year_quarter(None, rows)
            items_out = []
            for row in rows:
                a = clean_text(row[0]) if len(row) > 0 else ""
                if not a or a.lower().startswith(("department", "summary", "region", "province",
                                                  "city", "annual", "fdp form")):
                    continue
                items_out.append({"office": a,
                                  "head": clean_text(row[1]) if len(row) > 1 else "",
                                  "total": to_float(row[3]) if len(row) > 3 else None})
            if items_out:
                groups["app"].append({"form": "app_summary", "period": str(year) if year else "undated",
                                      "year": year, "quarter": None, "offices": [],
                                      "sheet": "summary",
                                      "summary": items_out,
                                      "source_file": f"datasets/fdp-csv/{path.parent.name}/{path.name}"})
            else:
                skipped.append(f"{path}: app_summary unparsed")
        elif kind == "fund_matrix":
            rec = parse_fund_matrix(rows)
            if rec:
                try:
                    rec["year"] = int(path.parent.name)
                    rec["period"] = str(rec["year"])
                except ValueError:
                    pass
                rec["sheet"] = rec.get("fund", "")
                rec["source_file"] = f"datasets/fdp-csv/{path.parent.name}/{path.name}"
                groups["fund_matrix"].append(rec)
            else:
                skipped.append(f"{path}: fund_matrix unparsed")
        elif kind == "spa":
            rec = parse_spa(rows)
            if rec:
                try:
                    rec["year"] = int(path.parent.name)
                    rec["period"] = str(rec["year"])
                except ValueError:
                    pass
                rec["sheet"] = rec.get("fund", "")
                rec["source_file"] = f"datasets/fdp-csv/{path.parent.name}/{path.name}"
                groups["spa"].append(rec)
            else:
                skipped.append(f"{path}: spa unparsed")
        elif kind == "gad":
            year, totals, entries = None, {}, []
            for row in rows[:10]:
                cells = [clean_text(c) for c in row]
                joined = " ".join(cells)
                match = re.search(r"FY\s+(20\d{2})", joined)
                if match:
                    year = int(match.group(1))
                for cell in cells:
                    match = re.search(r"total lg[g]?u budget:?\s*p?\s*([\d,\.]+)", cell, re.I)
                    if match:
                        totals["lgu_budget"] = to_float(match.group(1))
                    match = re.search(r"total gad budget:?\s*p?\s*([\d,\.]+)", cell, re.I)
                    if match:
                        totals["gad_budget"] = to_float(match.group(1))
            for row in rows:
                a = clean_text(row[0]) if len(row) > 0 else ""
                if re.match(r"^\d+\.\s*", a):
                    cells = [clean_text(c) for c in row]
                    entries.append({"issue": a, "objective": cells[1] if len(cells) > 1 else "",
                                    "program": cells[2] if len(cells) > 2 else "",
                                    "activity": cells[3] if len(cells) > 3 else "",
                                    "indicator": cells[4] if len(cells) > 4 else "",
                                    "result": cells[5] if len(cells) > 5 else "",
                                    "budget": to_float(cells[6]) if len(cells) > 6 else None,
                                    "cost": to_float(cells[7]) if len(cells) > 7 else None})
            groups["gad"].append({"form": "gad", "period": str(year) if year else "undated",
                                  "year": year, "quarter": None, "totals": totals,
                                  "entries": entries,
                                  "source_file": f"datasets/fdp-csv/{path.parent.name}/{path.name}"})
        else:
            skipped.append(f"{path}: unclassified")

    for (_workbook, year, quarter), parts in bids_parts.items():
        groups["bids"].append({"form": "bids", "period": period_key(year, quarter),
                               "year": year, "quarter": quarter,
                               "civil_works": parts["civil_works"], "goods": parts["goods"],
                               "consulting": parts["consulting"],
                               "source_file": parts["source_file"]})

    # dedup: same (form, period) -> keep most data rows; undated/nil never collapse.
    for key in ("sre", "sef", "ldrrmf", "cash_flows", "cash_advances", "trust_fund",
                "lgsf", "bids", "manpower", "spp", "budget", "budget_book", "dev_fund",
                "app", "gad", "fund_matrix", "spa"):
        best, keep_all = {}, []
        for rec in groups[key]:
            if rec.get("period") in (None, "undated") or rec.get("status") == "nil":
                keep_all.append(rec)
                continue
            pk = (rec.get("period"), rec.get("sheet", ""))
            rows = len(rec.get("rows", []) or rec.get("items", []) or rec.get("projects", [])
                       or rec.get("civil_works", []) or rec.get("goods", []) or rec.get("offices", [])
                       or rec.get("debtors", []) or rec.get("entries", []))
            if pk not in best or rows > best[pk][0]:
                best[pk] = (rows, rec)
        groups[key] = sorted([rec for _, rec in best.values()] + keep_all,
                             key=lambda r: (r.get("period", ""), r.get("source_file", "")))

    # dev_fund: same quarter on differently-named sheets -> merge projects.
    merged = {}
    for rec in groups["dev_fund"]:
        period = rec.get("period", "undated")
        slot = merged.setdefault(period, {"form": "dev_fund", "period": period,
                                          "year": rec.get("year"), "quarter": rec.get("quarter"),
                                          "projects": [], "totals": rec.get("totals", {}),
                                          "source_file": []})
        seen = {(p.get("project"), p.get("location"), p.get("cost")) for p in slot["projects"]}
        for proj in rec.get("projects", []):
            key = (proj.get("project"), proj.get("location"), proj.get("cost"))
            if key not in seen:
                seen.add(key)
                slot["projects"].append(proj)
        src = rec.get("source_file", "")
        if src and src not in slot["source_file"]:
            slot["source_file"].append(src)
    groups["dev_fund"] = [merged[p] for p in sorted(merged)]

    data = {"meta": {"municipality": "Mapandan, Pangasinan",
                     "source": "DILG Full Disclosure Policy Portal",
                     "retrieved": "2026-09-18",
                     "years": sorted({r.get("year") for g in groups.values() for r in g if r.get("year")})},
            **groups}
    write_json(OUTPUT, data)
    print(f"wrote {OUTPUT}")
    for key, recs in groups.items():
        print(f"  {key}: {len(recs)} records")
    for line in skipped:
        print("  SKIP:", line)
    for line in errors:
        print("  ERROR:", line)


if __name__ == "__main__":
    main()
