#!/usr/bin/env python3
"""Dump DILG FDP workbooks to raw per-sheet CSVs for local analysis.

Reads datasets/fdp/<year>/*.xlsx and writes one CSV per worksheet to
datasets/fdp-csv/<year>/<workbook>__<sheet>.csv. Values are kept raw:
empty cells become empty fields, datetimes become ISO strings, numbers
and text pass through otherwise untouched (merged cells only carry the
top-left value — openpyxl behavior).

Not wired into build.py; output dir is git-ignored (local use only).

Usage:
    python3 src/data/fdp_to_csv.py [--out DIR] [--year YYYY]
"""
import argparse
import csv
import re
import sys
from datetime import date, datetime
from pathlib import Path

try:
    import openpyxl
except ImportError:
    sys.exit("openpyxl is required: pip install openpyxl")

ROOT = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = ROOT / "datasets" / "fdp"
DEFAULT_OUT = ROOT / "datasets" / "fdp-csv"

SKIP_SHEETS = {"FDPP LICENSE"}
SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize(name: str) -> str:
    """Make a workbook/sheet name safe for use in a file name."""
    return SAFE_CHARS.sub("_", name).strip("._") or "sheet"


def cell_to_text(value):
    """Render a raw openpyxl cell value as CSV-safe text."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return " ".join(value.split())
    return str(value)


def dump_sheet(ws, csv_path: Path) -> int:
    """Write one worksheet to CSV. Returns the row count written."""
    rows = list(ws.iter_rows(values_only=True))
    # Trim trailing fully-empty rows/cols for compact output.
    while rows and all(v is None for v in rows[-1]):
        rows.pop()
    width = max((len(r) for r in rows), default=0)
    while width and all(r[width - 1] is None for r in rows):
        width -= 1
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        for row in rows:
            writer.writerow([cell_to_text(v) for v in list(row)[:width]])
    return len(rows)


def convert_workbook(path: Path, out_dir: Path) -> tuple[int, int]:
    """Convert one .xlsx to per-sheet CSVs. Returns (csvs_written, sheets_skipped)."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    written, skipped = 0, 0
    try:
        for ws in wb.worksheets:
            if ws.title in SKIP_SHEETS:
                skipped += 1
                continue
            csv_path = out_dir / f"{sanitize(path.stem)}__{sanitize(ws.title)}.csv"
            if csv_path.exists() and csv_path.stat().st_mtime >= path.stat().st_mtime:
                written += 1  # Fresh enough; count as done without rewriting.
                continue
            dump_sheet(ws, csv_path)
            written += 1
    finally:
        wb.close()
    return written, skipped


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output directory")
    parser.add_argument("--year", help="only convert one year folder (e.g. 2025)")
    args = parser.parse_args(argv)

    years = [args.year] if args.year else sorted(p.name for p in CACHE_DIR.iterdir() if p.is_dir())
    files = csv_total = skip_total = errors = 0
    for year in years:
        year_dir = CACHE_DIR / year
        if not year_dir.is_dir():
            print(f"no such year folder: {year_dir}", file=sys.stderr)
            errors += 1
            continue
        out_dir = args.out / year
        out_dir.mkdir(parents=True, exist_ok=True)
        for path in sorted(year_dir.glob("*.xlsx")):
            files += 1
            try:
                written, skipped = convert_workbook(path, out_dir)
                csv_total += written
                skip_total += skipped
            except Exception as exc:  # noqa: BLE001 - log and continue with next workbook
                errors += 1
                print(f"FAILED {path}: {exc}", file=sys.stderr)
    print(f"{files} workbook(s) -> {csv_total} csv(s), {skip_total} sheet(s) skipped, {errors} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
