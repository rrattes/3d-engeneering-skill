# Capacidades gerais incorporadas — CAD3D 1.8.0

Solicitação: incorporar as sete frentes restantes com o padrão de contexto enxuto,
validação/regressão, documentação e entrega verificável. Base1.7.0 preservada.

## Entregas concretas

1. Biblioteca inicial: pares roscados reais customizados direita/esquerda, dobradiça
   de três nós com pino simples e trilho T/carro. Exportação STEP/STL/BOM/conjunto.
2. Rotações, translações explícitas e trajetórias compostas cumulativas por operação,
   com contatos por instância, amostragem e prova conservadora de retirada.
3. Campanhas Cartesianas de variantes em cópias isoladas com build/validação nativos,
   parâmetros/logs/artefatos e orçamento limitado; sem publicação automática.
4. Calibração por medições, identidade, validade e evidência local com SHA256;
   recomendações por feature sem alterar presets. Aplicação nativa reconciliada com
   impressora, bico, perfil/material/lote, orientação e hash do processo atuais.
5. Envelopes de ferramentas/mãos e cabos com curvas e limite mínimo de dobra declarado,
   além de aproximação amostrada e exclusão apenas do alvo nomeado de engate.
6. Desenhos reais HLR com cotas externas, cortes do CAD e cotas de diâmetro/distância
   de faces, SVG/PDF; cotas solicitadas não resolvidas impedem publicação.
7. Pré-dimensionamento de viga retangular engastada com carga na ponta, propriedades,
   procedência e limites explícitos; sem propriedades de PETG presumidas.

Contratos e exemplos autocontidos: skills/3d-engineering/references/general_capabilities.md.
Detalhes das frentes delegadas: interfaces-drawings.md e calibration-structure.md.
A divisão usou dois agentes com contexto mínimo e arquivos independentes; raiz
integrou os contratos e uma revisão distinta verificou os gates/isolamento.

## Achados e correções

A revisão identificou que uma identidade de calibração aninhada podia continuar
PASS após troca do material do projeto. O teste reproduziu a falha (registro
current-identity-red.log). A identidade esperada agora deriva das configurações
atuais e do hash do arquivo de processo selecionado; testes de troca preservam o
ponteiro de entrega anterior. Desenhos com referências solicitadas não resolvidas
também bloqueiam publicação, em vez de exportar uma cota fictícia.

## Verificação e artefatos

Resultados consolidados finais em EVIDENCIAS.json, source/ e packaged/, com aceitação
legada separada. artifact-probe.json registra roundtrip STEP/STL de rosca real e
cortes/cotas de uma fixture geométrica. PDFs/SVGs e prévia visual em drawing-example/.
São fixtures de software e valores sintéticos, não calibração física de uma máquina,
um projeto de produto aprovado ou ensaio de carga. PDFs foram abertos como imagem.

## Limites

Biblioteca inicial não fornece todas as interfaces possíveis nem retenção de pino,
end stops ou certificação ISO de roscas. Movimentos são rígidos/amostrados dentro de
uma operação, não planejador geral com poses abertas persistidas entre operações.
Campanhas cobrem só combinações declaradas. Envelopes não são simulação de ergonomia,
forças ou elasticidade. Desenhos não constituem especificação ISO/GD&T completa.
A análise estrutural cobre somente o modelo idealizado declarado, não FEA ou
resistência comprovada de uma impressão. Dados medidos são declarações rastreadas,
não auditoria de metrologia ou garantia de população futura.

Imagens1.7.0 e entregas anteriores preservadas; sem dependências novas, banco de dados,
Orca alterado ou envio à impressora. Reversão por execução: selecionar
CAD3D_IMAGE=cad3d-engineering:1.7.0 e apenas contratos suportados por essa versão.
O kit1.8.0 é criado em dist/cad3d-1.8.0; ativação e hashes registrados nas evidências.

## Resultado final

-27/27 entradas de regressão na fonte e27/27 no runtime empacotado.
-38 testes novos em cada modo, distribuídos nas sete frentes e integração.
-35/35 controles legados preservados.
-Todos os24 módulos CLI coincidem entre fonte/imagem; doctor ativo1.8.0 PASS.
-Skill válida; kit com CRC e hashes do inventário conferidos.
-Imagem1.7.0 e entrega selecionada original da cesta preservadas.

O impacto observado coincide com o plano: módulos opcionais, comandos, verificadores, gates de publicação e documentação. A correção de identidade foi necessária para impedir a aplicação de calibração incompatível; sem expansão para banco, novas dependências, FEA geral ou impressão física.

## Aprovação e promoção pelo usuário

Em 17/10/2026, o usuário aprovou e promoveu a versão 1.8.0 como referência local.
O [registro de aprovação e promoção](APROVACAO_E_PROMOCAO.md) vincula a decisão às
evidências acima e preserva a separação entre aceitação da plataforma e validação
física de cada produto. O [readme do workspace](../../../../readme.md) reúne os
pontos de entrada, o fluxo de skills e as instruções de compartilhamento.
