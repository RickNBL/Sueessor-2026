"""Regressão da página Produtos e Serviços e do CSS público servido pela Vercel."""
from pathlib import Path
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

BASE = Path(__file__).resolve().parents[1]


def test_products_page_contains_exact_partners_and_contact_links():
    from app import app, PRODUCT_SERVICE_PARTNERS
    client = TestClient(app)
    resp = client.get('/servicos/parcerias/produtos-e-servicos')
    assert resp.status_code == 200
    dom = BeautifulSoup(resp.text, 'html.parser')
    cards = dom.select('article.product-partner')
    assert len(cards) == 3
    assert [p['name'] for p in PRODUCT_SERVICE_PARTNERS] == ['Cinemark', 'Disk Carreto', 'Maria Chica']
    assert not dom.select('iframe')
    for slug, tel in [('cinemark','tel:+551136523390'),('disk-carreto','tel:+5511997752672'),('maria-chica','tel:+5511985699023')]:
        card = dom.select_one('#' + slug)
        assert card
        assert card.select_one('img[src^="https://sites.diretasistemas.com.br/"]')
        assert card.select_one('a[href="' + tel + '"]')
    assert 'Noêmia' in cards[0].get_text(' ')
    assert 'Marcos' in cards[1].get_text(' ')
    assert 'Mariane' in cards[2].get_text(' ')
    assert 'https://www.instagram.com/mariachicauniverso/' in resp.text
    assert 'https://sueessor.org.br/produtos-e-servicos/' in resp.text


def test_product_css_available_in_both_static_roots():
    static = (BASE / 'static/style.css').read_bytes()
    public = (BASE / 'public/static/style.css').read_bytes()
    assert static == public
    assert b'.product-partner' in static
    assert b'@media(max-width:620px)' in static
