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
    "budget-fiscal.html": [
        ("fiscal-dashboard", "Fiscal dashboard"),
        ("appropriations", "Current budget"),
        ("revenue", "Revenue"),
        ("fiscal-structure", "Fiscal structure"),
        ("fiscal-snapshot", "Fiscal snapshot"),
        ("budget-trend", "Multi-year appropriations"),
        ("balance-sheet", "Balance sheet"),
        ("financial-performance", "Financial Performance"),
        ("fdp-disclosures", "FDP filings"),
    ],
    "audit-compliance.html": [
        ("audit-opinion-timeline", "Audit History"),
        ("compliance", "Compliance"),
        ("audit-findings", "Audit Findings"),
        ("implementation-rate", "Accountability"),
        ("coa-projects", "COA Infrastructure Projects"),
        ("disallowances", "Disallowances"),
        ("reform-trackers", "Reform Trackers"),
        ("audit-reports", "Audit Reports"),
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

# In-page section nav (desktop sidebar + mobile edge dots).
# Ordered section ids per long-form page; labels come from locales
# (transparency.nav_<id with dashes as underscores>), badges count <h3>
# sub-headings per section at build. Children render as a collapsible group.
SECTION_NAV = {
    "budget-fiscal.html": [
        "fiscal-dashboard",
        "appropriations",
        "revenue",
        "fiscal-structure",
        "fiscal-snapshot",
        "budget-trend",
        "balance-sheet",
        "financial-performance",
        "fdp-disclosures",
    ],
    "audit-compliance.html": [
        "audit-opinion-timeline",
        "compliance",
        "audit-findings",
        "implementation-rate",
        "coa-projects",
        "disallowances",
        "reform-trackers",
        "audit-reports",
    ],
}

# Sections with nested sub-nav (collapsible). Sub-items are extracted from
# the section body's id'd headings at build (capped in the builder).
SECTION_NAV_CHILDREN = {
    "audit-findings",
}

# Lucide line icons per section (rendered as <i data-lucide>).
SECTION_NAV_ICONS = {
    "fiscal-dashboard": "gauge",
    "appropriations": "wallet",
    "revenue": "trending-up",
    "fiscal-structure": "layers",
    "fiscal-snapshot": "camera",
    "budget-trend": "activity",
    "balance-sheet": "scale",
    "financial-performance": "calculator",
    "fdp-disclosures": "archive",
    "audit-opinion-timeline": "history",
    "compliance": "shield-check",
    "audit-findings": "file-search",
    "implementation-rate": "list-checks",
    "coa-projects": "building-2",
    "disallowances": "flag",
    "reform-trackers": "route",
    "audit-reports": "file-text",
}

LANGUAGES = [
    ("en", ROOT, False),
    ("fil", FIL_DIR, True),
]
