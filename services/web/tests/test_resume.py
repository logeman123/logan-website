"""Tests for the standalone ``/resume`` page.

Unlike the other web routes, ``/resume`` is a hand-built, self-contained retro
"jungle"-themed page. It pulls NO data from the content or ai services, so these
tests need no dependency overrides -- a plain ``TestClient(app)`` is enough. The
checks here are essentially "the special page renders and its distinctive,
easy-to-break details survived": the ported resume copy, the jungle theme body
class, the Egyptian-hieroglyph section headers (which Alpine later reveals into
plain words), and the nav link. Because these strings are load-bearing for the
page's identity/behavior, asserting their literal presence guards against
accidental deletion during refactors.
"""

from fastapi.testclient import TestClient
from web_service.main import app


def _client():
    # No dependency_overrides: /resume orchestrates no backends, so the real app
    # can be served as-is with no fakes injected.
    return TestClient(app)


def test_resume_page_200():
    # Smoke test: the route exists and renders without error.
    r = _client().get("/resume")
    assert r.status_code == 200


def test_resume_content_ported_verbatim():
    # Guard that the actual resume content (name + school) was ported into the
    # template verbatim and did not get lost in the hand-built markup.
    r = _client().get("/resume")
    assert "Logan Schwappach" in r.text
    assert "Hobart and William Smith" in r.text


def test_resume_jungle_theme_body_class():
    # The page opts into its route-specific "jungle" theme via a body class;
    # this asserts that themed styling hook is present.
    r = _client().get("/resume")
    assert 'class="jungle-theme"' in r.text


def test_resume_default_hieroglyphs_present():
    # Section headers ship as Egyptian hieroglyphs in the initial HTML; Alpine
    # reveals them into readable words on interaction. We assert the DEFAULT
    # (pre-reveal) glyph state is what the server sends, so the effect starts
    # from the intended point. Each glyph string corresponds to one section
    # header (e.g. "education", "honors", ...).
    r = _client().get("/resume")
    glyphs = ["𓂧𓅲𓎢𓄿𓏏𓇋𓈖", "𓉔𓈖𓂋𓋴", "𓇨𓊪𓂋𓇋𓈖𓎢", "𓊪𓂋𓆓𓎢𓏏𓋴", "𓄿𓎢𓏏𓇋𓆯𓇋𓏏𓇋𓋴"]
    assert all(g in r.text for g in glyphs)


def test_nav_has_resume_link():
    # The site navigation must expose a link to /resume so the page is reachable.
    r = _client().get("/resume")
    assert 'href="/resume"' in r.text
