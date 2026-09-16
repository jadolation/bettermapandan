import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _build.templates import (
    fill,
    parse_page,
    strip_front_matter,
    strip_html,
    compute_asset_base,
    compute_url,
)


def test_parse_page_with_front_matter():
    text = "---\ntitle: Test\ndescription: A test page\n---\n<h1>Hello</h1>"
    meta, body = parse_page(text)
    assert meta["title"] == "Test"
    assert meta["description"] == "A test page"
    assert body == "<h1>Hello</h1>"


def test_parse_page_no_front_matter():
    text = "<h1>Hello</h1>"
    try:
        parse_page(text)
        assert False, "Expected SystemExit"
    except SystemExit:
        pass


def test_fill_with_values():
    template = "<h1>{{title}}</h1><p>{body}</p>"
    result = fill(template, {"title": "Test", "body": "Content"})
    assert result == "<h1>Test</h1><p>Content</p>"


def test_fill_with_none_value():
    template = "<h1>{{title}}</h1>"
    result = fill(template, {"title": None})
    assert result == "<h1></h1>"


def test_strip_html():
    html = "<p>Hello <b>world</b></p>"
    result = strip_html(html)
    assert result == "Hello world"


def test_strip_front_matter_with_front_matter():
    text = "---\ntitle: Test\n---\n<p>Content</p>"
    result = strip_front_matter(text)
    assert result == "<p>Content</p>"


def test_strip_front_matter_without_front_matter():
    text = "<p>Content</p>"
    result = strip_front_matter(text)
    assert result == "<p>Content</p>"


def test_compute_url():
    assert compute_url(Path("index.html")) == "index.html"
    assert compute_url(Path("about/index.html")) == "about/index.html"
    assert compute_url(Path("a/b/c.html")) == "a/b/c.html"


def test_compute_asset_base_root():
    assert compute_asset_base(Path("index.html"), False) == "."
    assert compute_asset_base(Path("index.html"), True) == "."


def test_compute_asset_base_nested():
    assert compute_asset_base(Path("about/index.html"), False) == ".."
    assert compute_asset_base(Path("a/b/index.html"), False) == "../.."
