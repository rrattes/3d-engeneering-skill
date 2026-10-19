# Melhoria da 3d-engineering — 1.4.2

Implementação autorizada em 16/10/2026. A pasta com sufixo `candidate-20261016` contém a revisão; o nome registra sua origem isolada. O estado de ativação e os testes finais estão em `evaluations/improvement-20261016/`.

## O que mudou

| Frente | Mudança | Evidência/limite |
|---|---|---|
| Instruções | Entrada curta, rotas para peça simples, montagem e produto multidomínio | Não exige carregar outras 60 skills |
| Mecânica | Cabeça/porca/arruela, ferramenta, retenção, caminho de carga, tolerâncias com sinais, pré-requisitos de manutenção | Métodos e exemplos em referências; capacidade física continua separada |
| Fontes | Inventário conservador de Python/configuração local e entradas extras declaradas | Modificação, inclusão e exclusão invalidam o frescor; não é rastreador completo de I/O |
| Arquitetura | Gate antes de qualquer carregamento de modelo de produto, incluindo export/render/review | `model_gate: false` não contorna; diagnósticos sem geometria continuam disponíveis |
| Exportação | Regenera arquivos atuais e reabre STEP, compara contagem/soma de volumes/bounds e fechamento STL | Não certifica montagem, tolerância física ou liberação de produto |
| Orca | `slicer preflight` verifica seleção solicitada sem STL e sem fatiar | PETG-CF indisponível é explícito; não foi criado preset fictício |
| Visual | Participantes da interface resolvidos por imagem, corrigindo vista cinza | Raster confirma cores; inspeção das imagens continua necessária |
| Descoberta | Experimento rejeitado 1.4.1 arquivado fora da árvore ativa | Uma única entrada SKILL.md no diretório ativo |

## Skills usadas e ordem

1. `3d-engineering`, `change-impact`: ler fluxo, dependências e riscos da mudança.
2. `brainstorming`, `writing-plans`: delimitar solução e critérios; o plano já aprovado dispensou novas autorizações.
3. `using-git-worktrees`: aplicar isolamento. Como a origem não tinha commits, foi usada cópia com repositório e checkpoint próprios.
4. `dispatching-parallel-agents`, `executing-plans`: separar autoria, plataforma, aplicação e revisão, mantendo donos de arquivos.
5. `skill-creator`, `writing-skills`: preservar entrada curta, referências condicionais e observar baseline antes das alterações.
6. `systematic-debugging`, `test-driven-development`, `test-collaboration`: reproduzir falhas e ligar regressões aos critérios ENG-01 a ENG-07 do plano.
7. `requesting-code-review`: revisão em contexto independente, com achados corrigidos e rechecados.
8. `skill-host-compat`, `verification-before-completion`: conferir metadados, links, descoberta, código efetivamente empacotado e resultados atuais. O script específico do ECC não existe neste repo; foi usada a validação oficial de skill e inspeção local equivalente, sem alegar execução daquele script.

O registro completo está em [EXECUTION_LEDGER.md](evaluations/improvement-20261016/EXECUTION_LEDGER.md). Não foram instaladas outras skills.

## Avaliação e critérios de promoção

- Baseline e candidata aplicados em contextos separados aos mesmos três cenários de revisão. A baseline já respeitava os bloqueios nos exercícios; não se observou falha comportamental ali, portanto não se atribui uma melhora estatística a texto mais severo.
- A candidata foi também aplicada a uma fixture inédita: conflito de cabeça, ferramenta bloqueada, painel montado porém sem saída, caminhos independentes corrigidos e tolerância nominal enganosa. Resultados e scripts estão em [heldout](evaluations/improvement-20261016/heldout/).
- As diferenças automáticas foram demonstradas com regressões negativas/positivas reais. A aceitação V1.4 cobre três produtos genéricos e um gate vazio, preservando compatibilidade.
- Este é um piloto limitado: uma aplicação por variante, não cinco repetições, nem uma campanha de geração integral de produtos novos. Não demonstra superioridade estética, aumento geral de confiabilidade ou nível profissional certificado. A promoção é uma correção local respaldada pelas verificações descritas.
- Revisão independente: [independent-review.md](evaluations/improvement-20261016/independent-review.md). Os agentes que atingiram limite retomaram após uma tentativa e concluíram as entregas.

## Estado final e evidência atual

Revisão **ativa** por links globais; a origem permanece preservada. [Registro de ativação e rollback](evaluations/improvement-20261016/activation.json).

| Verificação executada | Resultado |
|---|---|
| Aceitação baseline V1.4 | 35/35 |
| Aceitação final, imagens 1.4.2 empacotadas, sem overlay | 35/35 |
| Regressões específicas, 6 suítes | 28 expectativas satisfeitas |
| Compatibilidade assembly-demo | 10 testes passaram |
| Compatibilidade template | 24 testes passaram |
| Preflight real PETG / PETG-CF | PASS rc0 / NOT_EVALUATED rc4 |
| Código candidato × código nas imagens | SHA256 coincide em todos os módulos |
| Skill | validador oficial, links e projeção local válidos |
| Origem | 499 arquivos do snapshot sem alteração |

Contagens misturam testes, fixtures e checagens de comandos; não representam 97 requisitos independentes. Os negativos esperados contam como expectativas satisfeitas. Resultados: [aceitação](evaluations/improvement-20261016/acceptance-packaged.json), [regressões](evaluations/improvement-20261016/regressions.json), [imagens](evaluations/improvement-20261016/runtime-images.json), [inspeção visual](evaluations/improvement-20261016/visual-inspection/REVIEW.md).

## Como repetir

No diretório desta revisão:

```sh
scripts/cad3d doctor
scripts/cad3d slicer preflight --printer elegoo-cc2 --material petg
scripts/cad3d slicer preflight --printer elegoo-cc2 --material petg-cf
```

O último comando retorna 4/NOT_EVALUATED enquanto esse preset não existir. Isso não impede desenvolver CAD e protótipos corretamente classificados.

Para testar fontes locais sem reempacotar, usar `CAD3D_DEV_SOURCE=1 scripts/cad3d ...`; o overlay é explícito e somente leitura. Execução normal usa as imagens empacotadas. Para nova aceitação, apontar PATH para `scripts/` e definir `CAD3D_V14_ACCEPTANCE_DIR` como diretório novo e vazio. Ver comando exato em `acceptance-packaged.log`/plano.

Empacotamento local sem reinstalar dependências:

```sh
docker build --network none --pull=false -f Dockerfile.patch --target cad3d -t cad3d-engineering:1.4.2 .
docker build --network none --pull=false -f Dockerfile.patch --target orca -t cad3d-orca:2.4.2-cad3d.1.4.2 .
```

Requer as bases locais `cad3d-engineering:1.4.0` e `cad3d-orca:2.4.2`; conferir seus IDs em `runtime-images.json`. Para reconstruir dependências, usar os Dockerfiles completos. Não confundir ID local com digest de registro remoto. Nenhum firmware, impressora ou serviço externo foi acionado.

## Compatibilidade e limites restantes

Manifestos antigos não provam o novo frescor: reconstruir o projeto para gerar o inventário. Arquivos STEP/STL/DXF/CSV e outros formatos fora da seleção automática devem estar em `project.source_inputs`. Não colocar entradas autoritativas em diretórios reservados a relatórios/saídas. Mudanças em arquivos Python/configuração não usados também podem invalidar o inventário. Há limites explícitos de tamanho, quantidade e profundidade.

Arquivos de componentes renomeados/removidos podem continuar na pasta de saída. A lista atual é `export-validation.json`; separar arquivos obsoletos e selecionar o modelo exato para fatiar. O Orca recusa diretório com múltiplos candidatos; não seleciona silenciosamente um deles. A correção de exportação desta revisão cobre arquivos atuais com nomes preservados e integridade da regeneração, sem apagar arquivos desconhecidos.

O sistema não fornece FEA, garantia de espessura mínima global, cinemática contínua, força de retenção, torque adequado, vedação, segurança elétrica/térmica, PAR ou validação física. Os caminhos são amostrados; as tolerâncias precisam de dados reais. O projeto Photon V não foi alterado nem usado como template geométrico universal.

## Reversão

A origem está preservada em `/home/rrattes/Documentos/engineering 3d/3d-engineering`; imagens 1.4.0 e Orca 2.4.2 continuam disponíveis. Se esta revisão foi ativada, os destinos anteriores dos dois links constam em `activation.json`. Para reverter, apontar `~/.local/bin/cad3d` para o script da origem e `~/.agents/skills/3d-engineering` para a skill da origem. Os projetos não precisam ser movidos; novos manifestos só serão plenamente interpretados pela revisão correspondente.
