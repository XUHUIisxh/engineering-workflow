"""Exercise real CLI side effects; regressions named by each test."""
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = pathlib.Path(__file__).parents[1] / 'skills/engineering-workflow/scripts/initialize.py'


class InitializeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name) / 'go-svelte-project'
        self.root.mkdir()
        (self.root / 'README.md').write_text('Go + PostgreSQL + Svelte\n')

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), '--project', str(self.root), *args],
                              capture_output=True, text=True)

    def snapshot(self):
        return {str(f.relative_to(self.root)): (hashlib.sha256(f.read_bytes()).hexdigest(),
                                               f.stat().st_mtime_ns)
                for f in self.root.rglob('*') if f.is_file()}

    def test_preview_does_not_write(self):
        before = self.snapshot()
        result = self.run_cli('--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(json.loads(result.stdout)['create'])

    def test_apply_creates_native_roles_and_preserves_existing_custom_role(self):
        agents = self.root / '.codex/agents'
        agents.mkdir(parents=True)
        personal = agents / 'frontend.toml'
        personal.write_text('name = "personal_frontend"\n')
        before = personal.read_bytes()
        result = self.run_cli('--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(personal.read_bytes(), before)
        import tomllib
        roles = [tomllib.loads(f.read_text()) for f in agents.glob('engineering_*.toml')]
        self.assertEqual(len(roles), 13)
        self.assertEqual(len({r['name'] for r in roles}), 13)
        self.assertTrue(all(r['description'] and r['developer_instructions'] for r in roles))
        self.assertEqual(self.run_cli('--check').returncode, 0)

    def test_repeat_apply_preserves_content_and_mtime(self):
        first = self.run_cli('--apply')
        self.assertEqual(first.returncode, 0, first.stderr)
        before = self.snapshot()
        result = self.run_cli('--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(json.loads(result.stdout)['create'], [])

    def test_conflicting_target_aborts_all_writes(self):
        agents = self.root / '.codex/agents'
        agents.mkdir(parents=True)
        (agents / 'engineering_backend.toml').write_text('personal customization\n')
        before = self.snapshot()
        result = self.run_cli('--apply')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.snapshot(), before)
        self.assertIn('engineering_backend.toml', result.stderr)

    def test_local_edit_is_detected_and_never_overwritten(self):
        self.assertEqual(self.run_cli('--apply').returncode, 0)
        target = self.root / '.codex/agents/engineering_frontend.toml'
        target.write_text(target.read_text() + '\n# personal change\n')
        before = self.snapshot()
        self.assertEqual(self.run_cli('--check').returncode, 1)
        self.assertEqual(self.run_cli('--apply').returncode, 1)
        self.assertEqual(self.snapshot(), before)

    def test_symlink_directory_cannot_redirect_writes(self):
        outside = pathlib.Path(self.temp.name) / 'outside'
        outside.mkdir()
        (self.root / '.codex').symlink_to(outside, target_is_directory=True)
        result = self.run_cli('--apply')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.root / 'docs').exists())

    def write_adapter(self, workflow):
        target = self.root / 'docs/agent-workflow/project-adapter.json'
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps({'schema_version': 1, 'project_name': 'go-order-service',
                                     'workflow': workflow, 'conventions': [],
                                     'role_documents': {}, 'cycle_root': 'docs/cycles'}))
        return target

    def test_project_owned_adapter_is_preserved_and_references_validated(self):
        (self.root / 'WORKFLOW.md').write_text('Go project governance\n')
        target = self.write_adapter(['WORKFLOW.md'])
        before = target.read_bytes()
        result = self.run_cli('--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(target.read_bytes(), before)
        self.assertEqual(json.loads(result.stdout)['project_name'], 'go-order-service')

    def test_missing_reference_aborts_before_creating_roles(self):
        self.write_adapter(['missing.md'])
        before = self.snapshot()
        result = self.run_cli('--apply')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_adapter_cannot_reference_outside_project(self):
        (pathlib.Path(self.temp.name) / 'outside.md').write_text('outside')
        self.write_adapter(['../outside.md'])
        result = self.run_cli('--apply')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse((self.root / '.codex').exists())

    def test_uninitialized_project_check_fails_without_writes(self):
        before = self.snapshot()
        self.assertEqual(self.run_cli('--check').returncode, 1)
        self.assertEqual(self.snapshot(), before)

    def test_unknown_stack_remains_needs_context_instead_of_guessing(self):
        result = self.run_cli('--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['context_status'], 'NEEDS_CONTEXT')
        adapter = json.loads((self.root / 'docs/agent-workflow/project-adapter.json').read_text())
        self.assertEqual(adapter['conventions'], [])
        self.assertEqual(adapter['role_documents'], {})

    def test_new_plugin_version_requires_explicit_migration(self):
        self.assertEqual(self.run_cli('--apply').returncode, 0)
        before = self.snapshot()
        updated = pathlib.Path(self.temp.name) / 'updated-plugin'
        shutil.copytree(SCRIPT.parents[3], updated, ignore=shutil.ignore_patterns('__pycache__'))
        manifest = updated / 'plugin.json'
        value = json.loads(manifest.read_text())
        value['version'] = '0.2.1'
        manifest.write_text(json.dumps(value))
        script = updated / 'skills/engineering-workflow/scripts/initialize.py'
        result = subprocess.run([sys.executable, str(script), '--project', str(self.root), '--apply'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('engineering-workflow.lock.json', result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_directory_swap_during_write_cannot_escape_and_rolls_back(self):
        spec = importlib.util.spec_from_file_location('initialize_race', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        files, report = module.build_plan(self.root)
        outside = pathlib.Path(self.temp.name) / 'race-outside'
        outside.mkdir()
        (outside / 'agents').mkdir()
        original = self.root / '.codex-original'
        real_open = os.open
        swapped = False

        def swap_then_open(path, flags, *args, **kwargs):
            nonlocal swapped
            if not swapped and pathlib.Path(path).name == 'engineering_architecture.toml':
                swapped = True
                (self.root / '.codex').rename(original)
                (self.root / '.codex').symlink_to(outside, target_is_directory=True)
            return real_open(path, flags, *args, **kwargs)

        with patch.object(module.os, 'open', side_effect=swap_then_open):
            with self.assertRaises((OSError, module.Conflict)):
                module.apply_plan(self.root, files, report['create'])
        self.assertTrue(swapped)
        self.assertEqual(list(outside.rglob('*.toml')), [])
        self.assertEqual(list(original.rglob('*.toml')), [])
        self.assertFalse((self.root / 'docs').exists())

    def test_rollback_preserves_replaced_or_edited_user_file(self):
        for replacement in (True, False):
            with self.subTest(replacement=replacement), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                spec = importlib.util.spec_from_file_location('initialize_rollback', SCRIPT)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                files, report = module.build_plan(root)
                first, second = (root / relative for relative in report['create'][:2])
                real_open = os.open
                modified = False

                def modify_then_conflict(path, flags, *args, **kwargs):
                    nonlocal modified
                    if not modified and pathlib.Path(path).name == second.name:
                        modified = True
                        if replacement:
                            first.unlink()
                        first.write_text('user content must survive\n')
                        second.write_text('concurrent user file\n')
                    return real_open(path, flags, *args, **kwargs)

                with patch.object(module.os, 'open', side_effect=modify_then_conflict):
                    with self.assertRaises((OSError, module.Conflict)):
                        module.apply_plan(root, files, report['create'])
                self.assertTrue(modified)
                self.assertTrue(first.exists(), 'Rollback deleted user content')
                self.assertEqual(first.read_text(), 'user content must survive\n')
                self.assertEqual(second.read_text(), 'concurrent user file\n')

    def test_partial_write_failure_removes_unchanged_created_files(self):
        spec = importlib.util.spec_from_file_location('initialize_partial', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        files, report = module.build_plan(self.root)
        real_write = os.write
        calls = 0

        def partial_then_fail(fd, data):
            nonlocal calls
            calls += 1
            if calls == 2:
                return real_write(fd, data[:10])
            if calls == 3:
                raise OSError('injected write failure')
            return real_write(fd, data)

        with patch.object(module.os, 'write', side_effect=partial_then_fail):
            with self.assertRaisesRegex(OSError, 'injected write failure'):
                module.apply_plan(self.root, files, report['create'])
        self.assertEqual(calls, 3)
        self.assertEqual(self.snapshot().keys(), {'README.md'})


if __name__ == '__main__':
    unittest.main()
