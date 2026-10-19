# Evolução 3d-engineering — candidata 1.5.0

> Atualização posterior: versão1.5.0 ativada por solicitação explícita do usuário para avaliação com projeto real. Ver docs/evaluations/promotion-1.5.0/AVALIACAO_E_PROMOCAO.md na raiz da plataforma. O relatório abaixo conserva o estado anterior à promoção; G9 continua pendente.

## Escopo

Implementação isolada em `evolution/20261017`. Mantidos o motor e a skill ativos em1.4.2, os produtos existentes e o motor Orca. A avaliação de arquitetura e as propostas RunContext, SQLite e Qdrant foram adiadas pelo usuário. Nenhum desses componentes é necessário para este kit.

## Capacidades implementadas

- Catálogo único separa peças de instâncias, materiais e processos. STEP por peça e do conjunto; STL selecionado para FDM; BOM com quantidades reais. Reabertura verifica corpos, volumes e limites, incluindo posições no conjunto.
- Calibração não lê variável antes da definição. Perfil ausente é orçamento conceitual e não compatibilidade com impressora. Usinagem sem avaliador conserva NOT_EVALUATED.
- Encaixe FDM explícito considera a rotação realmente entregue no STL. Alternativas de orientação não aprovam um arquivo incompatível com o volume nominal.
- Exemplo paramétrico demonstra alteração de ventilador, passo dos furos, parede, parafusos, altura e fonte; combinação incompatível é recusada. É uma fixture sintética, sem aprovar as medidas de qualquer produto anterior.
- Manutenção declara itens movidos, removidos, retidos, pré-requisitos e ferramentas. Etapas desconhecidas/falhas bloqueiam dependentes; remoções precisam de operações anteriores comprovadas. Verificações são nominais e amostradas, sem prova de rosca, torque, força ou trajetória contínua.
- Registros comerciais guardam origem, unidade, revisão e hash de seleção; corpos e envelopes de cabos/conectores são distintos. Metadados não constituem medição física.
- Apresentação CAD e catálogo de peças são gerados a partir da geometria. Legenda usa área própria; enquadramento considera a largura real do viewport. Vistas técnicas permanecem1600×1200.
- `cad3d release --target cad-prototype` gera execução isolada e publica por apontador atômico. Exige inventário completo, hashes, relatórios e reabertura real de STEP/STL. Falha preserva a entrega anterior. Peça simples tem montagem explicitamente não aplicável, sem liberar montagem desconhecida de um conjunto.
- Kit portátil fornece CLI, skill canônica e projeções Codex/Claude, referências, receitas Docker, perfis, template, exemplos e inventário SHA256. Não incorpora projetos privados, credenciais ou históricos.

## Como experimentar sem ativar globalmente

Use o wrapper desta candidata por caminho absoluto ou extraia o ZIP e use `bash scripts/cad3d`. Confirme `doctor` com versão1.5.0. Adicionar `scripts` ao PATH somente da sessão evita modificar os links globais. A imagem criada nesta máquina é `cad3d-engineering:1.5.0`; não confundir presença do ZIP de fontes com disponibilidade da imagem em outro computador.

O ZIP não contém imagem Docker. A construção verificada nesta sessão reutilizou dependências locais1.4.2 por `Dockerfile.patch`, sem rede. A construção completa com downloads e a exportação/importação de imagem não foram executadas. Para outra máquina, consulte `docs/INSTALL.md`.

## Evidência e limites

Consulte `evaluations/evolution-20261017/FINAL_REPORT.md`, os logs, hashes e testes negativos. Testes do motor demonstram capacidades determinísticas; não demonstram melhora universal na geração por um agente.

A campanha comportamental de18execuções está preparada, sem resultado atribuído: o plano a descreve como piloto proposto e explicitamente não a dispara. O revisor independente registrou achados antes de atingir limite de uso. Correções são cobertas por regressão; não se afirma segunda revisão independente aprovada. G9 e promoção global permanecem pendentes. Descoberta real em sessões novas de Codex/Claude, Windows/macOS/ARM e impressão física permanecem NOT_EVALUATED.

## Preservação e rollback

Os links globais, imagem1.4.2 e fontes ativas foram comparados com o inventário inicial. Não houve troca global a reverter. Para parar o teste, remova apenas o PATH temporário da candidata ou feche a sessão. Não remova os produtos, worktree ou imagens anteriores. A ativação futura deve ser autorizada separadamente e registrar os destinos anteriores dos links; nunca sobrescrever tags anteriores.

## Pendência de manutenção

Os novos módulos ainda têm trechos compactos que poderiam ser extraídos em funções de agregação mais legíveis. Essa observação de manutenção do revisor não é uma capacidade implementada nem equivale a uma falha física demonstrada.
