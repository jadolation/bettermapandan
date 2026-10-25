import json

import pytest

from _build.config import ROOT
from _build.generators.services import _build_category_service_links, generate_services
from _build.labels import resolve_body_placeholders


@pytest.mark.parametrize("lang", ["en", "fil", "pag"])
def test_tool_projection_preserves_official_services(lang):
    locale = json.loads((ROOT / f"locales/{lang}.json").read_text())
    data = json.loads((ROOT / "src/data/services.json").read_text())
    pages, _, _ = generate_services(locale, lang)
    assert len(pages) == len(data["services"]) + 1
    directory = pages["services.html"]
    assert directory.count('class="service-link"') == len(data["services"]) + 1
    assert directory.count('data-entry-type="digital-tool"') == 1
    prefix = "" if lang == "en" else f"/{lang}"
    assert f'href="{prefix}/commuter/"' in directory
    analytics = json.loads(directory.split("window.SERVICES_ANALYTICS = ")[1].split(";</script>")[0])
    assert sum(analytics["categories"].values()) == len(data["services"])
    assert sum(analytics["offices"].values()) == len(data["services"])
    assert "services/commuter.html" not in pages


@pytest.mark.parametrize("lang", ["en", "fil", "pag"])
def test_discovery_placement_and_compact_gis_notice(lang):
    locale = json.loads((ROOT / f"locales/{lang}.json").read_text())
    home = resolve_body_placeholders((ROOT / "src/pages/index.html").read_text(), locale, "/")
    assert home.index('id="dpwh-map"') < home.index('class="wrap commuter-discovery"') < home.index('class="map-container"')
    gis = resolve_body_placeholders((ROOT / "src/pages/gis.html").read_text(), locale, "/")
    assert "/commuter/" not in gis
    assert "DISCOVERY_" not in gis
    assert "map_title" not in locale["commuter_discovery"]
    assert "map_description" not in locale["commuter_discovery"]
    notice = [locale["gis"][key] for key in ("unavailable", "precision", "safety")]
    assert sum(len(text.split()) for text in notice) <= 65
    assert all(text.count(".") == 1 for text in notice)
    assert "911" in notice[2] and "MDRRMO" in notice[2]
    reviews = {row["key"]: row for row in json.loads((ROOT / "src/data/pag-review.json").read_text())}
    for key, text in zip(("unavailable", "precision", "safety"), notice):
        assert reviews[f"gis.{key}"][{"en": "english", "fil": "filipino", "pag": "pangasinan"}[lang]] == text


@pytest.mark.parametrize("destination", ["//example.org/", "https://example.org/", "/fil/../commuter/", "/commuter/?x=1"])
def test_tool_rejects_noncanonical_destination(destination):
    with pytest.raises(ValueError):
        _build_category_service_links([{
            "entry_type": "digital-tool", "destination": destination,
            "name": "Tool", "description": "Information",
        }], "en")
