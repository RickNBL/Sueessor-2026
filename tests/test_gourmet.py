from pathlib import Path
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[1]

def test_gourmet_page_content_and_actions():
    import app
    response=TestClient(app.app).get('/servicos/espaco-gourmet')
    assert response.status_code==200
    html=response.text
    for item in ['Espaço Gourmet','ASSOCIADOS','churrasqueira','forno de pizza','pebolim','ping-pong',
                 '(11) 3652-3390','(11) 94182-5124','Kátia','Noêmia',
                 'tel:+551136523390','https://wa.me/5511941825124']:
        assert item.lower() in html.lower(),item
    assert 'data-clinic-carousel' in html
    assert 'data-interval="5000"' in html
    assert html.count('data-clinic-slide')==7
    assert 'Salão de festas</h2>' not in html  # página própria, sem título errado
    assert 'clinic-gallery-wash' not in html

def test_gourmet_gallery_mirrored_to_vercel():
    import app
    for photo in app.BENEFIT_DETAILS['espaco-gourmet']['gallery']:
        path=photo['src'].removeprefix('/static/')
        public=ROOT/'public'/'static'/path
        local=ROOT/'static'/path
        assert public.exists() and local.exists()
        assert public.read_bytes()==local.read_bytes()
        assert len(public.read_bytes())>10000
    assert (ROOT/'public'/'static'/'benefits.js').read_bytes()==(ROOT/'static'/'benefits.js').read_bytes()
    assert (ROOT/'public'/'static'/'style.css').read_bytes()==(ROOT/'static'/'style.css').read_bytes()

def test_gourmet_assets_served():
    import app
    client=TestClient(app.app)
    for entry in app.BENEFIT_DETAILS['espaco-gourmet']['gallery']:
        res=client.get(entry['src'])
        assert res.status_code==200
        assert res.headers.get('content-type')=='image/webp'
