"""Página de clubes: conteúdo do SUEESSOR, mapas, galerias e respostas FastAPI."""
from fastapi.testclient import TestClient
import pytest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture(scope="module")
def club_env():
    from app import app, CLUB_PARTNERS
    return TestClient(app), CLUB_PARTNERS


def test_clubs_page_is_responsive_and_contains_two_verified_clubs(club_env):
    client, _ = club_env
    response=client.get('/servicos/parcerias/clubes')
    assert response.status_code==200
    text=response.text
    assert 'CEFOL' in text and 'SIMTRATECOR' in text
    assert text.count('class="club-partner"') == 2
    assert 'club-partners-section' in text
    assert 'club-partner-body' in text
    assert 'lang="pt-BR"' in text


def test_cefol_terms_and_contact(club_env):
    client, _ = club_env
    html=client.get('/servicos/parcerias/clubes').text
    for phrase in ('Estrada das Mulatas, 1000','90 dias','autorização','Kátia','(11) 3652-3390','(11) 94182-5124'):
        assert phrase in html
    assert 'wa.me/5511941825124' in html
    assert 'https://cefol.com.br/' in html


def test_simtratecor_conditions_and_schedule_note(club_env):
    client, _ = club_env
    html=client.get('/servicos/parcerias/clubes').text
    for phrase in ('até 17 anos','Taxaquara, 900','Camila ou Kátia','08h00 às 16h00','07h00 às 18h00','sábado das 08h00 às 17h00'):
        assert phrase in html


def test_two_accessible_maps_and_photos_with_verified_source(club_env):
    client, _ = club_env
    html=client.get('/servicos/parcerias/clubes').text
    assert html.count('google.com/maps?q=')==2
    assert html.count('google.com/maps/search/?api=1')==4
    assert html.count('data-clinic-carousel')==2
    assert html.count('data-interval="5000"')==2
    assert html.count('data-clinic-slide')==6
    assert html.count('data-clinic-prev')==2
    assert html.count('data-clinic-next')==2
    assert 'cefol-logo.jpeg' in html
    assert 'logo3-300x155-1.png' in html
    assert 'quimicosunificados.com.br' in html
    assert 'static.wixstatic.com' in html


def test_vercel_files_match_local_for_styles_and_behavior(club_env):
    client, CLUB_PARTNERS = club_env
    assert (ROOT/'static/style.css').read_bytes()==(ROOT/'public/static/style.css').read_bytes()
    assert (ROOT/'static/benefits.js').read_bytes()==(ROOT/'public/static/benefits.js').read_bytes()
    assert len(CLUB_PARTNERS)==2
    assert all(c['maps_url'].startswith('https://www.google.com/maps/search/') for c in CLUB_PARTNERS)
