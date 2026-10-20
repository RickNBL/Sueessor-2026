"""Checks for the events page and its uploaded gallery."""
from pathlib import Path
from fastapi.testclient import TestClient
from app import app, BENEFIT_DETAILS

c = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]


def test_eventos_information_and_contacts():
    response = c.get('/servicos/espaco-para-eventos')
    assert response.status_code == 200
    page = response.text
    for text in (
        'Salão de festas', 'O Salão de Festas do SUEESSOR está disponível',
        'Mesas e cadeiras', 'Ar condicionado', 'Iluminação',
        'Aparelhos sonoros', 'Cozinha', 'Freezer',
        '(11) 3652-3390', '(11) 94182-5124', 'Kátia ou Noêmia',
    ):
        assert text in page
    assert 'href="tel:+551136523390"' in page
    assert 'href="https://wa.me/5511941825124"' in page
    assert 'Consultas sem custo' not in page  # never show clinical claims on events


def test_eventos_gallery_images_and_autoplay():
    page = c.get('/servicos/espaco-para-eventos').text
    gallery = BENEFIT_DETAILS['espaco-para-eventos']['gallery']
    assert len(gallery) == 6
    assert 'data-interval="5000"' in page
    for image in gallery:
        src = image['src']
        assert src in page
        assert (ROOT / src.removeprefix('/')).is_file()
        assert (ROOT / 'public' / src.removeprefix('/')).is_file()
        response = c.get(src)
        assert response.status_code == 200
        assert response.headers['content-type'] == 'image/webp'


def test_other_benefits_still_available():
    for url in ('/servicos/clinica-medica', '/servicos/espaco-gourmet', '/servicos/beneficios'):
        assert c.get(url).status_code == 200
    page = c.get('/servicos/clinica-medica').text
    assert 'Consultas sem custo' in page
    assert 'data-interval="5000"' in page
