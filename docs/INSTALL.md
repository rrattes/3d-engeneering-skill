# CAD3D Kit — instalação e uso

Kit local para Codex ou Claude Code. Requer Docker Engine e Docker Compose v2, bash, Python3 para os orquestradores e utilitários GNU do wrapper (incluindo readlink -f). Primeiro alvo de suporte: Linuxx86_64. WSL/macOS/ARM e descoberta em agentes não executados permanecem NOT_EVALUATED.

1. Extraia o ZIP numa pasta própria, inclusive com espaços se desejar.
2. Confira FILE_MANIFEST.json. A imagem Docker não está embutida no ZIP de fontes.
3. Se você recebeu uma imagem exportada pelo autor, importe com `docker load -i imagem.tar`. Caso contrário construa a receita completa: `docker compose build cad3d`. Downloads são necessários durante a construção.
4. Na raiz do kit, execute `./scripts/cad3d doctor`. Se a permissão do ZIP não foi preservada, use `bash scripts/cad3d doctor` ou ajuste o executável.
5. Na sessão atual: `export PATH="$PWD/scripts:$PATH"`. O wrapper resolve sua localização; não há necessidade de instalar links globais.
6. Crie um projeto em diretório novo: `cad3d init projects/meu-projeto`. O template inclui os gates obrigatórios. Para um projeto existente, rode `cad3d workflow init`; em ambos, complete `.cad3d/engineering.yaml` com `cad3d architecture init --level product`, registre requisitos e evidências e execute `cad3d workflow check --gate requirements`, depois cada gate na ordem indicada pela skill, avançando somente com PASS.
7. Para protótipos: `cad3d build`, `cad3d render --view presentation`, `cad3d render --view parts`; quando elegível, `cad3d release --target cad-prototype` publica entrega selecionada. Consulte o apontador build/delivery/current.json.

As pastas .agents/skills e .claude/skills contêm projeções da mesma skill. Abra Codex ou Claude Code na raiz do kit; forneça AGENTS.md/CLAUDE.md e o briefing ao iniciar. A disponibilidade da skill deve ser conferida no agente real; presença de arquivo não prova descoberta. Após criar um projeto independente, mantenha acesso à skill do kit ou instale-a pelo mecanismo do seu agente sem substituir uma versão pessoal silenciosamente.

Nenhum banco de dados é necessário. O kit não instala SQLite/Qdrant, não contém credenciais e não envia trabalhos à impressora. O motor Orca é opcional: `cad3d slicer build` e preflight com impressora/material/processo exatos. Perfil ausente não deve ser substituído por outro material. O suporte real da impressora e a validação física são separados do CAD/fatiamento.

Leia as referências da skill conforme o tipo de projeto. Use só as capacidades de apoio necessárias: diagnóstico, impacto, testes e revisão. As outras skills globais do autor não são dependência obrigatória nem estão copiadas integralmente neste kit.

## Licenças e origem

Preservar avisos existentes das fontes e das dependências, incluindo licenses/ORCASLICER-LICENSE.txt. Não atribuir licença livre genérica a um conjunto sem licença definida pelo proprietário. Este pacote não inclui binários de dependências no ZIP de fontes; redistribuir imagens/binários exige conservar as obrigações aplicáveis. Definição da licença do código próprio para publicação pública permanece decisão do proprietário.

## Limites de reprodução

Manifestos vinculam arquivos, configuração e versão do motor; isso não registra automaticamente toda influência externa. Não modificar fontes durante execução. Medidas comerciais, roscas, tolerâncias, material, retenção, carga e temperatura precisam de confirmação. Os exemplos são fixtures, não produtos homologados.

## Helical service contract (1.6.0+)

Use image `cad3d-engineering:1.9.0` with this kit. The approved
1.8.0 image remains preserved for rollback. The engineering skill reference
`skills/3d-engineering/references/helical_motion.md` documents native sampled helical
paths. Confirm the installed version with `cad3d doctor`; earlier images do not
validate this contract. Linear contracts remain supported.

## Reliability contracts (1.7.0+)

See `skills/3d-engineering/references/reliability.md` for shared atomic-solid
interference checks, trimmed-face point anchors and signed worst-case tolerance
chains. Assumed/unknown uncertainty cannot publish as assembly PASS.

## General capabilities (1.8.0+)

See skills/3d-engineering/references/general_capabilities.md for interface generation,
rotation/composite paths, variants, measured fit records, access/cable envelopes,
SVG/PDF sections/dimensions and preliminary cantilever screening. Select only the
relevant contracts. Current manufacturing identity and requested drawing references
are checked before publication. These tools never start a print or certify a part.
