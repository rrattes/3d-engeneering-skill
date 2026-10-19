# Resultados de aceitação

Aceitação original V1 executada em 2026-10-12 em Arch Linux host, container `cad3d-engineering:0.1.0` (`sha256:5b4dbb11b01a107828295295ad06bdac5e23d53186e2726e209000bb9cc749cb`, usuário interno `cad3d`). Resultados V1 mantidos como registro histórico.

| Teste | Resultado | Evidência |
|---|---|---|
| A — Ambiente | PASS | `cad3d doctor`: Python 3.12.8, build123d 0.11.1, OCP importável, smoke Box volume 24 mm³ |
| B — Modelagem | PASS | Duas peças parametrizadas (`body`, `lid`) construídas; comprimento alterado de 60 para 70 mm e recompilado |
| C — Geometria | PASS | B-reps válidos; body 13248 mm³ / 60×40×24 mm, lid 4920.72 mm³ / 60.6×40.6×2 mm; valores restaurados |
| D — Exportação | PASS | STEP reaberto com build123d e volumes válidos; STL reaberto com trimesh, `is_watertight=true` |
| E — Visualização | PASS | `preview.png`, PNG 1440×1120 gerado headless com Matplotlib/Agg e inspecionado visualmente |
| F — Impressão | PASS (envelope) | Ambos dentro de 251×251×251 mm após margem operacional 5 mm no perfil Bambu A1 |
| G — Skill Codex | PASS | `codex debug prompt-input` no root do repositório mostrou `3d-engineering` em `.agents/skills` e a descrição no conjunto de skills disponível |
| H — Reprodutibilidade | PASS (geométrica) | Build original repetido após variação/restauração produziu volumes e bounding boxes idênticos; arquivos binários podem conter variação de serialização |

`cad3d test`: 1 teste passou. CLI build executou validate, preview, report e reopen checks. Arquivos gerados:

- `examples/calibration-box/build/outputs/body.step`, `body.stl`
- `examples/calibration-box/build/outputs/lid.step`, `lid.stl`
- `examples/calibration-box/build/outputs/preview.png`
- `examples/calibration-box/build/outputs/validation.json`, `report.json`, `export-validation.json`, `manifest.json`

## Aceitação V1.1 — assemblies e validação mecânica

Executada em 2026-10-12 com a imagem `cad3d-engineering:1.1.0` (`sha256:63d16d85cbbac775a3eff22f7d4dd517ec4a5a8b899beb04754212fff2eb6484`; Python 3.12.8, build123d 0.11.1, OCP 7.9.3.1.1, Trimesh 4.6.8). Docker doctor: PASS. A imagem foi reconstruída sem alteração global do host. A skill passou `quick_validate.py` e foi carregada/seguida por `codex exec` através de `.agents/skills/3d-engineering`.

| Verificação | Resultado | Evidência |
|---|---|---|
| Suite de engenharia | PASS — 10 testes | Casos separados, colisão, contato declarado/omisso, folga, fit dimensional, parede nominal, orientação/envelope, colisão após transformação, STEP round-trip e entrada inválida |
| Regressão V1 | PASS — 11 testes | Projeto `examples/calibration-box`, incluindo as 10 verificações mecânicas e o teste original de peça |
| Assembly válido | PASS | Distância B-rep 0,300000 mm, mínimo declarado 0,250 mm, interseção 0 mm³; paredes declaradas 2,0 mm vs 1,2 mm mínimo parametrizado |
| Assembly deliberadamente incorreto | FAIL esperado | `VOLUMETRIC_COLLISION`, volume de interseção 4,500000 mm³; o comando `validate` retorna código 3 para bloquear aprovação |
| STEP/STL | PASS | Dois arquivos de peça exportados; STEP reaberto com sólidos válidos; STL watertight. Artefatos no diretório de saída do assembly-demo |
| Renderização | PASS | Prévia headless do assembly válido e da configuração colidida |
| Projeto V1 de template | PASS | `cad3d init`, `cad3d build` e `cad3d test`; 11 testes passaram sem exigir manifesto de assembly |

Comandos CLI usados: `doctor`, `build`, `validate`, `validate --assembly .cad3d/assembly-collision.yaml`, `render --assembly .cad3d/assembly-collision.yaml` e `test`.

Arquivos para revisar:

- Assembly válido: [validation.json](../examples/assembly-demo/build/outputs/validation.json), [report.json](../examples/assembly-demo/build/outputs/report.json), [preview.png](../examples/assembly-demo/build/outputs/preview.png), [datum_block.step](../examples/assembly-demo/build/outputs/datum_block.step), [datum_block.stl](../examples/assembly-demo/build/outputs/datum_block.stl), [slider.step](../examples/assembly-demo/build/outputs/slider.step), [slider.stl](../examples/assembly-demo/build/outputs/slider.stl).
- Assembly colidido: [validation-assembly-collision.json](../examples/assembly-demo/build/outputs/validation-assembly-collision.json) e [preview-assembly-collision.png](../examples/assembly-demo/build/outputs/preview-assembly-collision.png).

Limites da aceitação: a parede foi comparada como parâmetro nominal, não como medição geométrica da menor espessura. Faixas de encaixe e valores de printer profile seguem não calibrados. Não houve impressão física, solver cinemático, análise estrutural nem execução de slicer.
