"""HTML-page translation helpers for the static build.

The provisional translation inventory is keyed by the exact English text
extracted from the built pages.  We apply it to text nodes and a small set of
user-visible attributes after all placeholders and generated sections have
been resolved.  Links are localized separately so /fil/ and /pag/ pages never
send readers back to the English tree.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

from _build.config import SRC_DATA

_TEXT_CACHE: dict[str, dict[str, str]] = {}
_JS_CACHE: dict[str, dict[str, str]] = {}

_ATTR_RE = re.compile(
    r'(?P<prefix>\b(?:alt|aria-label|title|placeholder|content|data-tip)\s*=\s*)(?P<q>["\'])(?P<value>.*?)(?P=q)',
    re.DOTALL,
)
_TAG_RE = re.compile(r"<\s*(/?)\s*([a-zA-Z][a-zA-Z0-9-]*)")
_HREF_RE = re.compile(r'(?P<prefix>\bhref\s*=\s*)(?P<q>["\'])(?P<url>/[^"\']*)(?P=q)')
_WS_RE = re.compile(r"\s+")

# Short JS strings that are not in the extraction inventory but are visible in
# charts, language banners, and the mobile action bar.
_JS_EXTRA = {
    "fil": {
        "Pages": "Mga Pahina",
        "result": "resulta",
        "results": "mga resulta",
        "for": "para sa",
        "Services": "Mga Serbisyo",
        "Transparency": "Transparency",
        "Government": "Pamahalaan",
        "Statistics": "Estadistika",
        "About": "Tungkol",
        "Support": "Suporta",
        "GIS": "GIS",
        "Legislative": "Lehislatibo",
        "Search": "Maghanap",
        "Today": "Ngayon",
        "Sun": "Lin",
        "Mon": "Lun",
        "Tue": "Mar",
        "Wed": "Miy",
        "Thu": "Huw",
        "Fri": "Biy",
        "Sat": "Sab",
        "Feels like": "Pakiramdam na parang",
        "Humidity": "Halumigmig",
        "Wind": "Hangin",
        "Rain": "Ulan",
        "Rain chance": "Tsansang umulan",
        "Updated": "Na-update",
        "Powered by Open-Meteo": "Pinapagana ng Open-Meteo",
        "View PAGASA Advisories": "Tingnan ang mga advisory ng PAGASA",
        "Weather data unavailable.": "Walang available na datos ng panahon.",
        "Weather request timed out.": "Nag-time out ang request ng panahon.",
        "This page is also available in Pangasinan": "Mababasa rin ito sa Pangasinan",
        "Nabasao met iti ed Filipino": "Mababasa rin ito sa Filipino",
        "Dismiss": "Isara",
        "Services": "Mga Serbisyo",
        "Average fee": "Karaniwang bayad",
        "across": "sa",
        "paid service": "bayad na serbisyo",
        "paid services": "mga bayad na serbisyo",
        "free": "libre",
        "paid": "may bayad",
        "Mababasa rin ito sa Filipino": "Mababasa rin ito sa Filipino",
        "This page is also available in English": "Mababasa rin ito sa Ingles",
        "Switch to Filipino": "Lumipat sa Filipino",
        "Switch to English": "Lumipat sa Ingles",
        "Switch to Pangasinan": "Lumipat sa Pangasinan",
        "Dismiss": "Isara",
        "This translation is a draft awaiting review.": "Ang salin na ito ay draft na hinihintay pa ang pagsusuri.",
        "Translation feedback": "Puna sa salin",
        "Switch to": "Lumipat sa",
    },
    "pag": {
        "Pages": "Saray Pahina",
        "result": "resulta",
        "results": "saray resulta",
        "for": "parad",
        "Services": "Saray Serbisyo",
        "Transparency": "Transparency",
        "Government": "Gobyerno",
        "Statistics": "Estadistika",
        "About": "Nipaakar",
        "Support": "Suporta",
        "GIS": "GIS",
        "Legislative": "Lehislatibo",
        "Search": "Anapen",
        "Today": "Natan",
        "Sun": "Lin",
        "Mon": "Lun",
        "Tue": "Mar",
        "Wed": "Miy",
        "Thu": "Huw",
        "Fri": "Biy",
        "Sat": "Sab",
        "Feels like": "Marandam a singa",
        "Humidity": "Halumigmig",
        "Wind": "Dagos",
        "Rain": "Uran",
        "Rain chance": "Tsansa na uran",
        "Updated": "Na-update",
        "Powered by Open-Meteo": "Pinapagana na Open-Meteo",
        "View PAGASA Advisories": "Nengnengen saray advisory na PAGASA",
        "Weather data unavailable.": "Anggapo datos na panahon.",
        "Weather request timed out.": "Nag-time out so request na panahon.",
        "This page is also available in Pangasinan": "Nabasao met iti ed Pangasinan",
        "Mababasa rin ito sa Pangasinan": "Nabasao met iti ed Pangasinan",
        "Nabasao met iti ed Filipino": "Nabasao met iti ed Filipino",
        "Dismiss": "Iserra",
        "Services": "Saray Serbisyo",
        "Average fee": "Karaniwan a bayad",
        "across": "ed",
        "paid service": "mabayadan a serbisyo",
        "paid services": "saray mabayadan a serbisyo",
        "free": "libre",
        "paid": "mabayadan",
        "Mababasa rin ito sa Filipino": "Nabasao met iti ed Filipino",
        "This page is also available in English": "Nabasao met iti ed English",
        "Switch to Filipino": "Mikyas ed Filipino",
        "Switch to English": "Mikyas ed English",
        "Switch to Pangasinan": "Mikyas ed Pangasinan",
        "Dismiss": "Iserra",
        "This translation is a draft awaiting review.": "Say sayan a salin et draft ya mangagalang ed review.",
        "Translation feedback": "Feedback ed salin",
        "Switch to": "Mikyas ed",
    },
}


def _norm(value: str) -> str:
    return _WS_RE.sub(" ", html.unescape(value or "")).strip()


def _load_page_text(lang_code: str) -> dict[str, str]:
    if lang_code == "en":
        return {}
    if lang_code not in _TEXT_CACHE:
        lookup: dict[str, str] = {}
        for name in ("page-text.json", "page-text-extra.json"):
            path = SRC_DATA / name
            if not path.exists():
                continue
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                raw = {}
            if isinstance(raw, dict):
                for english, values in raw.items():
                    if not isinstance(values, dict):
                        continue
                    translated = values.get(lang_code, "")
                    if translated and _norm(translated) != _norm(english):
                        lookup[_norm(english)] = translated
        _TEXT_CACHE[lang_code] = lookup
    return _TEXT_CACHE[lang_code]


def _load_js_i18n(lang_code: str) -> dict[str, str]:
    if lang_code == "en":
        return {}
    if lang_code not in _JS_CACHE:
        path = SRC_DATA / "js-text.json"
        lookup: dict[str, str] = {}
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                raw = {}
            if isinstance(raw, dict):
                for english, values in raw.items():
                    if not isinstance(values, dict):
                        continue
                    translated = values.get(lang_code, "")
                    if translated:
                        lookup[english] = translated
        lookup.update(_JS_EXTRA.get(lang_code, {}))
        _JS_CACHE[lang_code] = lookup
    return _JS_CACHE[lang_code]


def js_i18n_script(lang_code: str) -> str:
    if lang_code == "en":
        return ""
    payload = json.dumps(_load_js_i18n(lang_code), ensure_ascii=False, sort_keys=True)
    payload = payload.replace("</", "<\\/")
    return f"<script>window.__I18N__ = {payload};</script>"


def translate_display_text(text: str, lang_code: str) -> str:
    """Translate a single visible string, falling back to the source."""
    if not text or lang_code == "en":
        return text
    return _load_page_text(lang_code).get(_norm(text), text)


def _translate_text_segment(segment: str, lookup: dict[str, str]) -> str:
    match = re.match(r"^(\s*)(.*?)(\s*)$", segment, re.DOTALL)
    if not match:
        return segment
    lead, body, trail = match.groups()
    translated = lookup.get(_norm(body))
    if not translated:
        return segment
    return lead + html.escape(translated, quote=False) + trail


def _translate_tag(tag: str, lookup: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        value = match.group("value")
        translated = lookup.get(_norm(value))
        if not translated:
            return match.group(0)
        q = match.group("q")
        return match.group("prefix") + q + html.escape(translated, quote=True) + q

    return _ATTR_RE.sub(repl, tag)


def translate_html_fragment(fragment: str, lang_code: str) -> str:
    """Translate exact text nodes and selected attributes in an HTML fragment."""
    if not fragment or lang_code == "en":
        return fragment
    lookup = _load_page_text(lang_code)
    if not lookup:
        return fragment
    parts = re.split(r"(<[^>]*>)", fragment)
    raw_depth = 0
    out: list[str] = []
    for part in parts:
        if not part:
            continue
        if part.startswith("<"):
            match = _TAG_RE.match(part)
            if match:
                closing, name = match.groups()
                name = name.lower()
                if name in ("script", "style"):
                    if closing:
                        raw_depth = max(0, raw_depth - 1)
                    elif not part.rstrip().endswith("/>"):
                        raw_depth += 1
                if raw_depth == 0 or closing:
                    part = _translate_tag(part, lookup)
            out.append(part)
        elif raw_depth == 0:
            out.append(_translate_text_segment(part, lookup))
        else:
            out.append(part)
    return "".join(out)


_LINK_SKIP_PREFIXES = (
    "/assets/",
    "/datasets/",
    "/downloads/",
    "/fil/",
    "/pag/",
    "/CNAME",
    "/site.webmanifest",
    "/robots.txt",
    "/sitemap.xml",
    "/llms.txt",
    "/favicon",
)


def localize_internal_links(fragment: str, lang_code: str) -> str:
    """Prefix root-relative site links for a locale subtree.

    Language-prefixed links, assets, downloads, and external URLs are left
    untouched.  This keeps navigation inside /fil/ and /pag/.
    """
    if not fragment or lang_code == "en":
        return fragment

    def repl(match: re.Match[str]) -> str:
        url = match.group("url")
        if url.startswith("//") or any(url.startswith(prefix) for prefix in _LINK_SKIP_PREFIXES):
            return match.group(0)
        localized = f"/{lang_code}" + ("/" if url == "/" else url)
        q = match.group("q")
        return match.group("prefix") + q + localized + q

    return _HREF_RE.sub(repl, fragment)


def page_text_count(lang_code: str) -> int:
    return len(_load_page_text(lang_code))

_JS_EXTRA["fil"].update({
    "Report Error": "Iulat ang Error",
    "Submit Missing Info": "Isumite ang Kulang na Impormasyon",
    "Submit Missing Information": "Isumite ang Kulang na Impormasyon",
    "Suggest Feature": "Magmungkahi ng Feature",
    "Suggest New Feature": "Magmungkahi ng Bagong Feature",
    "Enter a title above...": "Maglagay ng pamagat sa itaas...",
    "Your submission preview will appear here as you type.": "Lalabas dito ang preview ng iyong isinumite habang nagta-type ka.",
    "Draft opened! Please press 'Send' in your email app to complete.": "Nabuksan ang draft! Pindutin ang 'Send' sa email app para makumpleto.",
    "Copied to clipboard! Paste into your email app.": "Nakopya sa clipboard! I-paste sa email app.",
    "Data Correction:": "Pagwawasto ng Datos:",
    "General": "Pangkalahatan",
    "Mode: Report Error": "Mode: Iulat ang Error",
    "Page/Item:": "Pahina/Item:",
    "Error:": "Error:",
    "Correction:": "Pagwawasto:",
    "Source:": "Pinagmulan:",
    "New Information:": "Bagong Impormasyon:",
    "Mode: Submit Missing Info": "Mode: Isumite ang Kulang na Impormasyon",
    "Category:": "Kategorya:",
    "Title:": "Pamagat:",
    "Description:": "Paglalarawan:",
    "Feature Suggestion:": "Mungkahing Feature:",
    "Mode: Suggest Feature": "Mode: Magmungkahi ng Feature",
    "Feature:": "Feature:",
    "Use Case:": "Use Case:",
    "The page or item where the error was found": "Ang pahina o item kung saan natagpuan ang error",
    "Description of the error": "Paglalarawan ng error",
    "The correct data if known": "Ang tamang datos kung alam",
    "Link to supporting document": "Link sa sumusuportang dokumento",
    "Category": "Kategorya",
    "Type of information being submitted": "Uri ng impormasyong isinusumite",
    "Information Title / Name": "Pamagat / Pangalan ng Impormasyon",
    "Title of the information": "Pamagat ng impormasyon",
    "Detailed description": "Detalyadong paglalarawan",
    "Link to verifiable source": "Link sa verifiable na pinagmulan",
    "Feature Name": "Pangalan ng Feature",
    "Name of the proposed feature": "Pangalan ng iminumungkahing feature",
    "Detailed description of the feature": "Detalyadong paglalarawan ng feature",
    "Use Case / Why it matters": "Use Case / Bakit mahalaga",
    "How this would help Mapandan residents": "Paano ito makakatulong sa mga residente ng Mapandan",
    "Unqualified": "Walang Puna",
    "Qualified": "May Puna",
    "Non-Compliant": "Di Sumusunod",
    "Adverse": "Laban",
    "Disclaimer": "Paunawa",
    "Implemented": "Naipatupad",
    "Partial": "Bahagya",
    "Not Implemented": "Hindi Naipatupad",
    "Tax revenue": "Buwis",
    "Non-tax revenue": "Hindi Buwis na Kita",
    "National Tax Allotment": "National Tax Allotment",
    "Other external": "Iba pang panlabas",
    "Population": "Populasyon",
    "Population 2024": "Populasyon 2024",
    "PHP Millions": "PHP Milyon",
    "Fiscal Year": "Taon ng Piskal",
    "Year:": "Taon:",
    "Population:": "Populasyon:",
    "Growth since previous census:": "Paglaki mula sa nakaraang census:",
    "Budget:": "Badyet:",
    "Million": "Milyon",
    "Note: 2022 spike reflects one-time infrastructure transfers": "Tandaan: ang pagtaas noong 2022 ay dulot ng one-time infrastructure transfers",
    "Note: CY 2026 figure is SP-approved appropriation": "Tandaan: ang CY 2026 na bilang ay SP-approved appropriation",
    "Barangay:": "Barangay:",
    "Population (2024):": "Populasyon (2024):",
    "Confirmed match": "Kumpirmadong tugma",
    "Strong match": "Malakas na tugma",
    "Possible match": "Posibleng tugma",
    "No linked record": "Walang naka-link na record",
    "No match": "Walang tugma",
    "Reported": "Iniulat",
    "Records found in": "Mga record na natagpuan sa",
    "of 4 sources": "sa 4 na pinagmulan",
    "Evidence": "Ebidensya",
    "Source coverage": "Saklaw ng pinagmulan",
    "Technical details": "Teknikal na detalye",
    "Reporting periods": "Mga panahon ng pag-uulat",
    "Detail unavailable offline.": "Walang detalye offline.",
})

_JS_EXTRA["pag"].update({
    "Report Error": "I-ulat so Error",
    "Submit Missing Info": "Ipasa so Kulang ya Impormasyon",
    "Submit Missing Information": "Ipasa so Kulang ya Impormasyon",
    "Suggest Feature": "Mangisuggest na Feature",
    "Suggest New Feature": "Mangisuggest na Balo a Feature",
    "Enter a title above...": "Mangilagay na titulo ed tagey...",
    "Your submission preview will appear here as you type.": "Onta dia so preview na insumit mo tandis ya mantatayp ka.",
    "Draft opened! Please press 'Send' in your email app to complete.": "Naabri so draft! Pinduten so 'Send' ed email app pian nakumpleto.",
    "Copied to clipboard! Paste into your email app.": "Nakopya ed clipboard! I-paste ed email app.",
    "Data Correction:": "Correction na Datos:",
    "General": "Pangkalahatan",
    "Mode: Report Error": "Mode: I-ulat so Error",
    "Page/Item:": "Pahina/Item:",
    "Error:": "Error:",
    "Correction:": "Correction:",
    "Source:": "Pinanlapuan:",
    "New Information:": "Balo a Impormasyon:",
    "Mode: Submit Missing Info": "Mode: Ipasa so Kulang ya Impormasyon",
    "Category:": "Kategoria:",
    "Title:": "Titulo:",
    "Description:": "Deskripsyon:",
    "Feature Suggestion:": "Suggest na Feature:",
    "Mode: Suggest Feature": "Mode: Mangisuggest na Feature",
    "Feature:": "Feature:",
    "Use Case:": "Use Case:",
    "The page or item where the error was found": "Say pahina odino item ya nanengneng so kamalian",
    "Description of the error": "Deskripsyon na kamalian",
    "The correct data if known": "Say tam ya datos no amta",
    "Link to supporting document": "Link ed supporting a dokumento",
    "Category": "Kategoria",
    "Type of information being submitted": "Klase na impormasyon ya ipapasa",
    "Information Title / Name": "Titulo / Ngaran na Impormasyon",
    "Title of the information": "Titulo na impormasyon",
    "Detailed description": "Detalyadong deskripsyon",
    "Link to verifiable source": "Link ed verifiable a pinanlapuan",
    "Feature Name": "Ngaran na Feature",
    "Name of the proposed feature": "Ngaran na proposed a feature",
    "Detailed description of the feature": "Detalyadong deskripsyon na feature",
    "Use Case / Why it matters": "Use Case / Agay la importantin",
    "How this would help Mapandan residents": "Panon a saya a ontulong ed saray residente na Mapandan",
    "Unqualified": "Anggapo Puna",
    "Qualified": "Walay Puna",
    "Non-Compliant": "Agi Sumusunod",
    "Adverse": "Laban",
    "Disclaimer": "Pangasaway",
    "Implemented": "Naipatupad",
    "Partial": "Bahagi",
    "Not Implemented": "Agi Naipatupad",
    "Tax revenue": "Buwis",
    "Non-tax revenue": "Kita ya Ali Buwis",
    "National Tax Allotment": "National Tax Allotment",
    "Other external": "Arum a panlabas",
    "Population": "Populasyon",
    "Population 2024": "Populasyon 2024",
    "PHP Millions": "PHP Milyon",
    "Fiscal Year": "Taon na Piskal",
    "Year:": "Taon:",
    "Population:": "Populasyon:",
    "Growth since previous census:": "Panagduruk manlapud samay nakaunor a census:",
    "Budget:": "Badyet:",
    "Million": "Milyon",
    "Note: 2022 spike reflects one-time infrastructure transfers": "Tandaan: say panagpataas nen 2022 et lapud one-time infrastructure transfers",
    "Note: CY 2026 figure is SP-approved appropriation": "Tandaan: say bilang na CY 2026 et SP-approved appropriation",
    "Barangay:": "Barangay:",
    "Population (2024):": "Populasyon (2024):",
    "Confirmed match": "Nakumpirma a tugma",
    "Strong match": "Mabiskeg a tugma",
    "Possible match": "Nayarin tugma",
    "No linked record": "Anggapo naka-link a record",
    "No match": "Anggapo tugma",
    "Reported": "Ni-ulat",
    "Records found in": "Saray record ya naala ed",
    "of 4 sources": "na 4 a pinanlapuan",
    "Evidence": "Ebidensya",
    "Source coverage": "Saklaw na pinanlapuan",
    "Technical details": "Teknikal a detalye",
    "Reporting periods": "Saray panaon na panag-ulat",
    "Detail unavailable offline.": "Anggapo detalye offline.",
})

_JS_EXTRA["fil"].update({
    "Total Enacted Budget (PHP Millions)": "Kabuuang Naipatupad na Badyet (PHP Milyon)",
    "Unknown": "Hindi Alam",
    "Income (PHP Millions)": "Kita (PHP Milyon)",
    "Expenses (PHP Millions)": "Gastos (PHP Milyon)",
})
_JS_EXTRA["pag"].update({
    "Total Enacted Budget (PHP Millions)": "Kabuuan na Naipatupad a Badyet (PHP Milyon)",
    "Unknown": "Agi Amta",
    "Income (PHP Millions)": "Kita (PHP Milyon)",
    "Expenses (PHP Millions)": "Gastos (PHP Milyon)",
})
