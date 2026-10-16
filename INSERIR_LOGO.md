# Inserção da logo oficial no SUEESSOR

O site já possui espaços reservados no cabeçalho, rodapé e painel administrativo para a logo SUEESSOR.

**Importante:** a imagem exibida nesta conversa não foi disponibilizada ao processo como arquivo físico, por isso não foi incluída no pacote. A marca **não** foi redesenhada, inventada ou substituída por outra.

## Como usar o arquivo original

- Caso tenha o arquivo **SVG**: copie para `static/logo-sueessor.svg` e `public/static/logo-sueessor.svg`. As referências HTML já apontam para esse caminho.
- Caso tenha o arquivo **PNG**: copie para `static/logo-sueessor.png` e `public/static/logo-sueessor.png`, e substitua `logo-sueessor.svg` por `logo-sueessor.png` em `templates/base.html`, `templates/admin_login.html` e `templates/admin.html`.
- Para o favicon, é possível adaptar o ícone da imagem original posteriormente.

Mantenha fundo transparente e evite recomprimir ou redesenhar a imagem. Depois, faça commit e novo deploy na Vercel.
