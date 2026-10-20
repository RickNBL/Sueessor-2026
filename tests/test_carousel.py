"""Campanhas da home: conteúdo fiel aos anexos, links e assets do carrossel."""
from pathlib import Path
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]

CAMPAIGNS = [
    ('destaque-assedio-moral.webp', '/denuncie'),
    ('destaque-o-que-sao-sindicatos.webp', '/sobre#o-que-e-um-sindicato'),
    ('destaque-sugestao-de-temas.webp', '/contato'),
    ('destaque-parques-conveniados.webp', '/servicos/parcerias/parques'),
    ('destaque-super-geeks.webp', '/servicos/parcerias/cursos'),
]


def test_carousel_is_after_app_banner_and_before_services():
    from app import app
    html = TestClient(app).get('/').text
    assert html.index('id="app-banner"') < html.index('id="destaques"') < html.index('id="servicos"')
    assert html.count('data-promo-slide') == 5
    assert html.count('data-promo-dot="') == 5
    for file, link in CAMPAIGNS:
        assert f'/static/{file}' in html
        assert f'href="{link}"' in html


def test_promo_images_and_interactions_are_deployed():
    from app import app
    client = TestClient(app)
    for filename, url in CAMPAIGNS:
        assert (ROOT / 'static' / filename).is_file()
        assert (ROOT / 'public/static' / filename).is_file()
        response = client.get('/static/' + filename)
        assert response.status_code == 200
        assert response.headers['content-type'].startswith('image/webp')
        assert client.get(url.split('#')[0]).status_code == 200
    assert 'data-promo-carousel' in client.get('/').text
    assert 'id="o-que-e-um-sindicato"' in client.get('/sobre').text
    assert 'href="/servicos/parcerias/parques"' in client.get('/servicos/parcerias').text
    assert 'href="/servicos/parcerias/cursos"' in client.get('/servicos/parcerias').text
    assert (ROOT / 'src/carousel.ts').is_file()
    assert (ROOT / 'static/carousel.js').is_file()
    assert (ROOT / 'public/static/carousel.js').is_file()
