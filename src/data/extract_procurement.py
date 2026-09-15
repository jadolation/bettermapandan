#!/usr/bin/env python3
"""Extract Mapandan procurement data from PhilGEPS parquet."""
import json
from pathlib import Path

import pandas as pd
from ._utils import clean, write_json

CACHE_DIR = Path("datasets/PhilGEPS")
OUTPUT = Path("src/data/procurement.json")


def main():
    philgeps_path = CACHE_DIR / "philgeps.parquet"
    if not philgeps_path.exists():
        raise SystemExit(f"ERROR: {philgeps_path} not found")

    print(f"Loading {philgeps_path} ...")
    df = pd.read_parquet(philgeps_path)

    mask = df["organization_name"].str.contains("Mapandan", case=False, na=False)
    mapandan = df[mask].copy()
    print(f"  Mapandan records: {len(mapandan)}")

    if len(mapandan) == 0:
        raise SystemExit("No Mapandan records found.")

    mapandan["award_date"] = pd.to_datetime(mapandan["award_date"], errors="coerce")
    mapandan = mapandan.sort_values("award_date", ascending=False)

    total_amount = float(mapandan["contract_amount"].fillna(0).sum())
    contract_count = int(len(mapandan))
    average_cost = total_amount / contract_count if contract_count > 0 else 0.0
    unique_categories = int(mapandan["business_category"].nunique()) if "business_category" in mapandan.columns else 0

    monthly = (
        mapandan.dropna(subset=["award_date"])
        .assign(month=lambda d: d["award_date"].dt.strftime("%Y-%m"))
        .groupby("month", sort=False)["contract_amount"]
        .sum()
        .reset_index()
        .sort_values("month")
    )
    monthly_trend = [
        {"month": row["month"], "total": float(row["contract_amount"])}
        for _, row in monthly.iterrows()
    ]

    awardee_totals = (
        mapandan.groupby(mapandan["awardee_name"].fillna("").str.strip(), sort=False)["contract_amount"]
        .sum()
        .reset_index()
        .rename(columns={"awardee_name": "name"})
        .sort_values("contract_amount", ascending=False)
        .head(10)
    )
    top_awardees = [
        {"name": clean(row["name"]), "total": float(row["contract_amount"])}
        for _, row in awardee_totals.iterrows()
    ]

    records = []
    for _, row in mapandan.iterrows():
        amount = row.get("contract_amount")
        try:
            amount_f = float(amount) if pd.notna(amount) else 0.0
        except (ValueError, TypeError):
            amount_f = 0.0

        award_date = row.get("award_date")
        if pd.notna(award_date):
            award_date_str = str(award_date)[:10]
        else:
            award_date_str = ""

        records.append({
            "title": clean(row.get("award_title", "")),
            "awardee": clean(row.get("awardee_name", "")),
            "amount": amount_f,
            "award_date": award_date_str,
            "status": clean(row.get("award_status", "")),
            "area": clean(row.get("area_of_delivery", "")),
            "business_category": clean(row.get("business_category", "")),
            "reference_id": clean(row.get("reference_id", "")),
            "contract_no": clean(row.get("contract_no", "")),
            "organization_name": clean(row.get("organization_name", "")),
        })

    output = {
        "metrics": {
            "total_amount": total_amount,
            "contract_count": contract_count,
            "average_cost": average_cost,
            "unique_categories": unique_categories,
            "source": "PhilGEPS",
            "aggregator": "BetterGov.ph Open Data Portal",
            "dataset_id": 5,
            "license": "CC0 1.0 Universal",
            "last_updated": pd.Timestamp.now().isoformat()[:10],
        },
        "monthly_trend": monthly_trend,
        "top_awardees": top_awardees,
        "contracts": records,
    }

    from ._utils import write_json
    write_json(OUTPUT, output)
    print(f"Wrote {len(records)} contracts to {OUTPUT}")
    print(f"Total: ₱{total_amount:,.0f} across {contract_count} contracts")
    print(f"Unique categories: {unique_categories}")
    print(f"Average cost: ₱{average_cost:,.0f}")
    print(f"Monthly trend points: {len(monthly_trend)}")
    print(f"Top awardees: {len(top_awardees)}")


if __name__ == "__main__":
    main()
