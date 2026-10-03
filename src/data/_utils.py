#!/usr/bin/env python3
"""Shared utilities for Mapandan data extraction scripts."""
import json
import re
from pathlib import Path


def clean(value, max_len: int = 200) -> str:
    """Normalize a raw cell value to a safe string."""
    if value is None:
        return ""
    try:
        import pandas as pd
        if pd.isna(value):
            return ""
    except (ValueError, TypeError):
        pass
    return str(value)[:max_len]


def parse_date(value):
    """Parse an ISO-like date value to YYYY-MM-DD, or None if unparseable."""
    if value is None:
        return None
    try:
        import pandas as pd
        ts = pd.to_datetime(value)
        return ts.strftime("%Y-%m-%d")
    except Exception:
        return None


def parse_money(value) -> float:
    """Parse a currency string or numeric value to float. Returns 0.0 on failure."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).replace("₱", "").replace(",", "").strip()
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def fiscal_year_from_contract_id(contract_id: str):
    """Derive a 4-digit fiscal year from a contract/reference ID, if possible."""
    if not contract_id:
        return None
    s = str(contract_id)
    if len(s) >= 2 and s[:2].isdigit():
        prefix = int(s[:2])
        return 2000 + prefix if prefix < 100 else prefix
    return None


def to_float(value, default: float = 0.0) -> float:
    """Best-effort float coercion with a safe default."""
    if value is None:
        return default
    try:
        import pandas as pd
        if pd.notna(value):
            return float(value)
    except (ValueError, TypeError):
        pass
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def write_json(path: Path, data, indent: int = 2) -> None:
    """Write a Python object as UTF-8 JSON to *path*."""
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=indent),
        encoding="utf-8",
    )


def load_json(path: Path):
    """Load and return parsed JSON from *path*."""
    return json.loads(path.read_text(encoding="utf-8"))


# Canonical short barangay names (matching barangays.json byte-for-byte).
# Letter-variant spellings in other sources resolve via BARANGAY_ALIASES.
BARANGAYS_CANONICAL = (
    "Amanoaoac",
    "Apaya",
    "Aserda",
    "Baloling",
    "Coral",
    "Golden",
    "Jimenez",
    "Lambayan",
    "Luyan",
    "Nilombot",
    "Pias",
    "Poblacion",
    "Primicias",
    "Sta. Maria",
    "Torres",
)

# Variant spellings observed in source datasets, mapped to the
# canonical repo form above (e.g. a 10-letter DPWH variant).
BARANGAY_ALIASES = {
    "amanaoaoac": "Amanoaoac",
}


def normalize_barangay(value, canonical=BARANGAYS_CANONICAL) -> str:
    """Map a messy location string to a canonical barangay name.

    Handles "Brgy. X", "Brgy.X" (no space), trailing dots, "X, Mapandan"
    suffixes, and known typos. Returns "" when nothing matches.
    For multi-barangay strings ("A / B"), returns the first match —
    callers needing all matches should use normalize_barangays().
    """
    if not value:
        return ""
    s = str(value).strip()
    # Strip common prefixes/suffixes and stray punctuation.
    s = re.sub(r"(?i)^\s*brgy\.?\s*", "", s)
    s = re.sub(r"(?i)[\s,]*mapandan[\s,.]*$", "", s).strip().rstrip(".")
    # Known typo corrections.
    s = re.sub(r"(?i)^papata\b", "Papaya", s)
    low = s.lower()
    if s.lower() in BARANGAY_ALIASES:
        return BARANGAY_ALIASES[s.lower()]
    low = s.lower()
    for name in canonical:
        if low == name.lower() or low.startswith(name.lower() + " ") or low.startswith(name.lower() + ","):
            return name
    # Multi-barangay: try each slash-separated part.
    for part in re.split(r"\s*/\s*", s):
        part = re.sub(r"(?i)^\s*brgy\.?\s*", "", part).strip().rstrip(".")
        if part.lower() in BARANGAY_ALIASES:
            part = BARANGAY_ALIASES[part.lower()]
        for name in canonical:
            if part.lower() == name.lower():
                return name
    return ""


def normalize_barangays(value, canonical=BARANGAYS_CANONICAL) -> list:
    """Return all canonical barangay names found in a location string."""
    if not value:
        return []
    found = []
    for part in re.split(r"\s*/\s*", str(value)):
        name = normalize_barangay(part, canonical)
        if name and name not in found:
            found.append(name)
    # Also catch "X, Mapandan (27)" style single strings already handled.
    if not found:
        name = normalize_barangay(value, canonical)
        if name:
            found.append(name)
    return found


def parse_fdp_date(value):
    """Parse dirty FDP date strings to YYYY-MM-DD, else None.

    Handles "May 19, 2023 at 9:00 AM", ISO dates, and junk commonly
    found in FDP sheets: empty strings, year-less dates
    ("December 11 at 9:00 AM"), and amounts misfiled in date columns.
    """
    if value is None:
        return None
    s = str(value).strip().rstrip(".").strip()
    if not s:
        return None
    # Amounts misfiled in date columns ("1498197.06").
    if re.fullmatch(r"[\d,]+\.\d+", s):
        return None
    # Tolerate missing space after comma ("June 08,2026").
    s = re.sub(r",(?=\d)", ", ", s)
    # Drop trailing time clauses (" at 9:00 AM", " at 10:00 AM .").
    s = re.sub(r"(?i)\s+at\s+\d{1,2}:\d{2}(\s*[AP]\.?M\.?)?\s*$", "", s).strip()
    # Require a 4-digit year; FDP sheets sometimes omit it.
    if not re.search(r"\b(19|20)\d{2}\b", s):
        return None
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            from datetime import datetime
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Last resort: pandas-style fuzzy parse is intentionally avoided;
    # fall back to a strict year-month-day search.
    m = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", s)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return None
