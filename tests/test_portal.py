"""Testes de integração: sessão, CMS, mídia e páginas públicas."""
import io
import os
import tempfile
from pathlib import Path

os.environ['DATA_DIR'] = tempfile.mkdtemp(prefix='sueessor_test_db_')
os.environ['UPLOAD_DIR'] = tempfile.mkdtemp(prefix='sueessor_test_uploads_')
os.environ['ADMIN_USERNAME'] = 'editor_teste'
os.environ['ADMIN_PASSWORD'] = 'UmaSenhaDeTesteLonga12345!'
os.environ['SESSION_COOKIE_SECURE'] = 'false'

from fastapi.testclient import TestClient
from PIL import Image
import app as portal

client = TestClient(portal.app)


def login():
    response = client.post('/api/admin/login', data={'username':'editor_teste','password':'UmaSenhaDeTesteLonga12345!'})
    assert response.status_code == 200
    panel = client.get('/central-restrita/painel')
    assert panel.status_code == 200
    csrf = panel.text.split('data-csrf="')[1].split('"')[0]
    return csrf


def draft(**kwargs):
    sample={'title':'Defesa dos profissionais da saúde em Osasco','excerpt':'Nova assembleia para mobilizar trabalhadores na unidade de saúde.','body':'Foi realizada uma assembleia para discutir importantes garantias da categoria na região.','category':'Sindicato','image':'','images':[],'video':'','place':'Osasco, SP','published':True}
    sample.update(kwargs)
    return sample


def test_pages_and_seed():
    for path in ('/','/sobre','/abrangencia','/diretoria','/convencoes','/noticias','/servicos/juridico','/servicos/beneficios','/documentos/editais','/associe-se','/contato','/denuncie','/imprensa/galeria'):
        result=client.get(path)
        assert result.status_code==200, path
        assert 'SUEESSOR' in result.text
    assert len(client.get('/api/noticias').json()['posts']) == 3
    assert client.get('/does-not-exist').status_code==404


def test_requires_session_and_csrf():
    assert client.get('/central-restrita/painel', follow_redirects=False).status_code==303
    assert client.post('/api/admin/posts',json=draft()).status_code==401
    assert client.post('/api/admin/login',data={'username':'editor_teste','password':'wrong'}).status_code==401
    csrf=login()
    assert client.post('/api/admin/posts',json=draft()).status_code==403
    assert client.post('/api/admin/posts',json=draft(),headers={'X-CSRF-Token':csrf}).status_code==200


def test_create_edit_delete_and_media():
    csrf=login()
    headers={'X-CSRF-Token':csrf}
    payload=draft(title='Um novo avanço para trabalhadores da saúde',video='https://youtu.be/dQw4w9WgXcQ')
    result=client.post('/api/admin/posts',json=payload,headers=headers)
    assert result.status_code==200,result.text
    id=result.json()['id']
    content=client.get('/api/noticias').json()['posts']
    assert any(x['id']==id and x['video_embed']=='https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ' for x in content)
    assert client.put(f'/api/admin/posts/{id}',json=draft(published=False),headers=headers).status_code==200
    assert not any(x['id']==id for x in client.get('/api/noticias').json()['posts'])
    assert client.delete(f'/api/admin/posts/{id}',headers=headers).status_code==200
    assert client.post('/api/admin/posts',json=draft(image='javascript:alert(1)'),headers=headers).status_code==400
    img=Image.new('RGB',(50,50),(10,180,100))
    b=io.BytesIO()
    img.save(b,format='PNG')
    resp=client.post('/api/admin/upload',files={'file':('foto.png',b.getvalue(),'image/png')},headers=headers)
    assert resp.status_code==200,resp.text
    assert client.get(resp.json()['url']).status_code==200
    assert client.post('/api/admin/upload',files={'file':('evil.jpg',b'<script>x</script>','image/jpeg')},headers=headers).status_code==400


def test_public_inquiry_and_private_inbox():
    form={'kind':'denuncie','name':'','contact':'','company':'Hospital Teste','subject':'Condições de trabalho','message':'Relato de condições de trabalho a serem avaliadas.','consent':True}
    r=client.post('/api/mensagem',json=form)
    assert r.status_code==200,r.text
    assert client.post('/api/mensagem',json={**form,'consent':False}).status_code==400
    assert client.get('/central-restrita/painel', follow_redirects=True).status_code==200
    assert client.get('/central-restrita/painel').text.find('Hospital Teste')>=0


def test_logout():
    csrf=login()
    assert client.post('/api/admin/logout',headers={'X-CSRF-Token':csrf}).status_code==200
    assert client.post('/api/admin/posts',json=draft(),headers={'X-CSRF-Token':csrf}).status_code==401
