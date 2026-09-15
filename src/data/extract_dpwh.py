#!/usr/bin/env python3
"""Extract Mapandan DPWH infrastructure data from raw exports."""
import json
from pathlib import Path

import pandas as pd
from ._utils import clean, parse_date, parse_money, fiscal_year_from_contract_id, to_float

CACHE_DIR = Path("datasets/dpwh")
OUTPUT = Path("src/data/dpwh.json")


def main():
    if not CACHE_DIR.exists():
        raise SystemExit(f"ERROR: {CACHE_DIR} not found")

    parquet = CACHE_DIR / "dpwh.parquet"
    csv = CACHE_DIR / "dpwh.csv"
    if parquet.exists():
        df = pd.read_parquet(parquet)
    elif csv.exists():
        df = pd.read_csv(csv)
    else:
        raise SystemExit(f"ERROR: no dpwh.parquet or dpwh.csv in {CACHE_DIR}")

    mask = (
        df["project_name"].astype(str).str.contains("Mapandan", case=False, na=False)
        | df["barangay_location"].astype(str).str.contains("Mapandan", case=False, na=False)
        | df["organization_name"].astype(str).str.contains("Mapandan", case=False, na=False)
    )
    mapandan = df[mask].copy()
    print(f"  Mapandan DPWH records: {len(mapandan)}")

    if len(mapandan) == 0:
        raise SystemExit("No Mapandan records found.")

    projects = []
    for _, row in mapandan.iterrows():
        contract_id = clean(row.get("contract_id") or row.get("reference_id") or "", max_len=500)
        project_name = clean(row.get("project_name") or row.get("contract_description") or "", max_len=500)
        category = clean(row.get("category") or row.get("project_category") or "", max_len=500)
        executing_agency = clean(row.get("executing_agency") or row.get("implementing_office") or "", max_len=500)
        contractor = clean(row.get("contractor") or row.get("winning_contractor") or "", max_len=500)
        contractor_id = clean(row.get("contractor_id") or "", max_len=500)
        approved_budget = parse_money(row.get("approved_budget"))
        contract_amount = parse_money(row.get("contract_amount") or row.get("contract_cost"))
        accomplishment = row.get("accomplishment_percent") or row.get("accomplishment")
        try:
            accomplishment_percent = float(accomplishment) if pd.notna(accomplishment) else 0.0
        except (ValueError, TypeError):
            accomplishment_percent = 0.0
        status = clean(row.get("status") or row.get("contract_status") or "", max_len=500)
        fiscal_year = fiscal_year_from_contract_id(contract_id)
        source_of_funds = clean(row.get("source_of_funds") or row.get("funding_source") or "", max_len=500)
        contract_effectivity_date = parse_date(row.get("contract_effectivity_date") or row.get("effectivity_date"))
        contract_expiry_date = parse_date(row.get("contract_expiry_date") or row.get("expiry_date"))
        actual_start_date = parse_date(row.get("actual_start_date") or row.get("start_date"))
        actual_completion_date = parse_date(row.get("actual_completion_date") or row.get("completion_date"))
        barangay_location = clean(row.get("barangay_location") or "", max_len=500)
        latitude = row.get("latitude")
        longitude = row.get("longitude")
        try:
            latitude = float(latitude) if pd.notna(latitude) else None
        except (ValueError, TypeError):
            latitude = None
        try:
            longitude = float(longitude) if pd.notna(longitude) else None
        except (ValueError, TypeError):
            longitude = None
        project_components = []
        bidders = []
        procurement_activities = []
        source_document_url = clean(row.get("source_document_url") or "https://transparency.dpwh.gov.ph/", max_len=500)

        projects.append({
            "transaction_id": f"DPWH-{fiscal_year or 0000}-{contract_id}" if fiscal_year else f"DPWH-{contract_id}",
            "contract_id": contract_id,
            "project_name": project_name,
            "category": category,
            "executing_agency": executing_agency,
            "contractor": contractor,
            "contractor_id": contractor_id,
            "approved_budget": approved_budget,
            "contract_amount": contract_amount,
            "accomplishment_percent": accomplishment_percent,
            "status": status,
            "fiscal_year": fiscal_year,
            "source_of_funds": source_of_funds,
            "contract_effectivity_date": contract_effectivity_date,
            "contract_expiry_date": contract_expiry_date,
            "actual_start_date": actual_start_date,
            "actual_completion_date": actual_completion_date,
            "barangay_location": barangay_location,
            "latitude": latitude,
            "longitude": longitude,
            "project_components": project_components,
            "bidders": bidders,
            "procurement_activities": procurement_activities,
            "source_document_url": source_document_url,
            "crossref": {},
        })

    output = {"projects": projects}
    from ._utils import write_json
    write_json(OUTPUT, output)
    print(f"Wrote {len(projects)} projects to {OUTPUT}")


if __name__ == "__main__":
    main()
