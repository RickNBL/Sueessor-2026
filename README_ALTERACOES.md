# Atualização da identidade visual — outubro de 2026

## O que foi feito

- Cor institucional utilizada no projeto: **`#BA0A0A`**. A sequência enviada (`#ba0a0`) contém cinco dígitos e não é um código hexadecimal CSS válido. Confirme se a cor pretendida era outra.
- Removida a barra superior do cabeçalho e eliminadas sobreposições com frases sobre fotos, contadores ornamentais nos cards e a observação técnica do rodapé.
- Destaque principal desde 12 de abril de 2002 e linha do tempo **interativa** com 2002, 2005, 2007 e hoje, botões anterior/próximo, navegação por teclado e preferência de movimento reduzido.
- Revisão de cores em home, feed, serviços, páginas internas, botões, ícones, áreas institucionais, rodapé, área administrativa e favicon.
- **CSS** customizado + classes de grade do **Bootstrap 5.3.6** (carregado pelo CDN do jsDelivr, com CSS de fallback para a linha do tempo).
- **TypeScript**: fonte `src/timeline.ts`, compilada para `static/timeline.js` e `public/static/timeline.js`. A Vercel carrega o JS compilado sem precisar instalar Node durante o deploy.
- **Rust**: módulo opcional de cálculo institucional em `rust/sueessor-timeline/`. O módulo foi escrito, mas **não foi compilado nem conectado à UI**; a experiência funciona plenamente no navegador com TypeScript.
- A área administrativa, o CMS, a sessão do servidor, as rotas, a busca e o feed permanecem no FastAPI original.

## Logo oficial pendente

**A imagem da logo foi exibida na conversa, mas o arquivo de imagem original não foi disponibilizado no diretório do projeto para inclusão no ZIP.** O cabeçalho, o rodapé e a área editorial estão preparados para mostrar a imagem **`static/logo-sueessor.svg`** (e a mesma cópia em `public/static/logo-sueessor.svg`). Enquanto esse arquivo não for adicionado, a interface apresenta o nome tipográfico SUEESSOR, sem inventar um emblema oficial. Para preservar a marca sem redesenhar, anexe o arquivo original em PNG ou SVG. Com ele, será possível copiar os bytes exatos da arte para `static/` e `public/static/`, atualizar as referências nas páginas e gerar um ZIP definitivo com a logo.

## Implantação na Vercel

1. Extraia o ZIP atualizado e faça commit de seu **conteúdo diretamente na raiz** do repositório conectado à Vercel. Não envie um ZIP como build para o projeto.
2. Confirme `vercel.json`, `app.py`, `requirements.txt`, `templates/` e `public/static/` na raiz.
3. Em Project Settings → Build and Deployment, Root Directory `./`, Framework Preset FastAPI, sem Build Command/Output Directory customizados. Faça Redeploy.
4. Se houver um arquivo logo oficial, coloque em **`static/` e `public/static/`** antes do deploy.
5. Para posts de notícias persistirem, mantenha a conexão **`DATABASE_URL`** (PostgreSQL), `ADMIN_USERNAME`, `ADMIN_PASSWORD` e, para uploads, `BLOB_READ_WRITE_TOKEN`. Veja `README_VERCEL.md`.

## Compilar TypeScript após alterações

```bash
npm install
npm run build:ts
cp static/timeline.js public/static/timeline.js
```

## Extensão Rust (opcional)

```bash
cd rust/sueessor-timeline
rustup target add wasm32-unknown-unknown
cargo test
cargo build --release --target wasm32-unknown-unknown
```

A integração com o JavaScript permanece opcional e requer implementação adicional. Não executá-la **não impede o funcionamento do portal**.

## Testes locais

```bash
pip install -r requirements.txt pytest httpx
python -m pytest -q tests/
uvicorn app:app --reload
```

**Atenção editorial:** nenhum deploy foi realizado na sua conta. Revise textos, imagens/licenças, LGPD, endereço e conteúdo antes do uso institucional oficial.
