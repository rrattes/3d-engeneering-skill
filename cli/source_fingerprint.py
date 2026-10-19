"""Bounded project-local source/config inventory shared by builds and reviews.

Conservatively includes every non-generated Python/JSON/YAML/TOML/INI/CFG file,
not just statically visible imports. project.source_inputs lists additional exact
project-relative files (no globs/directories). Does not execute project code or
follow symlinks. External modules, environment variables and files outside this
closure need separate provenance; this is source freshness, not reproducibility.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

SCHEMA = 'cad3d-project-inputs-v1'
EXTENSIONS = {'.py', '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg'}
EXCLUDED = {'build', 'dist', 'reports', 'renders', 'exports', 'artifacts',
            '__pycache__', 'node_modules', 'venv', 'env'}
MAX_ENTRIES = 50000
MAX_FILES = 10000
MAX_BYTES = 32 * 1024 * 1024
MAX_DEPTH = 20


def _relative(value):
    if not isinstance(value, str) or not value:
        raise ValueError('source input must be a nonempty project-relative path')
    path = Path(value)
    if path.is_absolute() or '..' in path.parts or path == Path('.'):
        raise ValueError('source input paths must remain inside the project')
    return path


def _safe_path(root, relative):
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f'symlink is not a supported source input: {relative}')
    if not current.resolve().is_relative_to(root):
        raise ValueError(f'source input escapes project: {relative}')
    return current


def project_fingerprint(project_root):
    import yaml
    root = Path(project_root).resolve()
    project_file = _safe_path(root, Path('.cad3d/project.yaml'))
    if project_file.stat().st_size > MAX_BYTES:
        raise ValueError('project config exceeds fingerprint size bound')
    cfg = (yaml.safe_load(project_file.read_text()) or {}).get('project', {})
    output = _relative(cfg.get('output', 'build/outputs'))
    # Validate mandatory paths even when an excluded folder would hide them.
    mandatory = {_relative(cfg['model']), Path('.cad3d') / _relative(cfg.get('parameters', 'params.yaml'))}
    extra = cfg.get('source_inputs', [])
    if not isinstance(extra, list):
        raise ValueError('project.source_inputs must be a list of exact local file paths')
    explicit = {_relative(value) for value in extra} | mandatory | {Path('.cad3d/project.yaml')}
    for relative in explicit:
        _safe_path(root, relative)
        if output == relative or output in relative.parents or any(
                part in EXCLUDED or (part.startswith('.') and part != '.cad3d') for part in relative.parts):
            raise ValueError(f'source input overlaps excluded/generated paths: {relative}')

    files = set(explicit)
    entries = 0

    def walk(directory, depth=0):
        nonlocal entries
        if depth > MAX_DEPTH:
            raise ValueError('project source tree exceeds depth bound')
        with os.scandir(root / directory) as children:
            for child in children:
                entries += 1
                if entries > MAX_ENTRIES:
                    raise ValueError('project source tree exceeds entry bound')
                relative = directory / child.name
                if child.name in EXCLUDED or (child.name.startswith('.') and relative != Path('.cad3d')):
                    continue
                if relative == output:
                    continue
                if child.is_symlink():
                    # Reject directory links and selected file links without following either.
                    if Path(child.name).suffix.lower() in EXTENSIONS or child.is_dir():
                        raise ValueError(f'symlink in project source tree: {relative}')
                    continue
                if child.is_dir(follow_symlinks=False):
                    walk(relative, depth + 1)
                elif child.is_file(follow_symlinks=False) and relative.suffix.lower() in EXTENSIONS:
                    files.add(relative)
                    if len(files) > MAX_FILES:
                        raise ValueError('project source inventory exceeds file bound')

    walk(Path('.'))
    records = []
    total_bytes = 0
    if len(files) > MAX_FILES:
        raise ValueError('project source inventory exceeds file bound')
    for relative in sorted(files):
        path = _safe_path(root, relative)
        # A deleted declared input cannot produce a new trustworthy fingerprint.
        if not path.is_file():
            raise ValueError(f'declared source input is missing or not a file: {relative}')
        total_bytes += path.stat().st_size
        if total_bytes > MAX_BYTES:
            raise ValueError('project source inventory exceeds byte bound')
        with path.open('rb') as stream:
            data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError('project source file exceeds byte bound')
        records.append({'path': relative.as_posix(), 'sha256': hashlib.sha256(data).hexdigest()})
    payload = json.dumps(records, sort_keys=True, separators=(',', ':')).encode()
    return {'schema': SCHEMA, 'sha256': hashlib.sha256(payload).hexdigest(), 'files': records,
            'scope': 'project-local Python and configuration plus declared source_inputs; excludes generated/cache/hidden paths and external runtime inputs'}
