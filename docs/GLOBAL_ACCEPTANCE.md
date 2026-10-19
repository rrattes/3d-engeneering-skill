# Aceitação global fora do repositório

Executada em 2026-10-12 após instalar os links globais. A sessão foi iniciada com `codex exec --ephemeral --skip-git-repo-check --sandbox danger-full-access --cd "/tmp/cad3d codex acceptance.wILEY7"` em uma pasta temporária independente, contendo espaços. O prompt pediu normalmente uma peça paramétrica de calibração com furo, validação, STEP/STL, prévia e relatório; não mencionou o nome nem o caminho da skill.

## Evidência de descoberta e execução

- O primeiro comando CAD gerado pelo Codex leu `/home/rrattes/.agents/skills/3d-engineering/SKILL.md` automaticamente e em seguida verificou o diretório e `cad3d doctor`. A sessão foi nova e fora do checkout. Isso comprova seleção/uso nesta solicitação concreta; a seleção futura continua sendo contextual pelo Codex, guiada pela descrição da skill.
- `cad3d init .` concluiu no diretório novo. O starter foi substituído por uma peça genérica de calibração sem copiar biblioteca Python, Dockerfile ou imagem.
- `cad3d doctor`: `PASS`; Python 3.12.8, build123d 0.11.1, OCP 7.9.3.1.1, trimesh 4.6.8, NumPy 2.2.4 e SciPy 1.15.2.
- `cad3d build`, `cad3d validate`, `cad3d export`, `cad3d render` e `cad3d report` concluíram. A validação geométrica e o envelope de impressão deram `PASS`. STEP reaberto; STL watertight e malha conectada.
- Relatório conservou as classificações corretas: prontidão geral de fabricação e impressão física `NOT_EVALUATED`; a heurística de suporte ficou `WARNING`. Não se inferiu aprovação física a partir da geometria.
- Primeiro `cad3d test` apontou uma expectativa desatualizada do template após a troca de modelo. O Codex alinhou o teste para verificar o bloco configurado, seus limites, volume e furo passante. Reexecução: **11 passed**.
- Artefatos ficaram com proprietário `rrattes:rrattes`, modo `0644`, confirmando a execução com UID/GID do host.

## Artefatos da sessão

Raiz: `/tmp/cad3d codex acceptance.wILEY7`

- `src/model.py`, `.cad3d/params.yaml`, `.cad3d/project.yaml`, `README.md`
- `build/outputs/calibration_block.step` — 19.081 bytes
- `build/outputs/calibration_block.stl` — 26.084 bytes
- `build/outputs/preview.png` — 329.300 bytes
- `build/outputs/validation.json`, `report.json`, `manifest.json`, `export-validation.json`

A pasta temporária permanece disponível para inspeção. O log JSONL bruto da sessão foi gravado temporariamente em `/tmp/cad3d-codex-acceptance.jsonl` no host.

## Limites

A seleção automática foi demonstrada para este pedido normal específico, não é uma garantia para qualquer formulação. O modelo aceito ainda tem medidas configuráveis, perfil de partida não calibrado e impressão física não testada. A imagem foi reutilizada pela tag existente `cad3d-engineering:1.1.0` e digest `sha256:63d16d85cbbac775a3eff22f7d4dd517ec4a5a8b899beb04754212fff2eb6484`; a imagem não foi reconstruída nem duplicada.

Referência do Codex: [Skills — Codex](https://developers.openai.com/codex/skills), descoberta por diretório de usuário e links simbólicos.
