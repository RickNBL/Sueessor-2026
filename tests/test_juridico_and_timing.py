"""Regressão das solicitações de horários jurídicos e troca a cada 10 s."""
from pathlib import Path
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


def test_autoplay_is_10_seconds_in_both_typescript_and_built_assets():
    for filename in ('src/carousel.ts', 'static/carousel.js', 'public/static/carousel.js'):
        content = (ROOT / filename).read_text()
        assert 'const intervalMs = 10000;' in content
        assert '7500' not in content
    from app import app
    client = TestClient(app)
    assert 'const intervalMs = 10000;' in client.get('/static/carousel.js').text


def test_juridical_page_contains_supplied_content_and_contact_links():
    from app import app
    response = TestClient(app).get('/servicos/juridico')
    assert response.status_code == 200
    html = response.text
    for phrase in (
        'Assessoria Jurídica',
        'ações (judiciais ou extrajudiciais) propostas pelo SUEESSOR',
        'trabalhista, familiar e previdenciária',
        'Horário de Atendimento dos Plantões',
        'Área Trabalhista e Familiar',
        'Quintas-feiras', '09H00 às 16H00',
        'Dra. Lilian Bisaro e/ou Dr. Flávio Bezerra',
        'Área Previdenciária', 'Sextas-feiras', '09H00 às 12H00',
        'Roberto Dias', 'Informações Gerais',
        'Rua General Bittencourt, 582 – Centro – Osasco/SP',
        '11.3652-3390', '11.94182-5124',
        'Google PLAYSTORE',
        'href="tel:+551136523390"', 'href="tel:+5511941825124"',
    ):
        assert phrase in html
    assert html.count('data-promo-slide') == 0


def test_other_services_are_unchanged():
    from app import app
    client = TestClient(app)
    assert 'Parques e lazer para associados' in client.get('/servicos/parcerias').text
    assert 'Acordos e convenções' in client.get('/servicos/beneficios').text
    assert client.get('/').status_code == 200
