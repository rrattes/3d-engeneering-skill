# Movimento helicoidal incorporado — CAD3D 1.6.0

## Escopo

Solicitação do usuário: incorporar à plataforma e à skill a capacidade antes usada
no projeto da cesta. Contrato aditivo em assembly_steps; `cli/helical_motion.py`
executa as poses e `cli/service_states.py` integra contatos, ferramentas e estados
com pré-requisitos. A sequência de skills permanece a mesma.

Eixo/origem mundiais arbitrários, translação assinada, mão direita/esquerda e
avanço por volta=pitch×starts. Extremos incluídos; intervalos aumentados para até90°
por amostra, máximo4096 intervalos. Contato permitido nunca dispensa volume positivo.
Trajetória PASS não estabelece retirada completa: a etapa dependente exige prova
conservadora de separação terminal de todas as caixas retidas.

## Problema encontrado e corrigido na incorporação

O primeiro probe com o STEP real retornou PASS também para a mão incorreta. A
investigação isolou o comportamento de booleanas de Compound importado/deslocado:
interseção do wrapper vazia, mas interseção de seus sólidos internos positiva
(23,281mm³ no giro de180°,169,822mm³ com deslocamento lateral3mm).

O avaliador helicoidal agora extrai sólidos com suas posições aplicadas antes de
analisar cada par. Um caso mínimo com Compound STEP transladado reproduziu o falso
PASS com contato permitido e foi corrigido. O validador linear/estático legado não
foi reescrito por esta alteração; não se atribui a ele a proteção nova.

## Evidências

Execuções e resultados finais são registrados em EVIDENCIAS.json, source-final/,
packaged-final/ e real-basket.json. Os logs anteriores, inclusive controles negativos,
foram preservados. A revisão independente foi estática, sem execução de suites pelo
revisor; a execução e a conferência final couberam ao agente principal.

## Entrega e reversão

Imagem `cad3d-engineering:1.6.0`; CLI, Compose, empacotamento e skill apontam para a
capacidade nova. Imagem1.5.0 preservada. Nenhuma dependência adicionada; Orca mantido.
Para uma execução com o runtime anterior: `CAD3D_IMAGE=cad3d-engineering:1.5.0 cad3d doctor`
e usar apenas contratos suportados por ele. Isso seleciona o runtime anterior;
não desfaz os documentos nem a skill atualizada. Não executar contratos helicoidais
na versão antiga e interpretá-los como verificados.

Os projetos/arquivos imutáveis da cesta não foram modificados. A aprovação anterior
do usuário refere-se à1.5.0;1.6.0 incorpora a evolução solicitada e suas evidências.

## Limites

Amostragem não prova movimento contínuo. Não avalia elasticidade, impressão, ajuste,
força, torque, desgaste, fluência ou resistência. A prova terminal por caixas é
conservadora e pode deixar uma retirada real sem comprovação. Ferramentas mantêm
checagem na posição assentada; não acompanham automaticamente a hélice. A seleção
não resolvida de faces para espessura do suporte Rev C permanece independente.

## Resultado final

- Regressão completa:18/18 verificações no código e18/18 no runtime empacotado.
- Controles helicoidais:16 testes em cada modo; release nativo também exercitado.
- Aceitação legada:35/35 controles.
- STEP real da cesta: mão correta PASS; mão incorreta FAIL; espelho com mão esquerda PASS,21 poses por caso.
- Hashes de todos os módulos CLI iguais entre fonte e imagem; doctor ativo1.6.0 PASS.
- Skill válida; kit portátil com CRC e hashes do inventário conferidos.
- Imagem1.5.0 e seleção imutável da cesta preservadas.

Plano e impacto coincidiram: módulo de movimento, integração de manutenção, regressões, empacotamento, skill e documentação. A correção de Compound foi necessária para impedir falso PASS no novo avaliador; não alterou os verificadores legados. Nenhuma arquitetura de banco ou dependência nova.
