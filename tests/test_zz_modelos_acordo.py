"""Regressão da página de modelos de acordo coletivo SUEESSOR."""
from pathlib import Path
import hashlib
import importlib

from fastapi.testclient import TestClient

BASE = Path(__file__).resolve().parents[1]


def test_modelos_catalogo_inclui_os_dois_pdfs():
    app = importlib.import_module('app')
    assert len(app.AGREEMENT_MODELS) == 2
    assert {m['id'] for m in app.AGREEMENT_MODELS} == {'banco-de-horas', 'jornada-12x36'}
    assert {m['pages'] for m in app.AGREEMENT_MODELS} == {3, 4}
    assert all(m['url'].startswith('/modelos-de-acordo/arquivos/') for m in app.AGREEMENT_MODELS)


def test_pagina_apresenta_conteudo_fiel_e_acoes():
    app = importlib.import_module('app')
    result = TestClient(app.app).get('/documentos/acordos')
    assert result.status_code == 200
    html = result.text
    for name in ('Acordo coletivo de trabalho para implantação de Banco de Horas',
                 'Acordo coletivo de trabalho para compensação de horas com implantação do regime de jornada 12×36',
                 'doze horas de trabalho por 36 horas de descanso',
                 'Visualizar PDF', 'Baixar PDF', 'modelos de referência de 2019'):
        assert name.casefold() in html.casefold(), name
    assert html.count('<article class="agreement-card"') == 2
    assert html.count('<iframe class="agreement-pdf-viewer"') == 2
    assert html.count('class="agreement-details"') == 2
    assert 'download="Acordo-Coletivo-Modelo-Banco-de-Horas.pdf"' in html
    assert 'download="Acordo-Coletivo-Modelo-Jornada-12x36.pdf"' in html


def test_pdfs_sao_os_originais_e_sao_servidos_por_url_local():
    app = importlib.import_module('app')
    client = TestClient(app.app)
    references = {
        'banco-de-horas': ('6343e3ea8f4c46f9faf83c54823eee690fd5de073d0639c5d2abd70e69f159c3', 4),
        'jornada-12x36': ('ae3442a2cc57083a556db1e8664fd776d090d82910b84a36f91a72a020a5bb71', 3),
    }
    for model in app.AGREEMENT_MODELS:
        path = BASE / 'public' / model['url'].lstrip('/')
        assert path.is_file()
        assert path.read_bytes()[:5] == b'%PDF-'
        expected_hash, pages = references[model['id']]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash
        assert model['pages'] == pages
        response = client.get(model['url'])
        assert response.status_code == 200
        assert response.headers['content-type'].startswith('application/pdf')
        assert response.content == path.read_bytes()


def test_css_sincronizado_e_menu_mobile_com_acesso():
    assert (BASE / 'static/style.css').read_bytes() == (BASE / 'public/static/style.css').read_bytes()
    app = importlib.import_module('app')
    html = TestClient(app.app).get('/documentos/acordos').text
    assert 'href="/static/style.css?v=design-mobile-20261021"' in html
    assert html.count('href="/documentos/acordos"') >= 2
    assert '.agreement-card' in (BASE / 'static/style.css').read_text(encoding='utf-8')
