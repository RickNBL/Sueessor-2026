# SUEESSOR — Portal moderno para os trabalhadores da saúde

Projeto de redesign funcional do portal institucional do **Sindicato Único dos Empregados em Estabelecimentos de Serviços de Saúde de Osasco e Região**. O projeto combina o clima de Conoxard/Econest das referências fornecidas com o `DESIGN.md` (verde vibrante, base branca, títulos escuros, botões arredondados, cartões macios, hierarquia tipográfica e responsividade), preservando as principais informações verificadas da instituição. O logotipo desenhado neste protótipo é **uma interpretação visual**, não um arquivo oficial.

## 1. Rodar localmente

É necessário **Python 3.11 ou superior** e acesso à internet para instalar as dependências na primeira execução.

```bash
cd sueessor-2026
python -m venv .venv
# macOS / Linux:
source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

**Edite `.env`** e escolha um usuário e uma **senha forte e única de pelo menos 14 caracteres**, sem deixar os valores de exemplo. A primeira execução inicializa a conta administrativa, o banco SQLite e três notícias editoriais de exemplo baseadas em matérias do portal oficial.

As variáveis precisam ser exportadas para o processo, pois o aplicativo não lê `.env` automaticamente:

```bash
# macOS / Linux: exporta as variáveis do arquivo .env
set -a; source .env; set +a
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Abra **http://127.0.0.1:8000**.

Para Windows, configure as mesmas variáveis de ambiente no PowerShell antes de executar `uvicorn` ou utilize Docker Compose.

### Docker Compose

```bash
cp .env.example .env
# edite a senha antes de executar
docker compose up --build -d
```

O site ficará disponível em **http://127.0.0.1:8000**. Os volumes `sueessor_data` e `sueessor_uploads` armazenam banco e mídias entre reinicializações. Para hospedar publicamente, configure domínio, **HTTPS**, cópias de segurança e um reverse proxy adequado (Nginx/Caddy/Cloudflare). `compose.yaml` publica apenas em localhost por segurança.

## 2. Área administrativa reservada

A URL de acesso foi intencionalmente omitida da navegação pública:

**`/central-restrita/entrar`**

A rota não é a proteção: a autenticação real ocorre no servidor. O login utiliza senha com `scrypt` e salt por usuário, sessão aleatória com token armazenado como SHA-256, cookie `HttpOnly`/`SameSite=Strict`, expiração de 12 horas, proteção CSRF, limite de tentativas e autorização antes de criar, alterar, excluir ou enviar mídias. A aplicação **não contém credenciais padrão**.

Depois do primeiro login, você pode:

- Criar posts com **título**, **resumo/descrição**, **texto completo** e **categoria**.
- **Publicar** imediatamente ou salvar como **rascunho**.
- **Editar**, **excluir** e consultar os posts existentes.
- Enviar **imagem de capa** e galeria (imagens locais são inspecionadas, redimensionadas e recriadas em JPEG).
- Adicionar **vídeos** enviados (MP4/WebM, limite 80 MB) ou **YouTube/Vimeo**.
- Adicionar um **endereço/local** que abre no Google Maps e aparece como mapa incorporado na matéria.
- Ler e excluir **mensagens e denúncias** recebidas pelo formulário público.

Os uploads de imagem têm limite de **10 MB por arquivo**. O banco é SQLite para uma implantação simples; é possível evoluir para PostgreSQL e armazenamento de mídia em S3, R2 ou equivalente.

**Importante:** para ambiente HTTPS defina `SESSION_COOKIE_SECURE=true` em `.env` e reinicie. Mantenha `false` apenas em desenvolvimento HTTP local. Se a conta administrativa já foi inicializada, mudar a senha no `.env` **não** altera a senha existente. Implemente um procedimento de recuperação/rotação supervisionado antes de liberar o portal à produção; não apague o banco para trocar a senha, pois ele contém as notícias.

## 3. Páginas e funcionalidades

| Rota | Finalidade |
| --- | --- |
| `/` | Home moderna, blocos interativos, conquistas, abrangência e últimas notícias |
| `/sobre`, `/abrangencia`, `/diretoria` | História, municípios de atuação e representantes |
| `/convencoes` | Convenções e acesso ao acervo oficial |
| `/servicos/beneficios`, `/servicos/parcerias`, `/servicos/juridico` | Serviços aos trabalhadores |
| `/associe-se` | Benefícios da sindicalização e acesso seguro ao serviço oficial de filiação |
| `/documentos/editais`, `/documentos/acordos`, `/documentos/oposicao`, `/documentos/financeiro`, `/documentos/aplicativo` | Documentos e ferramentas oficiais |
| `/imprensa/artigos`, `/imprensa/notas`, `/imprensa/galeria`, `/imprensa/revistas`, `/imprensa/jornal`, `/imprensa/videos` | Acesso ao acervo de comunicação da entidade |
| `/noticias` | Feed responsivo de notícias em estilo social, com busca, filtros, curtir/salvar no dispositivo e compartilhamento |
| `/noticias/<slug>` | Matéria completa, galeria, vídeo, mapa e fonte original |
| `/contato`, `/denuncie` | Formulários com opção de anonimato para denúncias, consentimento e caixa de entrada privativa |
| `/central-restrita/entrar` | Login não anunciado no menu |
| `/central-restrita/painel` | Gestão de notícias e mensagens; exige sessão |

Outras interações: menu responsivo, dropdowns, cards animados, WhatsApp flutuante, busca global em páginas/notícias com **Ctrl+K / Cmd+K**, feedback de envio e ajustes para `prefers-reduced-motion`. Curtidas e salvamentos são **locais ao dispositivo**; não há contadores públicos, contas de leitores ou comentários, e nenhum engajamento é inventado.

## 4. Informações preservadas e fontes

Levantamento das páginas públicas em **16 de outubro de 2026**:

- História/fundação: <https://sueessor.org.br/sueessor/>
- Abrangência (13 municípios): <https://sueessor.org.br/abrangencia/>
- Diretoria: <https://sueessor.org.br/diretoria/>
- Benefícios: <https://sueessor.org.br/beneficios/>
- Parcerias: <https://sueessor.org.br/parcerias/>
- Jurídico: <https://sueessor.org.br/fale-com-o-juridico/>
- Convenções: <https://sueessor.org.br/convencoes-coletivas/>
- Filiação: <https://sueessor.org.br/fique-socio/>
- Documentos/imprensa: <https://sueessor.org.br/editais/>, <https://sueessor.org.br/artigos/>
- Matérias iniciais: notícias de 08, 13 e 14 de outubro de 2026 no portal oficial, com links de atribuição em cada artigo.

**Dados oficiais na interface:** fundação em 12/04/2002, 13 cidades atendidas, sede na Rua General Bittencourt 582 em Osasco, horário comercial de segunda a sexta das 8h às 17h, telefone (11) 3685-4882, WhatsApp (11) 3652-3390, canal jurídico (11) 94182-5124. Cargos e nomes refletem a relação publicada na data da pesquisa.

**O que é uma migração parcial:** o portal histórico tem muito mais notícias, galerias, documentos e materiais. A versão entregue inclui **páginas institucionais essenciais, uma seleção de três notícias resumidas e atribuídas e links oficiais para arquivos e conteúdos não migrados**. O conjunto integral de imagens, PDFs, logotipos, cores originais e posts **não foi copiado**; é necessário acesso autorizado ao acervo/WordPress e revisão editorial para uma migração completa e fiel. Os textos das matérias iniciais foram reescritos em síntese, não copiados integralmente.

**Imagens:** três imagens de notícias são carregadas diretamente do servidor público da entidade; duas fotografias de destaque utilizam URLs externas do Unsplash, com arte vetorial de fallback. Antes de lançar oficialmente, confirme a autorização de uso e substitua os URLs externos por arquivos licenciados e hospedados na infraestrutura do sindicato. Links de terceiros podem deixar de funcionar. A marca atual do SUEESSOR usa elementos vermelhos; o novo layout adota predominantemente o verde pedido nas referências, preservando uma referência ao vermelho no símbolo tipográfico.

## 5. Segurança, LGPD e publicação

O protótipo é funcional para desenvolvimento e testes, porém a publicação de um site sindical real **exige validação humana e operação adequada**, especialmente porque recebe denúncias. Antes de abrir os formulários ao público:

1. Exigir **HTTPS**, monitoramento de tentativas e proteção adicional contra abuso (por exemplo, rate limiting compartilhado no proxy ou Redis). A limitação atual fica em memória por processo.
2. Adotar política de **privacidade, base legal, retenção e descarte**, acesso nominal dos operadores, revisão de consentimento e procedimento para incidentes conforme LGPD.
3. Manter o banco e os uploads em armazenamento privado, com **backup criptografado**, controle de acesso e atualização do servidor.
4. Avaliar criptografia dos relatos em repouso, autenticação multifator, auditoria de acesso e fluxo de resposta adequado para denúncias sensíveis.
5. Verificar direitos de uso de mídia, logotipo, nomes, conteúdo editorial, dispositivos de busca e integração com parceiros oficiais.
6. Revisar os textos e validar links, contatos, dados de dirigentes e documentos vigentes antes de substituir o site existente.

**Não implante isto como substituição automática do site atual sem autorização da entidade.**

## 6. Executar testes

```bash
pip install pytest httpx
pytest -q
```

Testes de integração cobrem navegação, criação e edição de posts, publicação/rascunho, proteção de sessão e CSRF, upload de imagens, denúncias e logout.

## 7. Stack

- **HTML5, CSS3 e JavaScript moderno:** interface visual e interações, com excelente desempenho sem dependência pesada de cliente.
- **Python + FastAPI:** backend moderno, validação de dados, sessões, API de conteúdo.
- **Jinja2:** templates reutilizáveis e renderização no servidor.
- **SQLite:** persistência e gestão editorial; preparado para evolução do armazenamento.
- **Pillow:** sanitização e otimização de imagens enviadas.
- **Docker Compose:** empacotamento e volumes persistentes.

O código permanece editável, modular, sem assinatura de plataforma ou custo de framework frontend. Se a operação passar a exigir múltiplos editores ou carga grande, é recomendada a migração para PostgreSQL, armazenamento de objetos e autenticação MFA.
