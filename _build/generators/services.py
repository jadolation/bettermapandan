import html
import json
import re
from collections import Counter
from pathlib import Path

from _build.config import ROOT, SRC_DATA, SRC_TEMPLATES
from _build.locales import t
from _build.templates import fill, compute_url, compute_asset_base, to_folder_index, FRONT_MATTER_RE


def generate_services(locale: dict, lang: str, is_fil: bool) -> tuple[dict[str, str], dict[str, dict], dict[str, dict]]:
    """Generate service detail pages and directory page.
    Returns (pages, metadata, hero_metadata) where pages is {relative_path: html_content}
    and metadata is {relative_path: {title, description}} for SEO."""
    data_path = SRC_DATA / "services.json"
    try:
        svc_template = (SRC_TEMPLATES / "service.html").read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(f"ERROR: Template file not found: {SRC_TEMPLATES / 'service.html'}")
    try:
        dir_template = (SRC_TEMPLATES / "services-directory.html").read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(f"ERROR: Template file not found: {SRC_TEMPLATES / 'services-directory.html'}")

    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"ERROR: Malformed JSON in {data_path}: {e}")

    services = data.get("services", [])
    try:
        categories = {c["slug"]: c for c in data.get("categories", [])}
    except KeyError as e:
        raise SystemExit(f"ERROR: Category missing 'slug' field in {data_path}: {e}")

    analytics = _build_services_analytics(services, categories)
    analytics_json = json.dumps(analytics, ensure_ascii=False)

    by_category: dict[str, list[dict]] = {}
    for svc in services:
        by_category.setdefault(svc.get("category", ""), []).append(svc)

    pages = {}
    meta = {}
    hero_meta_dict = {}

    svc_labels = _build_service_labels(locale)

    for svc in services:
        svc_slug, filled, hero_meta = _generate_single_service(
            svc, categories, services, svc_template, svc_labels, is_fil
        )
        pages[f"services/{svc_slug}.html"] = filled
        meta[f"services/{svc_slug}.html"] = {
            "title": f"{svc.get('name', '')} — BetterMapandan.org",
            "description": svc.get("description", "")[:160],
        }
        hero_meta_dict[f"services/{svc_slug}.html"] = hero_meta

    dir_filled, dir_hero_meta = _generate_services_directory(
        data, by_category, dir_template, svc_labels, is_fil, asset_base=compute_asset_base(Path("services/index.html"), is_fil), analytics_json=analytics_json
    )
    pages["services.html"] = dir_filled
    meta["services.html"] = {
        "title": t(locale, "services_dir.title", "Services") + " — BetterMapandan.org",
        "description": t(locale, "services_dir.desc", "Find the service you need."),
    }
    hero_meta_dict["services.html"] = dir_hero_meta
    return pages, meta, hero_meta_dict


def _build_service_labels(locale: dict) -> dict:
    return {
        "SVC_DESCRIPTION_LABEL": t(locale, "service_page.description", "Description"),
        "SVC_REQUIREMENTS_LABEL": t(locale, "service_page.requirements", "Requirements"),
        "SVC_PROCEDURE_LABEL": t(locale, "service_page.procedure", "Procedure"),
        "SVC_DETAILS_LABEL": t(locale, "service_page.details", "Service Details"),
        "SVC_OFFICE_LABEL": t(locale, "service_page.office", "Responsible Office:"),
        "SVC_CLASSIFICATION_LABEL": t(locale, "service_page.classification", "Classification:"),
        "SVC_MODE_LABEL": t(locale, "service_page.mode", "Mode:"),
        "SVC_PROCESSING_TIME_LABEL": t(locale, "service_page.processing_time", "Processing Time:"),
        "SVC_FEE_LABEL": t(locale, "service_page.fee", "Fee:"),
        "SVC_WHERE_LABEL": t(locale, "service_page.where_to_apply", "Where to Apply:"),
        "SVC_CONTACT_LABEL": t(locale, "service_page.contact", "Contact:"),
        "SVC_SOURCE_LABEL": t(locale, "service_page.source", "Source:"),
        "SVC_LAST_UPDATED_LABEL": t(locale, "service_page.last_updated", "Last Updated:"),
        "SVC_SCANNED_DOC_LABEL": t(locale, "service_page.scanned_doc", "Scanned Document"),
        "SVC_SCANNED_DOC_DESC": t(locale, "service_page.scanned_doc_desc", ""),
        "SVC_RELATED_LABEL": t(locale, "service_page.related", "Related Services"),
        "SVC_NO_RELATED": t(locale, "service_page.no_related", "No related services available."),
        "SVC_WAS_HELPFUL": t(locale, "service_page.was_helpful", "Was this information helpful?"),
        "SVC_YES": t(locale, "service_page.yes", "Yes"),
        "SVC_NO": t(locale, "service_page.no", "No"),
        "SVC_THANKS": t(locale, "service_page.thanks", "Thank you for your feedback!"),
        "SVC_REPORT": t(locale, "service_page.report", "Report incorrect information"),
    }


def _generate_single_service(svc: dict, categories: dict, services: list, template: str, labels: dict, is_fil: bool):
    cat = categories.get(svc.get("category", ""), {})
    svc_name = svc.get("name_fil", svc.get("name", "")) if is_fil else svc.get("name", "")
    svc_desc = svc.get("description_fil", svc.get("description", "")) if is_fil else svc.get("description", "")
    cat_name = cat.get("name_fil", cat.get("name", "")) if is_fil else cat.get("name", "")
    hero_lede = svc.get("hero_lede_fil", svc.get("hero_lede", svc_desc)) if is_fil else svc.get("hero_lede", svc.get("description", ""))

    reqs_html = "\n".join(f"            <li>{html.escape(r)}</li>" for r in svc.get("requirements", []))
    proc_html = "\n".join(f"            <li>{html.escape(p)}</li>" for p in svc.get("procedure", []))
    related_html = _build_related_links(svc, services, is_fil)

    svc_slug = svc.get("slug", "unknown")
    asset_base = compute_asset_base(Path(f"services/{svc_slug}/index.html"), is_fil)
    photo_html = _build_photo_html(svc, is_fil, asset_base)

    filled = fill(template, {
        "NAME": html.escape(svc_name),
        "DESCRIPTION": html.escape(svc_desc),
        "CATEGORY_NAME": html.escape(cat_name),
        "HERO_LEDE": html.escape(hero_lede),
        "DESCRIPTION_FULL": html.escape(svc.get("description_full", svc.get("description", ""))),
        "REQUIREMENTS": reqs_html,
        "PROCEDURE": proc_html,
        "OFFICE": html.escape(svc.get("office", "")),
        "CLASSIFICATION": html.escape(svc.get("classification", "")),
        "PROCESSING_TIME": html.escape(svc.get("processing_time", "")),
        "FEE": html.escape(svc.get("fee", "Free")),
        "WHERE": html.escape(svc.get("where_to_apply", "")),
        "CONTACT": html.escape(svc.get("contact", "")),
        "SOURCE": html.escape(svc.get("source", "Mapandan Citizen's Charter")),
        "LAST_UPDATED": html.escape(svc.get("last_updated", "August 2025")),
        "RELATED_SERVICES": related_html,
        "PHOTO_HTML": photo_html,
        "DELIVERY_MODE": html.escape(svc.get("delivery_mode", "in-person")),
        "SLUG": html.escape(svc.get("slug", "")),
        **labels,
    })

    hero_meta = _extract_hero_meta(filled)
    return svc_slug, filled, hero_meta


def _build_services_analytics(services: list, categories: dict) -> dict:
    import re
    cat_slugs = [svc.get("category", "") for svc in services]
    categories_count = dict(Counter(cat_slugs))

    office_count = dict(Counter(svc.get("office", "Unknown") for svc in services))

    simple = sum(1 for svc in services if svc.get("classification") == "Simple")
    complex_count = sum(1 for svc in services if svc.get("classification") in ("Complex", "Highly Technical"))
    classifications = {"Simple": simple, "Complex": complex_count}

    delivery_modes = dict(Counter(svc.get("delivery_mode", "in-person") for svc in services))

    fee_count_free = 0
    fee_amounts = []
    for svc in services:
        fee = svc.get("fee", "")
        fee_lower = fee.lower()
        if fee_lower.startswith("free"):
            fee_count_free += 1
        else:
            m = re.search(r"[\u20B1Pp]?\s*([\d,]+(?:\s*[-–]\s*[\d,]+)?)", fee)
            if m:
                raw = m.group(1)
                nums = [int(p.replace(",", "")) for p in re.split(r"\s*[-–]\s*", raw) if p.strip().isdigit()]
                if nums:
                    fee_amounts.append(sum(nums) / len(nums))
    fees_free = fee_count_free
    fees_paid = len(services) - fee_count_free
    fees_average = round(sum(fee_amounts) / len(fee_amounts), 2) if fee_amounts else 0.0

    return {
        "categories": categories_count,
        "offices": office_count,
        "classifications": classifications,
        "delivery_modes": delivery_modes,
        "fees": {
            "free": fees_free,
            "paid": fees_paid,
            "average": fees_average,
        },
    }


def _build_related_links(svc: dict, services: list, is_fil: bool) -> str:
    related = svc.get("related", [])
    if not related:
        return '<p>No related services available.</p>'
    links = []
    for rel_slug in related:
        rel_svc = next((s for s in services if s.get("slug") == rel_slug), None)
        if rel_svc:
            rel_name = rel_svc.get("name_fil", rel_svc.get("name", "Unknown Service")) if is_fil else rel_svc.get("name", "Unknown Service")
            links.append(f'<a href="/services/{html.escape(rel_slug)}/">{html.escape(rel_name)}</a>')
    return '<div class="service-links">\n' + "\n".join(f"          {link}" for link in links) + "\n        </div>"


def _build_photo_html(svc: dict, is_fil: bool, asset_base: str) -> str:
    photo_ref = svc.get("photo-referenced", "")
    if not photo_ref:
        return ""
    photo_filename = photo_ref.split("/")[-1]
    service_name = html.escape(svc.get("name", ""))
    return f'''
            <figure class="service-photo-container">
                <img class="service-photo" src="{asset_base}/{photo_ref}" alt="Citizens Charter for {service_name}"
                    loading="lazy" width="600" height="800"
                    data-fallback="hide">
                <figcaption class="service-photo-caption">
                    Citizens Charter document: {html.escape(photo_filename)}
                </figcaption>
            </figure>'''


def _generate_services_directory(data: dict, by_category: dict, template: str, labels: dict, is_fil: bool, asset_base: str = ".", analytics_json: str = ""):
    category_cards = []
    for cat in data.get("categories", []):
        cat_services = by_category.get(cat.get("slug", ""), [])
        cat_name = cat.get("name_fil", cat.get("name", "")) if is_fil else cat.get("name", "")
        cat_desc = cat.get("description_fil", cat.get("description", "")) if is_fil else cat.get("description", "")
        service_links = _build_category_service_links(cat_services, is_fil)
        card = (
            f'      <div class="card service-category-card">\n'
            f'        <div class="service-card-head">\n'
            f'          <div class="service-icon"><i data-lucide="{html.escape(cat.get("icon", ""))}"></i></div>\n'
            f'          <h2>{html.escape(cat_name)}</h2>\n'
            f'        </div>\n'
            f'        <p>{html.escape(cat_desc)}</p>\n'
            f'        <div class="service-links">\n'
            + "\n".join(f"          {link}" for link in service_links)
            + "\n        </div>\n"
            '      </div>'
        )
        category_cards.append(card)

    dir_filled = fill(template, {
        "ASSET_BASE": asset_base,
        "CATEGORY_CARDS": "\n".join(category_cards),
        "SERVICES_ANALYTICS_SCRIPT": (
            f"<script>window.SERVICES_ANALYTICS = {analytics_json};</script>"
            if analytics_json else ""
        ),
        "SVC_TITLE": t(labels, "services_dir.title", "Services"),
        "SVC_EYEBROW": t(labels, "services_dir.eyebrow", "Citizen's Charter"),
        "SVC_LEDE": t(labels, "services_dir.lede", "Every service Mapandan offers."),
        "SVC_DESC": t(labels, "services_dir.desc", "Find the service you need."),
        "SVC_SEARCH_PLACEHOLDER": t(labels, "services_dir.search_placeholder", "Search services..."),
        "SVC_NO_RESULTS": t(labels, "services_dir.no_results", "No services match your search."),
        "SVC_BROWSE_ALL": t(labels, "services_dir.browse_all", "browse all categories"),
        "SVC_NATIONAL_EYEBROW": t(labels, "services_dir.national_eyebrow", "National Platforms"),
        "SVC_NATIONAL_TITLE": t(labels, "services_dir.national_title", "Online services"),
        "SVC_NATIONAL_DESC": t(labels, "services_dir.national_desc", "Several national government services are available online."),
        "SVC_PHILSYS": t(labels, "services_dir.national_philsys", "PhilSys National ID"),
        "SVC_PHILSYS_DESC": t(labels, "services_dir.national_philsys_desc", ""),
        "SVC_PSA": t(labels, "services_dir.national_psa", "PSA Serbilis"),
        "SVC_PSA_DESC": t(labels, "services_dir.national_psa_desc", ""),
        "SVC_EGOV": t(labels, "services_dir.national_egov", "eGovPH"),
        "SVC_EGOV_DESC": t(labels, "services_dir.national_egov_desc", ""),
        "SVC_ELGU": t(labels, "services_dir.national_elgu", "e-LGU Portal"),
        "SVC_ELGU_DESC": t(labels, "services_dir.national_elgu_desc", ""),
        "SVC_ANALYTICS_EYEBROW": t(labels, "services_dir.analytics_eyebrow", "Service Analytics"),
        "SVC_ANALYTICS_TITLE": t(labels, "services_dir.analytics_title", "Services at a Glance"),
        "SVC_ANALYTICS_DESC": t(labels, "services_dir.analytics_desc", "Breakdown of services by category, office, classification, and delivery mode."),
        "SVC_ANALYTICS_BY_CATEGORY": t(labels, "services_dir.analytics_by_category", "Services by Category"),
        "SVC_ANALYTICS_BY_CATEGORY_DESC": t(labels, "services_dir.analytics_by_category_desc", "Number of services in each category"),
        "SVC_ANALYTICS_BY_OFFICE": t(labels, "services_dir.analytics_by_office", "Services by Office"),
        "SVC_ANALYTICS_BY_OFFICE_DESC": t(labels, "services_dir.analytics_by_office_desc", "Number of services handled by each office"),
        "SVC_ANALYTICS_FEES": t(labels, "services_dir.analytics_fees", "Fees at a Glance"),
        "SVC_ANALYTICS_FEES_DESC": t(labels, "services_dir.analytics_fees_desc", "Average fee for paid services"),
    })
    hero_meta = _extract_hero_meta(dir_filled)
    return dir_filled, hero_meta


def _build_category_service_links(cat_services: list, is_fil: bool) -> list:
    service_links = []
    for s in cat_services:
        s_name = s.get("name_fil", s.get("name", "")) if is_fil else s.get("name", "")
        name_html = html.escape(s_name)
        time_html = html.escape(s.get("processing_time", "")) if s.get("processing_time") else ""
        fee_html = html.escape(s.get("fee", "")) if s.get("fee") else ""
        meta_html = _build_service_meta_html(time_html, fee_html)
        service_links.append(
            f'<div class="service-link-wrap">'
            f'<a class="service-link" href="/services/{html.escape(s.get("slug", ""))}/">{name_html}</a>'
            f'{meta_html}</div>'
        )
    return service_links


def _build_service_meta_html(time_html: str, fee_html: str) -> str:
    if not time_html and not fee_html:
        return ""
    parts = []
    if time_html:
        parts.append(f'<span class="service-link-time">{time_html}</span>')
    if fee_html:
        parts.append(f'<span class="service-link-fee">{fee_html}</span>')
    return f'<div class="service-link-meta">{"".join(parts)}</div>'


def _extract_hero_meta(filled: str) -> dict:
    hero_meta = {}
    hero_meta_match = FRONT_MATTER_RE.match(filled)
    if hero_meta_match:
        hero_block = hero_meta_match.group(1)
        for line in hero_block.splitlines():
            key, _, value = line.partition(":")
            key = key.strip()
            if key in ("hero_eyebrow", "hero_heading", "hero_lede"):
                hero_meta[key] = value.strip()
    return hero_meta
