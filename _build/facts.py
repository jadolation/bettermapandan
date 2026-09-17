"""Shared municipal facts — single source of truth for headline figures.

Values live in src/data/municipal-facts.json. Pages reference them via
{POP_2024} / {LAND_AREA} / {DENSITY} placeholders resolved at build time
by orchestrator.resolve_body_placeholders, so a census update touches
one file instead of 20 literals across 4 pages.
"""
import json
from pathlib import Path

FACTS_PATH = Path(__file__).resolve().parent.parent / "src" / "data" / "municipal-facts.json"


def load_facts() -> dict:
    """Load canonical facts; fall back to hardcoded values if missing."""
    try:
        return json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "population_2024": "38,228",
            "land_area_km2": "32.92",
            "density_per_km2": "1,161.24",
        }


def facts_placeholders() -> dict:
    """Placeholder values merged into every page body at build time."""
    facts = load_facts()
    pop = facts.get("population_2024", "38,228")
    land = facts.get("land_area_km2", "32.92")
    density = facts.get("density_per_km2", "1,161.24")
    return {
        "POP_2024": pop,
        "LAND_AREA": f"{land} km&sup2;",
        "DENSITY": density,
    }
