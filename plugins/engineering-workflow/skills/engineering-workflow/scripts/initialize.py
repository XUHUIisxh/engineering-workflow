#!/usr/bin/env python3
"""Preview, create or verify project-native roles without replacing files.

Python >= 3.9, standard library only. Project adapter remains project-owned.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

SKILL_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = SKILL_ROOT.parents[1]
ADAPTER = 'docs/agent-workflow/project-adapter.json'
LOCK = '.codex/engineering-workflow.lock.json'


class Conflict(Exception):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def project_path(root, relative):
    """Reject both lexical escape and symlinks in any existing component."""
    if not isinstance(relative, str) or not relative:
        raise Conflict('Project path must be a non-empty relative string')
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts or path == Path('.'):
        raise Conflict('Path outside project or invalid: ' + relative)
    cursor = root
    for part in path.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise Conflict('Symlink path is not allowed: ' + relative)
    return root / path


def read_adapter(root):
    path = project_path(root, ADAPTER)
    if path.exists():
        adapter = json.loads(path.read_text(encoding='utf-8'))
    else:
        adapter = {'schema_version': 1, 'project_name': root.name,
                   'workflow': [], 'conventions': [], 'role_documents': {},
                   'cycle_root': 'docs/agent-workflow/cycles'}
    if not isinstance(adapter, dict) or adapter.get('schema_version') != 1:
        raise Conflict('Unsupported project adapter schema')
    if not isinstance(adapter.get('project_name'), str) or not adapter['project_name'].strip():
        raise Conflict('project_name must be a non-empty string')
    references = []
    for key in ('workflow', 'conventions'):
        values = adapter.get(key)
        if not isinstance(values, list):
            raise Conflict(key + ' must be a list of project file paths')
        references.extend(values)
    roles = adapter.get('role_documents')
    if not isinstance(roles, dict):
        raise Conflict('role_documents must be an object')
    supported = {p.stem.removeprefix('engineering_') for p in (SKILL_ROOT / 'assets/agents').glob('*.toml')}
    if set(roles) - supported:
        raise Conflict('Unknown role_documents keys: ' + ', '.join(sorted(set(roles) - supported)))
    references.extend(roles.values())
    for reference in references:
        if not project_path(root, reference).is_file():
            raise Conflict('Missing project reference: ' + str(reference))
    cycle_path = project_path(root, adapter.get('cycle_root'))
    if cycle_path.exists() and not cycle_path.is_dir():
        raise Conflict('cycle_root must be a directory')
    return adapter, None if path.exists() else json_bytes(adapter)


def source_digest():
    # Hash production resources only. Runtime caches and tests do not define the package.
    paths = [PLUGIN_ROOT / 'plugin.json'] + sorted((PLUGIN_ROOT / 'skills').rglob('*'))
    paths += sorted((PLUGIN_ROOT / 'hooks').rglob('*'))
    files = {p.relative_to(PLUGIN_ROOT).as_posix(): digest(p.read_bytes())
             for p in paths if p.is_file() and '__pycache__' not in p.parts
             and p.suffix != '.pyc'}
    return digest(json_bytes(files))


def build_plan(root):
    adapter, new_adapter = read_adapter(root)
    manifest = json.loads((PLUGIN_ROOT / 'plugin.json').read_text(encoding='utf-8'))
    templates = sorted((SKILL_ROOT / 'assets/agents').glob('*.toml'))
    if not templates:
        raise Conflict('Plugin has no native role templates')
    generated = {'.codex/agents/' + p.name: p.read_bytes() for p in templates}
    lock = {'schema_version': 1, 'plugin': manifest['name'], 'version': manifest['version'],
            'source_sha256': source_digest(),
            'generated_files': {p: digest(data) for p, data in generated.items()}}
    files = dict(generated)
    if new_adapter is not None:
        files[ADAPTER] = new_adapter
    files[LOCK] = json_bytes(lock)
    create, keep, conflicts = [], [], []
    for relative, data in files.items():
        target = project_path(root, relative)
        if not target.exists():
            create.append(relative)
        elif target.is_file() and target.read_bytes() == data:
            keep.append(relative)
        else:
            conflicts.append(relative)
    if conflicts:
        raise Conflict('Existing file conflicts; nothing written: ' + ', '.join(conflicts))
    report = {'project_name': adapter['project_name'], 'plugin': manifest['name'],
              'version': manifest['version'], 'source_sha256': lock['source_sha256'],
              'context_status': 'READY' if all(adapter[k] for k in
                                             ('workflow', 'conventions', 'role_documents'))
              else 'NEEDS_CONTEXT', 'create': create, 'keep': keep}
    return files, report


def open_parent(root_fd, relative):
    """Anchor traversal to directory handles; never follow a replaced link."""
    parent_fd = os.dup(root_fd)
    try:
        for part in Path(relative).parts[:-1]:
            try:
                os.mkdir(part, dir_fd=parent_fd)
            except FileExistsError:
                pass
            child_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                               dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = child_fd
        return parent_fd
    except Exception:
        os.close(parent_fd)
        raise


def rollback_created(created):
    """Best-effort cleanup under the single-writer contract.

    Detected changes are preserved. POSIX has no atomic compare-and-unlink;
    callers must not concurrently edit these paths during initialization.
    """
    preserved = []
    for entry in reversed(created):
        parent_fd, name, identity, expected, relative = entry
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                         dir_fd=parent_fd)
            with os.fdopen(fd, 'rb') as stream:
                current = os.fstat(stream.fileno())
                actual = hashlib.sha256()
                if not stat.S_ISREG(current.st_mode):
                    raise Conflict('Not a regular file')
                if (current.st_dev, current.st_ino) != identity:
                    raise Conflict('File replaced')
                for chunk in iter(lambda: stream.read(65536), b''):
                    actual.update(chunk)
                if actual.hexdigest() != expected.hexdigest():
                    raise Conflict('File edited')
                latest = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
                if (latest.st_dev, latest.st_ino, latest.st_size, latest.st_mtime_ns,
                    latest.st_ctime_ns) != (current.st_dev, current.st_ino, current.st_size,
                                           current.st_mtime_ns, current.st_ctime_ns):
                    raise Conflict('File changed during cleanup')
                os.unlink(name, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        except (OSError, Conflict):
            preserved.append(relative)
    return preserved


def apply_plan(root, files, create):
    if not create:
        return
    if not all(hasattr(os, flag) for flag in ('O_DIRECTORY', 'O_NOFOLLOW')):
        raise Conflict('Safe initialization requires POSIX directory handles (macOS/Linux)')
    root_fd = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    created = []
    try:
        for relative in create:
            project_path(root, relative)
            parent_fd = open_parent(root_fd, relative)
            name = Path(relative).name
            try:
                fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o644, dir_fd=parent_fd)
            except Exception:
                os.close(parent_fd)
                raise
            current = os.fstat(fd)
            written = hashlib.sha256()
            created.append((parent_fd, name, (current.st_dev, current.st_ino), written, relative))
            try:
                remaining = memoryview(files[relative])
                while remaining:
                    count = os.write(fd, remaining)
                    if count <= 0:
                        raise OSError('File write did not progress')
                    written.update(remaining[:count])
                    remaining = remaining[count:]
            finally:
                os.close(fd)
    except Exception as error:
        preserved = rollback_created(created)
        if preserved:
            raise Conflict(str(error) + '; cleanup preserved changed/unreadable files: '
                           + ', '.join(preserved)) from error
        raise
    finally:
        for parent_fd, *_ in created:
            os.close(parent_fd)
        os.close(root_fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, help='Existing project root (never inferred from plugin cwd)')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true', help='Preview only (default)')
    mode.add_argument('--apply', action='store_true', help='Create missing files after full conflict preflight')
    mode.add_argument('--check', action='store_true', help='Verify adapter, plugin lock and all generated roles')
    args = parser.parse_args()
    try:
        root = Path(args.project).resolve(strict=True)
        if not root.is_dir():
            raise Conflict('Project root must be a directory')
        files, report = build_plan(root)
        if args.check and report['create']:
            raise Conflict('Initialization incomplete: ' + ', '.join(report['create']))
        if args.apply:
            apply_plan(root, files, report['create'])
        report['mode'] = 'check' if args.check else 'apply' if args.apply else 'dry-run'
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (Conflict, OSError, ValueError, KeyError, TypeError) as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
