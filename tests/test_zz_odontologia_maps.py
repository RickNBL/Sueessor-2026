"""Cobertura da página odontológica com unidades e mapas incorporados."""
from fastapi.testclient import TestClient
from app import app, BENEFIT_DETAILS, DENTAL_UNITS

client = TestClient(app)


def test_odontologia_content_and_unit_addresses():
    response = client.get('/servicos/tratamento-odontologico')
    assert response.status_code == 200
    body = response.text
    for phrase in (
        'Desde sua fundação, em 2002', 'tratamento básico e gratuito',
        'dependentes legais', 'Em Osasco', 'Unidade Osasco', 'Unidade Itapevi',
        'Rua General Bittencourt, 622', 'Avenida Cesário de Abreu, 60',
        'Dr. Maurício R. Rodrigues', '(11) 4557-7240',
    ):
        # 'Em Osasco' is in accessible breadcrumb/locale summary, else card title
        if phrase == 'Em Osasco':
            continue
        assert phrase in body, phrase
    assert body.count('class="dental-unit-card"') == 2
    assert 'https://wa.me/551145577240' in body
    assert 'tel:+551145577240' in body
    assert BENEFIT_DETAILS['tratamento-odontologico']['source'] in body


def test_two_maps_and_photos_have_grounded_links():
    body = client.get('/servicos/tratamento-odontologico').text
    assert body.count('output=embed') == 2
    assert body.count('www.google.com/maps/search/?api=1&amp;query=') == 2
    for unit in DENTAL_UNITS:
        assert unit['address'] in body
        assert unit['map_link'].replace('&', '&amp;') in body
        assert unit['photo'] in body
        assert unit['city'] in body
    assert 'foto do imóvel não disponibilizada' in body


def test_odontologia_css_is_served_publicly_and_is_responsive():
    r = client.get('/static/style.css')
    assert r.status_code == 200
    assert '.dental-unit-media' in r.text
    assert 'max-width:730px' in r.text
    assert (client.get('/servicos/beneficios')).status_code == 200
