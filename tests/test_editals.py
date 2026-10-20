"""Regressão do acervo de editais disponibilizado para o público."""
from pathlib import Path
from fastapi.testclient import TestClient
import pytest
import importlib

@pytest.fixture
def portal():
    return importlib.import_module('app')

@pytest.fixture
def client(portal):
    return TestClient(portal.app)

def test_catalog_has_complete_archive_and_distinct_files(portal):
    assert len(portal.EDITAL_DOCS) == 46
    assert sorted(portal.EDITAL_YEARS, reverse=True) == [2026, 2025, 2024]
    assert {year: len(portal.EDITAL_BY_YEAR[year]) for year in portal.EDITAL_YEARS} == {2026: 21, 2025: 14, 2024: 11}
    assert len({entry['filename'] for entry in portal.EDITAL_DOCS}) == 46
    assert len({entry['original_filename'] for entry in portal.EDITAL_DOCS}) == 46
    for entry in portal.EDITAL_DOCS:
        assert entry['title'] and entry['name'] and entry['type']
        assert entry['year'] in (2024, 2025, 2026)
        assert entry['filename'].endswith('.pdf')
        assert entry['url'].startswith('/editais/arquivos/')


def test_editals_page_provides_filters_table_and_actions(client):
    r = client.get('/documentos/editais')
    assert r.status_code == 200
    text = r.text
    assert 'id="edital-busca"' in text
    assert 'id="edital-ano"' in text
    assert 'id="edital-nome"' in text
    assert 'data-edital-group' in text
    assert text.count('data-edital-row data-year=') == 46
    assert 'data-edital-toggle' in text
    assert 'Visualizar PDF' in text
    assert 'Baixar PDF' in text
    assert 'data-edital-clear' in text
    assert '/static/editals.js?v=editais-20261020' in text


def test_documents_have_valid_pdf_bytes_and_public_urls(client, portal):
    base = Path(__file__).resolve().parents[1]
    for doc in portal.EDITAL_DOCS:
        path = base / 'public' / 'editais' / 'arquivos' / doc['filename']
        assert path.is_file()
        assert path.stat().st_size == doc['size_bytes']
        assert path.read_bytes()[:5] == b'%PDF-'
        response = client.get(doc['url'])
        assert response.status_code == 200, doc['filename']
        assert response.headers.get('content-type', '').startswith('application/pdf')
        assert len(response.content) == doc['size_bytes']


def test_filter_javascript_available(client):
    r = client.get('/static/editals.js')
    assert r.status_code == 200
    assert 'applyFilters' in r.text
    assert '[data-edital-toggle]' in r.text
    assert 'expand-all' in r.text
