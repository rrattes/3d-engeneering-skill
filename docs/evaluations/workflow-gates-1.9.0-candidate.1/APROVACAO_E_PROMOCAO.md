# Aprovação e promoção — CAD3D / 3d-engineering 1.9.0

## Decisão

Em 19/10/2026, o usuário aprovou explicitamente a promoção: **“Promova a 1.9 pois a 1.8 é inútil pra mim”.** A versão 1.9.0 passa a ser a referência local ativa do workspace. A 1.8.0 fica apenas preservada para recuperação histórica e rollback.

## Ativação local

- Fonte ativa: `/home/rrattes/Documentos/engineering 3d/3d-engineering-evolution-20261019/`.
- Skill Codex: `/home/rrattes/.agents/skills/3d-engineering` → `skills/3d-engineering` da fonte 1.9.0.
- CLI: `/home/rrattes/.local/bin/cad3d` → `scripts/cad3d` da fonte 1.9.0.
- Runtime CAD: `cad3d-engineering:1.9.0`.
- Imagem local: `sha256:e8e3af356c82877a10317a4e915f543e0fc9b8c970576ba9f1b9624fb98539f2`.
- Orca preservado: `cad3d-orca:2.4.2-cad3d.1.4.2`.
- Kit portátil: `dist/cad3d-1.9.0/CAD3D_Kit.zip`, 310312 bytes.
- SHA256 do kit: `9e55a633d3fb5fc8c77c797ed93aab59ddccf496a1260419720b158f1715895a`.

## Evidências

- Suíte completa fonte: 30/30 PASS, `source_frozen: true`, imagem CAD 1.9.0.
- Suíte completa empacotada: 30/30 PASS, `source_frozen: true`, mesma imagem.
- Aceitação legada V1.4: 35/35 PASS com a CLI e runtime 1.9.0.
- `cad3d doctor`: PASS, CAD3D 1.9.0 e render headless disponível.
- `test-portable-kit.py`: PASS; manifesto e inventário do ZIP conferidos pelo empacotador.
- Evidências detalhadas em `promoted-source/`, `promoted-packaged/` e `legacy-v1.4-promoted/` neste diretório.
- O controle negativo que representa o defeito OceanTech confirma que requisito crítico `NOT_EVALUATED` não pode ser escondido por WARNING menor disposto. O filtro AIO continua como exemplo positivo de montagem colorida, vista explodida e detalhe macho/fêmea; isso não equivale a validação física.

## Escopo e limites

A promoção valida o fluxo/plataforma em testes CAD de software; não valida fisicamente qualquer produto. Encaixe físico, carga, fluxo hidráulico, temperatura, durabilidade, impressão real e desempenho do aquário continuam dependentes de ensaios específicos. A imagem de montagem e a folga B-rep não substituem esses ensaios.

A ativação é local neste workspace e nas duas ligações globais indicadas; não houve publicação remota nem alteração dos arquivos da 1.8.0. A instalação anterior continua disponível para rollback em `3d-engineering-evolution-20261017/` e `cad3d-engineering:1.8.0`.
