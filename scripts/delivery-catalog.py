#!/usr/bin/env python3
"""Generate a delivery catalog using only the Python standard library.

Run on the host. No CAD execution, geometry checking or visual inspection.
"""

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import quote


START = '<!-- cad3d:delivery-catalog:start -->'
END = '<!-- cad3d:delivery-catalog:end -->'


def confined(base, relative):
    """Reject absolute paths, traversal and links escaping the selected scope."""
    if not isinstance(relative, str) or not relative or '\\' in relative:
        raise ValueError(f'Caminho inválido: {relative!r}')
    parts = PurePosixPath(relative)
    if parts.is_absolute() or '..' in parts.parts:
        raise ValueError(f'Caminho fora do escopo: {relative}')
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError(f'Caminho fora do escopo: {relative}')
    return path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def cell(value):
    return str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('|', '&#124;').replace('\n', ' ').replace('\r', ' ')


def link(base, path):
    return quote(Path(os.path.relpath(path, base)).as_posix(), safe='/.-_')


def write_changed(path, content):
    if path.is_file() and path.read_bytes() == content.encode('utf-8'):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(content, encoding='utf-8')
    temporary.replace(path)
    return True


def generate(project, update_readme=False, output_dir='docs'):
    project = project.resolve(strict=True)
    pointer_path = confined(project, 'build/delivery/current.json')
    pointer_bytes = pointer_path.read_bytes()
    pointer = json.loads(pointer_bytes)
    if pointer.get('schema') != 'cad3d-delivery-v1':
        raise ValueError('Schema do ponteiro de entrega não suportado')
    run = pointer.get('run_id', '')
    if not isinstance(run, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', run):
        raise ValueError('run_id inválido')
    expected = f'build/delivery/releases/{run}'
    if pointer.get('directory') != expected:
        raise ValueError('Diretório não corresponde à execução selecionada')
    delivery = confined(project, expected)
    manifest_bytes = confined(delivery, 'manifest.json').read_bytes()
    if digest(manifest_bytes) != pointer.get('manifest_sha256'):
        raise ValueError('Hash do manifesto diverge do ponteiro de entrega')
    manifest = json.loads(manifest_bytes)
    artifacts = {}
    for artifact in manifest['artifacts']:
        name = artifact['path']
        confined(delivery, name)
        if name in artifacts:
            raise ValueError(f'Artefato duplicado: {name}')
        artifacts[name] = artifact
    verified = {}

    def read_artifact(name):
        if name not in artifacts:
            raise ValueError(f'Artefato não registrado no manifesto: {name}')
        data = confined(delivery, name).read_bytes()
        record = artifacts[name]
        if not data or len(data) != record['bytes'] or digest(data) != record['sha256']:
            raise ValueError(f'Artefato vazio ou divergente: {name}')
        verified[name] = {'path': name, 'bytes': len(data), 'sha256': digest(data)}
        return data

    config_path = confined(project, '.cad3d/delivery-catalog.json')
    config = json.loads(config_path.read_text(encoding='utf-8')) if config_path.exists() else {}
    if not isinstance(config, dict):
        raise ValueError('Configuração do catálogo deve ser um objeto JSON')
    labels = config.get('labels', {})
    if not isinstance(labels, dict) or any(not isinstance(v, str) for v in labels.values()):
        raise ValueError('labels deve mapear identificadores para textos')
    rows = list(csv.DictReader(io.StringIO(read_artifact('BOM.csv').decode('utf-8-sig'))))
    if not rows:
        raise ValueError('BOM vazia')
    parts, references, missing_images, seen = [], [], [], set()
    for row in rows:
        name = row['part']
        if not re.fullmatch(r'[A-Za-z0-9_-]+', name) or name in seen:
            raise ValueError(f'Identificador inválido/duplicado na BOM: {name}')
        seen.add(name)
        quantity_text = row['quantity']
        if not re.fullmatch(r'[1-9][0-9]*', quantity_text):
            raise ValueError(f'Quantidade inválida na BOM: {name}')
        item = {'part': name, 'label': labels.get(name, name), 'quantity': int(quantity_text),
                'kind': row['kind'], 'process': row['process'], 'material': row['material']}
        if row['kind'] != 'manufactured' or row['process'].lower() != 'fdm':
            references.append(item)
            continue
        stl = name + '.stl'
        read_artifact(stl)
        image = f'parts/{name}.png'
        item['stl'] = stl
        if image in artifacts:
            read_artifact(image)
            item['image'] = image
        else:
            item['image'] = None
            missing_images.append(name)
        parts.append(item)
    if not parts:
        raise ValueError('Nenhuma peça manufactured/fdm encontrada na BOM')
    views = []
    for name, label in [('A_assembly_iso.png', 'Conjunto montado'), ('F_exploded.png', 'Vista explodida')]:
        if name in artifacts:
            read_artifact(name)
            views.append({'path': name, 'label': label})
    report = {
        'schema': 'cad3d-delivery-catalog-v1', 'project': manifest.get('project', project.name),
        'run_id': run, 'delivery_directory': expected, 'manifest_sha256': digest(manifest_bytes),
        'pointer_sha256': digest(pointer_bytes),
        'config_sha256': digest(config_path.read_bytes()) if config_path.exists() else None,
        'distinct_stls': len(parts), 'printed_units': sum(p['quantity'] for p in parts),
        'parts': parts, 'non_fdm_items': references, 'views': views,
        'missing_images': missing_images, 'integrity_of_consulted_artifacts': 'PASS',
        'visual_review': 'NOT_EVALUATED',
        'physical_validation': pointer.get('physical_validation', 'NOT_EVALUATED'),
        'verified_artifacts': [verified[key] for key in sorted(verified)],
    }
    output = confined(project, f'{output_dir}/CATALOGO_ENTREGA.md')
    json_output = confined(project, f'{output_dir}/CATALOGO_ENTREGA.json')
    readme = confined(project, 'README.md')
    for path in (output, json_output, readme):
        if path.is_relative_to(confined(project, 'build/delivery')):
            raise ValueError('Saída não pode modificar a entrega imutável')
    lines = ['# Catálogo da entrega selecionada', '',
             'Gerado por `delivery-catalog.py`. Quantidades e materiais vêm da BOM; nomes de apresentação são opcionais.', '',
             f'Execução: `{run}`. Manifesto SHA256: `{report["manifest_sha256"]}`.', '',
             f'**{len(parts)} STLs distintos; {report["printed_units"]} peças a imprimir.**', '',
             '| Peça | STL | Imagem CAD | Quantidade | Material |', '|---|---|---|---:|---|']
    for item in parts:
        stl_url = link(output.parent, delivery / item['stl'])
        image_url = link(output.parent, delivery / item['image']) if item['image'] else None
        image_cell = f'[Ver imagem]({image_url})' if image_url else '**Imagem ausente**'
        lines.append(f'| {cell(item["label"])} | [{cell(item["stl"])}]({stl_url}) | {image_cell} | {item["quantity"]} | {cell(item["material"])} |')
    lines += ['', '## Vistas do conjunto', '']
    lines += [f'- [{view["label"]}]({link(output.parent, delivery / view["path"])})' for view in views] or ['Vistas não disponíveis no manifesto.']
    if references:
        lines += ['', '## Itens fora da impressão FDM', '', '| Item | Quantidade | Tipo | Processo |', '|---|---:|---|---|']
        lines += [f'| {cell(i["label"])} | {i["quantity"]} | {cell(i["kind"])} | {cell(i["process"])} |' for i in references]
    lines += ['', '## Alcance da conferência', '',
              'Hash do manifesto e tamanho/SHA256 da BOM, STLs e imagens vinculados conferidos. Outros artefatos do manifesto não foram inspecionados por este comando.', '',
              f'Imagens individuais ausentes: {", ".join(missing_images) if missing_images else "nenhuma"}.', '',
              'A conferência é de integridade dos arquivos consultados. Não executa CAD, revisão visual, fatiamento ou ensaio físico, nem compara a entrega com fontes atuais do projeto.', '',
              f'Validação física declarada no ponteiro: `{cell(report["physical_validation"])}`. Consulte o README e os relatórios do produto para as demais pendências.', '',
              '[Dados estruturados do catálogo](CATALOGO_ENTREGA.json).', '']
    readme_text = None
    if update_readme:
        readme_text = readme.read_text(encoding='utf-8') if readme.exists() else f'# {project.name}\n'
        block = (f'{START}\n## Catálogo de peças da entrega\n\n'
                 f'[Abrir STLs, imagens e quantidades]({link(readme.parent, output)}). '
                 f'**{len(parts)} arquivos STL; {report["printed_units"]} unidades a imprimir.**\n\n'
                 f'Execução `{run}`. Integridade dos arquivos consultados conferida; '
                 f'validação física declarada: `{cell(report["physical_validation"])}`.\n{END}')
        if readme_text.count(START) != readme_text.count(END) or readme_text.count(START) > 1:
            raise ValueError('Bloco gerenciado duplicado ou incompleto no README')
        if START in readme_text:
            start, end = readme_text.index(START), readme_text.index(END)
            if end < start:
                raise ValueError('Ordem inválida dos marcadores no README')
            readme_text = readme_text[:start] + block + readme_text[end + len(END):]
        else:
            readme_text = readme_text.rstrip() + '\n\n' + block + '\n'
    if pointer_path.read_bytes() != pointer_bytes:
        raise ValueError('Entrega selecionada mudou durante a geração; repetir comando')
    changed = []
    for path, content in [(output, '\n'.join(lines)), (json_output, json.dumps(report, ensure_ascii=False, indent=2) + '\n')]:
        if write_changed(path, content):
            changed.append(str(path.relative_to(project)))
    if readme_text is not None and write_changed(readme, readme_text):
        changed.append('README.md')
    return {'run_id': run, 'stls': len(parts), 'units': report['printed_units'],
            'missing_images': missing_images, 'changed': changed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--output-dir', default='docs', help='Pasta relativa de saída; usar reports para artefatos gerados fora do inventário de fontes CAD')
    parser.add_argument('--update-readme', action='store_true', help='Atualizar somente o bloco gerenciado do README')
    args = parser.parse_args()
    try:
        result = generate(args.project, args.update_readme, args.output_dir)
    except (ValueError, OSError, KeyError, TypeError, csv.Error) as exc:
        print(f'Catálogo não gerado: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
