# Fundamentos de confiabilidade — CAD3D 1.7.0

## Escopo autorizado

Três frentes: interferências robustas, referências geométricas e tolerâncias. O usuário
pediu otimizar o uso de tokens. Alteração aditiva sobre1.6.0, preservando seus arquivos
anteriores, imagem, dependências, Orca e entregas imutáveis dos produtos.

## Implementação

- `cli/brep_pairs.py`: núcleo compartilhado de operações entre sólidos localizados,
  utilizado pelos verificadores estáticos/lineares/ferramentas e helicoidais.
- `cli/face_references.py`: referência por ponto na face recortada, normal/raio/área,
  compatibilidade com centroide, diagnóstico e recusa de ambiguidade.
- `cli/tolerance_stack.py`: intervalos assinados de pior caso; desvios assimétricos,
  referências repetidas combinadas, procedência e hipóteses explícitas.
- Integração em `validation.py` e `cad3d.py`; contratos na skill em reliability.md.

Contatos próximos são classificados com tolerância numérica, mas não dispensam
folga mínima positiva. O revisor apontou esse limite do comportamento legado; um
controle reproduziu falso PASS para folga0,005mm e tolerância de contato0,01mm antes
da correção. O cálculo de folga agora permanece obrigatório.

As referências escolhem a candidata geometricamente mais próxima que atende aos
critérios; distâncias empatadas dentro de1e-5mm são ambíguas. Não há identidade CAD
persistente nem escolha por ordinal. Uma face selecionada não comprova cobertura
completa de espessura. Seleção parcial sem medição de outra região não vira PASS.

Tolerâncias calculadas usam dados declarados; rótulo measured/supplier não autentica
um registro externo. Ausência de limites/procedência é explícita; hipóteses ficam
WARNING. Gates existentes impedem publicação com montagem WARNING/NOT_EVALUATED.

## Evidências

Resultados finais em EVIDENCIAS.json e logs source/, packaged/ e legacy-acceptance.
O probe basket-reference.json usa o STEP real da execução da cesta, sem alterar seu
modelo/entrega: duas referências por ponto resolvidas, espessura amostrada no escopo
selecionado PASS e colisão estática por fase incorreta detectada. O relatório antigo
da cesta continua historicamente válido para os seletores anteriores.

Revisão independente somente leitura dos módulos e integração. Testes e conferência
de container executados pelo agente principal. Os logs negativos foram preservados.

## Economia de contexto

Leituras pontuais, uma entrada nova de regressão, logs completos em disco e resumos
curtos. Controles locais precederam as suites completas; sem múltiplos agentes de
implementação nem repetição de contexto completo na revisão. Não há medição que
permita declarar percentual de redução de tokens.

## Limites e reversão

Não há prova física de ajuste, resistência ou impressão. Tolerâncias cobrem apenas
cadeias lineares limitadas, não GD&T geral ou rendimento estatístico. Espessura e
movimentos continuam amostrados. A seleção por ponto depende dos datums corretos.

Runtime anterior preservado: `CAD3D_IMAGE=cad3d-engineering:1.6.0 cad3d doctor`.
Usar somente contratos suportados pelo runtime escolhido; isso não reverte docs/skill.
Nenhum arquivo da cesta foi regenerado. Kit portátil1.7.0 disponível em dist/cad3d-1.7.0.

## Resultado final

-19/19 verificações do código e19/19 do runtime empacotado.
-16 controles novos,16 controles helicoidais preservados e5 testes de publicação por modo.
-35/35 controles de aceitação legada.
-Doctor ativo1.7.0; todos os módulos CLI coincidem entre fonte e imagem.
-Kit portátil com CRC e hashes de inventário conferidos; skill válida.
-STEP real: duas referências resolvidas, espessura amostrada PASS no escopo e colisão estática por fase incorreta corretamente reprovada.

Impacto observado coincide com o plano: núcleo BREP compartilhado, seleção geométrica e tolerâncias com integração nos relatórios/gates. A pequena correção da tolerância de contato foi necessária para impedir falso PASS de folga positiva. Sem dados, dependências ou produtos migrados.
