"""Tests for the Mafisa Turismo page and the latest Vercel bundle."""
from pathlib import Path
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[1]


def test_mafisa_route_and_content():
    from app import app, TRAVEL_PARTNERS
    assert len(TRAVEL_PARTNERS)==1
    with TestClient(app) as client:
        resp=client.get('/servicos/parcerias/viagens-e-turismo')
        assert resp.status_code==200
        html=resp.text
        for phrase in ('Mafisa Turismo','Descontos exclusivos','Cristina','98828-8614','mafisaturismo.com.br','/servicos/excursoes'):
            assert phrase in html
        assert 'https://wa.me/5511988288614' in html
        assert 'mafisa-01-1024x1024.png' in html
        assert 'href="/servicos/parcerias"' in html


def test_travel_assets_are_synced_for_vercel():
    assert (ROOT/'public/static/style.css').read_bytes()==(ROOT/'static/style.css').read_bytes()
    html=(ROOT/'templates/partnership_travel.html').read_text()
    assert 'travel-partner' in html and 'rel="noopener noreferrer"' in html
    assert 'Dados de localização' not in html
