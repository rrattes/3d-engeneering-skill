# Melhoria da skill e verificadores CAD3D

Plano aprovado pelo usuário em 16/10/2026. Execução por frentes independentes, coordenada por executing-plans.

## Objetivo e limites
Melhorar engenharia de montagem, rastreabilidade e instruções sem inflar o fluxo de peças simples. Preservar projetos existentes e imagens base. A cópia candidata tem repositório próprio porque a origem ainda não possui commits. Nenhuma validação CAD implica liberação física.

## Escopo e impacto
- Skill: entrada curta, rotas por complexidade, referências mecânicas e revisão de forma. Não copiar requisitos Photon.
- CLI: manifesto de entradas transitivas/configurações e frescor da evidência; compatibilidade com manifesto antigo explicitamente limitada.
- Orca: preflight dos perfis reais antes do CAD, sem material substituto ou fatiamento implícito.
- Testes: regressões mecânicas e de entradas, aceitação V1.4 e avaliação comportamental em contextos separados.
- Deploy: candidata isolada; somente promover com evidência e revisão, manter rollback.

## Frentes e critérios de aceitação
| ID | Requisito | Evidência esperada |
|---|---|---|
| ENG-01 | Alterar import Python/config invalida evidência | regressão negativa/positiva de manifesto |
| ENG-02 | Cabeça/ferramenta bloqueada é detectada | interseção BREP negativa e reparada |
| ENG-03 | Posicionamento não comprova retenção | aceitação existente e cenário de revisão |
| ENG-04 | Perfil ausente detectado sem STL | preflight PETG-CF falha explícita; PETG disponível |
| ENG-05 | FAIL inicial interrompe sólidos/exportação | aceitação e exercício de agente |
| ENG-06 | Metadados PNG não provam legibilidade | teste nomeado corretamente e inspeção de imagens |
| ENG-07 | Processo proporcional + manutenção/tolerâncias | revisão de instruções e aplicação isolada |

## Execução
- [x] Congelar origem em cópia e commit de baseline.
- [x] Registrar comportamento baseline antes de editar skill.
- [x] Executar aceitação baseline e reproduzir lacunas.
- [x] Implementar correções com regressões.
- [x] Atualizar skill após observações baseline.
- [x] Rodar aceitação candidata, avaliações e revisão independente.
- [x] Registrar limites, promoção/rollback e guia de retomada.

## Foco da revisão
Arquivos de entrada fora do projeto/symlinks, relatórios antigos, bloqueios iniciais contornados, substituição silenciosa de material e evidência visual superestimada. Não exigir novos gates físicos para exportar protótipos já corretamente classificados.
