# Evolução da 3d-engineering — plano de implementação

> **Para execução por agentes:** usar `executing-plans` para implementação sequencial. `subagent-driven-development` é uma alternativa quando houver delegação autorizada; tarefas que compartilham contrato/modelo não devem editar esses arquivos simultaneamente. Este documento prepara a implementação; não a inicia.

**Objetivo:** consolidar as melhorias A01–A10 da avaliação, incorporando práticas úteis das outras skills e reduzindo regressões de CAD, montagem, fabricação, apresentação e instalação.

**Arquitetura:** manter a skill como entrada curta de orientação. Implementar regras verificáveis em módulos da plataforma, com um catálogo de peças e instâncias que alimente validação, exportação, BOM e imagens. Desenvolver em candidata isolada; preservar a versão ativa e as entregas existentes até uma promoção explícita.

**Stack:** Python/build123d/OCP no Docker CAD3D existente; PyVista/VTK para vistas; OrcaSlicer isolado somente nos testes de preflight/fatiamento aplicáveis; scripts de regressão existentes e novos casos específicos.

**Spec:** [avaliação A01–A10](../../evaluations/review-20261017/AVALIACAO.md). O mapa de contribuição das skills está abaixo e complementa essa especificação. Caminhos de código neste plano são relativos à raiz da candidata.

**Estado:** APROVADO PELO USUÁRIO; implementação ainda não iniciada. Antes da execução, foi solicitada avaliação arquitetural e de banco de dados. Ver [avaliação de arquitetura e persistência](../../evaluations/review-20261017/ARQUITETURA_E_PERSISTENCIA.md). SQLite opcional é recomendação adicional, não requisito aprovado automaticamente. Nenhum teste ou implementação foi executado para este plano; os resultados históricos citados não são evidência nova.

## Restrições globais

- Preservar a instalação ativa1.4.2, tags Docker atuais e projetos originais, incluindo Photon e BC250.
- Usar candidata em worktree; se não for viável, cópia isolada com origem e hashes registrados. Não fazer reset/clean na origem.
- Não instalar CAD no host; não enviar impressão, publicar repositório ou alterar serviços externos.
- Não herdar material, impressora ou hardware de um produto para outro.
- Não reduzir espessura/folga, remover obstáculos ou converter NOT_EVALUATED em PASS para obter resultado favorável.
- Separar validade geométrica, montagem nominal, avaliação de fabricação, fatiamento, compatibilidade de impressora e validação física.
- Preservar `build(params) -> dict[str, Shape]` nos modelos existentes. APIs e campos adicionais são aditivos; alterações incompatíveis exigem migração explícita.
- Uso de transações para arquivos é uma adaptação de princípio de software, não funcionalidade pronta de uma skill.
- Sem promessa de FEA/CFD, cinemática contínua, calibração física ou suporte multiplataforma sem evidência correspondente.

## Skills: o que incorporar e quando acionar

| Skill | Contribuição concreta | Onde aplicar |
|---|---|---|
| `3d-engineering` | Requisitos, interfaces, retenção, fabricação e limites físicos | Todos os requisitos CAD; permanece coordenadora do domínio |
| `product-capability` | Converter promessas em invariantes e estados verificáveis | Contratos do catálogo, exportação e manutenção |
| `coding-standards` | Dimensões nomeadas, funções focadas, dependências explícitas | Módulos e cadeia de parâmetros; adaptar para Python/CAD |
| `change-impact` | Mapear consumidores e efeitos de cada mudança | Antes de editar contratos, CLI, manifestos e empacotamento |
| `systematic-debugging` | Reproduzir e localizar a causa antes da correção | Calibração, colisões, ferramenta e falhas de geração |
| `test-driven-development` | Negativo que falha antes da correção e positivo após | Bugs e novas capacidades verificáveis do motor |
| `test-collaboration` | TEST-IDs estáveis ligados a requisitos e evidências | Registro de regressão; não usar contagem bruta como qualidade |
| `verification-before-completion` | Afirmações compatíveis com evidência atual | Saída de cada tarefa e promoção |
| `brainstorming` | Alternativas proporcionais, decisões do projetista explícitas | Concepção/implantação antes de detalhes caros; respeitar autorização existente |
| `frontend-design` | Coerência e crítica visual contra o briefing | Adaptar princípios à forma do produto e às galerias; não importar regras web como engenharia mecânica |
| `backend-patterns` | Princípio de transação e isolamento de efeitos | Staging/publicação do pacote; não importar banco/framework |
| `requesting-code-review` | Revisor com contexto mínimo e evidência verificável | Contratos, saídas de etapas e revisão final |
| `skill-creator` / `writing-skills` | Entrada curta, referências condicionais e ensaio comportamental | Consolidação da skill e avaliação antes/depois |
| `eval-harness` | Cenários equivalentes, regressão e avaliação humana | Piloto comparativo da etapa10; adaptar armazenamento e agentes |
| `skill-host-compat` | Inspeção de instruções específicas do host | Kit Codex/Claude; não atribuir ao lint cobertura que ele não tem |
| `agent-sort` | Núcleo pequeno e biblioteca sob demanda | Evitar carregar toda a biblioteca de skills |
| `agent-introspection-debugging` | Capturar falha antes de repetir agente/comando | Somente quando houver loops, limites ou estado inconsistente |
| `context-and-decisions` / `unified-memory` | Vocabulário, decisões e passagem de contexto com fontes | Handoff de etapas; documentos do projeto continuam fonte de verdade, sem instalar runtime de memória obrigatório |

Incorporar princípios específicos nas referências da skill e no motor. Manter revisões, depuração e avaliação como apoios acionados por necessidade. Não copiar corpos inteiros das outras skills nem transformar suas exigências genéricas em regras universais do CAD.

## Foco da revisão

1. Um perfil desconhecido precisa continuar desconhecido, inclusive com arquivos antigos presentes.
2. Peças comerciais e fixadores permanecem nas colisões mesmo sem STL de fabricação.
3. Fonte/configuração modificada durante a execução não pode receber manifesto de validação antigo.
4. Um parafuso não removido pode impedir manutenção; a ferramenta e o contra-aperto também ocupam volume.
5. Uma execução com falha tardia, interrupção ou duas publicações concorrentes não pode misturar entregas.

Cada condição acima tem casos de teste nas etapas abaixo.

## Estrutura de arquivos proposta

Existentes a modificar quando a etapa correspondente começar:

- `cli/cad3d.py`: resolver perfil, integrar módulos novos e manter CLI legada.
- `cli/product_engineering.py`: reconhecer contratos/estados novos e seus limites.
- `cli/validation.py`: conservar primitivas BREP; delegar estados de manutenção a módulo próprio.
- `cli/source_fingerprint.py`: incluir fontes autoritativas declaradas, sem tratar saídas como entradas.
- `cli/cad3d_visualization.py`: materiais, layout de legenda, catálogo e vistas legíveis.
- `Dockerfile`, `Dockerfile.patch`, `compose.dev.yaml`: incluir os mesmos módulos no runtime e no overlay.
- `scripts/cad3d`: integração dos comandos aditivos e da seleção de imagem candidata.
- `skills/3d-engineering/SKILL.md` e referências pertinentes: orientar as capacidades efetivamente implementadas.

Novos módulos propostos:

- `cli/component_catalog.py`: metadados de peças, instâncias, materiais/processos e exportação.
- `cli/artifact_publication.py`: staging, validação de publicação e seleção da entrega atual.
- `cli/service_states.py`: estado de desmontagem e envelopes de ferramenta/contra-aperto.
- `cli/commercial_components.py`: referências comerciais, interfaces e incertezas.
- `scripts/run-evolution-regressions.py`: orquestrador de testes com modo source/packaged e evidências.
- `scripts/package-kit.py`: kit portátil produzido a partir de inventário explícito.
- `TESTS.md`: mapa dos TEST-IDs, comandos e limites; criar somente se não houver registro equivalente na candidata.

Fixtures novas em `examples/evolution/`; evidências futuras em `docs/evaluations/evolution-20261017/`. Não colocar entradas do modelo em diretórios excluídos pelo fingerprint.

## Ciclo obrigatório de cada tarefa de implementação

- [ ] Ler o requisito/TEST-ID e mapear arquivos e consumidores afetados.
- [ ] Criar controle negativo que reproduz a falha real; executar e registrar por que falhou. Erro de sintaxe/importação não substitui a falha esperada.
- [ ] Implementar a menor mudança coerente e conferir o controle positivo.
- [ ] Executar regressão da área afetada e dos consumidores indicados.
- [ ] Atualizar somente os documentos/contratos afetados; inspecionar o diff e registrar evidências.
- [ ] Revisar, corrigir achados importantes e criar checkpoint na candidata. Resultado desconhecido fica aberto.

O ciclo não exige testes artificiais de títulos/frases. Critérios de forma e legibilidade precisam de inspeção visual; CAD nominal não prova efeito físico.

---

## Etapa0 — Congelar baseline e preparar regressão

**Skills:** `using-git-worktrees`, `change-impact`, `test-collaboration`, `verification-before-completion`.

**Arquivos:** inventário e resultados em `docs/evaluations/evolution-20261017/`; registro `TESTS.md`; criar `scripts/run-evolution-regressions.py`.

**Interface proposta:** `run-evolution-regressions.py --mode source|packaged --suite smoke|targeted|integration|full --output <diretorio-novo>`. Retorno0 somente se todas as expectativas executadas coincidirem, retorno não zero em falha, e NOT_EVALUATED explícito para suíte não executada. Não sobrescrever pasta de evidência existente.

- [ ] Registrar commit/estado sujo, destinos dos links globais, hashes de skill/CLI/entradas e IDs das imagens. Preservar documentos não versionados existentes.
- [ ] Reexecutar baseline da candidata isolada sem editar o código: aceitação V1.4, seis regressões existentes, template e assembly-demo.
- [ ] Registrar observações atuais, inclusive defeitos já existentes; histórico35/35 e28 expectativas não é resultado atual.
- [ ] Registrar hashes dos projetos originais a preservar; aplicações futuras usam cópias sem saídas geradas.
- [ ] Criar runner e um controle que espera FAIL por colisão: a suíte deve passar quando o produto é corretamente reprovado. Uma falha inesperada da própria suíte deve retornar não zero.

**Gate G0:** baseline reproduzida ou divergências explicadas e congeladas; nenhum resultado ausente conta como PASS.

## Etapa1 — Calibração e perfil de impressora [A01/A02]

**Skills:** `systematic-debugging`, `test-driven-development`, `product-capability`.

**Arquivos:** `cli/cad3d.py`, `cli/calibration.py` se necessário; criar `scripts/test-calibration-profile-regression.py`.

- [ ] `ENG2-CAL-01`: reproduzir o ramo `calibrated:true` sem `printer_cfg.min_wall_mm`; confirmar a leitura prematura antes de corrigir. Variar presença/ausência da chave também no perfil.
- [ ] `ENG2-CAL-02`: identidade de calibração incompatível não deve aplicar encolhimento/folgas ao perfil atual; relatório deve conservar a incompatibilidade.
- [ ] `ENG2-PROFILE-01`: perfil pedido inexistente ou não selecionado produz compatibilidade NOT_EVALUATED. Um orçamento conceitual separado pode ser exibido, mas sem apresentar uma impressora como selecionada.
- [ ] Corrigir a ordem de inicialização; manter distinção entre perfil CAD e preset Orca.
- [ ] Reexecutar calibração/template e `scripts/test-preflight.py`; PETG-CF ausente permanece explicitamente indisponível, sem substituição.

**Gate G1:** casos positivos/negativos coerentes; erro identificado reproduzido ou hipótese corrigida com evidência.

## Etapa2 — Catálogo de peças e instâncias [A04]

**Skills:** `product-capability`, `coding-standards`, `change-impact`, `3d-engineering`.

**Arquivos:** criar `cli/component_catalog.py`, fixture `examples/evolution/mixed-assembly/` e `scripts/test-component-catalog.py`; integrar CLI/contratos e empacotamento.

**Contrato proposto:** preservar `components` da montagem para instâncias com `id` e `part`. Adicionar mapa opcional `parts`, indexado pela chave retornada por `build(params)`, com `kind: manufactured|commercial|hardware`, `process: fdm|machined|none`, material, formatos de exportação e orientação. Não inferir tipo por prefixo do nome. IDs de instância não substituem IDs de peça.

**API:** `resolve_catalog(shapes: dict, assembly_config: dict) -> dict`, retornando `parts`, `instances`, `findings` e versão do schema. Peças sem metadados mantêm o caminho legado com aviso de classificação presumida; não habilitam liberação de fabricação por suposição.

- [ ] `ENG2-CAT-01`: fixture com suporteFDM, placa metálica, fan, fonte e fixadores; somente o suporte recebe STL, todos permanecem no conjunto e nas verificações.
- [ ] `ENG2-CAT-02`: duas instâncias da mesma peça preservam quantidade/pose no conjunto e uma única geometria de fabricação; BOM reflete quantidade2.
- [ ] `ENG2-CAT-03`: processo/ID inválido reprova contrato antes de exportar; metadata desconhecida não é descartada silenciosamente.
- [ ] Manter modelos legados funcionando; adaptar exemplo novo sem modificar produtos originais.

**Gate G2:** catálogo único alimenta seleção de fabricação/BOM/render; STEP reaberto preserva sólidos, volumes e poses. Nenhuma referência desaparece das colisões.

## Etapa3 — Entrega consistente por execução [A03]

**Skills:** `change-impact`, `verification-before-completion`; adaptar o princípio de transação de `backend-patterns`.

**Arquivos:** criar `cli/artifact_publication.py`, `scripts/test-artifact-publication.py`; integrar `cad3d.py`, exportador e manifestos.

**API proposta:** `publish_run(project_root: Path, run_directory: Path, expected_inputs: dict, target: str = 'cad-prototype') -> dict`. Staging em `build/runs/<run-id>/`; entrega em diretório imutável por execução; apontador `build/delivery/current.json` atualizado por substituição atômica no mesmo filesystem e sob lock. O manifesto usa paths relativos, hashes, input fingerprint e resultados. Não declarar publicação atômica de múltiplos arquivos soltos.

**CLI aditiva:** `cad3d release --target cad-prototype`. Executa gates, geração, validação, exportação e reabertura antes de publicar. Comandos legados continuam utilizáveis como área de trabalho; seus arquivos não significam entrega publicada.

- [ ] `ENG2-PUB-01`: injetar falha na última peça, espessura e reaberturaSTEP; entrega anterior e apontador permanecem intactos. Diagnóstico fica separado.
- [ ] `ENG2-PUB-02`: retirar/renomear peça e executar novamente; entrega nova e ZIP não incluem artefato obsoleto. Arquivos desconhecidos da área de trabalho não são apagados.
- [ ] `ENG2-PUB-03`: alterar configuração durante execução; impedir promoção por fingerprint divergente.
- [ ] `ENG2-PUB-04`: interrupção e publicações concorrentes; apontador referencia uma execução completa, nunca pacote misturado.
- [ ] Geometria inválida, colisão ou fabricação FAIL bloqueiam publicação. WARNING pode compor protótipo com pendências explícitas; desconhecido crítico requerido bloqueia. Nenhum target de uso físico homologado é criado neste escopo.

**Gate G3:** testes de falha e concorrência demonstram integridade, não apenas existência do ZIP.

## Etapa4 — Parâmetros derivados e verificação de propagação [A05]

**Skills:** `coding-standards`, `change-impact`, `test-driven-development`.

**Arquivos:** fixture `examples/evolution/parametric-enclosure/`, `scripts/test-parametric-propagation.py`; referência `requirements_and_interfaces.md` e template quando demonstrado genérico.

**Interface:** conservar `build(params)`; na fixture separar `derive_layout(params: dict) -> dict` e `validate_layout(layout: dict) -> list[dict]`. Parâmetros de entrada são distintos de datums calculados; posições são derivadas uma vez e reutilizadas em recortes, fixadores, desenhos e BOM.

- [ ] `ENG2-PAR-01`: variar fan de80 para120mm e pitch71,5 para105mm; frame, berço, furos, abertura, fixadores e BOM acompanham. Uma cavidade insuficiente deve rejeitar a combinação explicitamente.
- [ ] `ENG2-PAR-02`: variar parede de3 para4mm e altura do corpo dentro da faixa suportada; assentos, recortes e comprimento/engajamento nominal acompanham sem colisão.
- [ ] `ENG2-PAR-03`: variar envelope PSU entre duas referências sintéticas; batentes, cintas e reserva de chicote acompanham ou rejeitam por restrição identificada.
- [ ] Testar o resultado BREP e as interfaces, não somente o dicionário de parâmetros ou texto do script.

**Gate G4:** demonstração de propagação e rejeição explicada. Não alegar correção automática de modelos arbitrários nem alterar BC250 original.

## Etapa5 — Estados de manutenção e aperto [A06]

**Skills:** `3d-engineering`, `product-capability`, `systematic-debugging`, `test-collaboration`.

**Arquivos:** criar `cli/service_states.py`, `scripts/test-service-states.py`; integrar `validation.py`, `product_engineering.py` e `mechanical_assemblies.md`.

**API:** `resolve_service_state(instances: dict, step: dict) -> dict` e `check_service_step(state: dict, step: dict) -> dict`. Cada passo declara `moving_ids`, `removed_ids` e `prerequisite_step_ids`; os demais permanecem obstáculos. Grupo móvel preserva posições relativas. Referências inexistentes, movimentos cíclicos ou componente simultaneamente removido e móvel reprovam contrato. Falta de informação não remove hardware implicitamente.

- [ ] `ENG2-SVC-01`: fixador conservado bloqueia tampa; retirada apenas desse fixador libera. Outro hardware permanece nas duas execuções.
- [ ] `ENG2-SVC-02`: placa+cooler+conectores movem juntos; um conector solidário precisa bloquear quando colide com obstáculo.
- [ ] `ENG2-SVC-03`: driver livre e chave da porca bloqueada, depois controle com ambos livres. Engajamento/assentamento nominal incoerente deve ser reportado; torque/força continuam não avaliados.
- [ ] `ENG2-SVC-04`: resultado desconhecido do kernel não é agregado como PASS. Distância entre amostras e método aparecem no relatório.
- [ ] Conservar `assembly_path_check` legado via adaptação explícita; não inventar trajetória contínua a partir de amostras.

**Gate G5:** conjunto nominal, sequência e ferramenta têm evidências separadas; correção não pode consistir em excluir todos os fixadores.

## Etapa6 — Concepção e apresentação padrão [A07/A08]

**Skills:** `brainstorming`; adaptar crítica de `frontend-design`; `3d-engineering`, `verification-before-completion`.

**Arquivos:** `cad3d_visualization.py`, `visual_validation.md`, `design_review.md`; criar `references/concept_and_presentation.md` e `scripts/test-presentation-catalog.py`.

**API proposta:** `render_parts_catalog(project_root, shapes, catalog) -> dict`; adicionar `presentation` como modo de render, preservando modos técnicos atuais. Cores vêm do catálogo; escala comum deve ser opção explícita, caso contrário informar enquadramento individual. Galeria contém nome, função, quantidade, imagem e links atuais de fabricação.

- [ ] Para escolhas relevantes, orientar comparação curta de implantação/forma antes de detalhes: volume, peças, fixadores, fabricação e manutenção. Não exigir três conceitos para um espaçador simples.
- [ ] `ENG2-VIS-01`: conjunto com36componentes; legenda fora da região do modelo, nomes legíveis e nenhuma câmera cortando a geometria. Inspeção humana/imagens acompanha verificações de layout.
- [ ] `ENG2-VIS-02`: superfícies planas sem artefatos de normais; manter controle visual da interface colorida existente.
- [ ] `ENG2-VIS-03`: peças removidas/novas acompanham catálogo; imagens e links correspondem ao mesmo manifesto e somente às peças selecionadas.
- [ ] `ENG2-VIS-04`: vista de manutenção conserva o estado de hardware; vista com objetos apenas ocultos deve ter legenda diferente. Explodida não é prova de remoção.

**Gate G6:** apresentação legível inspecionada; estética avaliada contra briefing, sem confundir render bem sucedido com produto bem resolvido.

## Etapa7 — Referências comerciais e biblioteca [A09]

**Skills:** `3d-engineering`, `context-and-decisions`; princípios de evidência de `unified-memory` sem dependência obrigatória de runtime.

**Arquivos:** criar `cli/commercial_components.py`, `scripts/test-commercial-provenance.py`, `examples/evolution/commercial-interfaces/`; atualizar `commercial_components.md`.

**API:** `validate_commercial_record(record: dict) -> dict`. Registro contém fabricante/part number/revisão quando conhecidos, fonte, data, dimensões/unidades, origem da medida, incerteza, envelope e campos não conhecidos. Interfaces e keep-outs de plugue/cabo/ferramenta são distintos do corpo.

- [ ] `ENG2-COM-01`: dimensão do gabinete e foto sem escala não podem ser promovidas a PCB/furação verificados; permanecerem desconhecidas é resultado correto.
- [ ] `ENG2-COM-02`: mudar variante comercial invalida a evidência de interface anterior; nenhuma correspondência apenas por nome resolve o conflito.
- [ ] `ENG2-COM-03`: corpo cabe mas plugue/bend envelope colide; caso deve reprovar o envelope modelado, sem afirmar raio real não medido.
- [ ] Somente padrões com origem e limites aprovados entram na biblioteca; não promover apoios provisórios da BC250 como padrão comercial validado.

**Gate G7:** biblioteca reutiliza conhecimento rastreável sem transportar requisitos/geometria de um produto para outro automaticamente.

## Etapa8 — Consolidar a skill e revisar contratos

**Skills:** `skill-creator`, `writing-skills`, `agent-sort`, `requesting-code-review`.

**Arquivos:** `SKILL.md`, referências citadas, exemplos e `docs/IMPROVEMENT_NEXT.md` futuro.

- [ ] Incorporar requisitos verificáveis, depuração por causa, revisão de impacto, propagação paramétrica, estados de manutenção e publicação com evidência.
- [ ] Vincular aos comandos/APIs realmente implementados; não anunciar funcionalidades apenas planejadas.
- [ ] Remover duplicação com referências; manter módulos de software fora do texto principal. Não carregar todas as skills em cada projeto.
- [ ] Verificar links, descoberta e fronteiras de aplicação. Revisar também instruções excessivas que causariam novas perguntas/aprovações para trabalho autorizado.
- [ ] `ENG2-SKILL-01`: executar posteriormente pedidos de peça simples, conjunto e produto térmico com a skill; conferir decisões observáveis e artefatos, não correspondência de frases.

**Gate G8:** skill descreve capacidades existentes e preserva proporcionalidade e limites físicos.

## Etapa9 — Avaliação comparativa e revisão independente [parte de A10]

**Skills:** `eval-harness`, `writing-skills`, `requesting-code-review`, `test-collaboration`.

**Arquivos:** novos cenários em `docs/evaluations/evolution-20261017/scenarios/`, critérios e resultados por execução. Manter critério fixado antes de avaliar resultados.

- [ ] Comparar baseline congelada e candidata em3classes: peça simples, conjunto comercial e gabinete térmico. Incluir também casos reservados de medida insuficiente e combinação incompatível, não usados para ajustar instruções.
- [ ] Piloto proposto:3repetições por classe/variante em um agente =18execuções; repetir no outro agente somente quando disponível e autorizado. Este plano não dispara a campanha nem atribui resultado ao agente indisponível.
- [ ] Mesmos pedidos, limites de ferramenta e orçamento por execução; modelos/versões documentados. Alternar ordem das variantes para reduzir viés; não entregar a resposta esperada ao executor.
- [ ] Critérios determinísticos: requisitos verificáveis, colisões detectadas, desconhecidos mantidos, propagação, integridade e saídas. Métricas adicionais: retrabalho, falhas omitidas, tempo e custo/tokens quando disponíveis.
- [ ] Inspeção visual comparável com câmeras fixas e avaliador sem identificação da variante quando possível. Amostra pequena não sustenta percentual universal de melhoria.
- [ ] Revisão independente dos contratos e diffs, com achados corrigidos e reexecutados; sem revisão separada disponível, registrar essa limitação e manter promoção pendente.

**Gate G9:** zero regressão nos requisitos obrigatórios anteriores, zero falha importante omitida nos cenários e evidência das melhorias pretendidas. Ruído estético/tempo/custo não compensa falha de segurança ou geometria. Melhoria não demonstrada permanece hipótese.

## Etapa10 — Kit compartilhável e promoção [parte de A10]

**Skills:** `skill-host-compat`, `change-impact`, `verification-before-completion`.

**Arquivos:** criar `scripts/package-kit.py`, `docs/INSTALL.md`, `AGENTS.md`/`CLAUDE.md` do kit e fontes canônicas das projeções de skills. Adaptar wrapper e Dockerfiles conforme necessário.

- [ ] Kit com skill/referências, CLI, fontes/Dockerfile/locks, guias, template e exemplo; inventário explícito exclui credenciais, históricos pessoais e saídas obsoletas. Preservar licenças e origem; licença desconhecida exige resolver a distribuição desse item.
- [ ] `ENG2-KIT-01`: instalar/extrair em pasta limpa com espaços no nome, sem caminhos do autor; doctor e exemplo funcionam, STEP/STL reabrem e hashes correspondem.
- [ ] `ENG2-KIT-02`: Codex e Claude Code recebem projeções coerentes da mesma skill, sem variáveis do outro host. Descoberta real é verificada em cada agente disponível; lint ECC é evidência limitada, não certificação dos dois agentes. Não alegar execução do script ECC se ele não existir.
- [ ] Baseline inicial de suporte: Linuxx86_64. WSL/macOS/ARM permanecem NOT_EVALUATED até execução neles. Construção completa do Docker e exportação/importação de imagem são rotas distintas, documentadas conforme realmente verificadas.
- [ ] Reempacotar em tags novas; rodar regressão completa sem overlay e comparar SHA256 dos módulos fonte com os empacotados. Orca preservado salvo alteração justificada.
- [ ] Preparar release notes, inventário, resultados, pendências e rollback. Somente após autorização de ativação, trocar links globais; não sobrescrever tags anteriores.

**Gate G10:** candidata verificada e pacote íntegro; mudanças locais podem ser promovidas com rollback pronto. Publicação em GitHub/registry ou envio a terceiros exige autorização própria.

## Regressão: frequência e comando

### Histórico a preservar

- `scripts/test-v14-acceptance.py` (registro anterior:35expectativas).
- `scripts/test-source-fingerprint.py`, `test-product-geometry-gate.py`, `test-export-current.py`, `test-interface-render.py`, `test-preflight.py`, `test-fastener-envelope-regression.py` (registro anterior agregado:28expectativas).
- `templates/project/tests/` e `examples/assembly-demo/tests/`.
- Exemplos em `examples/product-engineering/`.

Inventariar os entrypoints atuais no G0. Se um script só suporta overlay/source, adaptar o runner para exercitar também a imagem empacotada; passar contra fonte não prova imagem. Não duplicar suítes só para elevar contagem.

### Níveis

| Nível | Quando | Cobertura |
|---|---|---|
| Smoke | Cada mudança de módulo/empacotamento | Importações, CLI, kernel e render básico |
| Targeted | Cada correção | TEST-IDs da tarefa e negativos associados |
| Integration | Mudança de catálogo/manifesto/CLI | Contratos, CAD, exportação, frescor e consumidores afetados |
| Full | Cada gate maior e antes da promoção | Legadas + novas + template/exemplos + preflight + inspeção visual pertinente |
| Aplicação | Após integração e antes da promoção | Cópias de projetos existentes e cenário novo, sem tocar originais |
| Packaged | Depois da construção final | Full sem overlay + igualdade de módulos + pacote em pasta limpa |

Comando proposto após existir o runner:

```sh
python scripts/run-evolution-regressions.py --mode source --suite targeted --output /tmp/cad3d-targeted-<id-unico>
python scripts/run-evolution-regressions.py --mode packaged --suite full --output /tmp/cad3d-packaged-<id-unico>
```

O host apenas orquestra; CAD e testes que o importam executam em container. O runner deve registrar imagem/ID, módulo importado, comandos completos, códigos de saída, TEST-IDs e hashes. Resultados não executados são NOT_EVALUATED, nunca copiados de uma rodada anterior.

### Critérios de não regressão

- Falha intencional no produto precisa ser detectada; sucesso da suíte é essa expectativa satisfeita.
- Alterar código/configuração/adicionar/remover entrada invalida a evidência anterior conforme o escopo do fingerprint.
- STEP conserva quantidade, volumes somados e bounding boxes com tolerâncias numéricas justificadas; STL fechado e conectado conforme a peça.
- Produtos físicos não ganham aprovação por aumento de testes/arquivos gerados.
- Uma alteração deliberada de comportamento exige requisito e fixture atualizados, diff explicado e controle da regra anterior. Não reescrever baseline silenciosamente.
- Original dos projetos e instalação ativa permanecem com hashes registrados, ressalvados somente novos documentos de planejamento autorizados.

## Coordenação, recuperação e rollback

Implementação sequencial é a escolha inicial recomendada porque catálogo, publicação e manutenção compartilham contratos. Pesquisa de fontes e revisão estática podem ser delegadas quando autorizado; cada frente tem dono e arquivos delimitados. Nenhum agente edita fonte/configuração durante uma validação ou exportação que depende desses arquivos.

Falha em gate: parar a tarefa afetada, preservar logs e diagnosticar; não reiniciar toda a implementação. Falha de agente: `agent-introspection-debugging`, registrar último checkpoint, retomar apenas pendências e verificar o diff. Não confiar somente no relato de sucesso de outro agente.

Rollback antes de ativar: manter links/tags atuais; descartar apenas a seleção da candidata, conservando sua evidência. Depois de ativar: restaurar os destinos dos links e IDs/tags registrados no G0. Não apagar projetos nem reinterpretar manifestos novos como prova de validade na versão antiga. Confirmar doctor/fixture de referência após reversão autorizada.

## Evidência e handoff por gate

Cada gate entrega: arquivos alterados, TEST-IDs, resultados e hashes atuais, achados de revisão, pendências, estado real de cada dimensão de validade, checkpoint e próxima tarefa. O estado mínimo é PLANNED/IN_PROGRESS/BLOCKED/PASS/WARNING/NOT_EVALUATED conforme o contexto; progresso de tarefa não substitui status de engenharia.

**Este plano não executou os gates.** Ao iniciar implementação, ler a avaliação e este documento, preparar G0 e seguir as dependências. A versão candidata recebe número somente após definir compatibilidade; nenhum número foi promovido neste planejamento.
