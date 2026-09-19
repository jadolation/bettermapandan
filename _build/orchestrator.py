import shutil
import json
import sys
from pathlib import Path

from _build.config import (
    SRC_PAGES,
    ROOT,
    SRC_PARTIALS,
    SRC_DATA,
    SRC_TEMPLATES,
    FIL_DIR,
    PAG_DIR,
    SITE_CONFIG,
    SECTION_ANCHORS,
    FRONT_MATTER_RE,
    LANGUAGES,
    validate_all,
    HAS_SCHEMA_VALIDATION,
)
from _build.locales import load_locale, t
from _build.facts import facts_placeholders
from _build.templates import parse_page, fill, strip_html, strip_front_matter, compute_url, compute_asset_base, to_folder_index
from _build.generators.services import generate_services
from _build.generators.legislative import generate_legislative
from _build.generators.dpwh import generate_dpwh, _build_dpwh_labels
from _build.generators.fdp import generate_fdp, generate_fdp_dashboard
from _build.generators.fdp_analytics import generate_fdp_summary
from _build.generators.procurement import generate_procurement, generate_homepage_procurement_data, generate_homepage_dpwh_data
from _build.generators.barangays import validate_barangays, generate_barangays, build_barangay_comparison_script, generate_barangay_councils_table
from _build.assets import minify_assets, compress_images, generate_sitemap, generate_llms_txt
from _build.lint import verify_translations


def deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base. Override values take precedence.
    Empty strings in override are treated as missing (fall back to base).
    """
    result = dict(base)
    for key, value in override.items():
        if value == "":
            continue
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def build_lang_switcher_urls(rel: Path, lang_code: str) -> dict[str, str]:
    """Build language switcher URLs for a page."""
    clean = to_folder_index(rel)
    if clean.name == "index.html":
        folder = "" if not clean.parent or clean.parent == Path(".") else str(clean.parent)
    else:
        folder = str(clean.parent / clean.stem)
    return {
        "en": f"/{folder}/" if folder else "/",
        "fil": f"/fil/{folder}/" if folder else "/fil/",
        "pag": f"/pag/{folder}/" if folder else "/pag/",
    }


def build_breadcrumbs(locale: dict, rel: Path, page_title: str) -> str:
    """Build breadcrumb HTML for a page. Only shown on service pages."""
    clean = to_folder_index(rel)
    depth = len(clean.parts) - 1
    if depth <= 0:
        return ""
    section_slug = clean.parts[0]
    if section_slug != "services":
        return ""
    home_href = "../" * depth
    if depth == 1:
        bc_items = [
            f'<a href="{home_href}">{t(locale, "nav.home", "Home")}</a>',
            f'<span aria-current="page">{section_slug.replace("-", " ").title()}</span>',
        ]
    else:
        section_href = "../" * (depth - 1)
        bc_items = [
            f'<a href="{home_href}">{t(locale, "nav.home", "Home")}</a>',
            f'<a href="{section_href}">{section_slug.replace("-", " ").title()}</a>',
            f'<span aria-current="page">{page_title}</span>',
        ]
    return '<div class="wrap"><nav class="breadcrumb" aria-label="Breadcrumb">' + " &rsaquo; ".join(bc_items) + "</nav></div>\n"


SECTION_NAMES = {
    "about": "nav.about",
    "government": "nav.government",
    "legislative": "nav.legislative",
    "statistics": "nav.statistics",
    "transparency": "nav.transparency",
    "search": "nav.search",
    "support": "nav.support",
    "services": "nav.services",
}


def build_breadcrumb_jsonld(locale: dict, rel: Path, page_title: str, lang_code: str) -> str:
    """Build BreadcrumbList JSON-LD for a page. Returns empty string for homepage."""
    clean = to_folder_index(rel)
    depth = len(clean.parts) - 1
    if depth <= 0:
        return ""

    base_url = "https://bettermapandan.org"
    lang_prefix = f"/{lang_code}/" if lang_code != "en" else "/"
    home_name = t(locale, "nav.home", "Home")

    items: list[dict[str, object]] = []

    def _add(position: int, name: str, url: str | None = None) -> None:
        entry: dict[str, object] = {
            "@type": "ListItem",
            "position": position,
            "name": name,
        }
        if url is not None:
            entry["item"] = url
        items.append(entry)

    _add(1, home_name, f"{base_url}{lang_prefix}")

    section_slug = clean.parts[0]

    if section_slug == "services":
        svc_name = t(locale, "nav.services", "Services")
        svc_url = f"{base_url}{lang_prefix}services/"
        if depth == 1:
            _add(2, svc_name)
        else:
            _add(2, svc_name, svc_url)
            _add(3, page_title)
    elif section_slug == "support":
        support_name = t(locale, "nav.support", "Support")
        support_url = f"{base_url}{lang_prefix}support/"
        if depth == 1:
            _add(2, support_name)
        else:
            _add(2, support_name, support_url)
            _add(3, page_title)
    else:
        key = SECTION_NAMES.get(section_slug)
        if key:
            section_name = t(locale, key, section_slug.replace("-", " ").title())
        else:
            section_name = section_slug.replace("-", " ").title()
        _add(2, section_name)

    schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": items,
    }
    jsonld = (
        '<script type="application/ld+json">\n'
        + json.dumps(schema, indent=2, ensure_ascii=False)
        + "\n</script>\n"
    )
    alternates = "".join(
        f'<xhtml:link rel="alternate" hreflang="{code}" href="{base_url}/{code}/"/>' if code != "en"
        else f'<xhtml:link rel="alternate" hreflang="en" href="{base_url}/"/>'
        for code, _, _ in LANGUAGES
    )
    return jsonld + alternates


def build_header(locale: dict, asset_base: str, lang_code: str, lang_urls: dict[str, str]) -> str:
    """Build the site header with navigation and locale strings."""
    header_raw = (SRC_PARTIALS / "header.html").read_text(encoding="utf-8")
    return fill(header_raw, {
        "ASSET_BASE": asset_base,
        "NAV_HOME": t(locale, "nav.home", "Home"),
        "NAV_SERVICES": t(locale, "nav.services", "Services"),
        "NAV_GOVERNMENT": t(locale, "nav.government", "Government"),
        "NAV_LEGISLATIVE": t(locale, "nav.legislative", "Legislative"),
        "NAV_STATISTICS": t(locale, "nav.statistics", "Statistics"),
        "NAV_TRANSPARENCY": t(locale, "nav.transparency", "Transparency"),
        "NAV_ABOUT": t(locale, "nav.about", "About"),
        "NAV_SEARCH": t(locale, "nav.search", "Search"),
        "NAV_MENU": t(locale, "nav.menu", "Menu"),
        "EMERGENCY_LABEL": t(locale, "emergency.label", "Emergency"),
        "EMERGENCY_MDRRMO": t(locale, "emergency.mdrrmo", "MDRRMO"),
        "EMERGENCY_FIRE": t(locale, "emergency.fire", "Fire (BFP)"),
        "EMERGENCY_POLICE": t(locale, "emergency.police", "Police (PNP)"),
        "LANG_EN_URL": lang_urls["en"],
        "LANG_FIL_URL": lang_urls["fil"],
        "LANG_PAG_URL": lang_urls["pag"],
        "LANG_ACTIVE_EN": "active" if lang_code == "en" else "",
        "LANG_ACTIVE_FIL": "active" if lang_code == "fil" else "",
        "LANG_ACTIVE_PAG": "active" if lang_code == "pag" else "",
        "LANG_LABEL_EN": t(locale, "lang_switch.en", "EN"),
        "LANG_LABEL_FIL": t(locale, "lang_switch.fil", "FIL"),
        "LANG_LABEL_PAG": t(locale, "lang_switch.pag", "PAG"),
    })


def build_footer(locale: dict, asset_base: str) -> str:
    """Build the site footer with locale strings."""
    footer_raw = (SRC_PARTIALS / "footer.html").read_text(encoding="utf-8")
    return fill(footer_raw, {
        "ASSET_BASE": asset_base,
        **SITE_CONFIG,
        "NAV_HOME": t(locale, "nav.home", "Home"),
        "NAV_SERVICES": t(locale, "nav.services", "Services"),
        "NAV_GOVERNMENT": t(locale, "nav.government", "Government"),
        "NAV_LEGISLATIVE": t(locale, "nav.legislative", "Legislative"),
        "NAV_STATISTICS": t(locale, "nav.statistics", "Statistics"),
        "NAV_TRANSPARENCY": t(locale, "nav.transparency", "Transparency"),
        "NAV_ABOUT": t(locale, "nav.about", "About"),
        "FOOTER_BRAND_DESC": t(locale, "footer.brand_desc", ""),
        "FOOTER_QUICK_LINKS": t(locale, "footer.quick_links", "Quick Links"),
        "FOOTER_RESOURCES": t(locale, "footer.resources", "Resources"),
        "FOOTER_PROJECT": t(locale, "footer.project", "Project"),
        "FOOTER_SITEMAP": t(locale, "footer.sitemap", "Sitemap"),
        "FOOTER_FAQ": t(locale, "footer.faq", "FAQ"),
        "FOOTER_SOURCE_CODE": t(locale, "footer.source_code", "Source Code (GitHub)"),
        "FOOTER_PRIVACY": t(locale, "footer.privacy", "Privacy Policy"),
        "FOOTER_TERMS": t(locale, "footer.terms", "Terms of Use"),
        "FOOTER_ACCESSIBILITY": t(locale, "footer.accessibility", "Accessibility"),
        "FOOTER_REPORT": t(locale, "footer.report", "Report Incorrect Info"),
        "FOOTER_COPYRIGHT": t(locale, "footer.copyright", ""),
        "FOOTER_COMMUNITY": t(locale, "footer.community", ""),
        "FOOTER_COST": t(locale, "footer.cost", "Cost to the People of Mapandan:"),
        "FOOTER_COST_AMOUNT": t(locale, "footer.cost_amount", "₱0"),
        "FOOTER_MUNICIPALITY": t(locale, "footer.municipality_of", "Municipality of Mapandan"),
        "FOOTER_PROVINCE": t(locale, "footer.province_of", "Province of Pangasinan"),
        "FOOTER_COA": t(locale, "footer.coa", "Commission on Audit"),
        "FOOTER_PSA": t(locale, "footer.psa", "Philippine Statistics Authority"),
    })


def resolve_body_placeholders(body: str, locale: dict, asset_base: str) -> str:
    """Resolve all locale placeholders in page body content."""
    return fill(body, {
        "ASSET_BASE": asset_base,
        **facts_placeholders(),
        ** _build_page_body_labels(locale),
        ** _build_homepage_labels(locale),
        ** _build_statistics_labels(locale),
        ** _build_transparency_labels(locale),
        ** _build_search_labels(locale),
    })


def _build_page_body_labels(locale: dict) -> dict:
    return {
        "ABOUT_CONTRIBUTE_CODE": t(locale, "about.contribute_code", ""),
        "ABOUT_CONTRIBUTE_GET_INVOLVED": t(locale, "about.contribute_get_involved", ""),
        "ABOUT_CONTRIBUTE_REPORT": t(locale, "about.contribute_report", ""),
        "ABOUT_CONTRIBUTE_SHARE": t(locale, "about.contribute_share", ""),
        "ABOUT_CONTRIBUTE_VERIFY": t(locale, "about.contribute_verify", ""),
        "ABOUT_DISCLAIMER_NOTICE": t(locale, "about.disclaimer_notice", ""),
        "ABOUT_GEOGRAPHY": t(locale, "about.geography", ""),
        "ABOUT_HISTORY": t(locale, "about.history", ""),
        "ABOUT_HISTORY_ERA1": t(locale, "about.history_era1", ""),
        "ABOUT_HISTORY_ERA2": t(locale, "about.history_era2", ""),
        "ABOUT_HISTORY_ERA3": t(locale, "about.history_era3", ""),
        "ABOUT_HISTORY_ERA5": t(locale, "about.history_era5", ""),
        "ABOUT_HISTORY_TITLE": t(locale, "about.history_title", ""),
        "ABOUT_MUNICIPALITY_TITLE": t(locale, "about.municipality_title", ""),
        "ABOUT_PHOTO_BRIDGE": t(locale, "about.photo_bridge", ""),
        "ABOUT_PHOTO_MARKET": t(locale, "about.photo_market", ""),
        "ABOUT_PHOTO_OFFICIALS": t(locale, "about.photo_officials", ""),
        "ABOUT_PHOTO_PLAZA": t(locale, "about.photo_plaza", ""),
        "ABOUT_PHOTO_SCHOOL": t(locale, "about.photo_school", ""),
        "ABOUT_POPULATION_GROWTH": t(locale, "about.population_growth", ""),
        "ABOUT_POPULATION_SUBTITLE": t(locale, "about.population_subtitle", ""),
        "ABOUT_PROJECT_HOW": t(locale, "about.project_how", ""),
        "ABOUT_PROJECT_MISSION": t(locale, "about.project_mission", ""),
        "ABOUT_PROJECT_OPEN_SOURCE": t(locale, "about.project_open_source", ""),
        "ABOUT_PROJECT_VOLUNTEER": t(locale, "about.project_volunteer", ""),
        "ABOUT_PROJECT_WHAT": t(locale, "about.project_what", ""),
        "ABOUT_READ_MORE": t(locale, "about.read_more", ""),
        "ABOUT_SHOW_LESS": t(locale, "about.show_less", ""),
        "ABOUT_TITLE": t(locale, "about.title", ""),
        "COMMON_COMMUNITY_VERIFIED": t(locale, "common.community_verified", ""),
        "COMMON_DISCLAIMER": t(locale, "common.disclaimer", ""),
        "COMMON_MUNICIPAL_ESTIMATE": t(locale, "common.municipal_estimate", ""),
        "COMMON_NEEDS_VERIFICATION": t(locale, "common.needs_verification", ""),
        "COMMON_OFFICIAL": t(locale, "common.official", ""),
        "COMMON_PLACEHOLDER": t(locale, "common.placeholder", ""),
        "COMMON_PROVINCIAL_ESTIMATE": t(locale, "common.provincial_estimate", ""),
        "COMMON_STATUTORY": t(locale, "common.statutory", ""),
        "COMMON_UNOFFICIAL": t(locale, "common.unofficial", ""),
        "COMMON_VERIFIED": t(locale, "common.verified", ""),
        "EMERGENCY_FIRE": t(locale, "emergency.fire", ""),
        "EMERGENCY_LABEL": t(locale, "emergency.label", ""),
        "EMERGENCY_MDRRMO": t(locale, "emergency.mdrrmo", ""),
        "EMERGENCY_POLICE": t(locale, "emergency.police", ""),
        "GOVERNMENT_BARANGAY_COUNCILS_TITLE": t(locale, "government.barangay_councils_title", ""),
        "GOVERNMENT_CONTACT_COL_LANDLINE": t(locale, "government.contact_col_landline", ""),
        "GOVERNMENT_CONTACT_COL_MOBILE": t(locale, "government.contact_col_mobile", ""),
        "GOVERNMENT_CONTACT_COL_OFFICE": t(locale, "government.contact_col_office", ""),
        "GOVERNMENT_CONTACT_TITLE": t(locale, "government.contact_title", ""),
        "GOVERNMENT_DEPARTMENTS_TITLE": t(locale, "government.departments_title", ""),
        "GOVERNMENT_DEPT_COL_ACRONYM": t(locale, "government.dept_col_acronym", ""),
        "GOVERNMENT_DEPT_COL_LOCATION": t(locale, "government.dept_col_location", ""),
        "GOVERNMENT_DEPT_COL_OFFICE": t(locale, "government.dept_col_office", ""),
        "GOVERNMENT_EXECUTIVE_TITLE": t(locale, "government.executive_title", ""),
        "GOVERNMENT_EXTERNAL_TITLE": t(locale, "government.external_title", ""),
        "GOVERNMENT_LEGISLATIVE_TITLE": t(locale, "government.legislative_title", ""),
        "HERO_BROWSE_SERVICES": t(locale, "hero.browse_services", ""),
        "HERO_EYEBROW": t(locale, "hero.eyebrow", ""),
        "HERO_SEARCH_TITLE": t(locale, "hero.search_title", ""),
        "HERO_SEE_BUDGET": t(locale, "hero.see_budget", ""),
        "HERO_TITLE": t(locale, "hero.title", ""),
        "ACTION_HUB_SERVICES": t(locale, "action_hub.services", "Services"),
        "ACTION_HUB_BUDGET": t(locale, "action_hub.budget", "Budget"),
        "ACTION_HUB_LEGISLATION": t(locale, "action_hub.legislation", "Legislation"),
        "ACTION_HUB_HOTLINES": t(locale, "action_hub.hotlines", "Hotlines"),
        "HERO_LEDE": t(locale, "hero.subtitle", ""),
        "HERO_SEARCH_DESC": t(locale, "hero.search_desc", ""),
        "HERO_SEARCH_PLACEHOLDER": t(locale, "hero.search_placeholder", ""),
        "HERO_SEARCH_POPULAR": t(locale, "hero.search_popular", "Popular:"),
        ** _build_homepage_labels(locale),
        ** _build_statistics_labels(locale),
        ** _build_transparency_labels(locale),
        ** _build_dpwh_labels(locale),
        ** _build_search_labels(locale),
    }


def _build_homepage_labels(locale: dict) -> dict:
    return {
        "HOMEPAGE_AGRI_TITLE": t(locale, "homepage.agri_title", ""),
        "HOMEPAGE_BARANGAY_EYEBROW": t(locale, "homepage.barangay_eyebrow", ""),
        "HOMEPAGE_BARANGAY_TITLE": t(locale, "homepage.barangay_title", ""),
        "HOMEPAGE_CULTURAL_EYEBROW": t(locale, "homepage.cultural_eyebrow", ""),
        "HOMEPAGE_CULTURAL_TITLE": t(locale, "homepage.cultural_title", ""),
        "HOMEPAGE_EMERGENCY_BFP": t(locale, "homepage.emergency_bfp", ""),
        "HOMEPAGE_EMERGENCY_EYEBROW": t(locale, "homepage.emergency_eyebrow", ""),
        "HOMEPAGE_EMERGENCY_HOSPITAL": t(locale, "homepage.emergency_hospital", ""),
        "HOMEPAGE_EMERGENCY_MDRRMO_DESC": t(locale, "homepage.emergency_mdrmmo_desc", ""),
        "HOMEPAGE_EMERGENCY_PNP": t(locale, "homepage.emergency_pnp", ""),
        "HOMEPAGE_EMERGENCY_RHU": t(locale, "homepage.emergency_rhu", ""),
        "HOMEPAGE_EMERGENCY_TITLE": t(locale, "homepage.emergency_title", ""),
        "HOMEPAGE_EMERGENCY_WATER": t(locale, "homepage.emergency_water", ""),
        "HOMEPAGE_EXPLORE_EYEBROW": t(locale, "homepage.explore_eyebrow", ""),
        "HOMEPAGE_EXPLORE_TITLE": t(locale, "homepage.explore_title", ""),
        "HOMEPAGE_HISTORY_CTA": t(locale, "homepage.history_cta", ""),
        "HOMEPAGE_HISTORY_EYEBROW": t(locale, "homepage.history_eyebrow", ""),
        "HOMEPAGE_HISTORY_TITLE": t(locale, "homepage.history_title", ""),
        "HOMEPAGE_LEADERSHIP_CTA": t(locale, "homepage.leadership_cta", ""),
        "HOMEPAGE_LEADERSHIP_EYEBROW": t(locale, "homepage.leadership_eyebrow", ""),
        "HOMEPAGE_LEADERSHIP_TITLE": t(locale, "homepage.leadership_title", ""),
        "HOMEPAGE_MAP_TITLE": t(locale, "homepage.map_title", ""),
        "HOMEPAGE_MUNICIPALITY_AGRI": t(locale, "homepage.municipality_agri", ""),
        "HOMEPAGE_MUNICIPALITY_FOUNDED": t(locale, "homepage.municipality_founded", ""),
        "HOMEPAGE_MUNICIPALITY_REESTABLISHED": t(locale, "homepage.municipality_reestablished", ""),
        "HOMEPAGE_MUNICIPALITY_TITLE": t(locale, "homepage.municipality_title", ""),
        "HOMEPAGE_PLAZA_TITLE": t(locale, "homepage.plaza_title", ""),
        "HOMEPAGE_WEATHER_TITLE": t(locale, "homepage.weather_title", ""),
        "HOMEPAGE_MUNICIPALITY_EYEBROW": t(locale, "homepage.municipality_eyebrow", ""),
        "HOMEPAGE_MUNICIPALITY_DESC": t(locale, "homepage.municipality_desc", ""),
        "HOMEPAGE_FOUNDED_DESC": t(locale, "homepage.founded_desc", ""),
        "HOMEPAGE_REESTABLISHED_DESC": t(locale, "homepage.reestablished_desc", ""),
        "HOMEPAGE_AGRI_DESC_FULL": t(locale, "homepage.agri_desc_full", ""),
        "HOMEPAGE_HISTORY_SUBTITLE": t(locale, "homepage.history_subtitle", ""),
        "HOMEPAGE_MILESTONE1_ERA": t(locale, "homepage.milestone1_era", ""),
        "HOMEPAGE_MILESTONE1_TITLE": t(locale, "homepage.milestone1_title", ""),
        "HOMEPAGE_MILESTONE1_DESC": t(locale, "homepage.milestone1_desc", ""),
        "HOMEPAGE_MILESTONE2_ERA": t(locale, "homepage.milestone2_era", ""),
        "HOMEPAGE_MILESTONE2_TITLE": t(locale, "homepage.milestone2_title", ""),
        "HOMEPAGE_MILESTONE2_DESC": t(locale, "homepage.milestone2_desc", ""),
        "HOMEPAGE_MILESTONE3_ERA": t(locale, "homepage.milestone3_era", ""),
        "HOMEPAGE_MILESTONE3_TITLE": t(locale, "homepage.milestone3_title", ""),
        "HOMEPAGE_MILESTONE3_DESC": t(locale, "homepage.milestone3_desc", ""),
        "HOMEPAGE_MILESTONE4_ERA": t(locale, "homepage.milestone4_era", ""),
        "HOMEPAGE_MILESTONE4_TITLE": t(locale, "homepage.milestone4_title", ""),
        "HOMEPAGE_MILESTONE4_DESC": t(locale, "homepage.milestone4_desc", ""),
        "HOMEPAGE_BARANGAY_SUBTITLE": t(locale, "homepage.barangay_subtitle", ""),
        "HOMEPAGE_SOURCES_TITLE": t(locale, "homepage.sources_title", "Sources & Historical Notes"),
        "HOMEPAGE_SOURCES_DESC": t(locale, "homepage.sources_desc", ""),
        "HOMEPAGE_PANDAN_TITLE": t(locale, "homepage.pandan_title", "Pandan Festival"),
        "HOMEPAGE_PANDAN_DESC": t(locale, "homepage.pandan_desc", ""),
        "HOMEPAGE_PANDAN_CREDIT": t(locale, "homepage.pandan_credit", ""),
        "HOMEPAGE_PLAZA_DESC": t(locale, "homepage.plaza_desc", ""),
        "HOMEPAGE_PLAZA_CREDIT": t(locale, "homepage.plaza_credit", ""),
        "HOMEPAGE_AGRI_DESC": t(locale, "homepage.agri_desc", ""),
        "HOMEPAGE_AGRI_CREDIT": t(locale, "homepage.agri_credit", ""),
        "HOMEPAGE_MAYOR_NAME": t(locale, "homepage.mayor_name", ""),
        "HOMEPAGE_MAYOR_ROLE": t(locale, "homepage.mayor_role", "Municipal Mayor"),
        "HOMEPAGE_MAYOR_AFFIL": t(locale, "homepage.mayor_affil", ""),
        "HOMEPAGE_VICE_MAYOR_NAME": t(locale, "homepage.vice_mayor_name", ""),
        "HOMEPAGE_VICE_MAYOR_ROLE": t(locale, "homepage.vice_mayor_role", "Vice Mayor &middot; Presiding Officer"),
        "HOMEPAGE_VICE_MAYOR_AFFIL": t(locale, "homepage.vice_mayor_affil", "Independent (IND)"),
        "HOMEPAGE_LEADER_SOURCE": t(locale, "homepage.leader_source", "Source: Mapandan.gov.ph"),
        "HOMEPAGE_WEATHER_LOADING": t(locale, "homepage.weather_loading", "Loading weather data..."),
        "HOMEPAGE_WEATHER_CTA": t(locale, "homepage.weather_cta", "View PAGASA Advisories &rarr;"),
        "HOMEPAGE_MAP_CTA": t(locale, "homepage.map_cta", "Open in Google Maps &rarr;"),
        "HOMEPAGE_TRANSPARENCY_DESC": t(locale, "homepage.transparency_desc", ""),
        "HOMEPAGE_TRANSPARENCY_EYEBROW": t(locale, "homepage.transparency_eyebrow", ""),
        "HOMEPAGE_TRANSPARENCY_TITLE": t(locale, "homepage.transparency_title", ""),
        "STATS_BARANGAYS": t(locale, "stats.barangays", ""),
        "STATS_DENSITY": t(locale, "stats.density", ""),
        "STATS_HOUSEHOLDS": t(locale, "stats.households", ""),
        "STATS_LAND_AREA": t(locale, "stats.land_area", ""),
        "STATS_RESIDENTS": t(locale, "stats.residents", ""),
    }


def _build_statistics_labels(locale: dict) -> dict:
    return {
        "STATISTICS_AGRI_CROPS": t(locale, "statistics.agri_crops", ""),
        "STATISTICS_AGRI_IRRIGATED": t(locale, "statistics.agri_irrigated", ""),
        "STATISTICS_AGRI_TITLE": t(locale, "statistics.agri_title", ""),
        "STATISTICS_CHART_DOWNLOAD": t(locale, "statistics.chart_download", ""),
        "STATISTICS_CHART_POP_TREND": t(locale, "statistics.chart_pop_trend", ""),
        "STATISTICS_ECON_AGRI_EMP": t(locale, "statistics.econ_agri_emp", ""),
        "STATISTICS_ECON_DYNAMISM": t(locale, "statistics.econ_dynamism", ""),
        "STATISTICS_ECON_LABOR": t(locale, "statistics.econ_labor", ""),
        "STATISTICS_ECON_POVERTY": t(locale, "statistics.econ_poverty", ""),
        "STATISTICS_ECON_TITLE": t(locale, "statistics.econ_title", ""),
        "STATISTICS_FISCAL_BALANCE_2025": t(locale, "statistics.fiscal_balance_2025", ""),
        "STATISTICS_FISCAL_BLGF": t(locale, "statistics.fiscal_blgf", ""),
        "STATISTICS_FISCAL_BLGF_TITLE": t(locale, "statistics.fiscal_blgf_title", ""),
        "STATISTICS_FISCAL_EXP_2025": t(locale, "statistics.fiscal_exp_2025", ""),
        "STATISTICS_FISCAL_REV_2025": t(locale, "statistics.fiscal_rev_2025", ""),
        "STATISTICS_FISCAL_TITLE": t(locale, "statistics.fiscal_title", ""),
        "STATISTICS_GROWTH_TITLE": t(locale, "statistics.growth_title", ""),
        "STATISTICS_LAND_BARANGAYS": t(locale, "statistics.land_barangays", ""),
        "STATISTICS_LAND_EYEBROW": t(locale, "statistics.land_eyebrow", ""),
        "STATISTICS_LAND_TITLE": t(locale, "statistics.land_title", ""),
        "STATISTICS_LAND_TOTAL": t(locale, "statistics.land_total", ""),
        "STATISTICS_LAND_URBAN_RURAL": t(locale, "statistics.land_urban_rural", ""),
        "STATISTICS_POP_DENSITY": t(locale, "statistics.pop_density", ""),
        "STATISTICS_POP_HOUSEHOLDS": t(locale, "statistics.pop_households", ""),
        "STATISTICS_POP_TITLE": t(locale, "statistics.pop_title", ""),
        "STATISTICS_POP_TOTAL": t(locale, "statistics.pop_total", ""),
        "STATISTICS_TITLE": t(locale, "statistics.title", ""),
        "STATISTICS_TRENDS_TITLE": t(locale, "statistics.trends_title", ""),
    }


def _build_transparency_labels(locale: dict) -> dict:
    return {
        "DPWH_EYEBROW": t(locale, "transparency.infrastructure_eyebrow", "DPWH &middot; Infrastructure"),
        "DPWH_TITLE": t(locale, "transparency.infrastructure_title", "Infrastructure Projects"),
        "DPWH_LEDE": t(locale, "transparency.infrastructure_lede", "DPWH contracts, road and flood-control projects, school buildings, and health facilities in Mapandan."),
        "TRANSPARENCY_APPROPRIATIONS_EYEBROW": t(locale, "transparency.appropriations_eyebrow", ""),
        "TRANSPARENCY_APPROPRIATIONS_TITLE": t(locale, "transparency.appropriations_title", ""),
        "TRANSPARENCY_AUDIT_TITLE": t(locale, "transparency.audit_title", ""),
        "TRANSPARENCY_BALANCE_ASSETS": t(locale, "transparency.balance_assets", ""),
        "TRANSPARENCY_BALANCE_EYEBROW": t(locale, "transparency.balance_eyebrow", ""),
        "TRANSPARENCY_BALANCE_LIABILITIES": t(locale, "transparency.balance_liabilities", ""),
        "TRANSPARENCY_BALANCE_NET": t(locale, "transparency.balance_net", ""),
        "TRANSPARENCY_BALANCE_TITLE": t(locale, "transparency.balance_title", ""),
        "TRANSPARENCY_BUDGET_2026": t(locale, "transparency.budget_2026", ""),
        "TRANSPARENCY_BUDGET_TREND_EYEBROW": t(locale, "transparency.budget_trend_eyebrow", ""),
        "TRANSPARENCY_CAPEX_EYEBROW": t(locale, "transparency.capex_eyebrow", ""),
        "TRANSPARENCY_CAPEX_TITLE": t(locale, "transparency.capex_title", ""),
        "TRANSPARENCY_COMPLIANCE_COA": t(locale, "transparency.compliance_coa", ""),
        "TRANSPARENCY_COMPLIANCE_FDP": t(locale, "transparency.compliance_fdp", ""),
        "TRANSPARENCY_COMPLIANCE_SGLG": t(locale, "transparency.compliance_sglg", ""),
        "TRANSPARENCY_COMPLIANCE_TITLE": t(locale, "transparency.compliance_title", ""),
        "TRANSPARENCY_CREDIT_EYEBROW": t(locale, "transparency.credit_eyebrow", ""),
        "TRANSPARENCY_CREDIT_TITLE": t(locale, "transparency.credit_title", ""),
        "TRANSPARENCY_EXPENDITURE_2025": t(locale, "transparency.expenditure_2025", ""),
        "TRANSPARENCY_EXTERNAL_EYEBROW": t(locale, "transparency.external_eyebrow", ""),
        "TRANSPARENCY_EXTERNAL_TITLE": t(locale, "transparency.external_title", ""),
        "TRANSPARENCY_FISCAL_DEV_FUND": t(locale, "transparency.fiscal_dev_fund", ""),
        "TRANSPARENCY_FISCAL_LDRRMF": t(locale, "transparency.fiscal_ldrrmf", ""),
        "TRANSPARENCY_FISCAL_NTA": t(locale, "transparency.fiscal_nta", ""),
        "TRANSPARENCY_FISCAL_PS_CAP": t(locale, "transparency.fiscal_ps_cap", ""),
        "TRANSPARENCY_FISCAL_SEF": t(locale, "transparency.fiscal_sef", ""),
        "TRANSPARENCY_FISCAL_SNAPSHOT_TITLE": t(locale, "transparency.fiscal_snapshot_title", ""),
        "TRANSPARENCY_FISCAL_STRUCTURE_EYEBROW": t(locale, "transparency.fiscal_structure_eyebrow", ""),
        "TRANSPARENCY_FISCAL_STRUCTURE_TITLE": t(locale, "transparency.fiscal_structure_title", ""),
        "TRANSPARENCY_HISTORICAL_EYEBROW": t(locale, "transparency.historical_eyebrow", ""),
        "TRANSPARENCY_HISTORICAL_INC_OPS": t(locale, "transparency.historical_inc_ops", ""),
        "TRANSPARENCY_HISTORICAL_MOOE": t(locale, "transparency.historical_mooe", ""),
        "TRANSPARENCY_HISTORICAL_TAX_REV": t(locale, "transparency.historical_tax_rev", ""),
        "TRANSPARENCY_HISTORICAL_TITLE": t(locale, "transparency.historical_title", ""),
        "TRANSPARENCY_HISTORICAL_TOTAL_EQUITY": t(locale, "transparency.historical_total_equity", ""),
        "TRANSPARENCY_HISTORICAL_TOTAL_OP_EXP": t(locale, "transparency.historical_total_op_exp", ""),
        "TRANSPARENCY_HISTORICAL_TOTAL_OP_INC": t(locale, "transparency.historical_total_op_inc", ""),
        "TRANSPARENCY_LATEST_COA_NOTE": t(locale, "transparency.latest_coa_note", ""),
        "TRANSPARENCY_PROCUREMENT_EYEBROW": t(locale, "transparency.procurement_eyebrow", ""),
        "TRANSPARENCY_PROCUREMENT_TITLE": t(locale, "transparency.procurement_title", ""),
        "TRANSPARENCY_REVENUE_2025": t(locale, "transparency.revenue_2025", ""),
        "TRANSPARENCY_REVENUE_TITLE": t(locale, "transparency.revenue_title", ""),
        "TRANSPARENCY_COA_PROJECTS_EYEBROW": t(locale, "transparency.coa_projects_eyebrow", ""),
        "TRANSPARENCY_COA_PROJECTS_TITLE": t(locale, "transparency.coa_projects_title", ""),
        "TRANSPARENCY_COA_PROJECTS_DESC": t(locale, "transparency.coa_projects_desc", ""),
        "TRANSPARENCY_COA_PROJECT_NAME": t(locale, "transparency.coa_project_name", ""),
        "TRANSPARENCY_COA_PROJECT_COST": t(locale, "transparency.coa_project_cost", ""),
        "TRANSPARENCY_COA_PROJECT_YEAR": t(locale, "transparency.coa_project_year", ""),
        "TRANSPARENCY_COA_PROJECT_CATEGORY": t(locale, "transparency.coa_project_category", ""),
        "TRANSPARENCY_COA_PROJECT_STATUS": t(locale, "transparency.coa_project_status", ""),
        "TRANSPARENCY_REFORM_EYEBROW": t(locale, "transparency.reform_eyebrow", ""),
        "TRANSPARENCY_REFORM_TITLE": t(locale, "transparency.reform_title", ""),
        "TRANSPARENCY_REFORM_DESC": t(locale, "transparency.reform_desc", ""),
        "TRANSPARENCY_DISALLOWANCES_EYEBROW": t(locale, "transparency.disallowances_eyebrow", ""),
        "TRANSPARENCY_DISALLOWANCES_TITLE": t(locale, "transparency.disallowances_title", ""),
        "TRANSPARENCY_DISALLOWANCES_DESC": t(locale, "transparency.disallowances_desc", ""),
        "TRANSPARENCY_SOCIAL_AGRI": t(locale, "transparency.social_agri", ""),
        "TRANSPARENCY_SOCIAL_EYEBROW": t(locale, "transparency.social_eyebrow", ""),
        "TRANSPARENCY_SOCIAL_TITLE": t(locale, "transparency.social_title", ""),
        "TRANSPARENCY_TITLE": t(locale, "transparency.title", ""),
        "AUDIT_OPINION_EYEBROW": t(locale, "transparency.audit_opinion_eyebrow", ""),
        "AUDIT_OPINION_TITLE": t(locale, "transparency.audit_opinion_title", ""),
        "AUDIT_OPINION_DESC": t(locale, "transparency.audit_opinion_desc", ""),
        "AUDIT_OPINION_CHART_TITLE": t(locale, "transparency.audit_opinion_chart_title", ""),
        "FINANCIAL_PERF_EYEBROW": t(locale, "transparency.financial_perf_eyebrow", ""),
        "FINANCIAL_PERF_TITLE": t(locale, "transparency.financial_perf_title", ""),
        "FINANCIAL_PERF_DESC": t(locale, "transparency.financial_perf_desc", ""),
        "FINANCIAL_PERF_ASSETS_TITLE": t(locale, "transparency.financial_perf_assets_title", ""),
        "FINANCIAL_PERF_INCOME_TITLE": t(locale, "transparency.financial_perf_income_title", ""),
        "FINANCIAL_PERF_REVENUE_TITLE": t(locale, "transparency.financial_perf_revenue_title", ""),
        "FINANCIAL_PERF_TABLE_TITLE": t(locale, "transparency.financial_perf_table_title", ""),
        "AUDIT_FINDINGS_EYEBROW": t(locale, "transparency.audit_findings_eyebrow", ""),
        "AUDIT_FINDINGS_TITLE": t(locale, "transparency.audit_findings_title", ""),
        "AUDIT_FINDINGS_DESC": t(locale, "transparency.audit_findings_desc", ""),
        "IMPL_RATE_EYEBROW": t(locale, "transparency.impl_rate_eyebrow", ""),
        "IMPL_RATE_TITLE": t(locale, "transparency.impl_rate_title", ""),
        "IMPL_RATE_DESC": t(locale, "transparency.impl_rate_desc", ""),
        "IMPL_RATE_CHART_TITLE": t(locale, "transparency.impl_rate_chart_title", ""),
        "IMPL_RATE_TABLE_TITLE": t(locale, "transparency.impl_rate_table_title", ""),
        "TRANSPARENCY_VIEW_TABLE": t(locale, "transparency.dash_view_table", "View full tables"),
        "TRANSPARENCY_CLOSE": t(locale, "transparency.dash_close", "Close"),
    }




def _build_search_labels(locale: dict) -> dict:
    return {
        "SEARCH_TITLE": t(locale, "search_page.title", ""),
        "SEARCH_SUBTITLE": t(locale, "search_page.subtitle", ""),
        "SEARCH_BROWSE_EYEBROW": t(locale, "search_page.browse_eyebrow", ""),
        "SEARCH_BROWSE_TITLE": t(locale, "search_page.browse_title", ""),
        "SEARCH_POPULAR_TITLE": t(locale, "search_page.popular_title", ""),
        "SEARCH_POPULAR_BIZ": t(locale, "search_page.popular_biz", ""),
        "SEARCH_POPULAR_CIVIL": t(locale, "search_page.popular_civil", ""),
        "SEARCH_POPULAR_HEALTH": t(locale, "search_page.popular_health", ""),
        "SEARCH_POPULAR_WELFARE": t(locale, "search_page.popular_welfare", ""),
        "REPORT_CHOOSE_TITLE": t(locale, "report_hub.choose_title", ""),
        "REPORT_ERROR": t(locale, "report_hub.report_error", ""),
        "REPORT_SUBMIT_INFO": t(locale, "report_hub.submit_info", ""),
        "REPORT_SUGGEST_FEATURE": t(locale, "report_hub.suggest_feature", ""),
        "REPORT_NEXT_TITLE": t(locale, "report_hub.next_title", ""),
        "REPORT_VERIFICATION_TITLE": t(locale, "report_hub.verification_title", ""),
    }


def build_hero(meta: dict, page_hero_raw: str, asset_base: str) -> str:
    """Build hero HTML if page has hero metadata."""
    if not any(meta.get(k) for k in ("hero_eyebrow", "hero_heading", "hero_lede")):
        return ""
    return fill(page_hero_raw, {
        "ASSET_BASE": asset_base,
        "HERO_EYEBROW": meta.get("hero_eyebrow", ""),
        "HERO_HEADING": meta.get("hero_heading", ""),
        "HERO_LEDE": meta.get("hero_lede", ""),
    })


def build_transparency_tabs(locale: dict, active_slug: str, lang_prefix: str) -> str:
    """Build the transparency section nav: pill tabs (desktop) + native select (mobile).

    Server-renders active/selected state so it works with JS disabled;
    dashboard-tabs.js only syncs + navigates the select.
    """
    tabs = [
        ("procurement", t(locale, "transparency.tab_procurement", "Public Procurement")),
        ("infrastructure", t(locale, "transparency.tab_infrastructure", "Infrastructure")),
        ("budget-fiscal", t(locale, "transparency.tab_budget_fiscal", "Budget & Fiscal")),
        ("audit-compliance", t(locale, "transparency.tab_audit", "Audit & Compliance")),
    ]
    label = t(locale, "transparency.section_label", "Transparency section")
    pills = []
    options = []
    for slug, name in tabs:
        url = f"{lang_prefix}/transparency/{slug}/"
        is_active = slug == active_slug
        aria = ' aria-current="page"' if is_active else ""
        cls = "tab-btn active" if is_active else "tab-btn"
        pills.append(f'<a href="{url}" class="{cls}"{aria}><span class="tab-label">{name}</span></a>')
        sel = " selected" if is_active else ""
        options.append(f'<option value="{url}"{sel}>{name}</option>')
    return (
        '<nav class="transparency-tabs" aria-label="' + label + '">\n'
        + "\n".join(pills)
        + '\n</nav>\n'
        + '<div class="transparency-tabs-dropdown">\n'
        + '<div class="wrap">\n'
        + f'<select id="transparency-section-select" class="form-input transparency-select" aria-label="{label}">\n'
        + "\n".join(options)
        + "\n</select>\n</div>\n</div>\n"
    )


def assemble_page(base: str, asset_base: str, title: str, description: str, header: str, body: str, footer: str, lang_code: str, page_url: str = "", breadcrumb_jsonld: str = "") -> str:
    """Assemble a complete page from its components."""
    base_url = "https://bettermapandan.org"
    if page_url:
        folder_path = to_folder_index(Path(page_url))
        if folder_path.name == "index.html":
            parent_name = folder_path.parent.name
            canonical = f"{base_url}/" if not parent_name else f"{base_url}/{folder_path.parent}/"
        else:
            canonical = f"{base_url}/{folder_path}/"
    else:
        canonical = base_url
    return fill(base, {
        "ASSET_BASE": asset_base,
        "TITLE": title,
        "DESCRIPTION": description,
        "HEADER": header,
        "BODY": body,
        "FOOTER": footer,
        "LANG_ATTR": f' lang="{lang_code}"',
        "CANONICAL_URL": canonical,
        "BREADCRUMB_JSONLD": breadcrumb_jsonld,
    })


def build_search_entry(rel: Path, title: str, description: str, body: str, lang_code: str, anchors_key: str = "") -> dict:
    """Build a search index entry from page content."""
    url = compute_url(rel)
    if lang_code != "en":
        url = f"{lang_code}/{url}"
    plain_body = strip_html(body)
    entry: dict[str, object] = {"title": title, "url": url, "description": description, "body": plain_body}
    if anchors_key:
        anchors = SECTION_ANCHORS.get(anchors_key, [])
        section_anchors = []
        for anchor_id, heading in anchors:
            idx = plain_body.lower().find(heading.lower())
            if idx != -1:
                section_anchors.append({"anchor": anchor_id, "pos": idx})
        section_anchors.sort(key=lambda s: s["pos"])  # type: ignore[arg-type, return-value]
        if section_anchors:
            entry["section_anchors"] = section_anchors
    return entry


def _process_static_page(
    lang_code: str, locale: dict, rel: Path, meta: dict, body: str,
    base: str, page_hero_raw: str, out_root: Path, search_entries: list
) -> int:
    out_rel = to_folder_index(rel)
    asset_base = compute_asset_base(out_rel, lang_code)
    lang_urls = build_lang_switcher_urls(rel, lang_code)
    page_title = meta["title"].split(" —")[0].split(" |")[0].strip()
    breadcrumbs = build_breadcrumbs(locale, rel, page_title)
    header = build_header(locale, asset_base, lang_code, lang_urls)
    footer = build_footer(locale, asset_base)
    hero_html = build_hero(meta, page_hero_raw, asset_base)
    body = resolve_body_placeholders(hero_html + body, locale, asset_base)
    if rel.name == "transparency.html" or (len(rel.parts) > 1 and rel.parts[0] == "transparency"):
        proc_html, _, _ = generate_procurement(locale)
        body = body.replace("{PROCUREMENT_SECTION}", proc_html, 1)
        dpwh_html, _, _ = generate_dpwh(locale, asset_base)
        body = body.replace("{DPWH_SECTION}", dpwh_html, 1)
        body = body.replace("{FDP_DASHBOARD}", generate_fdp_dashboard(locale), 1)
        body = body.replace("{FDP_SECTION}", generate_fdp(locale), 1)
    if len(rel.parts) > 1 and rel.parts[0] == "transparency" and rel.stem != "transparency":
        lang_prefix = f"/{lang_code}" if lang_code != "en" else ""
        body = body.replace("{TRANSPARENCY_TABS}", build_transparency_tabs(locale, rel.stem, lang_prefix), 1)
    if rel.name == "index.html":
        proc_data = generate_homepage_procurement_data()
        body = body.replace("{HOMEPAGE_PROCUREMENT_DATA}", proc_data, 1)
        dpwh_data = generate_homepage_dpwh_data()
        body = body.replace("{HOMEPAGE_DPWH_DATA}", dpwh_data, 1)
    if rel.name == "government.html":
        body = body.replace("{BARANGAY_COUNCILS_TABLE}", generate_barangay_councils_table(locale), 1)
    page_url = f"{lang_code}/{rel}" if lang_code != "en" else str(rel)
    breadcrumb_jsonld = build_breadcrumb_jsonld(locale, rel, page_title, lang_code)
    page_html = assemble_page(base, asset_base, meta["title"], meta["description"], header, breadcrumbs + body, footer, lang_code, page_url, breadcrumb_jsonld)

    if rel.name == "statistics.html":
        comparison_script = build_barangay_comparison_script()
        stats_js = '<script defer src="' + asset_base + '/assets/stats.min.js"></script>'
        page_html = page_html.replace("</body>", comparison_script + "\n" + stats_js + "\n</body>", 1)

    # Transparency subpages only (the /transparency/ hub is static — no JS data needed).
    if len(rel.parts) > 1 and rel.parts[0] == "transparency":
        transparency_js = (
            '<script defer src="' + asset_base + '/assets/js/common.min.js"></script>\n'
            '<script defer src="' + asset_base + '/assets/transparency.min.js"></script>\n'
            '<script defer src="' + asset_base + '/assets/js/transparency-charts.min.js"></script>\n'
            '<script defer src="' + asset_base + '/assets/js/procurement-table.min.js"></script>\n'
            '<script defer src="' + asset_base + '/assets/js/fdp-dashboard.min.js"></script>\n'
            '<script defer src="' + asset_base + '/assets/js/dashboard-tabs.min.js"></script>\n'
        )
        fdp_summary = generate_fdp_summary()
        transparency_js += '<script>window.FDP_SUMMARY = ' + json.dumps(fdp_summary, ensure_ascii=False) + ';</script>\n'
        csv_data_path = SRC_DATA / "transparency-csv.json"
        if csv_data_path.exists():
            csv_data = json.loads(csv_data_path.read_text(encoding="utf-8"))
            transparency_js += '<script>window.TRANSPARENCY_CSV_DATA = ' + json.dumps(csv_data, ensure_ascii=False) + ';</script>\n'
        audit_data_path = SRC_DATA / "audit-reports.json"
        if audit_data_path.exists():
            audit_data = json.loads(audit_data_path.read_text(encoding="utf-8"))
            transparency_js += '<script>window.AUDIT_DATA = ' + json.dumps(audit_data, ensure_ascii=False) + ';</script>\n'
        page_html = page_html.replace("</body>", transparency_js + "</body>", 1)

    if rel.name == "index.html":
        homepage_js = '<script defer src="' + asset_base + '/assets/stats.min.js"></script>'
        page_html = page_html.replace("</body>", homepage_js + "\n</body>", 1)
    if rel.name == "about.html":
        about_js = '<script defer src="' + asset_base + '/assets/stats.min.js"></script>'
        page_html = page_html.replace("</body>", about_js + "\n</body>", 1)

    out_path = out_root / to_folder_index(rel)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page_html, encoding="utf-8")
    print(f"  [{lang_code.upper()}] built {rel}  ({len(page_html):,} bytes)")

    search_entries.append(build_search_entry(rel, meta["title"], meta["description"], body, lang_code, rel.name))
    return 1


def _process_generated_page(
    lang_code: str, locale: dict, rel: Path, body_content: str, page_meta: dict, hero_meta: dict,
    base: str, page_hero_raw: str, out_root: Path, search_entries: list
) -> int:
    out_rel = to_folder_index(rel)
    asset_base = compute_asset_base(out_rel, lang_code)
    lang_urls = build_lang_switcher_urls(rel, lang_code)
    page_title = rel.stem.replace("-", " ").title()
    breadcrumbs = build_breadcrumbs(locale, rel, page_title)
    header = build_header(locale, asset_base, lang_code, lang_urls)
    footer = build_footer(locale, asset_base)

    rel_path_str = str(rel)
    page_hero = hero_meta.get(rel_path_str, {})
    if page_hero:
        hero_html = fill(page_hero_raw, {
            "ASSET_BASE": asset_base,
            "HERO_EYEBROW": page_hero.get("hero_eyebrow", ""),
            "HERO_HEADING": page_hero.get("hero_heading", ""),
            "HERO_LEDE": page_hero.get("hero_lede", ""),
        })
        body_content = hero_html + body_content

    page_url = f"{lang_code}/{rel_path_str}" if lang_code != "en" else rel_path_str
    breadcrumb_jsonld = build_breadcrumb_jsonld(locale, rel, page_title, lang_code)
    page_html = assemble_page(
        base, asset_base,
        page_meta.get(rel_path_str, {}).get("title", "Better Mapandan"),
        page_meta.get(rel_path_str, {}).get("description", ""),
        header, breadcrumbs + body_content, footer, lang_code, page_url, breadcrumb_jsonld
    )

    out_path = out_root / to_folder_index(rel)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page_html, encoding="utf-8")
    print(f"  [{lang_code.upper()}] built {rel}  ({len(page_html):,} bytes)")

    search_entries.append(build_search_entry(rel, rel.stem.replace("-", " ").title(), "", body_content, lang_code))
    return 1


def build() -> None:
    generate_barangays()

    en_locale = load_locale("en")
    fil_locale = load_locale("fil")
    pag_locale = load_locale("pag")
    pag_locale = deep_merge(en_locale, pag_locale)

    if HAS_SCHEMA_VALIDATION:
        schema_errors = validate_all(SRC_DATA)
        if schema_errors:
            print("\nWARNING: Data validation errors found:")
            for err in schema_errors:
                print(f"  - {err}")
            print("")

    base = (SRC_PARTIALS / "base.html").read_text(encoding="utf-8")
    page_hero_raw = (SRC_PARTIALS / "page-hero.html").read_text(encoding="utf-8")

    for out_dir in [FIL_DIR, PAG_DIR]:
        if out_dir.exists():
            shutil.rmtree(out_dir)

    cname_src = ROOT / "CNAME"
    if not cname_src.exists():
        (ROOT / "CNAME").write_text("bettermapandan.org\n", encoding="utf-8")
        print("  CNAME: generated")

    all_search_entries = []

    for lang_code, out_root, _ in LANGUAGES:
        locale = {"en": en_locale, "fil": fil_locale, "pag": pag_locale}[lang_code]
        print(f"\n--- Building [{lang_code.upper()}] ---")

        svc_pages, svc_meta, svc_hero_meta = generate_services(locale, lang_code, lang_code == "fil")
        leg_html, leg_meta, leg_hero_meta = generate_legislative(locale, lang_code == "fil")
        svc_pages["legislative.html"] = leg_html
        svc_meta["legislative.html"] = leg_meta
        svc_hero_meta["legislative.html"] = leg_hero_meta

        page_files = sorted(SRC_PAGES.rglob("*.html"))
        if not page_files:
            raise SystemExit(f"No page sources found in {SRC_PAGES}")

        search_entries: list[dict] = []
        count = 0

        for page_path in page_files:
            rel = page_path.relative_to(SRC_PAGES)
            meta, body = parse_page(page_path.read_text(encoding="utf-8"))
            count += _process_static_page(
                lang_code, locale, rel, meta, body, base, page_hero_raw, out_root, search_entries
            )

        for rel_path, body_content in svc_pages.items():
            body_content = strip_front_matter(body_content)
            rel = Path(rel_path)
            count += _process_generated_page(
                lang_code, locale, rel, body_content, svc_meta, svc_hero_meta, base, page_hero_raw, out_root, search_entries
            )

        all_search_entries.extend(search_entries)
        print(f"  [{lang_code.upper()}] search index: {len(search_entries)} entries")

    (ROOT / "assets" / "search-index.json").write_text(
        json.dumps(all_search_entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nSearch index: {len(all_search_entries)} total entries")

    minify_assets()

    assets_src = ROOT / "assets"
    for out_dir in [FIL_DIR, PAG_DIR]:
        assets_dst = out_dir / "assets"
        if assets_src.exists():
            if assets_dst.exists():
                shutil.rmtree(assets_dst)
            shutil.copytree(assets_src, assets_dst)
            print(f"\n  Copied assets to {out_dir.name}/assets/")

    generate_sitemap()
    generate_llms_txt()
    print(f"\nDone. {count * len(LANGUAGES)} page(s) written ({count} per language)")


def main():
    if "--compress" in sys.argv:
        compress_images()
    if "--verify-translations" in sys.argv:
        verify_translations()
    if "--compress" not in sys.argv and "--verify-translations" not in sys.argv:
        build()
