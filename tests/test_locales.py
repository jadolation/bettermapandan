import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _build.locales import load_locale, t


def test_load_locale_en():
    locale = load_locale("en")
    assert isinstance(locale, dict)
    assert "nav" in locale
    assert "home" in locale["nav"]
    assert "hero" in locale
    assert "eyebrow" in locale["hero"]
    assert locale["nav"]["home"] == "Home"
    assert locale["hero"]["title"] == "Better Mapandan"


def test_load_locale_fil():
    locale = load_locale("fil")
    assert isinstance(locale, dict)
    assert "nav" in locale
    assert "home" in locale["nav"]
    assert "hero" in locale
    assert "eyebrow" in locale["hero"]
    assert locale["nav"]["home"] == "Pangunahing Pahina"
    assert locale["hero"]["title"] == "Better Mapandan"


def test_load_locale_pag():
    locale = load_locale("pag")
    assert isinstance(locale, dict)
    assert "nav" in locale
    assert "home" in locale["nav"]
    assert locale["nav"]["home"] == "Abong"


def test_t_pag_existing_key():
    locale = load_locale("pag")
    result = t(locale, "nav.home", "default")
    assert result == "Abong"


def test_t_existing_key():
    locale = load_locale("en")
    assert t(locale, "nav.home", "default") == "Home"
    assert t(locale, "hero.title", "default") == "Better Mapandan"


def test_t_missing_key_returns_fallback():
    locale = load_locale("en")
    assert t(locale, "nonexistent.key", "fallback") == "fallback"


def test_t_nested_keys():
    locale = load_locale("en")
    result = t(locale, "nav.home")
    assert result == "Home"
    result = t(locale, "hero.search_placeholder")
    assert result == "business permit, barangay clearance, hospital..."
