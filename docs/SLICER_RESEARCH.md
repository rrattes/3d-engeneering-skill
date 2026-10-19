# OrcaSlicer Manufacturing Engine

Atualização V1.3: integração anterior que procurava OrcaSlicer no host foi substituída por um engine Docker dedicado. O container CAD continua sem OrcaSlicer; nenhum executável Orca é instalado no Arch Linux.

## Versão e origem

- Versão escolhida: OrcaSlicer v2.4.2, release oficial estável.
- Artefato: `OrcaSlicer_Linux_AppImage_Ubuntu2404_V2.4.2.AppImage`, x86_64.
- Origem: release oficial GitHub [v2.4.2](https://github.com/OrcaSlicer/OrcaSlicer/releases/tag/v2.4.2).
- SHA-256 verificado durante build e registrado no Dockerfile: `d12fb8c8eac1aecd2dfb6377acd48f994f8fa439ed5292fa532dd82880f029fd`.
- Base Ubuntu 24.04; dependências gráficas/linker necessárias ao binário empacotado, mas o CLI opera sem DISPLAY/sessão interativa. O runtime baixa o AppImage oficial, valida hash e extrai AppDir; não executa AppImage via FUSE.
- Licença upstream OrcaSlicer: AGPL-3.0-or-later; a imagem contém programa binário. Código-fonte e avisos de licença: [repositório oficial OrcaSlicer](https://github.com/OrcaSlicer/OrcaSlicer). A imagem não publica portas/serviços.

O CLI oficial descreve execução headless sem abrir GUI, `--load-settings`, `--load-filaments`, `--slice` e exportação do projeto fatiado 3MF ([CLI mode](https://github.com/OrcaSlicer/OrcaSlicer/wiki/cli_mode), [CLI actions](https://github.com/OrcaSlicer/OrcaSlicer/wiki/cli_actions), [CLI misc](https://github.com/OrcaSlicer/OrcaSlicer/wiki/cli_misc)). Os comandos e flags foram exercitados com o executável real, não simulados. O `--slice` gera um `plate_1.gcode` transitório como efeito colateral mesmo que o entregável solicitado seja 3MF; o adaptador o remove imediatamente após extrair as estimativas e registra essa remoção. Não entrega G-code independente nem conecta ao equipamento.

## Perfis verificados

Do AppDir incluído na release v2.4.2 (mesma origem/versionamento do executável):

- Máquina `resources/profiles/Elegoo/machine/ECC2/Elegoo Centauri Carbon 2 0.4 nozzle.json`, `printer_model=Elegoo Centauri Carbon 2`, `nozzle_diameter=0.4`, área e altura declaradas 256×256×256 mm.
- PETG `resources/profiles/Elegoo/filament/ECC2/Elegoo PETG @ECC2.json`, compatível explicitamente com o preset ECC2 de bico 0.4.
- Processo `resources/profiles/Elegoo/process/ECC2/0.20mm Standard @Elegoo CC2 0.4 nozzle.json`, compatível explicitamente com esse preset de máquina.
- Doctor recursivamente verifica tipos e cada `inherits` no próprio diretório `Elegoo` da biblioteca oficial do AppDir, evitando confusão com perfis “Centauri Carbon” originais. SHA-256 é reportado para cada nó da cadeia.

Somente a combinação acima e single-color está habilitada nesta fase. A seleção usa os start/end e definições do perfil oficial. Não é inserido G-code inventado. Combo/AMS/multicolor, outros diâmetros e materiais não são permitidos no mapa inicial.

## Arquitetura/segurança

- Engine principal fica `cad3d-engineering:1.2.0`.
- Engine de fabricação fica `cad3d-orca:2.4.2`, build separado de `Dockerfile.orca`.
- `cad3d slicer build|doctor`, `cad3d slice`, `cad3d slice-report`.
- Orca só executa sob demanda com Docker Compose. Container não-root, `network_mode:none`, `read_only`, capacidades descartadas, `no-new-privileges`, sem portas/socket, somente projeto montado, `/tmp` isolado e limites Docker configuráveis por CPU, memória, processos e tamanho de tmpfs.
- Imagem não é privilegiada e não monta `$HOME`; usuário host passa por UID/GID.
- Slicer não comunica com a rede da impressora e nunca começa impressão.

## Relatórios

Entradas copiadas, artefatos 3MF fatiados, stdout/stderr e linha de comando, hashes, estimates disponíveis, report JSON e manifesto ficam em `build/slicer/`. O CLI checa código de retorno, CRC ZIP e presença de `3D/*.model` no 3MF. Estatísticas ausentes ficam `null`, não são inferidas. Dimensões STL/3MF são verificadas contra nominal 256 mm com margem configurável padrão de 5 mm por eixo antes do slicing. O perfil de máquina descreve um `host_type` da Elegoo; isso não é prova de que esse 3MF será aceito em todas as versões do aplicativo/dispositivo da Elegoo. O usuário precisa rever o projeto no fluxo oficialmente suportado.

Orientação opcional `--compare-orientations` executa até seis poses reais no CLI e compara estimativas parseáveis de tempo. Não determina resistência estrutural nem sucesso físico; estimativa ausente impede ordenação por tempo.

## Teste real

Ver `docs/V1.3_ACCEPTANCE.md`. O host não recebeu instalação Orca. O ambiente construiu o container Linux e invocou o binário real com rede desabilitada. Perfis ausentes/nomes desconhecidos falham explícitamente; um modelo fora do envelope é bloqueado antes da chamada.
