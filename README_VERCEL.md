# SUEESSOR — versão adaptada para Vercel

## Qual era o problema?

O pacote original tinha uma pasta-raiz extra e tentava inicializar SQLite e uploads no diretório do código. Na Vercel, o código implantado é somente leitura. Esta versão tem `app.py`, `templates/`, `static/`, `public/`, `requirements.txt` e `vercel.json` no nível raiz do ZIP. O FastAPI é detectado pela Vercel automaticamente.

## Publicar a prévia visual

1. **Extraia** o ZIP. Envie o **conteúdo interno** da pasta extraída para a **raiz do seu repositório GitHub** (não deixe `SUEESSOR_Vercel_corrigido/` como pasta extra, a menos que configure Root Directory no painel).
2. Em https://vercel.com/new importe esse repositório. Framework Preset: **FastAPI** (ou automático). Root Directory: **`./`**. Remova eventuais Build Command/Output Directory personalizados.
3. Clique em Deploy. Ao concluir, acesse a URL exibida. A home deve abrir, com notícias de demonstração.

Se você usa uma pasta própria dentro do repositório, configure **Settings → Build and Deployment → Root Directory** apontando para ela e faça novo deploy.

## Habilitar o painel e manter notícias

**Importante:** para que uma notícia, login e formulário não desapareçam entre reinicializações da função, é necessário adicionar PostgreSQL persistente.

1. No projeto Vercel, vá em **Storage / Marketplace** e conecte um banco PostgreSQL (por exemplo Neon).
2. Em **Settings → Environment Variables**, verifique se existe **`DATABASE_URL`** (a string Postgres começando com `postgresql://` ou `postgres://`); caso o provedor dê outro nome, configure `DATABASE_URL` para a URL de conexão apropriada, **sem publicar o valor no GitHub**.
3. Configure `ADMIN_USERNAME` e `ADMIN_PASSWORD` (senha exclusiva de **no mínimo 14 caracteres**), `SESSION_COOKIE_SECURE=true`.
4. Faça **Redeploy**, para que as variáveis entrem na implantação.
5. Abra **`/central-restrita/entrar`** no domínio implantado. A rota não aparece no menu. A autenticação é validada no servidor.

O usuário administrativo é criado somente se ainda não existir uma conta; mudar `ADMIN_PASSWORD` depois não altera automaticamente a senha já cadastrada no banco.

## Imagens e vídeos

Para envio de arquivos pequenos, crie um **Vercel Blob público** no Storage do projeto, com a variável `BLOB_READ_WRITE_TOKEN`. Faça Redeploy. O armazenamento é persistente. **O limite por requisição das funções da Vercel é 4,5 MB**: para vídeos grandes e imagens maiores, cole diretamente uma URL HTTPS (YouTube/Vimeo/MP4/WebM) no editor. O envio direto de vídeos de 80 MB exigirá um fluxo dedicado de upload do navegador ao Blob, não incluído nesta versão.

Sem Postgres, a Vercel mostra o portal público em **modo prévia** e bloqueia operações administrativas/formulários para evitar perda de conteúdo sensível ou notícias. Sem Blob, usar URLs externas de mídia continua funcionando.

## Teste rápido

- Home: `/` — deve carregar com status HTTP 200.
- Notícias: `/noticias` — cards, busca e filtros.
- Arquivos estáticos: `/static/style.css` e `/static/main.js` — resposta 200.
- Editor: `/central-restrita/entrar` — habilitado somente após configurar `DATABASE_URL` e usuário.

Não envie denúncias reais enquanto não revisar a conformidade LGPD, retenção, autenticação, logs e backups.

## Caso apareça erro ainda

Em **Vercel → Project → Deployments → último deploy → Logs/Functions**, copie o erro exato. Também confira as configurações de Root Directory. Envie o link `.vercel.app` e o erro para diagnóstico preciso.

> Esta versão foi preparada e testada localmente para o modo Vercel, mas não foi implantada na sua conta (não temos acesso à Vercel ou às suas credenciais).
