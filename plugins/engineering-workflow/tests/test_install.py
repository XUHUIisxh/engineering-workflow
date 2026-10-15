"""Verify the joint installer command order and marketplace ownership checks."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[3] / 'scripts/install.py'
SPEC = importlib.util.spec_from_file_location('joint_install', SCRIPT)
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)
VERSION = json.loads((installer.PLUGIN / 'plugin.json').read_text())['version']


class InstallTests(unittest.TestCase):
    def test_local_install_checks_dependency_then_installs_workflow(self):
        calls = []

        def cli(*args):
            calls.append(args)
            if args == ('marketplace', 'list', '--json'):
                return json.dumps({'marketplaces': []})
            if args == ('list', '--json'):
                return json.dumps({'installed': [{
                    'pluginId': installer.PLUGIN_ID, 'version': VERSION, 'enabled': True}]})
            return '{}'

        with patch.object(sys, 'argv', ['install.py']), patch.object(installer, 'run', side_effect=cli), \
                patch.object(installer.subprocess, 'run') as dependency_run:
            self.assertEqual(installer.main(), 0)
        dependency_run.assert_called_once()
        self.assertEqual(calls, [
            ('marketplace', 'list', '--json'),
            ('marketplace', 'add', str(installer.ROOT)),
            ('add', installer.PLUGIN_ID, '--json'),
            ('list', '--json')])

    def test_source_conflict_stops_before_dependency_install(self):
        markets = {'marketplaces': [{
            'name': 'engineering-tools',
            'marketplaceSource': {'sourceType': 'git', 'source': installer.REMOTE}}]}
        with patch.object(sys, 'argv', ['install.py']), \
                patch.object(installer, 'run', return_value=json.dumps(markets)) as cli, \
                patch.object(installer.subprocess, 'run') as dependency_run:
            self.assertEqual(installer.main(), 1)
        cli.assert_called_once_with('marketplace', 'list', '--json')
        dependency_run.assert_not_called()

    def test_remote_install_refreshes_published_marketplace(self):
        calls = []
        markets = {'marketplaces': [{
            'name': 'engineering-tools',
            'marketplaceSource': {'sourceType': 'git', 'source': installer.REMOTE}}]}

        def cli(*args):
            calls.append(args)
            if args == ('marketplace', 'list', '--json'):
                return json.dumps(markets)
            if args == ('list', '--json'):
                return json.dumps({'installed': [{
                    'pluginId': installer.PLUGIN_ID, 'version': '0.1.1', 'enabled': True}]})
            return '{}'

        with patch.object(sys, 'argv', ['install.py', '--remote']), \
                patch.object(installer, 'run', side_effect=cli), \
                patch.object(installer.subprocess, 'run'):
            self.assertEqual(installer.main(), 0)
        self.assertIn(('marketplace', 'upgrade', 'engineering-tools', '--json'), calls)

    def test_local_install_rejects_stale_installed_version(self):
        def cli(*args):
            if args == ('marketplace', 'list', '--json'):
                return json.dumps({'marketplaces': []})
            if args == ('list', '--json'):
                return json.dumps({'installed': [{
                    'pluginId': installer.PLUGIN_ID, 'version': '0.1.1', 'enabled': True}]})
            return '{}'

        with patch.object(sys, 'argv', ['install.py']), patch.object(installer, 'run', side_effect=cli), \
                patch.object(installer.subprocess, 'run'):
            self.assertEqual(installer.main(), 1)


if __name__ == '__main__':
    unittest.main()
