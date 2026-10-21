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
    app.mount('/editais/arquivos', StaticFiles(directory=str(BASE / 'public' / 'editais' / 'arquivos')), name='editais-arquivos')
    app.mount('/modelos-de-acordo/arquivos', StaticFiles(directory=str(BASE / 'public' / 'modelos-de-acordo' / 'arquivos')), name='modelos-acordo-arquivos')
templates = Jinja2Templates(directory=str(BASE / 'templates'))
CONVENTION_DOCS = json.loads((BASE / 'static' / 'convention_index.json').read_text(encoding='utf-8'))
CONVENTION_COUNTS = {key:sum(len(year['documents']) for year in years) for key,years in CONVENTION_DOCS.items()}
EDITAL_DOCS = json.loads((BASE / 'static' / 'editais_index.json').read_text(encoding='utf-8'))
EDITAL_YEARS = sorted({record['year'] for record in EDITAL_DOCS}, reverse=True)
EDITAL_BY_YEAR = {year:[r for r in EDITAL_DOCS if r['year']==year] for year in EDITAL_YEARS}
EDITAL_NAMES = sorted({r['name'] for r in EDITAL_DOCS}, key=lambda s:s.casefold())
# PDFs de referência fornecidos pelo SUEESSOR: modelos não assinados, datados de 2019.
# Manter as cópias originais e servir como assets públicos (inclusive na Vercel).
AGREEMENT_MODELS = [
    {
        'id': 'banco-de-horas',
        'number': '01',
        'title': 'Acordo coletivo de trabalho para implantação de Banco de Horas',
        'summary': 'Modelo de acordo coletivo para implantação de banco de horas, com regras de formação, composição, compensação e acompanhamento dos saldos.',
        'topics': ['Criação e composição do banco de horas', 'Regras para compensação e informação dos saldos', 'Procedimentos de renovação, revisão ou revogação'],
        'pages': 4,
        'url': '/modelos-de-acordo/arquivos/acordo-coletivo-modelo-banco-de-horas.pdf',
        'filename': 'Acordo-Coletivo-Modelo-Banco-de-Horas.pdf',
    },
    {
        'id': 'jornada-12x36',
        'number': '02',
        'title': 'Acordo coletivo de trabalho para compensação de horas com implantação do regime de jornada 12×36',
        'subtitle': '(doze horas de trabalho por 36 horas de descanso) e outros fins específicos nele indicados.',
        'summary': 'Modelo para implementação da jornada de doze horas de trabalho por trinta e seis horas de descanso, com disposições sobre intervalos, trabalho noturno e feriados.',
        'topics': ['Jornada 12×36 e intervalos para refeição e descanso', 'Condições para trabalho noturno e feriados', 'Previsão expressa de vedação do banco de horas aos empregados abrangidos'],
        'pages': 3,
        'url': '/modelos-de-acordo/arquivos/acordo-coletivo-modelo-jornada-12x36.pdf',
        'filename': 'Acordo-Coletivo-Modelo-Jornada-12x36.pdf',
    },
]



AREAS = ['Barueri', 'Carapicuíba', 'Cotia', 'Embu', 'Embu-Guaçu', 'Ibiúna', 'Itapecerica da Serra', 'Itapevi', 'Jandira', 'Osasco', 'Santana de Parnaíba', 'Taboão da Serra', 'Vargem Grande Paulista']
DIRECTORY = [
 ('Diretoria efetiva', [('Antônio Gervásio Rodrigues', 'Presidente'),('Juarez Henrique de Paulo','Vice-presidente'),('Amilton Arlindo de Moura Rodrigues','Secretário-geral'),('Noêmia Telles de Oliveira','Tesoureira-geral'),('Fábio Ribeiro Aragão','Primeiro tesoureiro'),('Orlando Faustino da Silva','Secretário de Assistência Social')]),
 ('Diretores suplentes', [('Amélia Pereira Matos',''),('Luciana Pereira Santos',''),('Geni dos Santos Nascimento',''),('Edinaldo Alves Batista',''),('Ailton Merces Barbosa',''),('Rogério Pereira Nunes Mendes','')]),
 ('Conselho fiscal', [('José Aparecido Nascimento',''),('Raymundo José Gonçalves',''),('Cilda Conceição de Oliveira Queiroz','')]),
]
SERVICE_CARDS = [
  {'icon':'scale','name':'Assessoria jurídica','summary':'Orientação e defesa dos direitos trabalhistas da categoria.','link':'/servicos/juridico'},
  {'icon':'heart','name':'Clínica e odontologia','summary':'Saúde, acompanhamento clínico e atendimento odontológico aos associados.','link':'/servicos/clinica-medica'},
  {'icon':'file','name':'Convenções coletivas','summary':'Acesse acordos, instrumentos coletivos e documentos da sua categoria.','link':'/convencoes'},
  {'icon':'users','name':'Benefícios e parcerias','summary':'Mais possibilidades de cuidado, lazer e economia para você e sua família.','link':'/servicos/beneficios'},
]
# Serviço de benefícios: informações institucionais e links de referência.
# Valores, disponibilidade e regras devem ser confirmados com o SUEESSOR.
BENEFIT_CARDS = [
    {'title':'Assessoria Jurídica','slug':'juridico','icon':'scale','tag':'Direitos e orientação',
     'summary':'Orientações e acompanhamento nas áreas trabalhista, familiar e previdenciária.',
     'href':'/servicos/juridico'},
    {'title':'Clínica Médica','slug':'clinica-medica','icon':'stethoscope','tag':'Saúde e prevenção',
     'summary':'Consultas e acesso facilitado a cuidados de saúde para associados e dependentes.',
     'href':'/servicos/clinica-medica'},
    {'title':'Espaço para Eventos','slug':'espaco-para-eventos','icon':'calendar','tag':'Convivência',
     'summary':'Ambiente para encontros e comemorações de associados e familiares.',
     'href':'/servicos/espaco-para-eventos'},
    {'title':'Espaço Gourmet','slug':'espaco-gourmet','icon':'utensils','tag':'Lazer e encontros',
     'summary':'Espaço com churrasqueira e estrutura para confraternizações.',
     'href':'/servicos/espaco-gourmet'},
    {'title':'Excursões','slug':'excursoes','icon':'bus','tag':'Viagens e lazer',
     'summary':'Passeios organizados pelo sindicato para momentos de descanso e lazer.',
     'href':'/servicos/excursoes'},
    {'title':'Salão de Beleza','slug':'salao-de-beleza','icon':'scissors','tag':'Bem-estar',
     'summary':'Cuidados pessoais e condições especiais para a categoria.',
     'href':'/servicos/salao-de-beleza'},
    {'title':'Tratamento Odontológico','slug':'tratamento-odontologico','icon':'smile','tag':'Saúde bucal',
     'summary':'Atendimento odontológico básico em Osasco e Itapevi.',
     'href':'/servicos/tratamento-odontologico'},
]
# Categorias de parcerias; as condições devem ser confirmadas com o SUEESSOR.
# São exemplos da rede do sindicato, não garantia de desconto atual ou disponibilidade.
PARTNERSHIP_CARDS = [
    {'title':'Beleza','slug':'beleza','icon':'scissors','tag':'Autocuidado',
     'summary':'Salões, acessórios e serviços de beleza com vantagens para associados.',
     'href':'/servicos/parcerias/beleza'},
    {'title':'Clubes','slug':'clubes','icon':'users','tag':'Lazer em família',
     'summary':'Espaços de lazer, piscinas e atividades para aproveitar com a família.',
     'href':'/servicos/parcerias/clubes'},
    {'title':'Cursos','slug':'cursos','icon':'graduation','tag':'Educação',
     'summary':'Capacitação, formação profissional e oportunidades de aprendizagem.',
     'href':'/servicos/parcerias/cursos'},
    {'title':'Parques','slug':'parques','icon':'trees','tag':'Diversão',
     'summary':'Experiências e ingressos em parques de diversão e aquáticos.',
     'href':'/servicos/parcerias/parques'},
    {'title':'Produtos e Serviços','slug':'produtos-e-servicos','icon':'shopping','tag':'Economia',
     'summary':'Vantagens em compras, serviços e entretenimento.',
     'href':'/servicos/parcerias/produtos-e-servicos'},
    {'title':'Saúde','slug':'saude','icon':'heart','tag':'Cuidado',
     'summary':'Acesso facilitado a serviços de saúde e exames com parceiros.',
     'href':'/servicos/parcerias/saude'},
    {'title':'Viagens e Turismo','slug':'viagens-e-turismo','icon':'bus','tag':'Novas experiências',
     'summary':'Passeios, excursões e opções para viajar e descansar.',
     'href':'/servicos/parcerias/viagens-e-turismo'},
]
# Parceiros e endereços divulgados pelo SUEESSOR. Horários, descontos e localização
# podem mudar; cada card sinaliza quando a localização exige confirmação.
BEAUTY_PARTNERS = [
    {
        'slug': 'acessorios-rojo',
        'name': 'Acessórios Rojo',
        'category': 'Semijoias e acessórios',
        'offer': '10% de desconto',
        'summary': 'Associados SUEESSOR recebem 10% de desconto em brincos, pulseiras, correntes e anéis, conforme condições divulgadas pela entidade.',
        'image': '',
        'logo': '/static/parcerias/logo-rojo.webp',
        'show_map': False,
        'image_alt': 'Logo Acessórios Rojo enviado pelo SUEESSOR',
        'image_note': '',
        'address': 'Shopping Bella Vista, Rua Antônio Agú, 502, lojas 2 e 3, térreo, Centro, Osasco/SP',
        'place_note': 'Endereço divulgado pelo SUEESSOR. Outros cadastros públicos indicam outro endereço; confirme com a loja antes de sair.',
        'map_query': 'Shopping Bella Vista, Rua Antônio Agú, 502, Osasco, SP',
        'phone': '(11) 4311-9233', 'phone_href': 'tel:+551143119233',
        'whatsapp': '(11) 96391-7523', 'whatsapp_href': 'https://wa.me/5511963917523',
        'instagram': '@acessorios_rojo', 'instagram_href': 'https://www.instagram.com/acessorios_rojo/',
        'features': ['Brincos', 'Pulseiras', 'Correntes', 'Anéis'],
        'gallery': [],
    },
    {
        'slug': 'sao-paulo-fashion-hair',
        'name': 'São Paulo – Fashion Hair',
        'category': 'Salão de beleza',
        'offer': 'Desconto exclusivo',
        'summary': 'Serviços de corte, escova, química em geral, manicure e pedicure com desconto especial para associados e novas opções de horários, conforme divulgação.',
        'image': '',
        'image_alt': '',
        'image_note': 'Fotografia verificada do estabelecimento ainda indisponível. Use o mapa para consultar imagens recentes.',
        'address': 'Rua Presidente Castelo Branco, 159 – Centro, Osasco/SP',
        'place_note': 'Endereço confirmado em listagens do salão. Confirme os horários antes da visita.',
        'map_query': 'São Paulo Hair Fashion, Rua Presidente Castelo Branco, 159, Osasco SP',
        'phone': '(11) 3682-6297', 'phone_href': 'tel:+551136826297',
        'whatsapp': '(11) 97268-5658', 'whatsapp_href': 'https://wa.me/5511972685658',
        'instagram': None, 'instagram_href': None,
        'features': ['Corte', 'Escova', 'Química', 'Manicure', 'Pedicure'],
        'gallery': [],
    },
    {
        'slug': 'morellos-academia',
        'name': 'Morellos – Academia',
        'category': 'Atividade física e bem-estar',
        'offer': 'Planos especiais para associados',
        'summary': 'A parceria divulgada pelo SUEESSOR oferece condições especiais para associados e associadas da categoria na academia em Itapecerica da Serra.',
        'image': 'https://sites.diretasistemas.com.br/sites/1955/wp-content/uploads/2026/02/26170023/whatsapp-image-2026-02-25-at-12-01-08-2.jpeg',
        'image_alt': 'Entrada interna da Academia Morellos com o logotipo oficial na parede, em fotografia publicada pelo SUEESSOR',
        'image_note': 'Fotografia real da Academia Morellos e de sua marca, publicada pelo SUEESSOR.',
        'address': 'Rodovia Prefeito Bento Rotger Domingues, 238 – Jardim Elisa, Itapecerica da Serra/SP',
        'place_note': 'Endereço divulgado em plataformas de academias; confirme a unidade e as condições do convênio com Luciana.',
        'map_query': 'Morellos Academia, Rodovia Prefeito Bento Rotger Domingues, 238, Itapecerica da Serra SP',
        'phone': '(11) 96050-2742 (Luciana – SUEESSOR)', 'phone_href': 'tel:+5511960502742',
        'whatsapp': '(11) 96050-2742', 'whatsapp_href': 'https://wa.me/5511960502742',
        'instagram': '@morellosacademia', 'instagram_href': 'https://www.instagram.com/morellosacademia/',
        'features': ['Aulas coletivas', 'Avaliação física', 'Treino personalizado'],
        'gallery': [
            {'src':'https://sites.diretasistemas.com.br/sites/1955/wp-content/uploads/2026/02/26170025/whatsapp-image-2026-02-25-at-12-01-08-3.jpeg', 'alt':'Área de musculação da Academia Morellos divulgada pelo SUEESSOR'},
            {'src':'https://sites.diretasistemas.com.br/sites/1955/wp-content/uploads/2026/02/26170050/whatsapp-image-2026-02-25-at-12-01-07-768x346-1.jpeg', 'alt':'Recepção da Academia Morellos divulgada pelo SUEESSOR'},
            {'src':'https://sites.diretasistemas.com.br/sites/1955/wp-content/uploads/2026/02/26170051/whatsapp-image-2026-02-25-at-12-01-08-768x346-1.jpeg', 'alt':'Equipamentos de musculação da Academia Morellos'},
        ],
        'plans': [
            {'name':'Plano recorrente','price':'R$ 109,90 / mês', 'items':['Acesso a todas as aulas coletivas','Avaliação física','Treino personalizado']},
            {'name':'Plano anual','price':'12× de R$ 109,90', 'items':['Acesso a todas as aulas coletivas','Avaliação física','Treino personalizado','4 convidados por mês (na condição de dependentes do associado)','60 dias de trancamento']},
        ],
    },
]
for partner in BEAUTY_PARTNERS:
    partner['map_embed'] = 'https://www.google.com/maps?q=' + quote(partner['map_query'], safe='') + '&output=embed'
    partner['maps_url'] = 'https://www.google.com/maps/search/?api=1&query=' + quote(partner['map_query'], safe='')

# Parceiros de cursos: informações e logos de referência publicados pelo SUEESSOR.
# A localização no mapa é incorporada apenas quando um endereço físico específico
# pode ser associado ao parceiro. Para serviços online/multiunidade, usar pesquisa.
COURSE_PARTNERS = [
    {
        'slug':'argos', 'name':'Argos | Centro de Educação Profissional Santo Amaro',
        'type':'Educação profissional', 'discount':'15% de desconto',
        'summary':'Sócios e seus dependentes têm 15% de desconto nos cursos oferecidos.',
        'logo':'https://sites.diretasistemas.com.br/sites/1955/wp-content/uploads/2025/11/05152148/argos.jpg',
        'address':'Rua Clemente Álvares, 470 – Lapa, São Paulo/SP',
        'address_note':'Endereço publicado pelo SUEESSOR. O nome da instituição menciona Santo Amaro; confirme a unidade antes da visita.',
        'maps_query':'Rua Clemente Alvares 470 Lapa Sao Paulo SP',
        'show_map':True,
        'phones':[('(11) 5521-5847','tel:+551155215847'),('(11) 5522-1533','tel:+551155221533')],
        'whatsapps':[('(11) 94873-0486','https://wa.me/5511948730486'),('(11) 96996-0935','https://wa.me/5511969960935')],
        'email':'santoamaro@escolasargos.com.br', 'website':'http://escolasargos.com.br/',
        'benefits':['Cursos oferecidos pela escola com desconto para sócios e dependentes legais.'],
    },
    {
        'slug':'cna', 'name':'CNA Inglês definitivo',
        'type':'Idiomas', 'discount':'A partir de 30% de desconto',
        'summary':'Associados SUEESSOR e dependentes recebem descontos nas mensalidades dos cursos do CNA, nas unidades participantes.',
        'logo':'https://sites.diretasistemas.com.br/sites/1955/wp-content/uploads/2025/11/05152159/cna.jpg',
        'address':'Unidades participantes: Alphaville (Barueri), Cotia, Granja Viana, Osasco Centro, Vargem Grande Paulista e Vila dos Remédios.',
        'address_note':'Consulte o endereço da unidade escolhida com a rede CNA. A pesquisa no mapa é de uma das regiões abrangidas, não uma confirmação de endereço.',
        'maps_query':'CNA Ingles Osasco Centro SP', 'show_map':False,
        'phones':[('(11) 4003-3599','tel:+551140033599')],
        'whatsapps':[], 'email':None, 'website':'https://www.cna.com.br/',
        'benefits':['Desconto exclusivo para as seis regiões participantes, conforme regras do convênio.'],
        'units':['Alphaville (Barueri)','Cotia','Granja Viana','Osasco Centro','Vargem Grande Paulista','Vila dos Remédios'],
    },
    {
        'slug':'colegio-seta', 'name':'Colégio Seta',
        'type':'Educação básica e técnica', 'discount':'15% nas mensalidades',
        'summary':'Associados, dependentes legais e agregados têm desconto de 15% nas mensalidades dos cursos do Colégio Seta em Osasco.',
        'logo':'https://sites.diretasistemas.com.br/sites/1955/wp-content/uploads/2025/11/05152208/logo-colegio-seta.png',
        'address':'Avenida João Batista, 487 – Osasco/SP – CEP 06097-105',
        'address_note':'Endereço divulgado pelo SUEESSOR.',
        'maps_query':'Avenida Joao Batista 487 Osasco SP 06097-105', 'show_map':True,
        'phones':[('(11) 3681-9695','tel:+551136819695'),('(11) 3689-2121','tel:+551136892121')],
        'whatsapps':[], 'email':'contato@colegioseta.com.br', 'website':'https://www.colegioseta.com.br/',
        'benefits':['Ensino Fundamental e Ensino Médio regular','Educação de Jovens e Adultos (EJA)','Cursos técnicos integrados ao Médio ou sequenciais: Administração, Contabilidade, Eletrônica, Eletrotécnica, Informática, Mecatrônica e Segurança do Trabalho.'],
    },
    {
        'slug':'damasio', 'name':'Damásio Educacional',
        'type':'Concursos, OAB, pós-graduação e MBA', 'discount':'Até 30% de desconto',
        'summary':'Condições anunciadas para cursos preparatórios, pós-graduação e MBA voltadas aos associados SUEESSOR.',
        'logo':'https://sites.diretasistemas.com.br/sites/1955/wp-content/uploads/2025/11/05152218/adesivo_foto_vertical-02-650x450-1.jpg',
        'address':'Unidade Osasco (informação atual do Damásio): Rua Avelino Lopes, 297 – Centro, Osasco/SP.',
        'address_note':'O endereço da unidade é divulgado pelo Damásio, mas não confirma onde o desconto do convênio pode ser utilizado. Consulte antes de ir.',
        'maps_query':'Damásio Rua Avelino Lopes 297 Centro Osasco SP', 'show_map':True,
        'phones':[('(11) 3683-9432','tel:+551136839432'),('(11) 4623-2644','tel:+551146232644')],
        'whatsapps':[('(11) 94513-0422','https://wa.me/5511945130422')], 'email':None, 'website':'https://damasio.com.br/',
        'benefits':['Preparatórios para concursos públicos e OAB: 30% de desconto.','Pós-graduação com certificação Damásio: 25% de desconto.','MBA e IMBEC AGRO: 20% de desconto.'],
    },
    {
        'slug':'estacio', 'name':'Faculdade Estácio de Sá',
        'type':'Graduação e bolsas', 'discount':'Bolsas de 40% a 72%',
        'summary':'Associados e dependentes podem ter bolsas de 40% a 72% em cursos de graduação, com mais 10% de desconto acumulável nas mensalidades, conforme divulgação.',
        'logo':'https://sites.diretasistemas.com.br/sites/1955/wp-content/uploads/2025/11/05152226/estacio.png',
        'address':'Diversas unidades e modalidades. Confirme o campus ou polo de interesse.',
        'address_note':'Não há campus específico indicado para o convênio; o Maps abre uma busca, não uma unidade confirmada.',
        'maps_query':'Faculdade Estácio Osasco SP', 'show_map':False,
        'phones':[('(11) 96742-5757 (Paula)','tel:+5511967425757')],
        'whatsapps':[('(11) 9569-8690 (Coordenação Comercial)','https://wa.me/551195698690')],
        'email':'silva.paula@estacio.br', 'website':'https://estacio.br/selecao',
        'benefits':['Bolsas informadas de 40% até 72% na graduação.','Mais 10% de desconto nas mensalidades, acumulável conforme regras divulgadas.','Atendimento com a coordenadora comercial para simulação.'],
    },
    {
        'slug':'rg-cursos', 'name':'RG – Cursos de Capacitação',
        'type':'Capacitação profissional', 'discount':'Preços exclusivos',
        'summary':'Condições especiais para associados em cursos de capacitação nas áreas de cuidado e saúde.',
        'logo':None,
        'address':'Endereço não informado no material enviado.',
        'address_note':'Não encontramos endereço específico confirmado. Use o contato para localizar a unidade.',
        'maps_query':'RG Cursos de Capacitacao Sao Paulo SP', 'show_map':False,
        'phones':[('(11) 4237-6727','tel:+551142376727'),('(11) 99596-9301 (Júnior)','tel:+5511995969301')],
        'whatsapps':[('(11) 99596-9301','https://wa.me/5511995969301')],
        'email':'rgcursos@terra.com.br', 'website':'http://rgcursossp.com.br/',
        'benefits':['Cuidador de Idosos','Berçarista','Babá','Punção Venosa','Outras formações: consultar a instituição.'],
    },
    {
        'slug':'supergeeks', 'name':'SuperGeeks Carapicuíba',
        'type':'Robótica e programação', 'discount':'20% de desconto',
        'summary':'Parceria para crianças de 8 a 17 anos, com 20% de desconto nos cursos de robótica e programação (exceto material didático). Aula demonstrativa gratuita anunciada.',
        'logo':'https://sites.diretasistemas.com.br/sites/1955/wp-content/uploads/2025/11/05152247/whatsapp-image-2019-05-22-at-10-44-20.jpeg',
        'address':'Unidade Carapicuíba: Avenida Miriam, 122 – Carapicuíba/SP, CEP 06320-060.',
        'address_note':'Endereço de unidade divulgado no site atual da SuperGeeks. Confirme a aplicação do desconto informado pelo SUEESSOR.',
        'maps_query':'SuperGeeks Carapicuiba Avenida Miriam 122 SP', 'show_map':True,
        'phones':[], 'whatsapps':[('(11) 98364-3933','https://wa.me/5511983643933')],
        'email':None, 'website':'https://novo.supergeeks.ai/unidade/carapicuiba',
        'benefits':['20% de desconto para crianças de 8 a 17 anos (material didático não incluso).','Aula demonstrativa gratuita divulgada pelo convênio.','Cursos de programação, aplicativos, games e robótica.'],
        'extra_links':[('WhatsApp divulgado na campanha','https://bit.ly/WhattsSuperGeeks'),('Solicitar aula demonstrativa','https://bit.ly/AulaDemoGr%C3%A1tis')],
    },
    {
        'slug':'uninter', 'name':'UNINTER – Centro Universitário',
        'type':'Ensino superior', 'discount':'10% de desconto',
        'summary':'O associado SUEESSOR tem 10% de desconto nas mensalidades, conforme as condições do convênio divulgado.',
        'logo':'https://sites.diretasistemas.com.br/sites/1955/wp-content/uploads/2025/11/05152256/uninter.jpg',
        'address':'Vários polos e modalidades de ensino. Confirme o polo mais próximo.',
        'address_note':'Nenhum polo específico foi fornecido; a busca no Maps não indica um endereço de parceria confirmado.',
        'maps_query':'UNINTER polo Osasco SP', 'show_map':False,
        'phones':[('0800 702 0500','tel:08007020500')], 'whatsapps':[], 'email':None, 'website':'https://www.uninter.com/',
        'benefits':['10% de desconto nas mensalidades de cursos elegíveis, mediante confirmação do convênio.'],
    },
    {
        'slug':'unyleya', 'name':'Unyleya – Graduação e Pós-Graduação',
        'type':'Graduação e pós-graduação', 'discount':'Até 58% de bolsa',
        'summary':'Conforme divulgação, associados SUEESSOR e dependentes legais podem obter bolsas de até 58% em cursos elegíveis.',
        'logo':'https://sites.diretasistemas.com.br/sites/1955/wp-content/uploads/2025/11/05152304/whatsapp-image-2024-03-11-at-16-25-49.jpeg',
        'address':'Modalidades de ensino e unidades a consultar no site da instituição.',
        'address_note':'O material não fornece endereço de unidade; o Google Maps abre uma pesquisa geral.',
        'maps_query':'Unyleya ensino superior Osasco Sao Paulo', 'show_map':False,
        'phones':[('0800 604 2210','tel:08006042210')], 'whatsapps':[], 'email':None, 'website':'https://unyleya.edu.br/invista.voce',
        'benefits':['Até 58% de bolsa para associados e seus dependentes legais em cursos elegíveis.'],
    },
]
for partner in COURSE_PARTNERS:
    partner['maps_url'] = 'https://www.google.com/maps/search/?api=1&query=' + quote(partner['maps_query'],safe='')
    partner['map_embed'] = 'https://www.google.com/maps?q=' + quote(partner['maps_query'],safe='') + '&output=embed' if partner['show_map'] else None

CLUB_PARTNERS = [
    {
        'slug': 'cefol',
        'name': 'CEFOL – Centro de Formação e Lazer',
        'tag': 'Entrada gratuita',
        'subtitle': 'Cotia / SP',
        'intro': 'A entrada no CEFOL é gratuita para associados SUEESSOR e dependentes legais. Para usar a piscina, é cobrado apenas o valor do exame médico por pessoa, válido por 90 dias.',
        'terms': [
            'Entrada gratuita para associados e dependentes legais.',
            'Para utilizar as piscinas, é necessário exame médico pago por pessoa, válido por 90 dias.',
            'Antes da visita, solicite a autorização de acesso na sede do SUEESSOR.',
        ],
        'hours': 'Consulte os dias e horários atualizados com o clube antes da visita.',
        'address': 'Estrada das Mulatas, 1000 – Tijuco Preto – Cotia/SP',
        'phone': '(11) 3652-3390',
        'phone_href': 'tel:+551136523390',
        'contact_name': 'Kátia – SUEESSOR',
        'whatsapp': '(11) 94182-5124',
        'whatsapp_href': 'https://wa.me/5511941825124',
        'website': 'https://cefol.com.br/',
        'logo': 'https://sites.diretasistemas.com.br/sites/1955/wp-content/uploads/2025/11/05151243/cefol-logo.jpeg',
        'logo_alt': 'Logotipo oficial CEFOL – Centro de Formação e Lazer',
        'gallery': [
            {'src':'https://quimicosunificados.com.br/arquivos/2016/05/banner-site-quimicos-20171.jpg', 'alt':'Piscina do CEFOL em foto divulgada pelo Sindicato Químicos Unificados'},
            {'src':'https://www.quimicosunificados.com.br/arquivos/2011/03/68deb1ace75874ec7e3aa6d027576f9.JPG', 'alt':'Área de lazer e piscina do CEFOL Osasco em fotografia institucional'},
            {'src':'https://www.quimicosunificados.com.br/arquivos/2011/03/00aa7692265fcb084d57fa02fb3a3815.JPG', 'alt':'Área de quiosques do CEFOL Osasco em fotografia institucional'},
        ],
        'photo_source': 'Fotografias publicadas pelo Sindicato Químicos Unificados (registros institucionais e históricos).',
        'source_url': 'https://sueessor.org.br/clubes/',
    },
    {
        'slug': 'simtratecor',
        'name': 'Clube de Campo SIMTRATECOR',
        'tag': 'Piscinas gratuitas',
        'subtitle': 'São Roque / SP',
        'intro': 'O uso das piscinas é gratuito para o associado SUEESSOR e seus dependentes legais com até 17 anos, conforme as condições divulgadas pelo sindicato.',
        'terms': [
            'Uso gratuito das piscinas para associados SUEESSOR.',
            'Benefício estendido aos dependentes legais de até 17 anos.',
            'De terça a sexta-feira: das 08h00 às 16h00.',
            'Sábados, domingos e feriados: das 07h00 às 18h00, conforme a informação divulgada pelo SUEESSOR.',
        ],
        'hours': 'Terça a sexta: 08h00–16h00. Sábados, domingos e feriados: 07h00–18h00 (conforme SUEESSOR).',
        'hour_note': 'O portal do próprio SIMTRATECOR informa sábado das 08h00 às 17h00. Confirme o horário atualizado antes de sair de casa.',
        'address': 'Estrada Taxaquara, 900 – São João Novo – São Roque/SP',
        'phone': '(11) 3652-3390',
        'phone_href': 'tel:+551136523390',
        'contact_name': 'Camila ou Kátia – SUEESSOR',
        'whatsapp': None,
        'whatsapp_href': None,
        'website': 'https://www.simtratecor.com.br/clube-de-campo',
        'logo': 'https://sites.diretasistemas.com.br/sites/1955/wp-content/uploads/2025/11/05151250/logo3-300x155-1.png',
        'logo_alt': 'Logotipo oficial SIMTRATECOR',
        'gallery': [
            {'src':'https://static.wixstatic.com/media/a998bb_b1243e4968d44156b5fe73834e5bd333~mv2.jpg', 'alt':'Instalações do Clube de Campo SIMTRATECOR em imagem publicada pelo próprio clube'},
            {'src':'https://static.wixstatic.com/media/a998bb_cfdb9c95cb174629ab9a57f1ec40eb13~mv2.jpg', 'alt':'Piscinas e área de lazer do Clube de Campo SIMTRATECOR'},
            {'src':'https://static.wixstatic.com/media/a998bb_fba559717c25453b881a985cf8e2c6ae~mv2.jpg', 'alt':'Estrutura do Clube de Campo SIMTRATECOR em São Roque'},
        ],
        'photo_source': 'Fotografias divulgadas no site oficial do SIMTRATECOR.',
        'source_url': 'https://sueessor.org.br/clubes/',
    },
]
for club in CLUB_PARTNERS:
    query = club['name'] + ', ' + club['address']
    club['maps_url'] = 'https://www.google.com/maps/search/?api=1&query=' + quote(query, safe='')
    club['map_embed'] = 'https://www.google.com/maps?q=' + quote(club['address'], safe='') + '&output=embed'

PARK_PARTNERS = [
    {
        'slug': 'hopi-hari',
        'name': 'Hopi Hari',
        'tag': 'Preços especiais',
        'summary': 'Parque temático com preços especiais para associado SUEESSOR, conforme a parceria divulgada pelo sindicato.',
        'address': 'Rodovia dos Bandeirantes, km 72, 7001 – Moinho – Vinhedo/SP – CEP 13288-130',
        'phone': '(11) 3652-3390',
        'phone_href': 'tel:+551136523390',
        'contact_name': 'Noêmia – SUEESSOR',
        'website': 'https://www.hopihari.com.br/',
        'website_label': 'Site do parque',
        'logo': '/static/parcerias/parques/hopi-hari-logo.webp',
        'cover': '/static/parcerias/parques/hopi-hari-cover.webp',
        'logo_alt': 'Logo Hopi Hari na arte promocional do SUEESSOR',
        'cover_alt': 'Arte promocional do SUEESSOR destacando Hopi Hari',
        'benefits': [
            'Preços especiais para associado SUEESSOR.',
            'Condições, disponibilidade e valores devem ser confirmados com o sindicato.',
        ],
        'map_query': 'Hopi Hari Rodovia dos Bandeirantes km 72 7001 Vinhedo SP',
    },
    {
        'slug': 'magic-city',
        'name': 'Parque Aquático Magic City',
        'tag': 'Preços especiais',
        'summary': 'Parque aquático parceiro com preços especiais para associado SUEESSOR.',
        'address': 'Estrada do Koyama, 1 – Suzano/SP',
        'phone': '(11) 3652-3390',
        'phone_href': 'tel:+551136523390',
        'contact_name': 'Noêmia – SUEESSOR',
        'website': 'http://magiccity.com.br/',
        'website_label': 'Site do parque',
        'logo': '/static/parcerias/parques/magic-city-logo.webp',
        'cover': '/static/parcerias/parques/magic-city-cover.webp',
        'logo_alt': 'Logo Magic City na arte promocional do SUEESSOR',
        'cover_alt': 'Arte promocional do SUEESSOR destacando Magic City',
        'benefits': [
            'Preços especiais para associado SUEESSOR.',
            'Condições, disponibilidade e valores devem ser confirmados com o sindicato.',
        ],
        'map_query': 'Magic City Estrada do Koyama 1 Suzano SP',
    },
    {
        'slug': 'parque-da-monica',
        'name': 'Parque da Mônica',
        'tag': 'Preços especiais',
        'summary': 'Opção de lazer em São Paulo com preços especiais para associado SUEESSOR.',
        'address': 'Av. das Nações Unidas, 22540 – Jurubatuba – São Paulo/SP – CEP 04795-000',
        'phone': '(11) 3652-3390',
        'phone_href': 'tel:+551136523390',
        'contact_name': 'Noêmia – SUEESSOR',
        'website': 'https://parquedamonica.com.br/',
        'website_label': 'Site do parque',
        'logo': '/static/parcerias/parques/parque-da-monica-logo.webp',
        'cover': '/static/parcerias/parques/parque-da-monica-cover.webp',
        'logo_alt': 'Logo Parque da Mônica na arte promocional do SUEESSOR',
        'cover_alt': 'Arte promocional do SUEESSOR destacando Parque da Mônica',
        'benefits': [
            'Preços especiais para associado SUEESSOR.',
            'Condições, disponibilidade e valores devem ser confirmados com o sindicato.',
        ],
        'map_query': 'Parque da Monica Avenida das Nacoes Unidas 22540 Jurubatuba Sao Paulo SP',
    },
    {
        'slug': 'wetn-wild',
        'name': "Wet'n Wild",
        'tag': 'Preços especiais',
        'summary': 'Parque aquático com preços especiais para associado SUEESSOR.',
        'address': 'Rodovia dos Bandeirantes, Km 72, s/n – Zona Rural – Itupeva/SP – CEP 13295-000',
        'phone': '(11) 3652-3390',
        'phone_href': 'tel:+551136523390',
        'contact_name': 'Noêmia – SUEESSOR',
        'website': 'https://www.wetnwild.com.br/',
        'website_label': 'Site do parque',
        'logo': '/static/parcerias/parques/wetn-wild-logo.webp',
        'cover': '/static/parcerias/parques/wetn-wild-cover.webp',
        'logo_alt': "Logo Wet'n Wild na arte promocional do SUEESSOR",
        'cover_alt': "Arte promocional do SUEESSOR destacando Wet'n Wild",
        'benefits': [
            'Preços especiais para associado SUEESSOR.',
            'Condições, disponibilidade e valores devem ser confirmados com o sindicato.',
        ],
        'map_query': "Wet'n Wild Rodovia dos Bandeirantes km 72 Itupeva SP",
    },
]
for park in PARK_PARTNERS:
    park['maps_url'] = 'https://www.google.com/maps/search/?api=1&query=' + quote(park['map_query'], safe='')
    park['map_embed'] = 'https://www.google.com/maps?q=' + quote(park['map_query'], safe='') + '&output=embed'

# Parceiros de Produtos e Serviços. Imagens extraídas da identificação editorial
# do portal oficial do SUEESSOR; a imagem do Disk Carreto é ilustrativa, não logotipo.
PRODUCT_SERVICE_PARTNERS = [
    {
        'slug': 'cinemark',
        'name': 'Cinemark',
        'category': 'Cinema e entretenimento',
        'offer': 'Preços especiais',
        'summary': 'Viva a experiência de assistir a um filme na Cinemark. O SUEESSOR divulga preços especiais para os associados.',
        'image': 'https://sites.diretasistemas.com.br/sites/1955/wp-content/uploads/2025/11/05153845/cinemark.jpg',
        'image_alt': 'Arte de divulgação Cinemark publicada pelo SUEESSOR, com a marca em um ingresso vermelho',
        'image_kind': 'marca divulgada',
        'items': ['Experiência no cinema', 'Condições especiais para associados'],
        'phone': '(11) 3652-3390',
        'phone_href': 'tel:+551136523390',
        'contact_name': 'Noêmia – SUEESSOR',
        'website': 'https://www.cinemark.com.br/',
        'website_label': 'Site da Cinemark',
        'social': None,
    },
    {
        'slug': 'disk-carreto',
        'name': 'Disk Carreto',
        'category': 'Transportes e mudanças',
        'offer': 'Preços especiais',
        'summary': 'Mudanças residenciais e comerciais, fretes e apoio para eventos em toda a Grande São Paulo, com condições especiais para associados SUEESSOR.',
        'image': 'https://sites.diretasistemas.com.br/sites/1955/wp-content/uploads/2025/11/05153900/carreto.jpg',
        'image_alt': 'Imagem ilustrativa de serviço de carreto publicada pelo SUEESSOR: caminhão e profissional carregando caixa',
        'image_kind': 'imagem ilustrativa do serviço',
        'items': ['Mudanças residenciais', 'Mudanças comerciais', 'Fretes', 'Eventos'],
        'phone': '(11) 99775-2672',
        'phone_href': 'tel:+5511997752672',
        'contact_name': 'Marcos – Disk Carreto',
        'website': None,
        'website_label': None,
        'social': None,
    },
    {
        'slug': 'maria-chica',
        'name': 'Maria Chica',
        'category': 'Semijoias e acessórios',
        'offer': 'Descontos especiais',
        'summary': 'Semijoias e acessórios com brilho para todos os looks, descontos especiais e atendimento personalizado com Mariane.',
        'image': 'https://sites.diretasistemas.com.br/sites/1955/wp-content/uploads/2025/11/05153910/download-3.png',
        'image_alt': 'Logo Maria Chica Semijoias de Luxo, divulgado pelo SUEESSOR',
        'image_kind': 'logo divulgada',
        'items': ['Semijoias', 'Acessórios', 'Atendimento personalizado'],
        'phone': '(11) 98569-9023',
        'phone_href': 'tel:+5511985699023',
        'contact_name': 'Mariane – Maria Chica',
        'website': None,
        'website_label': None,
        'social': [
            ('Instagram @mariachicauniverso', 'https://www.instagram.com/mariachicauniverso/'),
            ('Facebook @mariachicauniverso', 'https://www.facebook.com/mariachicauniverso/'),
        ],
    },
]


HEALTH_PARTNERS = [
    {
        'slug':'bio-imagem-diagnosticos',
        'name':'Bio Imagem Diagnósticos',
        'category':'Exames e diagnósticos',
        'offer':'Exames a partir de R$ 27,00',
        'summary':'Confiança e respeito é na Bio Imagem. Condições divulgadas para associados SUEESSOR em exames e diagnósticos.',
        'logo':'/static/parcerias/saude/bio-imagem.svg',
        'website':'https://www.bioimagemdiagnosticos.com.br/',
        'website_label':'Site oficial',
        'items':['Exames a partir de R$ 27,00','Atendimento por telefone e WhatsApp','Unidade em Barueri'],
        'locations':[
            {'label':'Unidade Barueri','address':'Rua Enedina Chalupe Guerra, 44 - Centro, Barueri/SP','maps_query':'Rua Enedina Chalupe Guerra 44 Centro Barueri SP','phones':[('(11) 3173-3550','tel:+551131733550')],'whatsapps':[('(11) 94196-9113','https://wa.me/5511941969113')]}
        ],
        'email':None,
        'notes':['Valores e disponibilidade sujeitos à confirmação com o parceiro.'],
    },
    {
        'slug':'cdi-itapevi',
        'name':'Centro de Diagnósticos de Itapevi',
        'category':'Exames e diagnósticos',
        'offer':'Exames a partir de R$ 80,00',
        'summary':'Exames na CDI a partir de R$ 80,00 para associados SUEESSOR, conforme informações divulgadas.',
        'logo':'/static/parcerias/saude/cdi-itapevi.svg',
        'website':'http://www.cdiitapevi.com.br/',
        'website_label':'Site oficial',
        'items':['Exames a partir de R$ 80,00','Atendimento em Itapevi','Contatos por telefone e celular'],
        'locations':[
            {'label':'Unidade Itapevi','address':'Rua Dr. Pedro de Castro, 332 – Centro - Itapevi/SP','maps_query':'Rua Dr. Pedro de Castro 332 Centro Itapevi SP','phones':[('(11) 4553-7571','tel:+551145537571'),('(11) 4553-7572','tel:+551145537572'),('(11) 97571-3542','tel:+5511975713542')],'whatsapps':[]}
        ],
        'email':None,
        'notes':['Confirme a tabela vigente antes do agendamento.'],
    },
    {
        'slug':'clinica-lares',
        'name':'Clínica Lares',
        'category':'Psicologia e cuidado emocional',
        'offer':'Descontos exclusivos para associados',
        'summary':'A Clínica de Psicologia LARES atua desde 2000 com atendimento a crianças, adolescentes e adultos.',
        'logo':'/static/parcerias/saude/lares.svg',
        'website':None,
        'website_label':'',
        'items':['Atendimento a crianças, adolescentes e adultos','Duas unidades em Osasco','Descontos exclusivos para associados SUEESSOR'],
        'locations':[
            {'label':'Unidade I','address':'Rua Padre Dâmaso, 181 – Centro, Osasco/SP','maps_query':'Rua Padre Damaso 181 Centro Osasco SP','phones':[('(11) 3699-4245','tel:+551136994245')],'whatsapps':[]},
            {'label':'Unidade II','address':'Rua dos Marianos, 444 – Centro, Osasco/SP','maps_query':'Rua dos Marianos 444 Centro Osasco SP','phones':[('(11) 3683-0630','tel:+551136830630')],'whatsapps':[]},
        ],
        'email':'contato@clinicalares.com.br',
        'notes':['Instituto LARES de Psicologia e afins S/S Ltda.'],
    },
    {
        'slug':'dr-mauricio-rodrigues',
        'name':'Consultório Odontológico Dr. Maurício R. Rodrigues',
        'category':'Odontologia',
        'offer':'Agendamento facilitado para associados',
        'summary':'Consultório odontológico parceiro em Itapevi para agendamento de consultas e atendimento relacionado ao convênio.',
        'logo':'/static/parcerias/saude/dr-mauricio.svg',
        'website':None,
        'website_label':'',
        'items':['Consultório em Itapevi','Atendimento com agendamento prévio','Telefone e WhatsApp para marcação'],
        'locations':[
            {'label':'Unidade Itapevi','address':'Avenida Cesário de Abreu, 60 – Centro, Itapevi/SP (em frente à Loja Marisa)','maps_query':'Avenida Cesario de Abreu 60 Centro Itapevi SP','phones':[('(11) 4557-7240','tel:+551145577240')],'whatsapps':[('(11) 4557-7240','https://wa.me/551145577240')]}
        ],
        'email':None,
        'notes':['Parceria divulgada também na área de tratamento odontológico do SUEESSOR.'],
    },
    {
        'slug':'gs-imagem',
        'name':'GS Imagem',
        'category':'Exames e procedimentos',
        'offer':'Exames e procedimentos a partir de R$ 30,00',
        'summary':'Associados e dependentes contam com exames e procedimentos em condições especiais, conforme divulgação do sindicato.',
        'logo':'/static/parcerias/saude/gs-imagem.svg',
        'website':'https://www.gsimagem.com.br/',
        'website_label':'Site oficial',
        'items':['Exames e procedimentos a partir de R$ 30,00','Unidade em Osasco','Agendamento direto com a clínica'],
        'locations':[
            {'label':'Unidade Osasco','address':'Rua Madre Rosselo, 77 - Centro, Osasco/SP','maps_query':'Rua Madre Rosselo 77 Centro Osasco SP','phones':[('SUEESSOR: (11) 3652-3390','tel:+551136523390'),('GS Imagem: (11) 3651-9330','tel:+551136519330')],'whatsapps':[]}
        ],
        'email':None,
        'notes':['Agendamentos podem ser orientados pelo sindicato com Camila ou Kátia.'],
    },
    {
        'slug':'kpo-vitalle',
        'name':'KPO Vitalle Odontologia e Bem Estar',
        'category':'Odontologia e harmonização',
        'offer':'Serviços para associados e dependentes',
        'summary':'Serviços de ortodontia e harmonização orofacial para associados e dependentes.',
        'logo':'/static/parcerias/saude/kpo-vitalle.svg',
        'website':'https://www.facebook.com/KPO-Vitalle-Odontologia-Bem-Estar',
        'website_label':'Página oficial',
        'items':['Ortodontia','Harmonização orofacial','Atendimento em Osasco'],
        'locations':[
            {'label':'Unidade Osasco','address':'Rua Eloy Candido Lopes, 269 - Centro, Osasco – SP','maps_query':'Rua Eloy Candido Lopes 269 Centro Osasco SP','phones':[('(11) 3681-8826','tel:+551136818826')],'whatsapps':[]}
        ],
        'email':None,
        'notes':[],
    },
    {
        'slug':'otica-ricon',
        'name':'Ótica Ricon',
        'category':'Ótica',
        'offer':'Descontos especiais',
        'summary':'Associados SUEESSOR contam com descontos especiais na Ótica Ricon.',
        'logo':'/static/parcerias/saude/otica-ricon.svg',
        'website':None,
        'website_label':'',
        'items':['Descontos especiais para associados','Unidade no Centro de Osasco','Atendimento orientado pelo SUEESSOR'],
        'locations':[
            {'label':'Unidade Osasco','address':'R. Itabuna, 30 - Centro, Osasco - SP, 06010-120','maps_query':'Rua Itabuna 30 Centro Osasco SP 06010-120','phones':[('SUEESSOR: (11) 3652-3390','tel:+551136523390')],'whatsapps':[]}
        ],
        'email':None,
        'notes':['Informações com Camila ou Kátia no SUEESSOR.'],
    },
]
for partner in HEALTH_PARTNERS:
    for location in partner['locations']:
        location['map_embed'] = 'https://www.google.com/maps?q=' + quote(location['maps_query'], safe='') + '&output=embed'
        location['maps_url'] = 'https://www.google.com/maps/search/?api=1&query=' + quote(location['maps_query'], safe='')

TRAVEL_PARTNERS = [
    {
        'slug': 'mafisa-turismo',
        'name': 'Mafisa Turismo',
        'category': 'Viagens e turismo',
        'offer': 'Descontos exclusivos',
        'summary': 'Na Mafisa Turismo, associados SUEESSOR e seus dependentes têm descontos exclusivos. Entre em contato com a representante Cristina para conhecer destinos, descontos e formas de pagamento.',
        'logo': 'https://sites.diretasistemas.com.br/sites/1955/wp-content/uploads/2025/11/05155148/mafisa-01-1024x1024.png',
        'logo_alt': 'Marca da Mafisa Turismo divulgada no site oficial do SUEESSOR',
        'phone_display': '(11) 98828-8614',
        'phone_href': 'tel:+5511988288614',
        'whatsapp_url': 'https://wa.me/5511988288614',
        'contact_person': 'Cristina',
        'website': 'https://www.mafisaturismo.com.br/',
        'source_url': 'https://sueessor.org.br/viagens-e-turismo/',
        'services': ['Hotéis e pousadas', 'Pacotes de viagens', 'Destinos nacionais e internacionais', 'Formas de pagamento a consultar'],
    }
]

PARTNERSHIP_DETAILS = {
    'beleza': {
        'intro':'Conheça opções de beleza e autocuidado divulgadas pelo sindicato para associados e seus familiares.',
        'features':[
            {'title':'São Paulo – Fashion Hair','description':'Salão com serviços de corte, escova, química, manicure e pedicure; o portal divulga condições especiais para associados.','info':'Rua Presidente Castelo Branco, 159 – Centro, Osasco/SP. Telefone: (11) 3682-6297.'},
            {'title':'Acessórios Rojo','description':'Loja de acessórios, como brincos, pulseiras, correntes e anéis. O portal divulga desconto para associados.','info':'Rua Antônio Agú, 502 – Centro de Osasco. Informações: (11) 4311-9233.'},
        ],
        'source':'https://sueessor.org.br/beleza/',
        'internal_links':[{'title':'Conheça o SPAÇO BELEZA SUEESSOR','href':'/servicos/salao-de-beleza'}],
    },
    'clubes': {
        'intro':'Opções de lazer em clubes de campo, com regras específicas para acesso de associados e dependentes legais.',
        'features':[
            {'title':'CEFOL — Centro de Formação e Lazer','description':'O portal divulga entrada gratuita para associados e dependentes legais. O uso das piscinas depende de exame médico e o associado precisa solicitar autorização ao SUEESSOR.','info':'Estrada das Mulatas, 1000 – Tijuco Preto, Cotia/SP.'},
            {'title':'Clube de Campo SIMTRATECOR','description':'O portal divulga uso de piscinas em condições especiais para associados e dependentes legais, conforme regras e faixa etária do clube.','info':'Estrada Taxaquara, 900 – São João Novo, São Roque/SP.'},
        ],
        'source':'https://sueessor.org.br/clubes/',
        'internal_links':[],
    },
    'cursos': {
        'intro':'A qualificação abre novas possibilidades. Conheça oportunidades e parceiros de cursos e formação divulgados pelo sindicato.',
        'features':[
            {'title':'SuperGeeks — Robótica e Programação','description':'Parceria divulgada para cursos de robótica e programação voltados ao público infantojuvenil. Consulte turmas e condições atuais antes da matrícula.','info':'Informações e encaminhamentos pelo SUEESSOR.'},
            {'title':'Capacitação e formação','description':'O SUEESSOR divulga oportunidades de formação e cursos profissionalizantes para associados. Consulte as opções disponíveis neste momento.','info':'Peça informações sobre instituições, inscrições e eventuais descontos.'},
        ],
        'source':'https://sueessor.org.br/cursos/',
        'internal_links':[],
    },
    'parques': {
        'intro':'Diversão para toda a família com opções de parques que aparecem na rede de parcerias do sindicato.',
        'features':[
            {'title':'Hopi Hari','description':'Parque de diversões com condições especiais para associados divulgadas pelo sindicato.','info':'Rodovia dos Bandeirantes, km 72 – Vinhedo/SP.'},
            {'title':'Parque Aquático Magic City','description':'Parque aquático com condições especiais divulgadas para a categoria.','info':'Estrada do Koyama, 1 – Suzano/SP.'},
            {'title':'Parque da Mônica','description':'Opção de lazer familiar com preços especiais anunciados pelo SUEESSOR.','info':'Av. das Nações Unidas, 22540 – Jurubatuba, São Paulo/SP.'},
            {'title':"Wet'n Wild",'description':'Parque aquático incluído nas opções divulgadas pelo sindicato.','info':'Rodovia dos Bandeirantes, km 72 – Itupeva/SP.'},
        ],
        'source':'https://sueessor.org.br/parques/',
        'internal_links':[],
    },
    'produtos-e-servicos': {
        'intro':'Entretenimento, transportes e acessórios com condições especiais para associados SUEESSOR.',
        'features':[
            {'title':'Cinemark','description':'Preços especiais para associados SUEESSOR em experiências de cinema.','info':'Informações: (11) 3652-3390 (Noêmia).'},
            {'title':'Disk Carreto','description':'Mudanças residenciais, comerciais, fretes e eventos em toda a Grande São Paulo.','info':'Informações: (11) 99775-2672 (Marcos).'},
            {'title':'Maria Chica','description':'Semijoias e acessórios com descontos especiais e atendimento personalizado.','info':'Informações: (11) 98569-9023 (Mariane).'},
        ],
        'source':'https://sueessor.org.br/produtos-e-servicos/',
        'internal_links':[],
    },
    'saude': {
        'intro':'Além do atendimento oferecido pelo sindicato, associados podem conhecer opções de exames com condições especiais em laboratórios parceiros.',
        'features':[
            {'title':'Alphaclin — exames laboratoriais','description':'O Ambulatório Médico SUEESSOR orienta associados e dependentes sobre descontos em exames laboratoriais no parceiro.','info':'Rua Salem Bechara, 143 – Centro, Osasco/SP. (11) 2284-5566.'},
            {'title':'Sabin — diagnóstico por imagem','description':'Unidades de Alphaville/Barueri e Osasco, com encaminhamento carimbado pelo SUEESSOR para acesso às condições informadas.','info':'Agendamento: (11) 4195-1679.'},
        ],
        'source':'https://sueessor.org.br/clinica-medica/',
        'internal_links':[{'title':'Conheça a Clínica Médica','href':'/servicos/clinica-medica'}, {'title':'Tratamento odontológico','href':'/servicos/tratamento-odontologico'}],
    },
    'viagens-e-turismo': {
        'intro':'Passeios, viagens e oportunidades de lazer para descansar, conhecer novos destinos e aproveitar momentos especiais.',
        'features':[
            {'title':'Lambari (MG)','description':'Destino divulgado em excursões do SUEESSOR, conhecido por suas fontes de água mineral e atrações naturais.','info':'Consulte novas datas e disponibilidade diretamente com o sindicato.'},
            {'title':'Ilha Morena','description':'Excursão já divulgada pelo SUEESSOR. A programação publicada foi em novembro de 2024 e não representa uma viagem com inscrições atuais.','info':'Informe-se sobre futuros roteiros com a equipe do sindicato.'},
        ],
        'source':'https://sueessor.org.br/excursoes/',
        'internal_links':[{'title':'Conheça as Excursões do SUEESSOR','href':'/servicos/excursoes'}],
    },
}

BENEFIT_DETAILS = {
    'clinica-medica': {
        'title':'Clínica Médica', 'tag':'Saúde e prevenção', 'icon':'stethoscope',
        'heading':'Excelência, agilidade e consulta médica gratuita para quem cuida de quem cuida.',
        'intro':'O Ambulatório Médico SUEESSOR — Cuidando de Quem Cuida oferece atendimento humanizado, ágil e gratuito para associados, além de cobertura para dependentes legais e descontos em exames laboratoriais e de imagem.',
        'lead_paragraphs':[
            'Quem é associado ao SUEESSOR tem consultas médicas sem custo adicional, e o melhor: seus dependentes legais também. Com o Benefício Assistencial do SUEESSOR, você não precisa esperar meses por um agendamento nem pagar caro por uma consulta de qualidade.',
            'Os atendimentos com as especialidades médicas disponíveis na clínica já estão incluídos na mensalidade associativa do sindicato, tanto para os associados quanto para seus dependentes legais: cônjuge e filhos de até 21 anos.',
            'Cuidar da sua saúde com qualidade e dignidade é a nossa prioridade. Além das consultas, você e sua família contam com atendimento odontológico básico gratuito e descontos exclusivos em exames de laboratório e imagem.',
        ],
        'highlights':[
            ('Consultas gratuitas','As consultas nas especialidades médicas disponíveis na clínica já estão incluídas na mensalidade associativa para os associados e dependentes legais.'),
            ('Dependentes legais','Cônjuge e filhos de até 21 anos têm consulta médica gratuita, atendimento odontológico básico gratuito e descontos em exames. Na psicologia, o valor é de R$ 40,00 por consulta, sujeito a alterações.'),
            ('Mais agilidade no cuidado','O atendimento é realizado no Ambulatório Médico SUEESSOR, em Osasco, com agenda facilitada e acesso a laboratórios parceiros para exames com descontos.'),
        ],
        'gallery': [
            {'src':'/static/clinica-medica/1.jpg','alt':'Ambulatório Médico SUEESSOR — foto 1','caption':'Ambulatório Médico SUEESSOR • estrutura de atendimento e acolhimento'},
            {'src':'/static/clinica-medica/10.jpg','alt':'Ambulatório Médico SUEESSOR — foto 2','caption':'Ambulatório Médico SUEESSOR • estrutura de atendimento e acolhimento'},
            {'src':'/static/clinica-medica/12.jpg','alt':'Ambulatório Médico SUEESSOR — foto 3','caption':'Ambulatório Médico SUEESSOR • estrutura de atendimento e acolhimento'},
            {'src':'/static/clinica-medica/13.jpg','alt':'Ambulatório Médico SUEESSOR — foto 4','caption':'Ambulatório Médico SUEESSOR • estrutura de atendimento e acolhimento'},
            {'src':'/static/clinica-medica/14.jpg','alt':'Ambulatório Médico SUEESSOR — foto 5','caption':'Ambulatório Médico SUEESSOR • estrutura de atendimento e acolhimento'},
            {'src':'/static/clinica-medica/15.jpg','alt':'Ambulatório Médico SUEESSOR — foto 6','caption':'Ambulatório Médico SUEESSOR • estrutura de atendimento e acolhimento'},
            {'src':'/static/clinica-medica/16.jpg','alt':'Ambulatório Médico SUEESSOR — foto 7','caption':'Ambulatório Médico SUEESSOR • estrutura de atendimento e acolhimento'},
            {'src':'/static/clinica-medica/17.jpg','alt':'Ambulatório Médico SUEESSOR — foto 8','caption':'Ambulatório Médico SUEESSOR • estrutura de atendimento e acolhimento'},
            {'src':'/static/clinica-medica/18.jpg','alt':'Ambulatório Médico SUEESSOR — foto 9','caption':'Ambulatório Médico SUEESSOR • estrutura de atendimento e acolhimento'},
            {'src':'/static/clinica-medica/2.jpg','alt':'Ambulatório Médico SUEESSOR — foto 10','caption':'Ambulatório Médico SUEESSOR • estrutura de atendimento e acolhimento'},
            {'src':'/static/clinica-medica/4.jpg','alt':'Ambulatório Médico SUEESSOR — foto 11','caption':'Ambulatório Médico SUEESSOR • estrutura de atendimento e acolhimento'},
            {'src':'/static/clinica-medica/7.jpg','alt':'Ambulatório Médico SUEESSOR — foto 12','caption':'Ambulatório Médico SUEESSOR • estrutura de atendimento e acolhimento'},
            {'src':'/static/clinica-medica/8.jpg','alt':'Ambulatório Médico SUEESSOR — foto 13','caption':'Ambulatório Médico SUEESSOR • estrutura de atendimento e acolhimento'},
        ],
        'gallery_interval': 5000,
        'dependent_rights':[
            'Consulta médica gratuita, exceto na especialidade de psicologia (R$ 40,00 por consulta, sujeito a alterações).',
            'Atendimento odontológico básico gratuito.',
            'Descontos nos exames de laboratório e de imagem.',
        ],
        'specialties':['Cardiologista','Clínico Geral','Dentista (em Osasco e Itapevi)','Dermatologista','Endocrinologista','Geriatria','Ginecologista','Neurologista','Oftalmologista','Ortopedista','Pediatra','Psicólogo','Urologista'],
        'exam_partners':[
            {
                'title':'Exames laboratoriais — Alphaclin',
                'description':'Descontos exclusivos em exames laboratoriais para associados e dependentes.',
                'address':'Rua Salem Bechara, nº 143, Centro, Osasco – SP',
                'contact':'(11) 2284-5566 / (11) 95453-4174 (WhatsApp)',
                'cta':'https://www.alphaclin.com.br/',
                'cta_label':'Visitar site da Alphaclin'
            },
            {
                'title':'Exames de imagem — Sabin Diagnóstico e Saúde',
                'description':'Exames de imagem nas unidades de Alphaville/Barueri e Osasco. É necessário estar com o pedido médico carimbado pelo SUEESSOR em mãos.',
                'address':'Unidades Alphaville/Barueri e Osasco',
                'contact':'Agendamento: (11) 4195-1679',
                'cta':'https://www.sabin.com.br/',
                'cta_label':'Conhecer o Sabin'
            },
        ],
        'address':'Rua General Bittencourt, 622 – Centro – Osasco / São Paulo',
        'hours':'De segunda a sexta, das 08h00 às 17h00',
        'phone_display':'(11) 4557-7240 • (11) 3681-0780', 'phone_href':'https://wa.me/551145577240',
        'source':'https://sueessor.org.br/clinica-medica/',
    },
    'espaco-para-eventos': {
        'title':'Espaço para Eventos', 'tag':'Salão de festas', 'icon':'calendar',
        'heading':'Um lugar especial para os encontros e celebrações de nossos associados.',
        'intro':'O Salão de Festas do SUEESSOR está disponível para a realização dos eventos de associados e seus dependentes. O espaço disponibiliza mesas e cadeiras, ar condicionado, iluminação, aparelhos sonoros, cozinha e freezer.',
        'highlights':[
            ('Estrutura para celebrações','Mesas, cadeiras, ar condicionado e iluminação.'),
            ('Aparelhos e apoio','Aparelhos sonoros, cozinha e freezer para auxiliar na realização dos eventos.'),
            ('Reservas','Entre em contato pelo telefone (11) 3652-3390 ou pelo WhatsApp (11) 94182-5124 e fale com Kátia ou Noêmia.'),
        ],
        'amenities':['Mesas e cadeiras','Ar condicionado','Iluminação','Aparelhos sonoros','Cozinha','Freezer'],
        'gallery':[
            {'src':'/static/espaco-para-eventos/1.webp','alt':'Vista ampla do salão de festas, palco e mesas com cadeiras'},
            {'src':'/static/espaco-para-eventos/DSCN4698.webp','alt':'Área do salão com mesas e cadeiras organizadas'},
            {'src':'/static/espaco-para-eventos/DSCN4705.webp','alt':'Salão preparado com mesas para confraternização'},
            {'src':'/static/espaco-para-eventos/DSCN4703.webp','alt':'Visão do salão e dos equipamentos de iluminação'},
            {'src':'/static/espaco-para-eventos/2.webp','alt':'Equipamentos de iluminação e climatização do salão'},
            {'src':'/static/espaco-para-eventos/DSCN4700.webp','alt':'Mesa com aparelhos sonoros do espaço para eventos'},
        ],
        'gallery_interval':5000,
        'address':'Rua General Bittencourt, 582 – Centro – Osasco/SP',
        'hours':'Reservas mediante consulta',
        'phone_display':'(11) 3652-3390', 'phone_href':'tel:+551136523390',
        'whatsapp_display':'(11) 94182-5124', 'whatsapp_href':'https://wa.me/5511941825124',
        'reservation_contacts':'Kátia / Noêmia',
        'source':'https://sueessor.org.br/espaco-para-eventos/',
    },
    'espaco-gourmet': {
        'title':'Espaço Gourmet', 'tag':'Lazer e encontros', 'icon':'utensils',
        'heading':'Um espaço para celebrar, reunir a família e aproveitar bons momentos.',
        'intro':'O Espaço Gourmet do SUEESSOR está disponível para a realização dos eventos de ASSOCIADOS e seus dependentes. Conta com uma estrutura composta de churrasqueira, forno de pizza, mesas de pebolim e ping-pong.',
        'highlights':[
            ('Gastronomia','Churrasqueira e forno de pizza para os encontros e confraternizações.'),
            ('Lazer','Mesas de pebolim e ping-pong disponíveis no espaço.'),
            ('Reservas','Mais informações pelo telefone (11) 3652-3390 ou pelo WhatsApp (11) 94182-5124. Falar com Kátia ou Noêmia.'),
        ],
        'amenities':['Churrasqueira','Forno de pizza','Mesa de pebolim','Mesa de ping-pong'],
        'gallery':[
            {'src':'/static/espaco-gourmet/espaco-gourmet-07.webp','alt':'Cozinha, forno de pizza e freezer do Espaço Gourmet'},
            {'src':'/static/espaco-gourmet/espaco-gourmet-02.webp','alt':'Mesa de ping-pong e ambiente de jogos do Espaço Gourmet'},
            {'src':'/static/espaco-gourmet/espaco-gourmet-04.webp','alt':'Mesa de pebolim do Espaço Gourmet'},
            {'src':'/static/espaco-gourmet/espaco-gourmet-05.webp','alt':'Área de convivência e jogos do Espaço Gourmet'},
            {'src':'/static/espaco-gourmet/espaco-gourmet-01.webp','alt':'Foto do forno de pizza e churrasqueira do Espaço Gourmet'},
            {'src':'/static/espaco-gourmet/espaco-gourmet-03.webp','alt':'Acesso e corredor interno do Espaço Gourmet'},
            {'src':'/static/espaco-gourmet/espaco-gourmet-06.webp','alt':'Área de circulação do Espaço Gourmet'},
        ],
        'gallery_interval':5000,
        'address':'Rua General Bittencourt, 582 – Centro – Osasco/SP',
        'hours':'Reservas mediante consulta',
        'phone_display':'(11) 3652-3390', 'phone_href':'tel:+551136523390',
        'whatsapp_display':'(11) 94182-5124', 'whatsapp_href':'https://wa.me/5511941825124',
        'reservation_contacts':'Kátia / Noêmia',
        'source':'https://sueessor.org.br/espaco-gourmet/',
    },
    'excursoes': {
        'title':'Excursões', 'tag':'Viagens e lazer', 'icon':'bus',
        'heading':'Tempo de descanso, novas experiências.',
        'intro':'O SUEESSOR divulga excursões e atividades de lazer para os trabalhadores. Os destinos e pacotes dependem da programação vigente.',
        'highlights':[
            ('Destinos divulgados','O histórico de excursões no portal oficial inclui Lambari (MG) e Ilha Morena.'),
            ('Programação','As datas disponíveis são divulgadas pelo sindicato. Não há viagem confirmada nesta página.'),
            ('Inscrições','Consulte vagas, transporte, hospedagem, valores e condições antes de reservar.'),
        ],
        'address':'Informações na sede: Rua General Bittencourt, 582 – Centro – Osasco/SP',
        'hours':'Datas a confirmar',
        'phone_display':'(11) 3652-3390', 'phone_href':'tel:+551136523390',
        'source':'https://sueessor.org.br/excursoes/',
    },
    'salao-de-beleza': {
        'title':'Salão de Beleza', 'tag':'Bem-estar e autoestima', 'icon':'scissors',
        'heading':'SPAÇO BELEZA SUEESSOR — cuidado e bem-estar para a categoria.',
        'intro':'O SPAÇO BELEZA SUEESSOR oferece aos trabalhadores serviços de manicure, depilação, designer de sobrancelha e cabeleireiro unissex. Associados e seus dependentes legais contam com valores diferenciados em todos os serviços, realizados por profissionais qualificados.',
        'gallery': [
            {'src':'/static/salao-de-beleza/foto-01.jpg', 'alt':'Ambiente de atendimento com maca e toalha identificada com o SUEESSOR'},
            {'src':'/static/salao-de-beleza/foto-02.jpg', 'alt':'Salão de beleza SUEESSOR com cadeiras, espelhos e área de espera'},
        ],
        'gallery_interval':5000,
        'beauty_services':['Manicure','Depilação','Designer de sobrancelha','Cabeleireiro unissex'],
        'highlights':[
            ('Atendimento aos associados','Os associados ao SUEESSOR, assim como seus dependentes legais, têm acesso a valores diferenciados em todos os serviços disponíveis.'),
            ('Profissionais de beleza','Serviços de manicure, depilação, designer de sobrancelha e cabeleireiro unissex oferecidos por profissionais qualificados.'),
            ('Agendamento','Atendimento de segunda a sexta-feira, das 08h00 às 17h00. Agende diretamente pelo telefone da entidade.'),
        ],
        'address':'Rua General Bittencourt, 582 – Centro – Osasco/SP',
        'hours':'De segunda a sexta-feira, das 08h00 às 17h00',
        'phone_display':'(11) 3652-3390', 'phone_href':'tel:+551136523390',
        'source':'https://sueessor.org.br/beleza/',
    },
    'tratamento-odontologico': {
        'title':'Tratamento Odontológico', 'tag':'Saúde bucal', 'icon':'smile',
        'heading':'Cuidado com o sorriso dos trabalhadores desde 2002.',
        'intro':'Desde sua fundação, em 2002, o SUEESSOR disponibiliza em sua sede um consultório odontológico moderno e equipado para a realização de tratamento básico e gratuito dedicado aos trabalhadores. Exclusivamente para os associados, esse atendimento se estende aos dependentes legais.',
        'highlights':[
            ('Tratamento básico gratuito','O SUEESSOR oferece tratamento odontológico básico gratuito aos trabalhadores, de acordo com as regras de acesso ao benefício.'),
            ('Dependentes legais','Para os associados, o tratamento básico também é oferecido aos seus dependentes legais.'),
            ('Unidades em Osasco e Itapevi','Os atendimentos são realizados no Ambulatório Médico SUEESSOR em Osasco e no consultório do Dr. Maurício R. Rodrigues em Itapevi.'),
        ],
        'address':'Osasco: Rua General Bittencourt, 622 • Itapevi: Avenida Cesário de Abreu, 60',
        'hours':'Atendimento mediante agendamento',
        'phone_display':'(11) 4557-7240', 'phone_href':'tel:+551145577240',
        'whatsapp_href':'https://wa.me/551145577240',
        'source':'https://sueessor.org.br/tratamento-odontologico/',
    },
}

# Unidades odontológicas: endereços, mapas e imagens oficiais do portal SUEESSOR.
DENTAL_UNITS = [{'city': 'Osasco', 'name': 'Ambulatório Médico SUEESSOR — Cuidando de Quem Cuida', 'address': 'Rua General Bittencourt, 622, Centro, Osasco – SP', 'map_search': 'Rua General Bittencourt, 622, Centro, Osasco, SP, Brasil', 'photo': 'https://sites.diretasistemas.com.br/sites/1955/wp-content/uploads/2025/10/30113309/unidade-osasco-350x150-1.png', 'photo_alt': 'Foto de um consultório odontológico com cadeira, equipamentos e bancada na unidade de Osasco, publicada pelo SUEESSOR', 'image_type': 'Foto do consultório', 'map_embed': 'https://www.google.com/maps?q=Rua%20General%20Bittencourt%2C%20622%2C%20Centro%2C%20Osasco%2C%20SP%2C%20Brasil&output=embed', 'map_link': 'https://www.google.com/maps/search/?api=1&query=Rua%20General%20Bittencourt%2C%20622%2C%20Centro%2C%20Osasco%2C%20SP%2C%20Brasil'}, {'city': 'Itapevi', 'name': 'Consultório Odontológico Dr. Maurício R. Rodrigues', 'address': 'Avenida Cesário de Abreu, 60, Centro, Itapevi – SP', 'map_search': 'Avenida Cesário de Abreu, 60, Centro, Itapevi, SP, Brasil', 'photo': 'https://sites.diretasistemas.com.br/sites/1955/wp-content/uploads/2025/10/30113331/whatsapp-image-2024-03-11-at-16-22-41-350x150-1.jpeg', 'photo_alt': 'Identidade visual do Consultório Odontológico Dr. Maurício R. Rodrigues publicada pelo SUEESSOR', 'image_type': 'Identidade visual divulgada pelo sindicato — foto do imóvel não disponibilizada', 'map_embed': 'https://www.google.com/maps?q=Avenida%20Ces%C3%A1rio%20de%20Abreu%2C%2060%2C%20Centro%2C%20Itapevi%2C%20SP%2C%20Brasil&output=embed', 'map_link': 'https://www.google.com/maps/search/?api=1&query=Avenida%20Ces%C3%A1rio%20de%20Abreu%2C%2060%2C%20Centro%2C%20Itapevi%2C%20SP%2C%20Brasil'}]

LAMBARI_PHOTOS = [{'src': '/static/excursoes/lambari/01.webp', 'alt': 'Lambari, Minas Gerais — foto 1'}, {'src': '/static/excursoes/lambari/02.webp', 'alt': 'Lambari, Minas Gerais — foto 2'}, {'src': '/static/excursoes/lambari/03.webp', 'alt': 'Lambari, Minas Gerais — foto 3'}, {'src': '/static/excursoes/lambari/04.webp', 'alt': 'Lambari, Minas Gerais — foto 4'}, {'src': '/static/excursoes/lambari/05.webp', 'alt': 'Lambari, Minas Gerais — foto 5'}, {'src': '/static/excursoes/lambari/06.webp', 'alt': 'Lambari, Minas Gerais — foto 6'}, {'src': '/static/excursoes/lambari/07.webp', 'alt': 'Lambari, Minas Gerais — foto 7'}, {'src': '/static/excursoes/lambari/08.webp', 'alt': 'Lambari, Minas Gerais — foto 8'}]
ILHA_MORENA_PHOTOS = [{'src': '/static/excursoes/ilha-morena/01.webp', 'alt': 'Ilha Morena, imagens do hotel e entorno — foto 1'}, {'src': '/static/excursoes/ilha-morena/02.webp', 'alt': 'Ilha Morena, imagens do hotel e entorno — foto 2'}, {'src': '/static/excursoes/ilha-morena/03.webp', 'alt': 'Ilha Morena, imagens do hotel e entorno — foto 3'}, {'src': '/static/excursoes/ilha-morena/04.webp', 'alt': 'Ilha Morena, imagens do hotel e entorno — foto 4'}, {'src': '/static/excursoes/ilha-morena/05.webp', 'alt': 'Ilha Morena, imagens do hotel e entorno — foto 5'}, {'src': '/static/excursoes/ilha-morena/06.webp', 'alt': 'Ilha Morena, imagens do hotel e entorno — foto 6'}, {'src': '/static/excursoes/ilha-morena/07.webp', 'alt': 'Ilha Morena, imagens do hotel e entorno — foto 7'}, {'src': '/static/excursoes/ilha-morena/08.webp', 'alt': 'Ilha Morena, imagens do hotel e entorno — foto 8'}, {'src': '/static/excursoes/ilha-morena/09.webp', 'alt': 'Ilha Morena, imagens do hotel e entorno — foto 9'}, {'src': '/static/excursoes/ilha-morena/10.webp', 'alt': 'Ilha Morena, imagens do hotel e entorno — foto 10'}]

EXCURSION_DESTINATIONS = [
    {
        'slug': 'lambari',
        'title': 'Lambari, Minas Gerais',
        'label': 'Natureza e águas minerais',
        'description': 'A cidade de Lambari é conhecida por suas belezas naturais, clima e fontes de água mineral. Segundo a apresentação histórica do destino, suas águas minerais teriam sido consideradas no passado a terceira melhor do mundo. São descritas sete fontes, com destaque para as de números 1 e 2, apontadas nessa divulgação como a maior fonte de água mineral naturalmente gasosa do mundo. Relatos antigos sobre supostas propriedades curativas não representam comprovação de eficácia médica.',
        'includes': ['Transporte', 'Hospedagem', 'Refeição completa'],
        'schedule': 'Saída às 14h00 e retorno às 17h00, conforme informação do passeio divulgado anteriormente. Datas a confirmar com o sindicato.',
        'meeting_place': 'Rua General Bittencourt, 582 — Centro, Osasco/SP',
        'notice': 'Programação de referência: confirme novas datas, valores e disponibilidade.',
        'gallery': LAMBARI_PHOTOS,
    },
    {
        'slug': 'ilha-morena',
        'title': 'Ilha Morena',
        'label': 'Viagem e lazer',
        'description': 'A excursão divulgada pelo SUEESSOR para Ilha Morena incluía transporte, hospedagem e refeição completa. A programação original indicava vagas limitadas e atendimento aos associados interessados por telefone ou WhatsApp.',
        'includes': ['Transporte', 'Hospedagem', 'Refeição completa'],
        'schedule': 'Programação anterior: saída às 21h00 de 22 de novembro de 2024 e retorno às 17h00 de 24 de novembro de 2024.',
        'meeting_place': 'Sede do SUEESSOR — Rua General Bittencourt, 582 — Centro, Osasco/SP',
        'notice': 'Evento de novembro de 2024 encerrado. Consulte o sindicato sobre novas excursões.',
        'gallery': ILHA_MORENA_PHOTOS,
    },
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
    if kind == 'beneficios':
        return render(request,'benefits.html',page='servicos',benefits=BENEFIT_CARDS)
    if kind == 'parcerias':
        return render(request,'partnerships.html',page='servicos',partnerships=PARTNERSHIP_CARDS)
    if kind == 'excursoes':
        return render(request,'excursions.html',page='servicos',destinations=EXCURSION_DESTINATIONS,benefits=BENEFIT_CARDS)
    if kind == 'tratamento-odontologico':
        return render(request,'dental.html',page='servicos',detail=BENEFIT_DETAILS[kind],benefits=BENEFIT_CARDS,slug=kind,units=DENTAL_UNITS)
    if kind in BENEFIT_DETAILS:
        return render(request,'benefit_detail.html',page='servicos',detail=BENEFIT_DETAILS[kind],benefits=BENEFIT_CARDS,slug=kind)
    if kind == 'juridico':
        return render(request,'services.html',page='servicos',kind=kind)
    raise HTTPException(404)

@app.get('/servicos/parcerias/{slug}', response_class=HTMLResponse)
def partnership_detail(request:Request,slug:str):
    if slug not in PARTNERSHIP_DETAILS:
        raise HTTPException(404)
    card = next(card for card in PARTNERSHIP_CARDS if card['slug'] == slug)
    if slug == 'beleza':
        return render(request,'partnership_beauty.html',page='servicos',partnership=card,
                      partners=BEAUTY_PARTNERS,partnerships=PARTNERSHIP_CARDS)
    if slug == 'clubes':
        return render(request,'partnership_clubs.html',page='servicos',partnership=card,
                      clubs=CLUB_PARTNERS,partnerships=PARTNERSHIP_CARDS)
    if slug == 'cursos':
        return render(request,'partnership_courses.html',page='servicos',partnership=card,
                      courses=COURSE_PARTNERS,partnerships=PARTNERSHIP_CARDS)
    if slug == 'parques':
        return render(request,'partnership_parks.html',page='servicos',partnership=card,
                      parks=PARK_PARTNERS,partnerships=PARTNERSHIP_CARDS)
    if slug == 'produtos-e-servicos':
        return render(request,'partnership_products.html',page='servicos',partnership=card,
                      products=PRODUCT_SERVICE_PARTNERS,partnerships=PARTNERSHIP_CARDS)
    if slug == 'saude':
        return render(request,'partnership_health.html',page='servicos',partnership=card,
                      partners=HEALTH_PARTNERS,partnerships=PARTNERSHIP_CARDS)
    if slug == 'viagens-e-turismo':
        return render(request,'partnership_travel.html',page='servicos',partnership=card,
                      travel_partners=TRAVEL_PARTNERS,partnerships=PARTNERSHIP_CARDS)
    return render(request, 'partnership_detail.html',page='servicos',
                  partnership=card,detail=PARTNERSHIP_DETAILS[slug],partnerships=PARTNERSHIP_CARDS)

@app.get('/documentos/{kind}', response_class=HTMLResponse)
def document(request:Request,kind:str):
    options={'editais':('Editais','https://sueessor.org.br/editais/'), 'acordos':('Modelos de acordo','https://sueessor.org.br/modelos-de-acordo/'), 'oposicao':('Modelo de oposição','https://sueessor.org.br/modelo-de-oposicao/'), 'financeiro':('Emissão de boletos','https://sueessor.org.br/emissao-de-boleto/'), 'aplicativo':('Aplicativo SUEESSOR','https://sueessor.org.br/aplicativo/')}
    if kind not in options: raise HTTPException(404)
    if kind == 'editais':
        return render(request, 'editals.html', page='convencoes',
                      documents=EDITAL_DOCS, years=EDITAL_YEARS, grouped=EDITAL_BY_YEAR,
                      names=EDITAL_NAMES)
    if kind == 'acordos':
        return render(request, 'agreements.html', page='convencoes', models=AGREEMENT_MODELS)
    if kind == 'financeiro':
        return render(request, 'finance.html', page='convencoes')
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
