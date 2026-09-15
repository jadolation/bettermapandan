#!/usr/bin/env python3
"""Shared utilities for Mapandan data extraction scripts."""
import json
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
