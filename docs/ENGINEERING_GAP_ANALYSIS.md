# Análise de lacunas de engenharia — estudo AIO Reef 80 V0.1/V0.2

## Escopo e preservação

Auditoria somente leitura de `/home/rrattes/Documentos/engineering 3d/aio-reef-80`. O repositório estava limpo e permanece sem alterações nesta missão. Histórico inspecionado:

- `44443f7` — **Archive initial AIO concept V0.1 before architecture review**. Gera 29 sólidos; README registra Assembly `NOT_EVALUATED`, validação de fabricação `FAIL` e falta de interfaces/fluxos CAD verificados.
- `9fc3e6a` — **Rebuild AIO filter architecture and placed assembly V0.2**. Acrescenta assembly com 23 instâncias, cortes/revisões de serviço e seis vistas. Registra claramente que retenção das quatro cascas, bomba real, hidráulica e ensaios continuam pendentes.

Foram lidos `src/model.py`, `.cad3d/params.yaml`, os dois manifests de assembly, relatórios em `build/outputs`, testes, logs versionados nos commits e `docs/V01_DESIGN_AUDIT.md`, `ARCHITECTURE_V02.md`, `HYDRAULICS_V02.md`, `ASSEMBLY.md`, `REVIEW_GATE_V02.md` e `OPEN_MEASUREMENTS.md`.

## O que ocorreu

### V0.1

O commit criou componentes CAD antes de fixar um modelo funcional. O teste de modelo verificava somente tipo/nome, validade B-rep, volume positivo e bounding box não nulo. Os testes adicionais mediam pares sintéticos, tolerâncias declaradas e exportação; não ligavam os requisitos do filtro a componentes, portas e provas do produto. Assim, 29 sólidos e um nozzle fatiado podiam ser reportados sem confirmar um assembly ou caminho hidráulico. O próprio README arquivado já limitava a validade a geometria e declarava o gate de fabricação FAIL.

O inventário V0.1 identificou, entre outros, bases/paredes divididas sem juntas; baffles que não fechavam o percurso; trilhos que atravessavam cestos; berço de bomba que invadia o envelope; e bocais sólidos sem lúmen ou conexão. Esses são defeitos do projeto V0.1, não defeitos descobertos por ensaio físico.

### V0.2

A reconstrução melhorou substancialmente: dimensões livres foram decompostas, fluxos foram mapeados e as instâncias foram posicionadas. `cad3d validate` passou a verificar B-reps, pares, folgas e trajetórias amostradas. O teste de V0.2 reporta 26 testes aprovados e imagens derivadas de meshes reais. O documento `REVIEW_GATE_V02.md` não diz que o produto está liberado: chama a revisão de proposta humana e lista a união das cascas como impeditiva.

A lacuna é que essas ressalvas vivem em texto livre. Em `.cad3d/assembly.yaml`, a restrição de pressão menciona chaves/clamps “architecture-stage open item”, mas não há componentes/clamps CAD nem interfaces de retenção. Ao mesmo tempo, a validação CAD escreve `assembly_validity=PASS` para pares sem colisão ou com contato intencional. O estado responde à pergunta geométrica de interferência; não responde se a casca fica presa, resiste à carga ou veda. A sequência de assembly do operating state não é avaliada (`assembly_steps: []`); testes de serviço cobrem percursos lineares amostrados em estados específicos, não uma sequência completa de destravamento.

A hidráulica V0.2 documenta áreas e velocidades ideais, estimativa de bypass e riscos, e afirma explicitamente que não fez CFD. Testes de abertura verificam B-reps. Nenhum teste mede vazão, perda de pressão, bypass saturado, vedação, volume de retorno ou restart. A sequência correta de conceitos está documentada, mas não existe ligação computada entre REQ, subsistema, componente, abertura geométrica e valor esperado.

### Visualização

As seis vistas são construídas a partir dos STL e do manifest, mas usam Matplotlib 3D com transparência. A vista isométrica deixa a carcaça quase toda wireframe/translúcida e linhas ocultas competem com baffles, baskets e bomba. A vista explodida é explicitamente esquemática, com offsets radiais ilustrativos, não uma sequência de montagem. A seção adiciona setas e rótulos sobre o desenho; algumas cruzam as peças. A vista superior é 3D quase ortográfica, não projeção técnica gerada pelo renderer CAD. O teste `test_technical_views.py` só verifica a existência de quatro arquivos; não verifica legibilidade, identidade/cor por componente, câmera, projeção, corte, relação com interface, nem se o componente pode ser ocultado.

## Classificação por causa

| Classe | Evidência observada | Lacuna de V1.3 | Resposta V1.4 |
|---|---|---|---|
| Processo | V0.1 parte diretamente para 29 sólidos. As fases V0.2 foram recompostas e registradas retrospectivamente; o build não as exigia. | Não havia portão antes da execução do modelo. | `engineering.yaml`, fase 1–3 validada antes de `cad3d build` em workflow `product`; modo `lightweight` mantém caminho curto. |
| Representação de requisitos | Requisitos de função, medidas, riscos e critérios aparecem em solicitação/README/docs, sem IDs e relações verificáveis. | Texto não rastreável a interfaces, partes e evidências. | IDs de REQ/subsistema/componente/interface, medidas `verified|assumption`, método e JSON Pointer a relatório observado. |
| Modelagem | V0.1 tem segmentos livres, trilhos sem par de guias, suportes com interseção e geometrias-bocais sólidos. V0.2 posiciona módulos, porém registra união/clamps não modelados. | Transformações e contato são representados; suporte/retenção, DOFs e intenção de serviço ainda podem faltar. | Componentes precisam função e método de retenção, interface por par e eixos mantidos/liberados; interfaces se ligam ao assembly CAD. |
| Validação | OCP calcula validade/interseção/folga e paths discretos; fluxo está em checklist e cálculos 1D. `assembly_validity=PASS` não inclui carga estrutural ou retenção. | Estado único foi interpretado como plausibilidade sistêmica; provas ausentes eram fáceis de esquecer. | Revisão cruza evidência com requisitos, expõe retenção não provada e distingue geometria, assembly, fabricação e teste físico; caminhos fluidos amostram B-rep e declaram cobertura/limites. |
| Visualização | `A_assembly_iso.png` usa opacidade baixa na casca; exploded é esquemática. Teste verifica apenas nomes de arquivo. | Falta de vista B-rep opaca, projeções ortográficas compartilhadas, cortes tampados, legenda estável e assertions visuais. | PyVista/VTK sobre tesselação dos sólidos build123d, render headless, cores opacas, câmera/cotas comuns, corte fechado, exploded e views seletivas com manifest/testes de imagem. |
| Comportamento da skill | V1.3 orienta modelagem, comandos e validadores CAD/slicer. Não exige processo de arquitetura independente do CAD, nem uma revisão adversarial de contexto separado. | Agente pode otimizar a próxima peça a pedido e usar relatório PASS de colisão como revisão final. | Skill curta com roteamento por classe, portões de fase, relatório de crítica e instrução explícita de revisão em sessão contextual nova; sem alegar agente independente. |

## Causa raiz e limites da inferência

A plataforma foi eficaz em gerar e validar sólidos. A falha sistêmica foi deixar que **completude geométrica** substituísse **completude de produto**: contexto e ressalvas no README não eram contrato executável; o relatório CAD de assembly media interferências, não retenção/força; verificação hidráulica era documentação sem checagem de caminho sobre a geometria; e as imagens eram derivados de malha sem critérios de revisão visual.

Não há evidência suficiente nos commits para atribuir as decisões a uma limitação específica do modelo Codex ou a uma preferência do usuário. A sequência de prompts corretivos é compatível com gates ausentes e falta de estado de projeto persistente; a auditoria não a trata como prova de causalidade individual. A V0.2 já contém revisão humana crítica útil; a V1.4 automatiza rastreabilidade, explicita o que segue em julgamento e torna bloqueios verificáveis, sem converter hipóteses ou renders em provas físicas.

## Não escopo

Nenhuma fonte, artefato, configuração ou commit de `aio-reef-80` foi alterado. Esta auditoria usa o AIO somente como estudo de caso; os testes V1.4 são exemplos genéricos independentes.
