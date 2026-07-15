from fastapi.testclient import TestClient
from web_service.main import app


def _client():
    return TestClient(app)


def test_resume_page_200():
    r = _client().get("/resume")
    assert r.status_code == 200


def test_resume_content_ported_verbatim():
    r = _client().get("/resume")
    assert "Logan Schwappach" in r.text
    assert "Hobart and William Smith" in r.text


def test_resume_jungle_theme_body_class():
    r = _client().get("/resume")
    assert 'class="jungle-theme"' in r.text


def test_resume_default_hieroglyphs_present():
    r = _client().get("/resume")
    glyphs = ["𓂧𓅲𓎢𓄿𓏏𓇋𓈖", "𓉔𓈖𓂋𓋴", "𓇨𓊪𓂋𓇋𓈖𓎢", "𓊪𓂋𓆓𓎢𓏏𓋴", "𓄿𓎢𓏏𓇋𓆯𓇋𓏏𓇋𓋴"]
    assert all(g in r.text for g in glyphs)


def test_nav_has_resume_link():
    r = _client().get("/resume")
    assert 'href="/resume"' in r.text
