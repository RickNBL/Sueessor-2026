from pathlib import Path
from fastapi.testclient import TestClient


BASE=Path(__file__).resolve().parents[1]
def runtime():
    from app import app, EXCURSION_DESTINATIONS
    return TestClient(app), EXCURSION_DESTINATIONS

def test_excursions_has_both_destinations_and_historical_dates():
    client, EXCURSION_DESTINATIONS = runtime()
    res=client.get('/servicos/excursoes')
    assert res.status_code==200
    for item in EXCURSION_DESTINATIONS:
        assert item['title'] in res.text
        assert item['slug'] in res.text
    assert '22 de novembro de 2024' in res.text
    assert '24 de novembro de 2024' in res.text
    assert 'novas excursões' in res.text
    assert '(11) 3652-3390' in res.text
    assert '(11) 94182-5124' in res.text

def test_each_carousel_has_all_photos_and_five_second_interval():
    client, EXCURSION_DESTINATIONS = runtime()
    res=client.get('/servicos/excursoes')
    assert res.text.count('data-clinic-carousel')==2
    assert res.text.count('data-interval="5000"')==2
    assert len(EXCURSION_DESTINATIONS[0]['gallery'])==8
    assert len(EXCURSION_DESTINATIONS[1]['gallery'])==10
    for item in EXCURSION_DESTINATIONS:
        for photo in item['gallery']:
            path=photo['src'].removeprefix('/')
            assert Path(BASE/path).is_file()
            assert (BASE/'public'/path).is_file()
            assert (BASE/path).read_bytes()==(BASE/'public'/path).read_bytes()
            assert client.get(photo['src']).status_code==200

def test_no_photo_gradient_overlay_and_js_synchronized():
    template=(BASE/'templates/excursions.html').read_text()
    assert 'clinic-gallery-wash' not in template
    css=(BASE/'static/style.css').read_bytes()
    assert css==(BASE/'public/static/style.css').read_bytes()
    js=(BASE/'static/benefits.js').read_bytes()
    assert js==(BASE/'public/static/benefits.js').read_bytes()
    assert b'IntersectionObserver' in js
