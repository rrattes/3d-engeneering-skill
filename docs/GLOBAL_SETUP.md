# Uso global no Arch Linux

A instalação global usa dois links simbólicos para manter este checkout como fonte de verdade; não duplica a skill nem constrói outra imagem.

## Atalhos instalados

- Skill Codex: `~/.agents/skills/3d-engineering` → `skills/3d-engineering` neste repositório.
- CLI: `~/.local/bin/cad3d` → `scripts/cad3d` neste repositório. `~/.local/bin` já precisa estar no `PATH` da sessão.
- Imagem CAD atual: `cad3d-engineering:1.9.0` (1.8.0 e anteriores ficam preservadas para rollback).

Codex suporta skills de usuário em `~/.agents/skills` e permite links simbólicos para diretórios de skill. A descrição da skill é usada para seleção automática; tarefas não relacionadas a CAD mecânico, CAD paramétrico ou impressão 3D não são seu escopo. Não há alteração em `~/.codex/config.toml`.

## Inicializar um projeto independente

```sh
mkdir -p "meu projeto mecânico"
cd "meu projeto mecânico"
cad3d init .
cad3d doctor
cad3d architecture init --level product
# Complete .cad3d/engineering.yaml and run dependency gates in order through visual_review.
cad3d workflow check --gate requirements
cad3d build
cad3d validate
cad3d export
cad3d render
cad3d report
cad3d test
cad3d calibration generate
# opcional, se OrcaSlicer e presets explícitos estiverem configurados:
cad3d slice
```

`init` copia somente o template/configuração (modelo, testes, `pyproject.toml`, `.cad3d/` e perfis declarativos). Não copia imagem, Dockerfile, dependências CAD ou ambiente Python. Ele pode inicializar uma pasta já existente, mas para sem sobrescrever se algum nome do template colidir. Os comandos CAD montam somente o diretório de trabalho como `/workspace`, usam o UID/GID corrente e não montam Docker socket nem abrem portas.

Parâmetros do modelo estão em `.cad3d/params.yaml`; impressora/material selecionados em `.cad3d/printer.yaml`; definições de perfis em `profiles/printers/` e `profiles/materials/`. O template inclui perfis iniciais para Bambu Lab A1 e Elegoo Centauri Carbon 2 Combo e materiais PLA, PETG, PETG-CF e ABS/ASA. Seus limites e tolerâncias são premissas genéricas não calibradas: registre medições reais antes de usá-las como especificação.

## Atualizações

1. Atualize este repositório versionado normalmente. Como skill e CLI são links, as mudanças em `skills/3d-engineering/SKILL.md` e `scripts/cad3d` ficam imediatamente disponíveis globalmente.
2. Se apenas modelo, CLI, perfis ou skill mudaram, não há imagem a reconstruir.
3. Se `Dockerfile` ou dependências travadas mudaram, a partir da raiz do repositório execute `docker compose build` e depois a regressão `cad3d test` em um projeto de aceitação.
4. A CLI consome `cad3d-engineering:1.9.0`; imagens anteriores permanecem para rollback compatível. Não limpe imagens anteriores indiscriminadamente.

Se a imagem não estiver disponível, `cad3d` explica como construí-la uma vez. O wrapper não constrói ou puxa imagens automaticamente.

## Verificação da instalação

```sh
readlink -f ~/.agents/skills/3d-engineering
readlink -f ~/.local/bin/cad3d
codex --version
cad3d doctor
```

Para testar o roteamento da skill, abra uma nova sessão Codex num diretório vazio e peça normalmente uma peça paramétrica mecânica, análise de encaixe/montagem ou preparação FDM; não é preciso fornecer o caminho da skill. Consulte `docs/V1.2_ACCEPTANCE.md` para a aceitação registrada.
