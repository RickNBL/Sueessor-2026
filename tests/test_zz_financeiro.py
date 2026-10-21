"""Regressão da página Financeiro e publicação dos estilos para Vercel."""
from pathlib import Path
from fastapi.testclient import TestClient
from app import app

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://sweb.diretasistemas.com.br/prosindweb/index.php?sind=1955'


def test_financeiro_tem_texto_e_link_de_boletos():
    response = TestClient(app).get('/documentos/financeiro')
    assert response.status_code == 200
    html = response.text
    assert 'Agora sua empresa ou contabilidade tem a facilidade de imprimir os boletos' in html
    assert URL.replace('&', '&amp;') in html or URL in html
    assert 'Acessar emissão de boletos' in html
    assert 'target="_blank"' in html
    assert 'rel="noopener noreferrer"' in html
    assert 'finance-section' in html


def test_financeiro_estilos_iguais_para_vercel():
    local_css = (ROOT / 'static' / 'style.css').read_bytes()
    public_css = (ROOT / 'public' / 'static' / 'style.css').read_bytes()
    assert local_css == public_css
    assert b'.finance-section' in public_css
    assert b'.finance-access-button' in public_css


def test_financeiro_sem_alterar_outros_documentos():
    client = TestClient(app)
    for url in ('/documentos/acordos', '/documentos/editais', '/convencoes'):
        assert client.get(url).status_code == 200
