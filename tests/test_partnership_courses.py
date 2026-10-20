"""Coverage of nine courses, accurate links, map semantics, and Rojo image removal."""
from pathlib import Path
from fastapi.testclient import TestClient
from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parents[1]
URL = '/servicos/parcerias/cursos'


def env():
    from app import app, COURSE_PARTNERS, BEAUTY_PARTNERS
    return TestClient(app), COURSE_PARTNERS, BEAUTY_PARTNERS


def test_all_nine_course_cards_and_brands_show():
    client, COURSE_PARTNERS, _ = env()
    assert len(COURSE_PARTNERS) == 9
    page = client.get(URL)
    assert page.status_code == 200
    root = BeautifulSoup(page.text, 'html.parser')
    cards = root.select('.course-partner')
    assert len(cards) == 9
    assert {x.get('id') for x in cards} == {c['slug'] for c in COURSE_PARTNERS}
    for school in COURSE_PARTNERS:
        card = root.select_one('#'+school['slug'])
        assert school['name'] in card.text
        assert school['discount'] in card.text
        assert school['address'] in card.text
        assert card.select_one('a[href="'+school['website']+'"]') is not None
        assert card.select_one('a[href="'+school['maps_url']+'"]') is not None
        if school['logo']:
            assert card.select_one('.course-logo-box img')['src'] == school['logo']
        else:
            assert card.select_one('.course-logo-fallback') is not None
    assert 'santoamaro@escolasargos.com.br' in page.text
    assert '94873-0486' in page.text
    assert '4003-3599' in page.text
    assert '3681-9695' in page.text
    assert '94513-0422' in page.text
    assert '9569-8690' in page.text
    assert '99596-9301' in page.text
    assert '98364-3933' in page.text
    assert '0800 702 0500' in page.text
    assert '0800 604 2210' in page.text
    assert '12x' not in page.text


def test_exact_addresses_in_maps_only_when_specific():
    client, COURSE_PARTNERS, _ = env()
    root = BeautifulSoup(client.get(URL).text, 'html.parser')
    iframe_cards = {x.parent.parent.parent.get('id') for x in root.select('.course-map iframe')}
    assert iframe_cards == {'argos','colegio-seta','damasio','supergeeks'}
    assert root.select_one('#argos iframe')['src'].startswith('https://www.google.com/maps?q=')
    for school in COURSE_PARTNERS:
        card = root.select_one('#'+school['slug'])
        assert (card.select_one('.course-map iframe') is not None) == school['show_map']
        if not school['show_map']:
            assert card.select_one('.course-map-lookup') is not None


def test_supergeeks_and_damasio_details_and_courses():
    client, _, _ = env()
    html = client.get(URL).text
    for s in ('40% a 72%', '10% de desconto', 'Até 58%', 'Administração, Contabilidade', '8 a 17 anos', 'exceto material didático', '20% de desconto', '25% de desconto', '15% nas mensalidades'):
        assert s in html, s
    assert 'Unidade Osasco' in html
    assert 'Avenida Miriam, 122' in html


def test_rojo_old_photo_is_gone_and_logo_stays():
    client, _, BEAUTY_PARTNERS = env()
    root = BeautifulSoup(client.get('/servicos/parcerias/beleza').text, 'html.parser')
    rojo = root.select_one('#acessorios-rojo')
    assert rojo.select_one('.beauty-partner-logo')['src'] == '/static/parcerias/logo-rojo.webp'
    assert not rojo.select('.beauty-partner-gallery, .beauty-partner-map, .beauty-partner-image-credit')
    assert 'acessorios.jpg' not in rojo.decode()
    assert not any(p['slug']=='acessorios-rojo' and p['gallery'] for p in BEAUTY_PARTNERS)


def test_new_css_synced_for_vercel():
    assert (BASE / 'static/style.css').read_bytes() == (BASE / 'public/static/style.css').read_bytes()
    client, _, _ = env()
    css = client.get('/static/style.css')
    assert css.status_code == 200
    assert '.course-partner-head' in css.text
    assert '@media(max-width:590px)' in css.text
