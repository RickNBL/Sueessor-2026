"""Garantias da nova página de benefícios e das seis páginas individuais."""
from fastapi.testclient import TestClient
from app import app, BENEFIT_CARDS, BENEFIT_DETAILS

client = TestClient(app)


def test_all_seven_cards_are_links_with_descriptions():
    response = client.get('/servicos/beneficios')
    assert response.status_code == 200
    html = response.text
    assert html.count('data-benefit-card') == 7
    for item in BENEFIT_CARDS:
        assert f'href="{item["href"]}"' in html
        assert item['title'] in html
    assert '/static/benefits.js' in html


def test_each_card_routes_to_correct_detail():
    for item in BENEFIT_CARDS:
        resp = client.get(item['href'])
        assert resp.status_code == 200, item['href']
        assert item['title'].lower() in resp.text.lower(), item
        assert 'SUEESSOR' in resp.text
    assert len(BENEFIT_DETAILS) == 6
    assert 'Lilian Bisaro' in client.get('/servicos/juridico').text


def test_new_details_are_real_pages_with_contacts_and_source_links():
    for slug, detail in BENEFIT_DETAILS.items():
        response = client.get('/servicos/' + slug)
        text = response.text
        assert response.status_code == 200
        assert detail['phone_display'] in text
        assert detail['source'] in text
        assert detail['address'] in text
        assert 'Informações no portal oficial' in text
        assert len(detail['highlights']) >= 3


def test_animation_assets_are_served_and_degrade_gracefully():
    css = client.get('/static/style.css')
    js = client.get('/static/benefits.js')
    assert css.status_code == 200
    assert js.status_code == 200
    assert 'rotateY(45deg)' in css.text
    assert 'benefit-tremble' in css.text
    assert 'prefers-reduced-motion' in css.text
    assert 'event.preventDefault()' in js.text
    assert 'window.location.assign(target)' in js.text
    assert client.get('/servicos/nao-existe').status_code == 404
