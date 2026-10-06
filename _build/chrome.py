"""Page shell builders: header, footer, hero, assembled page."""
from pathlib import Path

from _build.config import SITE_CONFIG, SRC_PARTIALS
from _build.locales import t
from _build.templates import fill, to_folder_index


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
        "LANG_LABEL_PAG": t(locale, "lang_switch.pag", "PANG"),
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
