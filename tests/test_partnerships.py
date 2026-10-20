"""Regressão para as sete novas páginas de parcerias e o texto de Benefícios."""
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def partner_env():
    # Import only when running tests: test_portal configures an isolated test DB at collection.
    from app import app, PARTNERSHIP_CARDS, PARTNERSHIP_DETAILS
    return TestClient(app), PARTNERSHIP_CARDS, PARTNERSHIP_DETAILS


def test_landing_matches_benefits_cards_interaction_and_routes(partner_env):
    client, PARTNERSHIP_CARDS, PARTNERSHIP_DETAILS = partner_env
    resp = client.get('/servicos/parcerias')
    assert resp.status_code == 200
    html = resp.text
    assert 'Mais vantagens.' in html
    assert html.count('data-benefit-card') == 7
    assert 'benefit-grid partnership-grid' in html
    assert 'benefits.js' in html
    assert len(PARTNERSHIP_CARDS) == 7
    for card in PARTNERSHIP_CARDS:
        assert card['title'] in html
        assert f'href="{card["href"]}"' in html


def test_seven_partner_pages_with_real_content_and_no_missing_routes(partner_env):
    client, PARTNERSHIP_CARDS, PARTNERSHIP_DETAILS = partner_env
    assert len(PARTNERSHIP_DETAILS) == 7
    for card in PARTNERSHIP_CARDS:
        resp = client.get(card['href'])
        assert resp.status_code == 200, card['href']
        html = resp.text
        assert card['title'] in html
        assert ('beauty-partner-card' in html if card['slug'] == 'beleza' else ('club-partner' in html if card['slug'] == 'clubes' else '<article class="partnership-feature">' in html))
        assert ('Portal oficial do SUEESSOR' in html if card['slug'] == 'beleza' else ('Informações divulgadas pelo SUEESSOR' in html if card['slug'] == 'clubes' else 'Ver informações no portal oficial' in html))
        assert 'Condições' in html or 'condições' in html or 'condições' in html.lower()
        details = PARTNERSHIP_DETAILS[card['slug']]
        assert len(details['features']) > 0
        assert details['source'] in html
        if card['slug'] != 'clubes':
            for feature in details['features']:
                assert feature['title'] in html
    assert client.get('/servicos/parcerias/nao-existe').status_code == 404


def test_benefits_page_includes_supplied_copy_and_real_path_to_partnerships(partner_env):
    client, PARTNERSHIP_CARDS, PARTNERSHIP_DETAILS = partner_env
    html = client.get('/servicos/beneficios').text
    for phrase in (
        'Parcerias exclusivas para ampliar suas vantagens no dia a dia',
        'O Sindicato disponibiliza uma rede de parcerias cuidadosamente selecionadas',
        'Ser associado é contar com vantagens reais que acompanham você em todos os momentos.',
        'beleza, clubes, cursos, parques, produtos e serviços, saúde, além de viagens e turismo.',
    ):
        assert phrase in html
    assert 'href="/servicos/parcerias"' in html
    assert html.count('data-benefit-card') == 7


def test_promo_slides_point_to_relevant_partner_pages(partner_env):
    client, PARTNERSHIP_CARDS, PARTNERSHIP_DETAILS = partner_env
    html = client.get('/').text
    assert '/servicos/parcerias/parques' in html
    assert '/servicos/parcerias/cursos' in html


def test_animated_cards_share_same_assets_on_vercel(partner_env):
    client, PARTNERSHIP_CARDS, PARTNERSHIP_DETAILS = partner_env
    stylesheet = client.get('/static/style.css').text
    script = client.get('/static/benefits.js').text
    assert '.partnership-card' in stylesheet
    assert 'rotateY(45deg)' in stylesheet
    assert 'benefit-card-clicked' in script
    assert 'window.location.assign(target)' in script
    assert (ROOT / 'static' / 'benefits.js').read_bytes() == (ROOT / 'public' / 'static' / 'benefits.js').read_bytes()
    assert (ROOT / 'static' / 'style.css').read_bytes() == (ROOT / 'public' / 'static' / 'style.css').read_bytes()
