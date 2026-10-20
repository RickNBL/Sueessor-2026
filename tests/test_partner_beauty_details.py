"""Regressão das três parcerias, mapas, serviços e regras divulgadas."""
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

@pytest.fixture(scope="module")
def site():
    from app import app, BEAUTY_PARTNERS
    return TestClient(app), BEAUTY_PARTNERS

BASE = Path(__file__).resolve().parents[1]
URL = '/servicos/parcerias/beleza'


def test_beauty_partners_render_and_only_other_two_maps(site):
    response = site[0].get(URL)
    assert response.status_code == 200
    html = response.text
    assert html.count('class="beauty-partner-card"') == 3
    assert html.count('output=embed') == 2
    assert html.count('class="beauty-partner-map"') == 2
    assert html.count('Falar no WhatsApp') == 3
    assert 'R$ 109,90' in html
    assert '12× de R$ 109,90' in html
    assert '4 convidados por mês' in html
    assert '60 dias de trancamento' in html
    assert '10% de desconto' in html
    assert 'Rua Presidente Castelo Branco, 159' in html
    assert 'Rua Antônio Agú, 502' in html
    assert '11.96050-2742' not in html
    assert '96050-2742' in html
    assert 'São Paulo – Fashion Hair' in html
    assert 'Morellos – Academia' in html


def test_images_are_grounded_not_mislabeled_and_have_source_fallback(site):
    response = site[0].get(URL)
    html = response.text
    assert '/static/parcerias/logo-rojo.webp' in html
    assert 'beauty-partner-image-credit' not in html
    assert 'logotipo oficial na parede' in html
    assert html.count('class="beauty-partner-gallery"') == 1
    assert '24105827/acessorios.jpg' not in html
    assert 'beauty-partner-picture--logo' in html


def test_maps_urls_and_whatsapp_for_every_partner(site):
    BEAUTY_PARTNERS = site[1]
    assert len(BEAUTY_PARTNERS) == 3
    for p in BEAUTY_PARTNERS:
        assert 'maps?q=' in p['map_embed']
        assert 'output=embed' in p['map_embed']
        assert 'https://www.google.com/maps/search/?api=1&query=' in p['maps_url']
        assert p['whatsapp_href'].startswith('https://wa.me/5511')
        assert p['phone_href'].startswith('tel:+5511')
        assert p['name']


def test_css_on_static_and_public_match_and_mobile_rules_present():
    css = (BASE / 'static/style.css').read_text()
    assert '@media(max-width:670px)' in css
    assert '.beauty-partner-card' in css
    assert '.beauty-partner-map iframe' in css
    assert (BASE / 'public/static/style.css').read_bytes() == (BASE / 'static/style.css').read_bytes()


def test_rojo_no_map_but_logo_visible_and_other_partners_have_maps(site):
    from bs4 import BeautifulSoup
    page = BeautifulSoup(site[0].get(URL).text, 'html.parser')
    rojo = page.select_one('#acessorios-rojo')
    assert rojo is not None
    assert rojo.select_one('.beauty-partner-logo')['src'] == '/static/parcerias/logo-rojo.webp'
    assert not rojo.select('.beauty-partner-map, iframe, a[href*="google.com/maps"]')
    assert not page.select('.beauty-partner-image-credit')
    assert len(page.select('.beauty-partner-map')) == 2
    assert len(page.select('#sao-paulo-fashion-hair .beauty-partner-map')) == 1
    assert len(page.select('#morellos-academia .beauty-partner-map')) == 1
    assert (BASE / 'public/static/parcerias/logo-rojo.webp').read_bytes() == (BASE / 'static/parcerias/logo-rojo.webp').read_bytes()
    asset=site[0].get('/static/parcerias/logo-rojo.webp')
    assert asset.status_code == 200
    assert asset.headers['content-type'] == 'image/webp'
