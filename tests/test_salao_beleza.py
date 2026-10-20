from pathlib import Path
from fastapi.testclient import TestClient
from app import app, BENEFIT_DETAILS

BASE=Path(__file__).resolve().parents[1]

def test_spaco_beleza_texto_e_agendamento():
    r=TestClient(app).get('/servicos/salao-de-beleza')
    assert r.status_code == 200
    for text in ('SPAÇO BELEZA SUEESSOR','Manicure','Depilação','Designer de sobrancelha','Cabeleireiro unissex','dependentes legais','08h00 às 17h00','(11) 3652-3390','Rua General Bittencourt, 582'):
        assert text in r.text
    assert 'href="tel:+551136523390"' in r.text


def test_spaco_beleza_gallery():
    detail=BENEFIT_DETAILS['salao-de-beleza']
    assert detail['gallery_interval'] == 5000
    assert len(detail['gallery']) == 2
    html=TestClient(app).get('/servicos/salao-de-beleza').text
    assert 'data-clinic-carousel' in html and 'data-interval="5000"' in html
    assert html.count('data-clinic-slide') == 2
    assert 'clinic-gallery-wash' not in html
    for image in detail['gallery']:
        assert image['src'] in html
        path=image['src'].removeprefix('/')
        assert (BASE / path).exists() and (BASE / 'public' / path).exists()
        assert (BASE / path).read_bytes() == (BASE / 'public' / path).read_bytes()
        response=TestClient(app).get(image['src'])
        assert response.status_code == 200
        assert response.headers['content-type'].startswith('image/')


def test_static_assets_synced_for_vercel():
    for rel in ['style.css','benefits.js']:
        assert (BASE/'static'/rel).read_bytes()==(BASE/'public/static'/rel).read_bytes()
    assert 'benefits.js?v=beleza-20261020' in (BASE/'templates/benefit_detail.html').read_text()
