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


def test_beauty_partners_render_and_three_maps(site):
    response = site[0].get(URL)
    assert response.status_code == 200
    html = response.text
    assert html.count('class="beauty-partner-card"') == 3
    assert html.count('output=embed') == 3
    assert html.count('class="beauty-partner-map"') == 3
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
    assert 'Foto dos produtos, publicada pelo SUEESSOR' in html
    assert 'Fotografia verificada do estabelecimento ainda indisponível' in html
    assert 'logotipo oficial na parede' in html
    assert html.count('class="beauty-partner-gallery"') == 1
    assert html.count('class="beauty-partner-picture"') == 3


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
