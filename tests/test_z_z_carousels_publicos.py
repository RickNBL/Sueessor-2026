"""Regression tests for deployable clinic and event benefit carousels."""
from pathlib import Path
from fastapi.testclient import TestClient
from app import app, BENEFIT_DETAILS

ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def test_vercel_assets_synced():
    for name in ('benefits.js', 'style.css'):
        assert (ROOT / 'static' / name).read_bytes() == (ROOT / 'public' / 'static' / name).read_bytes()
    javascript = (ROOT / 'public/static/benefits.js').read_text()
    assert "[data-clinic-carousel]" in javascript
    assert "window.setInterval" in javascript
    assert 'visibilitychange' in javascript


def test_galleries_serve_assets_and_controls_without_gradient():
    for slug in ('clinica-medica', 'espaco-para-eventos'):
        response = client.get(f'/servicos/{slug}')
        assert response.status_code == 200
        assert 'data-clinic-carousel' in response.text
        assert 'data-interval="5000"' in response.text
        assert 'data-clinic-prev' in response.text
        assert 'data-clinic-next' in response.text
        assert 'clinic-gallery-wash' not in response.text
        gallery = BENEFIT_DETAILS[slug]['gallery']
        assert len(gallery) > 1
        for photo in gallery:
            path = photo['src'].removeprefix('/static/')
            assert (ROOT / 'static' / path).is_file()
            assert (ROOT / 'public/static' / path).is_file()
            file_response = client.get(photo['src'])
            assert file_response.status_code == 200
            assert file_response.headers['content-type'].startswith('image/')


def test_no_photo_overlay_styles():
    css = (ROOT / 'static/style.css').read_text()
    assert '.clinic-gallery-wash{' not in css
    assert '.clinic-slide figcaption{' not in css
    assert '.clinic-slide img{width:100%;height:100%;object-fit:contain;' in css
