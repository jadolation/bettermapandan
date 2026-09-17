import html
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

try:
    from src.data.schemas import validate_all
    HAS_SCHEMA_VALIDATION = True
except ImportError:
    HAS_SCHEMA_VALIDATION = False

ROOT = Path(__file__).resolve().parent.parent
SRC_PAGES = ROOT / "src" / "pages"
SRC_PARTIALS = ROOT / "src" / "partials"
SRC_DATA = ROOT / "src" / "data"
SRC_TEMPLATES = ROOT / "src" / "templates"
LOCALES_DIR = ROOT / "locales"
FIL_DIR = ROOT / "fil"

SITE_CONFIG = {
    "REPO_URL": "https://github.com/jadolation/bettermapandan.git",
}

SECTION_ANCHORS = {
    "government.html": [
        ("executive", "Executive Branch"),
        ("legislative", "Legislative Branch"),
        ("barangay-councils", "Barangay Councils"),
        ("contacts", "Contact Directory"),
    ],
    "legislative.html": [
        ("governance-framework", "Local governance"),
        ("ordinances", "Municipal ordinances"),
        ("resolutions", "Resolutions"),
        ("executive-issuances", "Executive issuances"),
        ("fiscal", "Budgets"),
        ("trends", "Legislative trends"),
    ],
    "statistics.html": [
        ("population", "Demographic overview"),
        ("economy", "Economic indicators"),
        ("fiscal-data", "Revenue"),
    ],
    "transparency.html": [
        ("appropriations", "Current budget"),
        ("budget-trend", "Multi-year appropriations"),
        ("revenue", "Revenue"),
        ("fiscal-snapshot", "Fiscal snapshot"),
        ("financial-performance", "Financial Performance"),
        ("audit-opinion-timeline", "Audit History"),
        ("audit-findings", "Audit Findings"),
        ("implementation-rate", "Accountability"),
        ("compliance", "Compliance"),
        ("audit-reports", "Audit Reports"),
        ("coa-projects", "COA Infrastructure Projects"),
        ("disallowances", "Disallowances"),
        ("reform-trackers", "Reform Trackers"),
        ("capital-projects", "Capital Projects"),
        ("recent-projects", "Recent Projects"),
        ("social", "Social Programs"),
        ("external-links", "External Platforms"),
    ],
}

FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)

LANGUAGES = [
    ("en", ROOT, False),
    ("fil", FIL_DIR, True),
]
