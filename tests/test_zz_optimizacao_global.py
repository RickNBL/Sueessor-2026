"""Contrato de navegação, responsividade e assets após a revisão global."""
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

import app

ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app.app)


@pytest.mark.parametrize('route',[ 
    '/', '/sobre', '/abrangencia', '/diretoria', '/convencoes',
    '/servicos/beneficios', '/servicos/parcerias',
    '/servicos/parcerias/beleza', '/servicos/parcerias/clubes',
    '/servicos/parcerias/cursos', '/servicos/parcerias/parques',
    '/servicos/parcerias/produtos-e-servicos', '/servicos/parcerias/saude',
    '/servicos/parcerias/viagens-e-turismo', '/servicos/clinica-medica',
    '/servicos/tratamento-odontologico', '/documentos/editais',
    '/documentos/acordos', '/documentos/financeiro', '/noticias',
    '/contato', '/denuncie',
])
def test_paginas_permanecem_acessiveis(route):
    response = client.get(route)
    assert response.status_code == 200, route
    assert 'id="main"' in response.text
    assert 'Pular para o conteúdo principal' in response.text
    assert 'id="mobile-nav"' in response.text


def test_menu_mobile_agrupado_com_destinos():
    html = client.get('/servicos/parcerias').text
    assert 'aria-controls="mobile-nav"' in html
    assert html.count('class="mobile-nav-group"') == 4
    for href in ['/servicos/parcerias/parques','/documentos/editais','/documentos/acordos',
                 '/documentos/financeiro','/servicos/clinica-medica']:
        assert f'href="{href}"' in html


def test_otimizacao_fontes_e_css_versionados():
    html = client.get('/').text
    assert '/static/style.css?v=design-mobile-20261021' in html
    assert 'bootstrap-grid.min.css' not in html
    assert 'fonts.gstatic.com' in html
    assert (ROOT / 'static/style.css').read_bytes() == (ROOT / 'public/static/style.css').read_bytes()
    assert (ROOT / 'static/main.js').read_bytes() == (ROOT / 'public/static/main.js').read_bytes()


def test_carrossel_mobile_tem_imagens_menores():
    html=client.get('/').text
    assert 'sizes="(max-width:760px)' in html
    assert 'poster="/static/hero-video-poster.webp"' in html
    assert (ROOT / 'static/hero-video-poster.webp').is_file()
    for name in ['destaque-assedio-moral','destaque-o-que-sao-sindicatos',
                 'destaque-sugestao-de-temas','destaque-parques-conveniados',
                 'destaque-super-geeks']:
        original=ROOT / f'static/{name}.webp'
        mobile=ROOT / f'static/{name}-mobile.webp'
        assert mobile.is_file()
        assert mobile.stat().st_size < original.stat().st_size
        assert (ROOT / 'public/static' / mobile.name).read_bytes() == mobile.read_bytes()
        assert f'/static/{name}-mobile.webp' in html


def test_interacoes_celular_e_busca():
    js=(ROOT/'static/main.js').read_text()
    assert 'setMenu=(open,restoreFocus=false)' in js
    assert 'e.composedPath().includes(header)' in js
    assert "if(e.key==='Escape'" in js
    assert "['Parques conveniados'" in js
