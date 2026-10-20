# Módulo Rust — uso opcional

A experiência visual entregue é implementada em **TypeScript** e funciona sem Rust na Vercel. Este módulo de cálculo de anos completos desde a fundação foi incluído como extensão de alto desempenho para futura integração via WebAssembly; **não é necessário nem compilado no deploy padrão**.

Se optar por ativar a extensão no futuro, instale Rust e o alvo `wasm32-unknown-unknown`, execute `cargo build --target wasm32-unknown-unknown --release`, copie o WASM gerado para `static/` e adicione o carregamento explícito no TypeScript. Não declare o módulo WASM como já integrado enquanto esse passo não tiver sido feito.
