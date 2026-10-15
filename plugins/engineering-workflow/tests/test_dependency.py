"""Verify the plugin dependency gate without changing the user's Codex installation."""
import importlib.util
import io
import json
from pathlib import Path
from contextlib import redirect_stdout
import sys
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).parents[1] / 'skills/engineering-workflow/scripts/ensure_dependency.py'
SPEC = importlib.util.spec_from_file_location('ensure_dependency', SCRIPT)
dependency = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dependency)


class DependencyTests(unittest.TestCase):
    def test_stable_baseline_and_build_metadata_are_ready_without_network(self):
        for version in ('1.3.1', 'v1.3.1+build.2', '1.4.0-rc.1'):
            with self.subTest(version=version), patch.object(dependency, 'run') as run:
                run.return_value = json.dumps({'installed': [
                    {'pluginId': dependency.PLUGIN_ID, 'version': version, 'enabled': True,
                     'marketplaceSource': {'sourceType': 'git', 'source': dependency.SOURCE}}]})
                self.assertEqual(dependency.ensure(), (version, False))
                run.assert_called_once_with('list', '--json')

    def test_current_version_from_unrelated_source_is_rejected(self):
        with patch.object(dependency, 'run', return_value=json.dumps({'installed': [
                {'pluginId': dependency.PLUGIN_ID, 'version': '1.3.1', 'enabled': True,
                 'marketplaceSource': {'sourceType': 'git', 'source': 'https://example.com/skills'}}]})) as run:
            with self.assertRaisesRegex(dependency.DependencyError, '来源'):
                dependency.ensure()
            run.assert_called_once_with('list', '--json')

    def test_prerelease_at_baseline_is_upgraded(self):
        states = iter(('1.3.1-rc.1', '1.3.1', '1.3.1'))
        calls = []

        def cli(*args):
            calls.append(args)
            if args == ('list', '--json'):
                return json.dumps({'installed': [
                    {'pluginId': dependency.PLUGIN_ID, 'version': next(states), 'enabled': True}]})
            if args == ('marketplace', 'list', '--json'):
                return json.dumps({'marketplaces': [{
                    'name': dependency.MARKETPLACE,
                    'marketplaceSource': {'sourceType': 'git', 'source': dependency.SOURCE}}]})
            return '{}'

        with patch.object(dependency, 'run', side_effect=cli):
            self.assertEqual(dependency.ensure(), ('1.3.1', True))
        self.assertIn(('marketplace', 'upgrade', dependency.MARKETPLACE, '--json'), calls)
        self.assertNotIn(('add', dependency.PLUGIN_ID, '--json'), calls)

    def test_old_installed_version_is_reinstalled_after_marketplace_refresh(self):
        states = iter(('1.2.0', '1.2.0', '1.3.1'))
        calls = []

        def cli(*args):
            calls.append(args)
            if args == ('list', '--json'):
                return json.dumps({'installed': [
                    {'pluginId': dependency.PLUGIN_ID, 'version': next(states), 'enabled': True}]})
            if args == ('marketplace', 'list', '--json'):
                return json.dumps({'marketplaces': []})
            return '{}'

        with patch.object(dependency, 'run', side_effect=cli):
            self.assertEqual(dependency.ensure(), ('1.3.1', True))
        self.assertEqual(calls, [
            ('list', '--json'), ('marketplace', 'list', '--json'),
            ('marketplace', 'add', 'mattpocock/skills'),
            ('marketplace', 'upgrade', dependency.MARKETPLACE, '--json'),
            ('list', '--json'), ('add', dependency.PLUGIN_ID, '--json'),
            ('list', '--json')])

    def test_unrelated_marketplace_source_is_preserved(self):
        def cli(*args):
            if args == ('list', '--json'):
                return json.dumps({'installed': []})
            if args == ('marketplace', 'list', '--json'):
                return json.dumps({'marketplaces': [{
                    'name': dependency.MARKETPLACE,
                    'marketplaceSource': {'sourceType': 'git', 'source': 'https://example.com/skills'}}]})
            self.fail('Unexpected mutation: ' + repr(args))

        with patch.object(dependency, 'run', side_effect=cli):
            with self.assertRaisesRegex(dependency.DependencyError, '来源'):
                dependency.ensure()

    def test_upgrade_failure_is_reported(self):
        def cli(*args):
            if args == ('list', '--json'):
                return json.dumps({'installed': []})
            if args == ('marketplace', 'list', '--json'):
                return json.dumps({'marketplaces': [{
                    'name': dependency.MARKETPLACE,
                    'marketplaceSource': {'sourceType': 'git', 'source': dependency.SOURCE}}]})
            raise dependency.DependencyError('网络更新失败')

        with patch.object(dependency, 'run', side_effect=cli):
            with self.assertRaisesRegex(dependency.DependencyError, '网络更新失败'):
                dependency.ensure()

    def test_hook_reports_failed_gate_even_with_unexpected_input(self):
        output = io.StringIO()
        with patch.object(sys, 'argv', ['ensure_dependency.py', '--hook']), \
                patch.object(sys, 'stdin', io.StringIO('not-json')), \
                patch.object(dependency, 'ensure', side_effect=dependency.DependencyError('更新失败')), \
                redirect_stdout(output):
            self.assertEqual(dependency.main(), 0)
        result = json.loads(output.getvalue())
        self.assertIn('更新失败', result['systemMessage'])
        self.assertIn('不要调用', result['hookSpecificOutput']['additionalContext'])


if __name__ == '__main__':
    unittest.main()
