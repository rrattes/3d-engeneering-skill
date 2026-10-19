# CAD3D Engineering — 1.9.0

> **Aprovada e promovida localmente em 19/10/2026.** A 1.8.0 permanece preservada
> em `../3d-engineering-evolution-20261017/` para rollback histórico.

**Aprovação 1.9.0:** [registro de promoção](docs/evaluations/workflow-gates-1.9.0-candidate.1/APROVACAO_E_PROMOCAO.md). A aprovação anterior da [1.8.0](docs/evaluations/capabilities-1.8.0/APROVACAO_E_PROMOCAO.md) é mantida como histórico.

Novas capacidades opcionais: interfaces paramétricas, movimentos compostos,
campanhas de variantes, calibração por medições, acesso/cabos, desenhos com cortes
e cotas e pré-dimensionamento de vigas declaradas. Novos comandos: interfaces,
drawings, variants, structure e calibration fit.
[Contratos/limites](skills/3d-engineering/references/general_capabilities.md) ·
[Evidências1.8.0](docs/evaluations/capabilities-1.8.0/INCORPORACAO.md).

Interferências compartilhadas entre sólidos reais de conjuntos importados, referências
geométricas por ponto com diagnóstico e cadeias lineares de tolerância de pior caso.
[Contratos](skills/3d-engineering/references/reliability.md) ·
[Evidências1.7.0](docs/evaluations/reliability-1.7.0/INCORPORACAO.md).

Movimento helicoidal incorporado ao contrato de manutenção: eixos mundiais arbitrários,
origem deslocada, passo/entradas, sentido, percurso assinado, amostragem e retirada
com pré-requisitos. Casos lineares anteriores mantidos. Base anterior 1.5.0 aprovada
pelo usuário; dependências CAD e Orca preservados.

[Contrato de uso](skills/3d-engineering/references/helical_motion.md) ·
[Entrega e evidências](docs/evaluations/helical-1.6.0/INCORPORACAO.md).

Histórico: [revisão 1.4.2](docs/IMPROVEMENT_1_4_2.md).

# cad3d-engineering

Plataforma local de CAD paramétrico e DfAM. Codex executa no host; CAD executa sob demanda em Docker sem daemon residente, usuário não-root, sem portas e sem Docker socket.

## Começo rápido

Depois de instalar os atalhos globais, em qualquer pasta nova:

```sh
mkdir projeto-novo
cd projeto-novo
cad3d init .
cad3d doctor
```

Preencha o briefing, o modelo e os contratos de arquitetura antes de executar `cad3d build`. Execute testes quando solicitados no escopo do projeto.

Consulte [docs/GLOBAL_SETUP.md](docs/GLOBAL_SETUP.md). Codex e CLI apontam para este checkout; projetos recebem só template, testes e perfis declarativos, não ambiente Python ou Dockerfile.

## CLI

Comandos mantidos: `doctor`, `init`, `build`, `validate`, `render`, `export`, `report`, `test`. V1.4 adiciona `architecture init|validate` e `review`. Novos: `calibration generate`, `calibration record <json>`, `slicer build|doctor`, `slice` e `slice-report`. Use `cad3d <comando> --help`.

`cad3d architecture init --level product` cria um contrato de engenharia. Em projetos com esse contrato, `cad3d build` bloqueia modelagem enquanto requisitos e arquiteturas funcional/mecânica não passarem. `cad3d review` grava achados com evidências e limites explícitos. Para sistemas de fluxo, `cad3d architecture validate --geometry` compara passagens amostradas com sólidos B-rep. `cad3d render --view engineering` gera vistas opacas isométrica, ortográficas, seção, explodida e, conforme contrato, peças ocultas/interface. Projetos V1.3 sem contrato mantêm o comportamento legado. `cad3d build` valida antes de concluir STEP/STL, PNG, relatórios e manifesto em `build/outputs/`. `cad3d calibration generate` cria cupons em `build/calibration-coupons/`. `cad3d-engineering:1.9.0` e `cad3d-orca:2.4.2-cad3d.1.4.2` são engines separadas. A segunda usa OrcaSlicer v2.4.2 headless com presets oficiais Elegoo Centauri Carbon 2 0.4 mm + PETG + processo 0.20 Standard da mesma versão. Use `cad3d slicer build` uma vez e `cad3d slicer doctor` para confirmar preset/herança. `cad3d slice --printer elegoo-cc2 --material petg --model build/outputs/part.stl` salva a entrada, 3MF fatiado, logs, estimates, hashes e relatório sob `build/slicer/`; `--compare-orientations` fatiará várias rotações com o slicer real. O container não tem rede, portas, Docker socket nem acesso à impressora. Não exporta G-code independente nem valida impressão física.

Mandatory workflow: new templates enable `.cad3d/workflow.yaml`; existing projects run
`cad3d workflow init`. Advance with `cad3d workflow check --gate requirements`, then
`functional_architecture`, `mechanical_architecture`, `modeling`, `system_verification`
and `visual_review`. Only a PASS on the requested gate permits advancement. Optional
product-design depends on engineering and visual PASS. Manufacturing, slicing, physical
validation, and CAD prototype release have separate gates and claim boundaries. The
workflow implementation and evidence are recorded under `docs/evaluations/`.

## Fabricação e assemblies

`cad3d validate` separa estados de geometria, assembly, avaliação de fabricação e validação física. Ele verifica sólidos e malhas, colisão global B-rep, gaps de faces funcionais selecionadas, faixas dimensionais de encaixe, espessura normal local amostrada, envelope e recomendações heurísticas de orientação. `assembly_steps` em `.cad3d/assembly.yaml` avalia inserção/remoção por posições lineares discretas; desde1.6.0, operações explícitas também podem configurar `motion.type: helical`.

Espessura geométrica amostrada não é a espessura nominal do parâmetro e não prova mínimo global; seletores sem correspondência aparecem como `NOT_EVALUATED`. Perfis de impressora/material começam genéricos e não calibrados. Registros dimensionalmente medidos são versionados em `profiles/calibrations/` e só afetam um projeto após seleção explícita e correspondência de impressora, bico, material e hash de processo.

O exemplo `examples/assembly-demo` demonstra gap de guia com faces selecionadas e trajetória livre; `.cad3d/assembly-collision.yaml` introduz interferência e bloqueio. Para schemas detalhados, consulte [skills/3d-engineering/references/assembly-validation.md](skills/3d-engineering/references/assembly-validation.md) e [manufacturing-intelligence.md](skills/3d-engineering/references/manufacturing-intelligence.md).

## Imagens

Imagem CAD: `cad3d-engineering:1.9.0` (PyVista 0.49.1/VTK 9.6.2 EGL headless). Engine Orca separada: `cad3d-orca:2.4.2-cad3d.1.4.2` (`docker compose build orca` ou `cad3d slicer build`). Base Python 3.12.8 e dependências CAD fixadas em `requirements/requirements.lock`; o kernel continua build123d 0.11.1/OCP 7.9.3.1. Para atualizar código Python, skill ou perfis, atualize este repositório. Reconstrua a imagem com `docker compose build` apenas após alterações runtime/Dockerfile. A tag V1.1 e a imagem aprovada 1.8.0 permanecem na árvore de baseline.

## Limitações

A análise estrutural disponível é um cálculo preliminar de viga retangular engastada com carga estática na ponta e hipóteses declaradas. Não existe solver cinemático geral, swept-volume contínuo, FEA ou análise estrutural geral, prova exaustiva de espessura, plano real de suporte do slicer nem validação física automática. A classificação `PASS` geométrica não significa pronto para fabricar. Leia os campos de cobertura, `WARNING` e `NOT_EVALUATED`.

## Documentação e testes

- [Análise de lacunas de engenharia](docs/ENGINEERING_GAP_ANALYSIS.md)
- [Decisões técnicas V1.4](docs/TECHNICAL_DECISIONS_V14.md)
- [Aceitação V1.4](docs/V1.4_ACCEPTANCE.md)
- [Auditoria e decisões anteriores](docs/TECHNICAL_DECISIONS.md)
- [Pesquisa, presets e integração OrcaSlicer](docs/SLICER_RESEARCH.md)
- [Aceitação V1.3 — OrcaSlicer Engine](docs/V1.3_ACCEPTANCE.md)
- [Acceptance V1.2](docs/V1.2_ACCEPTANCE.md)
- [Setup global no Arch](docs/GLOBAL_SETUP.md)
- [Aceitação da V1.1 global](docs/GLOBAL_ACCEPTANCE.md)


## Catálogo documental da entrega

Automação adicional no host, com Python padrão e sem execução CAD:

```sh
python3 scripts/delivery-catalog.py --project /caminho/do/projeto --update-readme
```

Consome `build/delivery/current.json` (`cad3d-delivery-v1`), manifesto com hashes e
`BOM.csv`. Gera `docs/CATALOGO_ENTREGA.md` e `.json`, com STLs, imagens, quantidades,
materiais e vistas. Atualiza somente o bloco gerenciado do README; sem a opção,
gera apenas os catálogos. Rótulos opcionais em `.cad3d/delivery-catalog.json`, no
objeto `labels`; quantidades vêm exclusivamente da BOM.

Confere integridade dos artefatos consultados e explicita imagens ausentes. Não
executa geometria, inspeção visual ou ensaios físicos. Esta adição de host não
reconstrói automaticamente imagem CAD nem atualiza kits ZIP anteriormente aprovados. O script
é incluído pelo inventário de `scripts/` ao gerar um futuro kit em diretório novo.

O catálogo também aceita `--output-dir reports`, recomendado em projetos CAD3D
para guardar JSON gerado fora do inventário de fontes/configuração. O padrão `docs`
permanece disponível. A pasta é relativa ao projeto e não pode modificar a entrega
em `build/delivery`.
