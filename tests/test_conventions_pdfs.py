from pathlib import Path
from urllib.parse import unquote
import json
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[1]
INDEX=json.loads((ROOT/'static/convention_index.json').read_text(encoding='utf-8'))
ENTITIES=('sindihclor','sindhosp','sindhosfil','sinamge','sinog','sinbfir')


def test_every_legal_document_attached_to_correct_card_and_year():
    assert tuple(INDEX)==ENTITIES
    assert sum(len(g['documents']) for sections in INDEX.values() for g in sections)==94
    for entity, groups in INDEX.items():
        assert groups
        assert [g['year'] for g in groups]==sorted((g['year'] for g in groups),reverse=True)
        for group in groups:
            assert group['count']==len(group['documents'])
            for doc in group['documents']:
                assert doc['url'].startswith(f'/convencoes/arquivos/{entity}/')
                relative=unquote(doc['url'].split('/convencoes/arquivos/',1)[1])
                file=ROOT/'public'/'convencoes'/'arquivos'/relative
                assert file.is_file(),file
                with file.open('rb') as f:
                    assert f.read(5)==b'%PDF-'
                assert doc['download_name'].lower().endswith('.pdf')
                assert doc['pages']>0


def test_corrected_metadata_and_no_misassigned_sinog_docs():
    sinamge={g['year']:[d['filename'] for d in g['documents']] for g in INDEX['sinamge']}
    assert '2-sinamge-2013.pdf' in sinamge[2023]  # capa do PDF: 2023/2024
    assert all('sinbfir' not in d['filename'].lower() for y in INDEX['sinog'] for d in y['documents'])
    assert not any(g['year']==2009 for g in INDEX['sindihclor'])  # PDF arquivado era do SINDHOSP


def test_cards_expand_and_pdf_links_work():
    import app  # import após a configuração de teste em test_portal.py
    client=TestClient(app.app)
    res=client.get('/convencoes')
    assert res.status_code==200
    assert res.text.count('class="convention-card"')==6
    assert res.text.count('class="convention-year"')>=60
    assert res.text.count('class="convention-download"')==94
    assert res.text.count('class="convention-view"')==94
    assert 'download="' in res.text
    for entity in ENTITIES:
        link=INDEX[entity][0]['documents'][0]['url']
        with client.stream('GET',link) as pdf:
            assert pdf.status_code==200
            assert 'application/pdf' in pdf.headers['content-type']
            assert next(pdf.iter_bytes())[:5]==b'%PDF-'
