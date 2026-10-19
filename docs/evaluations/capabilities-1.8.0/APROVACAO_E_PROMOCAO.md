# Aprovação e promoção — CAD3D / 3d-engineering 1.8.0

## Decisão

Em 17/10/2026, o usuário declarou: **“Aprovado e promovido. Documente e crie readme.md”.**
Fica registrada a aprovação da evolução 1.8.0 e sua promoção como referência local
para os próximos projetos, sobre a ativação técnica já realizada.

## Instalação promovida

- Fonte: `3d-engineering-evolution-20261017`, branch `evolution/20261017`.
- CLI: `/home/rrattes/.local/bin/cad3d` → `scripts/cad3d` dessa fonte.
- Skill: `/home/rrattes/.agents/skills/3d-engineering` → `skills/3d-engineering` dessa fonte.
- Runtime: `cad3d-engineering:1.8.0`.
- Imagem: `sha256:81ff095d899a294b16b58435622b2a16555ba5c45ff4e1f1c7d3613f818cfa4a`.
- Orca preservado: `cad3d-orca:2.4.2-cad3d.1.4.2`.

A aprovação humana e as evidências de execução são registros distintos.
O [relatório de incorporação](INCORPORACAO.md) descreve escopo, correções e limites;
o [manifesto técnico](EVIDENCIAS.json) conserva os resultados anteriores à aprovação.

## Base de evidências

- 27/27 entradas de regressão na fonte e 27/27 no runtime empacotado.
- 38 testes novos por modo; 35/35 controles legados.
- 24 módulos CLI coincidentes entre fonte e imagem; doctor ativo 1.8.0 PASS.
- Skill validada e kit com CRC e hashes de inventário conferidos.
- Artefatos STEP/STL e desenhos CAD efetivos em fixtures de software.

Kit: `dist/cad3d-1.8.0/CAD3D_Kit.zip`, 290315 bytes.
SHA256: `aa75e016e91e5cac6c327bfc299814f78c9cb1a64ac1b50581850e5f9ade993c`.
O pacote e o manifesto técnico permanecem com os hashes registrados. Esta aprovação
fica documentada separadamente, sem reempacotar o kit.

## Continuidade e limites

A imagem `cad3d-engineering:1.7.0` permanece preservada. Para reversão por execução,
selecionar `CAD3D_IMAGE=cad3d-engineering:1.7.0` e contratos compatíveis com essa versão.

A promoção não qualifica fisicamente produtos. A entrega original da cesta Rev C
permanece preservada, com suas pendências. Ensaios de encaixe, carga, calor,
durabilidade e fabricação dependem de cada briefing.

Este registro é documental: não acrescenta execução de regressões, ensaios físicos,
reconstrução da imagem, tag Git ou publicação remota. Os resultados citados são os
já registrados na avaliação técnica.

Ponto de entrada do workspace: [readme.md](../../../../readme.md).
