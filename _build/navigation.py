"""Navigation builders: lang switcher, breadcrumbs, tabs, section nav."""
import json
import re
from pathlib import Path

from _build.config import (
    LANGUAGES,
    SECTION_NAV,
    SECTION_NAV_CHILDREN,
    SECTION_NAV_GRANDCHILD_PREFIXES,
    SECTION_NAV_GRANDCHILDREN,
    SECTION_NAV_GROUP_LABEL,
    SECTION_NAV_ICONS,
    SECTION_NAV_PREFIXES,
)
from _build.locales import t
from _build.templates import to_folder_index

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
        ("projects", t(locale, "transparency.tab_projects", "Project Explorer")),
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

def build_section_nav(locale: dict, nav_key: str, body: str) -> str:
    """Build dual-mode in-page nav: desktop sticky sidebar + mobile edge dots.

    Sections come from SECTION_NAV (ordered ids); section labels from locales
    (<prefix>.nav_<id underscores>); badges count linked nav children
    (sub-items, never raw h3 volume). CHILDREN sections extract id'd <h3>
    sub-items (cap 10); GRANDCHILDREN sub-items extract id'd descendants
    by id prefix (cap 6). audit-findings wraps children under one toggle
    (GROUP_LABEL); other sections list children directly. Sections missing
    from the body are skipped. Server-renders everything so the nav works
    with JS disabled; section-nav.js adds scrollspy, collapse, and the
    mobile hold gesture.
    """
    import html as _html

    prefix = SECTION_NAV_PREFIXES.get(nav_key, "transparency")
    configured = SECTION_NAV.get(nav_key, [])
    # Locate each <section id="..."> in the rendered body.
    positions = [(m.group(1), m.start()) for m in re.finditer(r'<section\b[^>]*\bid="([^"]+)"', body)]
    present = {sid for sid, _ in positions}

    def section_slice(sid: str) -> str:
        idxs = [pos for s, pos in positions if s == sid]
        if not idxs:
            return ""
        start = idxs[0]
        later = [pos for _, pos in positions if pos > start]
        end = min(later) if later else len(body)
        return body[start:end]

    def extract_headings(sl: str):
        """Sub-items in document order: id'd h3 headings. Sections without
        any id'd h3 (e.g. #sangguniang-bayan member cards) fall back to
        elements carrying an explicit data-nav-label. Capped at 10."""
        kids = []
        for m in re.finditer(r'<h3\b[^>]*\bid="([^"]+)"[^>]*>(.*?)</h3>', sl, re.DOTALL):
            kid_id, raw = m.group(1), m.group(2)
            text = _html.unescape(re.sub(r"<[^>]+>", "", raw)).strip()
            if kid_id and text:
                kids.append((kid_id, text))
            if len(kids) == 10:
                break
        if not kids:
            for m in re.finditer(
                r'''<[a-zA-Z]+\b[^<>]*\bid=(["'])([^"']+)\1[^<>]*\bdata-nav-label=(["'])([^"']+)\3[^<>]*>''',
                sl,
            ):
                kid_id, text = m.group(2), _html.unescape(m.group(4)).strip()
                if kid_id and text:
                    kids.append((kid_id, text))
                if len(kids) == 10:
                    break
        return kids

    def extract_prefixed(sl: str, stem: str):
        """Id'd h3/div descendants whose id starts with stem + '-': (id, text).

        Prefers an explicit data-nav-label (short card titles); falls back
        to stripped inner text.
        """
        kids = []
        for m in re.finditer(
            r'''<(?:h3|div)\b[^<>]*\bid=(["'])''' + re.escape(stem) + r'''-([^"']+)\1[^<>]*>''',
            sl,
        ):
            kid_id = stem + "-" + m.group(2)
            tag = m.group(0)
            lm = re.search(r'''data-nav-label=(["'])([^"']+)\1''', tag)
            if lm:
                text = _html.unescape(lm.group(2)).strip()
            else:
                inner = re.match(
                    r'<(?:h3|div)\b[^>]*>(.*?)</(?:h3|div)>',
                    sl[m.start():], re.DOTALL,
                )
                raw = inner.group(1) if inner else ""
                text = re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", "", raw)).strip())
            if kid_id and text:
                kids.append((kid_id, text))
            if len(kids) == 6:
                break
        return kids

    def sub_link(kid: str, text: str) -> str:
        return (
            f'<li><a href="#{_html.escape(kid, quote=True)}" data-section="{_html.escape(kid, quote=True)}">'
            f"{_html.escape(text)}</a></li>"
        )

    items = []
    dots = []
    show_more = t(locale, "common.show_subsections", "Show subsections")
    hide_less = t(locale, "common.hide_subsections", "Hide subsections")
    for n, sid in enumerate([s for s in configured if s in present]):
        label = t(locale, f"{prefix}.nav_{sid.replace('-', '_')}", sid.replace("-", " ").title())
        icon = SECTION_NAV_ICONS.get(sid, "circle")
        sl = section_slice(sid)
        sub_html = ""
        kid_count = 0
        if sid in SECTION_NAV_CHILDREN:
            kids = extract_headings(sl)
            if kids:
                kid_items = []
                for kid, text in kids:
                    grand = ""
                    if kid in SECTION_NAV_GRANDCHILDREN:
                        gpref = SECTION_NAV_GRANDCHILD_PREFIXES.get(kid, kid)
                        gkids = extract_prefixed(sl, gpref)
                        if gkids:
                            kid_esc = _html.escape(text)
                            grand = (
                                f'<div class="section-nav-split">'
                                f'<a href="#{_html.escape(kid, quote=True)}" data-section="{_html.escape(kid, quote=True)}">{kid_esc}</a>'
                                f'<button type="button" class="section-nav-sub-toggle section-nav-sub-sub-toggle" aria-expanded="false" '
                                f'aria-label="{_html.escape(show_more)}" data-hide-label="{_html.escape(hide_less)}" data-show-label="{_html.escape(show_more)}">'
                                f'<span aria-hidden="true">+</span>'
                                f'<span class="section-nav-badge" aria-hidden="true">{len(gkids)}</span></button>'
                                f"</div>"
                                f'<ul class="section-nav-sub-sub" hidden>'
                                + "".join(sub_link(g, gt) for g, gt in gkids)
                                + "</ul>"
                            )
                            kid_items.append(f"<li>{grand}</li>")
                            continue
                    kid_items.append(sub_link(kid, text))
                group_suffix = SECTION_NAV_GROUP_LABEL.get(sid)
                if group_suffix:
                    sub_label = t(locale, f"{prefix}.{group_suffix}", "Details")
                    sub_html = (
                        f'<button type="button" class="section-nav-sub-toggle" aria-expanded="false">'
                        f"<span>{_html.escape(sub_label)}</span>"
                        f'<span class="section-nav-badge" aria-hidden="true">{len(kids)}</span></button>'
                        f'<ul class="section-nav-sub" hidden>{"".join(kid_items)}</ul>'
                    )
                else:
                    sub_html = f'<ul class="section-nav-sub">{"".join(kid_items)}</ul>'
                kid_count = len(kids)
        badge = f'<span class="section-nav-badge" aria-hidden="true">{kid_count}</span>' if kid_count else ""
        items.append(
            f'<li><a href="#{sid}" data-section="{sid}">'
            f'<i data-lucide="{icon}" aria-hidden="true"></i>'
            f"<span>{_html.escape(label)}</span>{badge}</a>{sub_html}</li>"
        )
        dots.append(
            f'<button type="button" class="edge-dot edge-c{n % 4}" data-target="{sid}" aria-label="{_html.escape(label)}">'
            f'<span class="edge-tip" aria-hidden="true">{_html.escape(label)}</span></button>'
        )
    if not items:
        return ""
    nav_label = t(locale, "transparency.section_nav_label", "Page sections")
    head_title = t(locale, "transparency.sections_title", "Categories")
    hide_label = t(locale, "transparency.hide_menu", "Hide menu")
    show_label = t(locale, "transparency.show_menu", "Show menu")
    return (
        '<nav class="section-nav" aria-label="' + _html.escape(nav_label) + '">\n'
        f'<div class="section-nav-head"><span class="section-nav-title">{_html.escape(head_title)}</span>'
        f'<button type="button" class="section-nav-toggle" aria-expanded="true" aria-controls="section-nav-list" data-hide-label="{_html.escape(hide_label)}" data-show-label="{_html.escape(show_label)}">'
        f"<span>{_html.escape(hide_label)}</span>"
        '<span aria-hidden="true">&lt;</span></button></div>\n'
        '<ul id="section-nav-list">\n' + "\n".join(items) + "\n</ul>\n</nav>\n"
        '<nav class="edge-nav" aria-label="' + _html.escape(nav_label) + '">\n'
        '<div class="edge-backdrop" aria-hidden="true"></div>\n'
        '<div class="edge-tab" aria-hidden="true"></div>\n'
        '<div class="edge-dots">\n' + "\n".join(dots) + "\n</div>\n</nav>\n"
    )
