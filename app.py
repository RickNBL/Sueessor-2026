"""SUEESSOR — portal institucional com feed e painel editorial seguro.
Python 3.11+, FastAPI, SQLite, Jinja2, Javascript. Conteúdo inicial é uma
seleção resumida e atribuída de publicações verificadas do portal oficial.
"""
import base64
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import sqlite3
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urlparse, parse_qs

from fastapi import FastAPI, Request, UploadFile, File, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from PIL import Image, ImageOps, UnidentifiedImageError

BASE = Path(__file__).resolve().parent
IS_VERCEL = bool(os.getenv('VERCEL'))
# The Vercel function bundle is read-only; only /tmp is writable.
DATA = Path('/tmp/sueessor-data' if IS_VERCEL else os.getenv('DATA_DIR', str(BASE / 'data'))).resolve()
UPLOADS = Path('/tmp/sueessor-uploads' if IS_VERCEL else os.getenv('UPLOAD_DIR', str(BASE / 'uploads'))).resolve()
# Persistent data on Vercel requires a managed Postgres database.
DATABASE_URL = os.getenv('DATABASE_URL', '') or os.getenv('POSTGRES_URL', '')
USE_POSTGRES = DATABASE_URL.startswith(('postgresql://','postgres://'))
PERSISTENT = (not IS_VERCEL) or USE_POSTGRES
DATA.mkdir(parents=True, exist_ok=True)
UPLOADS.mkdir(parents=True, exist_ok=True)
DB = DATA / 'portal.db'
ADMIN_ROUTE = '/central-restrita/entrar'
COOKIE_SECURE = IS_VERCEL or os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
MAX_IMAGE = 10 * 1024 * 1024
MAX_VIDEO = 80 * 1024 * 1024

app = FastAPI(title='SUEESSOR — Portal', docs_url=None, redoc_url=None, openapi_url=None)
app.mount('/static', StaticFiles(directory=str(BASE / 'static')), name='static')
app.mount('/uploads', StaticFiles(directory=str(UPLOADS)), name='uploads')
# PDFs públicos em public/: na Vercel são servidos como assets estáticos; localmente, pelo FastAPI.
if not IS_VERCEL:
    app.mount('/convencoes/arquivos', StaticFiles(directory=str(BASE / 'public' / 'convencoes' / 'arquivos')), name='convencoes-arquivos')
templates = Jinja2Templates(directory=str(BASE / 'templates'))
CONVENTION_DOCS = json.loads((BASE / 'static' / 'convention_index.json').read_text(encoding='utf-8'))
CONVENTION_COUNTS = {key:sum(len(year['documents']) for year in years) for key,years in CONVENTION_DOCS.items()}

AREAS = ['Barueri', 'Carapicuíba', 'Cotia', 'Embu', 'Embu-Guaçu', 'Ibiúna', 'Itapecerica da Serra', 'Itapevi', 'Jandira', 'Osasco', 'Santana de Parnaíba', 'Taboão da Serra', 'Vargem Grande Paulista']
DIRECTORY = [
 ('Diretoria efetiva', [('Antônio Gervásio Rodrigues', 'Presidente'),('Juarez Henrique de Paulo','Vice-presidente'),('Amilton Arlindo de Moura Rodrigues','Secretário-geral'),('Noêmia Telles de Oliveira','Tesoureira-geral'),('Fábio Ribeiro Aragão','Primeiro tesoureiro'),('Orlando Faustino da Silva','Secretário de Assistência Social')]),
 ('Diretores suplentes', [('Amélia Pereira Matos',''),('Luciana Pereira Santos',''),('Geni dos Santos Nascimento',''),('Edinaldo Alves Batista',''),('Ailton Merces Barbosa',''),('Rogério Pereira Nunes Mendes','')]),
 ('Conselho fiscal', [('José Aparecido Nascimento',''),('Raymundo José Gonçalves',''),('Cilda Conceição de Oliveira Queiroz','')]),
]
SERVICE_CARDS = [
  {'icon':'scale','name':'Assessoria jurídica','summary':'Orientação e defesa dos direitos trabalhistas da categoria.','link':'/servicos/juridico'},
  {'icon':'heart','name':'Clínica e odontologia','summary':'Saúde, acompanhamento clínico e atendimento odontológico aos associados.','link':'/servicos/beneficios'},
  {'icon':'file','name':'Convenções coletivas','summary':'Acesse acordos, instrumentos coletivos e documentos da sua categoria.','link':'/convencoes'},
  {'icon':'users','name':'Benefícios e parcerias','summary':'Mais possibilidades de cuidado, lazer e economia para você e sua família.','link':'/servicos/beneficios'},
]
NEWS_SEED = [
  {'slug':'mobilizacao-hospital-ibiuna','title':'Sindicato reforça presença no Hospital Municipal de Ibiúna','excerpt':'Assembleias dos dias 13 e 14 de outubro abordaram direitos previstos na Convenção Coletiva 2026/2027 e mobilizaram profissionais da saúde.', 'body':'Nos dias 13 e 14 de outubro, dirigentes do SUEESSOR estiveram no Hospital Municipal de Ibiúna para conversar com profissionais sobre a aplicação da Convenção Coletiva de Trabalho 2026/2027. Entre os temas debatidos estiveram reajuste salarial, pisos, jornada 12×36 e benefícios sociais. Leia o relato integral no portal oficial.', 'category':'Mobilização','date':'2026-10-14T14:32:00','image':'https://sites.diretasistemas.com.br/sites/1955/wp-content/uploads/2026/10/14132122/Sindicato-mobiliza-trabalhadores-em-Ibiuna.png','source':'https://sueessor.org.br/2026/10/14/sindicato-reforca-presenca-no-hospital-municipal-de-ibiuna-e-mobiliza-trabalhadores-pela-garantia-dos-direitos-coletivos/','place':'Hospital Municipal de Ibiúna, Ibiúna, SP'},
  {'slug':'conquista-folga-feriado-hgc','title':'Mobilização garante retorno da folga feriado aos trabalhadores 12×36 do HGC','excerpt':'Após negociações com a Fundação do ABC, foram anunciados a recuperação da folga feriado, reajuste e pagamento de retroativos.', 'body':'A negociação entre representantes dos trabalhadores do Hospital Geral de Carapicuíba e a Fundação do ABC terminou com o retorno da folga feriado para profissionais da escala 12×36. A reportagem oficial também registra reajuste salarial de 4,11% e diferenças retroativas. Confira todos os detalhes na fonte.', 'category':'Conquistas','date':'2026-10-13T19:21:00','image':'https://sites.diretasistemas.com.br/sites/1955/wp-content/uploads/2026/10/13190428/SUEESSOR-conquista-folga-feriado.png','source':'https://sueessor.org.br/2026/10/13/apos-negociacao-acirrada-sindicato-conquista-retorno-da-folga-feriado-para-trabalhadores-do-12x36-no-hgc/','place':'Hospital Geral de Carapicuíba, Carapicuíba, SP'},
  {'slug':'hgc-estado-greve','title':'Trabalhadores do HGC rejeitam proposta e aprovam estado de greve','excerpt':'Em assembleia, a categoria avaliou a proposta apresentada pela administração e deliberou sobre os próximos passos de mobilização.', 'body':'Após meses de negociações, trabalhadores do Hospital Geral de Carapicuíba rejeitaram uma proposta da Fundação do ABC e aprovaram estado de greve. A mobilização integra a defesa dos direitos e das condições de trabalho dos profissionais de saúde. Consulte a matéria original para os desdobramentos.', 'category':'Direitos','date':'2026-10-08T12:00:00','image':'https://sites.diretasistemas.com.br/sites/1955/wp-content/uploads/2026/10/08111948/Trabalhadores-do-HGC-aprovam-greve-1.png','source':'https://sueessor.org.br/2026/10/08/trabalhadores-do-hgc-rejeitam-proposta-da-fundacao-do-abc-e-aprovam-estado-de-greve/','place':'Hospital Geral de Carapicuíba, Carapicuíba, SP'},
]


class PostgresDB:
    """Small compatibility wrapper for this project's SQLite-style placeholders."""
    def __init__(self, url):
        import psycopg
        from psycopg.rows import dict_row
        self.connection = psycopg.connect(url, row_factory=dict_row, connect_timeout=8)

    def __enter__(self):
        self.connection.__enter__()
        return self

    def __exit__(self, typ, value, traceback):
        return self.connection.__exit__(typ, value, traceback)

    def execute(self, query, params=()):
        return self.connection.execute(query.replace('?', '%s'), params)

    def executescript(self, sql):
        for statement in sql.split(';'):
            if statement.strip():
                self.execute(statement)


def db():
    if USE_POSTGRES:
        return PostgresDB(DATABASE_URL)
    conn = sqlite3.connect(DB, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def hash_pass(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    result = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return base64.b64encode(salt + result).decode()


def verify_pass(password, stored):
    try:
        raw = base64.b64decode(stored, validate=True)
        expected = raw[16:]
        actual = hashlib.scrypt(password.encode(), salt=raw[:16], n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(expected, actual)
    except Exception:
        return False


def init_db():
    # PostgreSQL is persistent on Vercel; local development continues to use SQLite.
    schema = '''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), csrf TEXT NOT NULL, expires INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS posts(id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE NOT NULL, title TEXT NOT NULL, excerpt TEXT NOT NULL, body TEXT NOT NULL, category TEXT NOT NULL, image TEXT NOT NULL DEFAULT '', images TEXT NOT NULL DEFAULT '[]', video TEXT NOT NULL DEFAULT '', place TEXT NOT NULL DEFAULT '', published INTEGER NOT NULL DEFAULT 0, source TEXT NOT NULL DEFAULT '', date TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS inquiries(id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, name TEXT NOT NULL DEFAULT '', contact TEXT NOT NULL DEFAULT '', company TEXT NOT NULL DEFAULT '', subject TEXT NOT NULL DEFAULT '', message TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    '''
    if USE_POSTGRES:
        schema = schema.replace('id INTEGER PRIMARY KEY AUTOINCREMENT', 'id SERIAL PRIMARY KEY').replace('id INTEGER PRIMARY KEY,', 'id SERIAL PRIMARY KEY,')
    with db() as c:
        c.executescript(schema)
        user = os.getenv('ADMIN_USERNAME','').strip()
        password = os.getenv('ADMIN_PASSWORD','')
        if user and len(password) >= 14 and not password.upper().startswith(('SUBSTITUA', 'CHANGE_ME', 'TROQUE_A_SENHA')) and not c.execute('SELECT id FROM users LIMIT 1').fetchone():
            c.execute('INSERT INTO users(username,password_hash) VALUES (?,?) ON CONFLICT (username) DO NOTHING', (user,hash_pass(password)))
        if c.execute('SELECT count(*) AS total FROM posts').fetchone()['total'] == 0:
            for n in NEWS_SEED:
                c.execute('''INSERT INTO posts (slug,title,excerpt,body,category,image,images,video,place,published,source,date)
                  VALUES (?,?,?,?,?,?,?,?,?,1,?,?) ON CONFLICT (slug) DO NOTHING''', (n['slug'],n['title'],n['excerpt'],n['body'],n['category'],n['image'],'[]','',n['place'],n['source'],n['date']))

init_db()

@app.middleware('http')
async def require_persistent_backend_for_writes(request: Request, call_next):
    # Never silently accept private reports, news or login into volatile /tmp storage.
    if IS_VERCEL and not PERSISTENT:
        if request.url.path.startswith('/central-restrita/'):
            return HTMLResponse(
                '<!doctype html><html lang="pt-BR"><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>Painel indisponível • SUEESSOR</title>'
                '<body style="font:17px system-ui;max-width:650px;margin:12vh auto;padding:24px;line-height:1.55">'
                '<h1>Central editorial aguardando configuração</h1>'
                '<p>O site público já pode ser visualizado. Para publicar notícias e receber formulários, '
                'adicione um banco PostgreSQL persistente nas configurações da Vercel e defina suas credenciais administrativas.</p>'
                '<p><a href="/">Voltar para o site</a></p></body></html>', status_code=503,
                headers={'Cache-Control':'no-store','X-Robots-Tag':'noindex'})
        if request.url.path.startswith('/api/admin/') or (request.method not in ('GET','HEAD','OPTIONS') and request.url.path.startswith('/api/')):
            return JSONResponse({'detail':'Configure DATABASE_URL (PostgreSQL) para habilitar publicações e formulários com persistência.'}, status_code=503)
    return await call_next(request)


def rows(sql, params=()):
    with db() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]


def one(sql, params=()):
    with db() as c:
        r = c.execute(sql, params).fetchone()
        return dict(r) if r else None


def session(request):
    token = request.cookies.get('sueessor_session','')
    if len(token) != 64 or not re.fullmatch(r'[a-f0-9]{64}', token):
        return None
    data = one('''SELECT s.user_id,s.csrf,s.expires,u.username FROM sessions s JOIN users u ON s.user_id=u.id WHERE token_hash=?''', (hashlib.sha256(token.encode()).hexdigest(),))
    return data if data and data['expires'] > int(time.time()) else None


def protected(request, csrf=False):
    sess = session(request)
    if not sess:
        raise HTTPException(401, 'Acesso não autorizado')
    if csrf and not hmac.compare_digest(request.headers.get('x-csrf-token',''), sess['csrf']):
        raise HTTPException(403, 'Proteção de sessão inválida')
    return sess


def public_post(p):
    p = dict(p)
    try:
        p['images'] = json.loads(p.get('images') or '[]')
    except ValueError:
        p['images'] = []
    p['video_embed'] = video_embed(p.get('video',''))
    return p


def video_embed(url):
    if not url:
        return ''
    try:
        u = urlparse(url)
        if u.scheme != 'https': return ''
        domain = (u.hostname or '').lower()
        vid = ''
        if domain in ('www.youtube.com','youtube.com','m.youtube.com'):
            if u.path == '/watch': vid = parse_qs(u.query).get('v',[''])[0]
            elif u.path.startswith('/shorts/') or u.path.startswith('/embed/'):
                vid = u.path.split('/')[2]
        elif domain == 'youtu.be': vid = u.path.strip('/')
        if re.fullmatch(r'[a-zA-Z0-9_-]{11}', vid): return 'https://www.youtube-nocookie.com/embed/' + vid
        if domain in ('vimeo.com','www.vimeo.com','player.vimeo.com'):
            num = u.path.strip('/').split('/')[-1]
            if re.fullmatch(r'\d{5,15}',num): return 'https://player.vimeo.com/video/'+num
    except Exception: pass
    return ''


def safe_url(url):
    if not url: return ''
    if url.startswith('/uploads/') and re.fullmatch(r'/uploads/[a-z0-9_-]+\.(jpg|png|webp|mp4|webm)',url):
        return url
    try:
        x = urlparse(url)
        if x.scheme == 'https' and x.hostname and not x.username and not x.password:
            return url
    except ValueError: pass
    return ''


def slugify(s):
    x = unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
    return re.sub('-+','-', re.sub('[^a-z0-9]+','-',x)).strip('-')[:90] or 'noticia'


def render(request, name, **kw):
    base = {'request':request,'page':kw.pop('page','inicio'),'services':SERVICE_CARDS,'areas':AREAS,'news':[], 'social':'https://www.instagram.com/sueessor/'}
    base.update(kw)
    response = templates.TemplateResponse(request, name, base)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
    response.headers['Content-Security-Policy']=("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
      "font-src 'self' https://fonts.gstatic.com data:; img-src 'self' https: data:; media-src 'self' https:; "
      "connect-src 'self'; frame-src https://maps.google.com https://www.google.com https://www.youtube-nocookie.com https://player.vimeo.com; "
      "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
    if COOKIE_SECURE: response.headers['Strict-Transport-Security']='max-age=31536000; includeSubDomains'
    return response

@app.get('/', response_class=HTMLResponse)
def home(request:Request):
    news = [public_post(p) for p in rows('SELECT * FROM posts WHERE published=1 ORDER BY date DESC,id DESC LIMIT 3')]
    return render(request,'home.html',page='inicio',news=news)

@app.get('/noticias', response_class=HTMLResponse)
def news_page(request:Request):
    items = [public_post(p) for p in rows('SELECT * FROM posts WHERE published=1 ORDER BY date DESC,id DESC LIMIT 6')]
    return render(request,'news.html',page='noticias',news=items)

@app.get('/noticias/{slug}', response_class=HTMLResponse)
def article(request:Request,slug:str):
    p = one('SELECT * FROM posts WHERE slug=? AND published=1',(slug,))
    if not p: raise HTTPException(404, 'Publicação não encontrada')
    return render(request,'article.html',page='noticias',post=public_post(p))

@app.get('/api/noticias')
def api_news(q:str='',category:str='Todos',page:int=1):
    page=max(1,min(page,500))
    term='%'+q[:90].strip()+'%'
    params=[term,term]
    cat=''
    if category != 'Todos':
        cat=' AND category=?'
        params.append(category[:50])
    params.extend([(page-1)*6])
    items=rows('SELECT * FROM posts WHERE published=1 AND (title LIKE ? OR excerpt LIKE ?)'+cat+' ORDER BY date DESC,id DESC LIMIT 6 OFFSET ?',params)
    return {'posts':[public_post(p) for p in items], 'has_more':len(items)==6}

@app.get('/sobre', response_class=HTMLResponse)
def about(request:Request):
    return render(request,'about.html',page='sobre')

@app.get('/abrangencia', response_class=HTMLResponse)
def reach(request:Request):
    return render(request,'reach.html',page='sobre')

@app.get('/diretoria', response_class=HTMLResponse)
def director(request:Request):
    return render(request,'directory.html',page='sobre',directory=DIRECTORY)

@app.get('/convencoes', response_class=HTMLResponse)
def conventions(request:Request):
    return render(request,'conventions.html',page='convencoes',docs_by_entity=CONVENTION_DOCS,doc_counts=CONVENTION_COUNTS)

@app.get('/servicos/{kind}', response_class=HTMLResponse)
def services(request:Request,kind:str):
    if kind not in ('beneficios','juridico','parcerias'): raise HTTPException(404)
    return render(request,'services.html',page='servicos',kind=kind)

@app.get('/documentos/{kind}', response_class=HTMLResponse)
def document(request:Request,kind:str):
    options={'editais':('Editais','https://sueessor.org.br/editais/'), 'acordos':('Modelos de acordo','https://sueessor.org.br/modelos-de-acordo/'), 'oposicao':('Modelo de oposição','https://sueessor.org.br/modelo-de-oposicao/'), 'financeiro':('Emissão de boletos','https://sueessor.org.br/emissao-de-boleto/'), 'aplicativo':('Aplicativo SUEESSOR','https://sueessor.org.br/aplicativo/')}
    if kind not in options: raise HTTPException(404)
    return render(request,'documents.html',page='convencoes',kind=kind,doc=options[kind])

@app.get('/associe-se', response_class=HTMLResponse)
def membership(request:Request):
    return render(request,'membership.html',page='servicos')

@app.get('/imprensa/{kind}', response_class=HTMLResponse)
def press(request:Request,kind:str):
    sections={'artigos':('Artigos','https://sueessor.org.br/artigos/'),
      'notas':('Notas','https://sueessor.org.br/notas/'),
      'galeria':('Galeria de fotos','https://sueessor.org.br/galeria-de-fotos/'),
      'revistas':('Revistas','https://sueessor.org.br/revistas/'),
      'jornal':('Jornal','https://sueessor.org.br/jornal/'),
      'videos':('Vídeos','https://sueessor.org.br/videos/')}
    if kind not in sections: raise HTTPException(404)
    return render(request,'press.html',page='noticias',section=sections[kind])

@app.get('/contato', response_class=HTMLResponse)
def contact(request:Request):
    return render(request,'contact.html',page='contato',kind='contato')

@app.get('/denuncie', response_class=HTMLResponse)
def denuncie(request:Request):
    return render(request,'contact.html',page='denuncie',kind='denuncie')

# Formulários públicos: simples, com campo-armadilha, limitação e dados privados.
ATTEMPTS={}
def throttle(key, limit=7, window=900):
    now=time.monotonic()
    times=[t for t in ATTEMPTS.get(key,[]) if now-t<window]
    if len(times)>=limit:
        ATTEMPTS[key]=times
        return False
    times.append(now)
    ATTEMPTS[key]=times
    if len(ATTEMPTS)>10000:
        ATTEMPTS.clear()
    return True

class Inquiry(BaseModel):
    kind:str
    name:str=Field('',max_length=120)
    contact:str=Field('',max_length=180)
    company:str=Field('',max_length=180)
    subject:str=Field('',max_length=140)
    message:str=Field(...,min_length=12,max_length=4500)
    website:str=''
    consent:bool=False

@app.post('/api/mensagem')
async def public_inquiry(request:Request, data:Inquiry):
    if data.website: return {'ok':True}
    if data.kind not in ('contato','denuncie') or not data.consent:
        raise HTTPException(400,'Confira o tipo de formulário e o consentimento')
    if not data.company.strip() and data.kind=='denuncie':
        raise HTTPException(400,'Informe a empresa ou unidade')
    if not throttle('form:'+str(request.client.host),5,3600):
        raise HTTPException(429,'Limite de envios atingido. Tente mais tarde.')
    with db() as c:
        c.execute('INSERT INTO inquiries(kind,name,contact,company,subject,message) VALUES (?,?,?,?,?,?)',
                  (data.kind,data.name.strip(),data.contact.strip(),data.company.strip(),data.subject.strip(),data.message.strip()))
    return {'ok':True}

@app.get(ADMIN_ROUTE, response_class=HTMLResponse)
def admin_login_page(request:Request):
    if session(request): return RedirectResponse('/central-restrita/painel',status_code=303)
    response=render(request,'admin_login.html',page='admin')
    response.headers['X-Robots-Tag']='noindex, nofollow, noarchive'
    response.headers['Cache-Control']='no-store'
    return response

@app.post('/api/admin/login')
async def admin_login(request:Request, username:str=Form(...), password:str=Form(...)):
    ip=str(request.client.host)
    if not throttle('login:'+ip,5,900):
        raise HTTPException(429,'Muitas tentativas. Aguarde 15 minutos.')
    admin=one('SELECT * FROM users WHERE username=?',(username.strip(),))
    if not admin or not verify_pass(password,admin['password_hash']):
        raise HTTPException(401,'Usuário ou senha inválidos')
    token=secrets.token_hex(32)
    csrf=secrets.token_urlsafe(32)
    with db() as c:
        c.execute('DELETE FROM sessions WHERE expires<?',(int(time.time()),))
        c.execute('INSERT INTO sessions(token_hash,user_id,csrf,expires) VALUES (?,?,?,?)',
                  (hashlib.sha256(token.encode()).hexdigest(),admin['id'],csrf,int(time.time())+43200))
    response=JSONResponse({'ok':True,'redirect':'/central-restrita/painel'})
    response.set_cookie('sueessor_session',token,httponly=True,samesite='strict',secure=COOKIE_SECURE,max_age=43200,path='/')
    response.headers['Cache-Control']='no-store'
    return response

@app.get('/central-restrita/painel', response_class=HTMLResponse)
def admin_panel(request:Request):
    sess=session(request)
    if not sess: return RedirectResponse(ADMIN_ROUTE,status_code=303)
    posts=[public_post(p) for p in rows('SELECT * FROM posts ORDER BY date DESC,id DESC')]
    inquiries=rows('SELECT * FROM inquiries ORDER BY created_at DESC,id DESC LIMIT 100')
    response=render(request,'admin.html',page='admin',posts=posts,inquiries=inquiries,csrf=sess['csrf'],admin_name=sess['username'])
    response.headers['Cache-Control']='no-store'
    response.headers['X-Robots-Tag']='noindex, nofollow, noarchive'
    return response

class NewsInput(BaseModel):
    title:str=Field(...,min_length=8,max_length=180)
    excerpt:str=Field(...,min_length=12,max_length=350)
    body:str=Field(...,min_length=20,max_length=25000)
    category:str=Field('Sindicato',max_length=40)
    image:str=Field('',max_length=1500)
    images:list[str]=Field(default_factory=list,max_length=12)
    video:str=Field('',max_length=1500)
    place:str=Field('',max_length=250)
    published:bool=False

@app.post('/api/admin/posts')
async def save_post(request:Request,data:NewsInput):
    protected(request,True)
    if any(not safe_url(url) for url in [data.image,*data.images] if url):
        raise HTTPException(400,'Imagem inválida. Use HTTPS ou upload local.')
    if data.video and not (video_embed(data.video) or (safe_url(data.video) and urlparse(data.video).path.lower().endswith(('.mp4','.webm')))):
        raise HTTPException(400,'Vídeo inválido. Use YouTube, Vimeo ou MP4/WebM HTTPS.')
    with db() as c:
        insert_sql='''INSERT INTO posts(slug,title,excerpt,body,category,image,images,video,place,published,date)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)'''
        cur=c.execute(insert_sql + (' RETURNING id' if USE_POSTGRES else ''),
        ('tmp-'+secrets.token_hex(8),data.title.strip(),data.excerpt.strip(),data.body.strip(),data.category.strip(),data.image,json.dumps(data.images),data.video,data.place.strip(),int(data.published),datetime.now(timezone.utc).isoformat()))
        ident=cur.lastrowid
        c.execute('UPDATE posts SET slug=? WHERE id=?',(slugify(data.title)+'-'+str(ident),ident))
    return {'ok':True,'id':ident}

@app.put('/api/admin/posts/{ident}')
async def edit_post(request:Request,ident:int,data:NewsInput):
    protected(request,True)
    if any(not safe_url(url) for url in [data.image,*data.images] if url):
        raise HTTPException(400,'Imagem inválida')
    if data.video and not (video_embed(data.video) or (safe_url(data.video) and urlparse(data.video).path.lower().endswith(('.mp4','.webm')))):
        raise HTTPException(400,'Vídeo inválido')
    with db() as c:
        cur=c.execute('''UPDATE posts SET title=?,excerpt=?,body=?,category=?,image=?,images=?,video=?,place=?,published=? WHERE id=?''',
        (data.title.strip(),data.excerpt.strip(),data.body.strip(),data.category.strip(),data.image,json.dumps(data.images),data.video,data.place.strip(),int(data.published),ident))
    if not cur.rowcount: raise HTTPException(404)
    return {'ok':True}

@app.delete('/api/admin/posts/{ident}')
async def delete_post(request:Request,ident:int):
    protected(request,True)
    with db() as c:
        cur=c.execute('DELETE FROM posts WHERE id=?',(ident,))
    if not cur.rowcount: raise HTTPException(404)
    return {'ok':True}

@app.delete('/api/admin/inquiries/{ident}')
async def delete_inquiry(request:Request,ident:int):
    protected(request,True)
    with db() as c:
        cur=c.execute('DELETE FROM inquiries WHERE id=?',(ident,))
    if not cur.rowcount: raise HTTPException(404)
    return {'ok':True}

@app.post('/api/admin/logout')
async def logout(request:Request):
    protected(request,True)
    token=request.cookies.get('sueessor_session','')
    with db() as c:
        c.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),))
    resp=JSONResponse({'ok':True})
    resp.delete_cookie('sueessor_session',path='/')
    return resp

@app.post('/api/admin/upload')
async def upload(request:Request, file:UploadFile=File(...)):
    protected(request,True)
    name=(file.filename or '').lower()
    is_video=name.endswith(('.mp4','.webm'))
    maxsize=MAX_VIDEO if is_video else MAX_IMAGE
    data=bytearray()
    while True:
        chunk=await file.read(1024*1024)
        if not chunk: break
        data.extend(chunk)
        if len(data)>maxsize: raise HTTPException(413, 'Arquivo excede tamanho máximo')
    if not data: raise HTTPException(400,'Arquivo vazio')
    if IS_VERCEL and len(data) > 4 * 1024 * 1024:
        raise HTTPException(413,'Na Vercel, o upload direto aceita até aproximadamente 4 MB. Use um link HTTPS para vídeos maiores.')
    if IS_VERCEL and not os.getenv('BLOB_READ_WRITE_TOKEN'):
        raise HTTPException(503,'Configure Vercel Blob para salvar arquivos. Links HTTPS de mídia já podem ser usados.')
    key=secrets.token_urlsafe(20).replace('-','a').replace('_','b').lower()
    if is_video:
        ext='mp4' if name.endswith('.mp4') else 'webm'
        good=(ext=='mp4' and b'ftyp' in data[4:16]) or (ext=='webm' and bytes(data[:4])==b'\x1aE\xdf\xa3')
        if not good: raise HTTPException(400,'Formato de vídeo inválido')
        # extensão, assinatura e content-type controlados; nunca serve HTML como upload
        out=UPLOADS / (key+'.'+ext)
        if IS_VERCEL:
            processed=bytes(data)
            mime='video/'+ext
        else:
            out.write_bytes(data)
    else:
        try:
            with Image.open(io.BytesIO(data)) as img:
                img.verify()
            with Image.open(io.BytesIO(data)) as img:
                if img.width*img.height > 35_000_000: raise HTTPException(413,'Imagem grande demais')
                clean=ImageOps.exif_transpose(img).convert('RGB')
                clean.thumbnail((2400,2400),Image.Resampling.LANCZOS)
                out=UPLOADS/(key+'.jpg')
                if IS_VERCEL:
                    buf=io.BytesIO()
                    clean.save(buf,'JPEG',quality=87,optimize=True)
                    processed=buf.getvalue()
                    mime='image/jpeg'
                else:
                    clean.save(out,'JPEG',quality=87,optimize=True)
        except (UnidentifiedImageError,OSError,ValueError):
            raise HTTPException(400,'Envie uma imagem válida')
    if IS_VERCEL:
        from vercel.blob import AsyncBlobClient
        try:
            blob = await AsyncBlobClient().put('noticias/'+out.name, processed, access='public', content_type=mime)
            return {'ok':True,'url':blob.url}
        except Exception as exc:
            raise HTTPException(502,'Não foi possível enviar a mídia ao Vercel Blob; verifique a conexão do armazenamento.') from exc
    return {'ok':True,'url':'/uploads/'+out.name}

@app.get('/robots.txt')
def robots():
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse('User-agent: *\nDisallow: /central-restrita/\nDisallow: /api/admin/\n')

@app.exception_handler(404)
async def not_found(request:Request,exc):
    response = render(request,'404.html',page='404')
    response.status_code=404
    return response
