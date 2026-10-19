# Seleção técnica (2026-10-12)

## CAD

| Opção | Avaliação | Decisão |
|---|---|---|
| build123d | API Python legível em modo Algebra/Builder, construída sobre OCP/OCC; operações B-rep, export STEP/STL, validação e utilidades de montagem | Backend primário. Agente consegue gerar código Python compacto, mantendo kernel OCC |
| CadQuery | Alternativa madura, Python sobre OCC, exporta sólidos e assemblies STEP; API fluent/Workplane excelente | Não incluído no runtime inicial para evitar dois motores/kernel versões concorrentes. Pode ser backend alternativo futuro |
| Open CASCADE/OCP | Kernel de modelagem B-rep subjacente; OCP é binding Python de baixo nível | Incluído transitivamente por build123d, usar APIs diretas apenas quando a API de alto nível não atender |
| FreeCAD API | Workbench paramétrico rico, scripting Python, muitas importações/exportações; ambiente maior e mais orientado ao app/documento | Não incluído inicialmente; GUI/versão e distribuição headless elevam custo para CLI mínima |
| OpenSCAD | CSG programático simples, CLI exporta malhas e PNG; não tem fluxo nativo equivalente de STEP B-rep | Útil para peças CSG simples, não satisfaz STEP paramétrico do baseline |

build123d suporta sólidos/assemblies e export STEP/STL; seu kernel valida a validade topológica. O projeto usa milímetros por contrato. Testes reais do container são gate para decidir compatibilidade da versão travada.

## Análise e visualização

- OCP/build123d: verdade geométrica B-rep, volume, bounding box e validade; base para métricas exatas e futura colisão por interseção.
- trimesh: leitura de STL e verificação de malha fechada/watertight, volumes de mesh e operações úteis. Não substitui validação CAD B-rep.
- NumPy/SciPy: dependências úteis para operações numéricas futuras, sem análise fabricada neste baseline.
- PNG: exporta malha STL via Matplotlib `Agg`; não requer X server, GUI, GPU nem pyglet. Preview é qualitativo.
- Espessura mínima de parede, colisão de assemblies, acessibilidade e estabilidade de impressão seguem `NOT_EVALUATED` enquanto não existir teste real implementado.

## Slicers

OrcaSlicer tem CLI headless documentada para carregar, transformar e fatiar com opções de máquina, filamento e processo. PrusaSlicer CLI documenta slicing e export G-code. Bambu Studio também documenta Command Line Usage, mas a compatibilidade/estabilidade de opções e perfis varia por release e alvo. Nenhum entra no contêiner CAD: CAD export e fatiamento são etapas separadas. Próxima fase pode adicionar adaptador explicitamente testado usando binários e perfis reais. Não automatizar envio/controle da impressora.

## MCP

Nenhum MCP CAD adotado. CLI estável oferece operação sem sessão e encaixa com projeto versionado; MCP adicionaria protocolo/servidor e dependência sem benefício demonstrado para build/test/export. Avaliar novamente quando houver necessidade de consulta interativa à geometria, controle de GUI ou integração CAD ao vivo. Pesquisa inicial não encontrou MCP CAD oficial com maturidade suficiente para preferir à CLI.

## V1.1: validação mecânica e assemblies

O runtime permanece build123d 0.11.1 sobre OCP 7.9.3.1.1. A montagem é descrita em YAML com IDs persistentes, referências às geometrias de peça, posição/orientação, interfaces, folgas e contatos intencionais. Nenhum solver de junta ou segundo kernel foi adicionado.

Os pares usam AABB como broad phase e operações B-rep OCP (`Shape & Shape` para volume comum e `BRepExtrema_DistShapeShape` para distância). A pesquisa atual do build123d confirma a API de interseção high-level; o teste no container demonstrou uma caixa separada, contato coplanar, uma interseção de volume conhecido e distâncias nominais de folga. Qualquer volume positivo é falha independentemente da intenção declarada de contato.

O relatório verifica paredes apenas a partir de dimensões nominais declaradas e nunca chama isso de medição geométrica. Para medição geral da espessura mínima seria necessário amostrar superfícies/raios e tratar paredes curvas, nervuras, furos e geometrias locais; não há base validada para declarar um mínimo global seguro nesta versão. Foi preferida checagem de parâmetro mais `NOT_EVALUATED` geométrico a um número aproximado enganoso.

Faixas por material para sliding, press fit, pin-hole, tampa removível e trilho são explicitamente iniciais/não calibradas. Press fit compara dimensões nominais de interface; o B-rep posicionado segue sujeito à regra independente que proíbe volume de interseção. Não há análise de força/contato elastoplástico. Envelope testa rotações ortogonais candidatas por peça, e risco de suporte é uma heurística de faces trianguladas; ambas não substituem fatiamento nem ensaio físico.

Referências do runtime: [documentação direta da API build123d](https://build123d.readthedocs.io/en/stable/direct_api_reference.html), [releases do build123d](https://github.com/gumyr/build123d/releases), [referência de OCP BRepExtrema](https://dev.opencascade.org/doc/refman/html/class_b_rep_extrema___dist_shape_shape.html). A versão de runtime continua travada na combinação testada em vez de atualizar automaticamente para uma release posterior.

## V1.2 — medição geométrica e fabricação

- Mantido o kernel build123d/OCP, já presente na imagem. Para paredes, a V1.2 classifica pontos paramétricos dentro de faces trimadas e usa `IntCurvesFace_ShapeIntersector` para lançar raios normais para dentro do B-rep; o primeiro hit é reportado como corda normal local. Isso é verificável em CAD analítico e mais direto que estimativas sobre STL, sem alegar mínimo medial-axis/exaustivo. Referência: [OCCT IntCurvesFace API](https://dev.opencascade.org/doc/occt-8.0.0/refman/html/_int_curves_face___intersector_8hxx.html) e [módulo BRepClass](https://dev.opencascade.org/doc/occt-7.3.0/refman/html/annotated.html). A implementação real executa em OCP 7.9.3.1.1, testado em contêiner. A abordagem reporta cobertura amostral e regiões não avaliadas.
- Mantido `BRepExtrema_DistShapeShape` para colisão/distância global; adicionado seletor geométrico face/superfície para medir interfaces funcionais. Planos opostos usam gap assinado; interseção de sólidos continua independente. Referência: [OCCT BRepExtrema_DistShapeShape](https://dev.opencascade.org/doc/occt-7.3.0/refman/html/annotated.html).
- Sequência de montagem é translação linear discretizada com B-rep em cada pose. Sem solver cinemático e sem promessa de varredura contínua.
- Orientação compara seis candidatos ortogonais; estima contato por triangulação e risco de suporte por normais de faces STL. Não é cálculo mecânico nem simulação de slicer.
- OrcaSlicer roda opcionalmente no host, fora da imagem CAD. Presets explícitos evitam presumir processo. Perfil/calibração só afeta projeto após escolha e fingerprint idêntico; medição não propaga automaticamente a projetos.
- Imagem versionada `cad3d-engineering:1.2.0`; runtime permanece Python 3.12.8, build123d 0.11.1, OCP 7.9.3.1.1. Nenhuma dependência Python nova foi adicionada.
