#!/usr/bin/env python3
"""Install engineering-workflow and its mattpocock-skills dependency."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/engineering-workflow'
DEPENDENCY = PLUGIN / 'skills/engineering-workflow/scripts/ensure_dependency.py'
PLUGIN_ID = 'engineering-workflow@engineering-tools'
REMOTE = 'https://github.com/XUHUIisxh/engineering-workflow.git'


def run(*args):
    result = subprocess.run(['codex', 'plugin', *args], capture_output=True, text=True,
                            timeout=150)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--remote', action='store_true', help='Install from the published main branch')
    args = parser.parse_args()
    try:
        markets = json.loads(run('marketplace', 'list', '--json'))['marketplaces']
        market = next((item for item in markets if item['name'] == 'engineering-tools'), None)
        if market is not None:
            source = market.get('marketplaceSource', {})
            local_match = source.get('sourceType') == 'local' and Path(source.get('source', '')).resolve() == ROOT
            remote_match = source.get('sourceType') == 'git' and source.get('source', '').rstrip('/') in (
                REMOTE, REMOTE.removesuffix('.git'))
            if not (remote_match if args.remote else local_match):
                raise RuntimeError('engineering-tools marketplace 来源与所选安装方式不符；未覆盖现有配置')
        subprocess.run([sys.executable, str(DEPENDENCY)], check=True, timeout=180)
        if market is None:
            run('marketplace', 'add', 'XUHUIisxh/engineering-workflow' if args.remote else str(ROOT),
                *(['--ref', 'main'] if args.remote else []))
        elif args.remote:
            run('marketplace', 'upgrade', 'engineering-tools', '--json')
        run('add', PLUGIN_ID, '--json')
        installed = json.loads(run('list', '--json'))['installed']
        actual = next((item for item in installed if item['pluginId'] == PLUGIN_ID), None)
        if not actual or not actual.get('enabled'):
            raise RuntimeError('安装后的 engineering-workflow 未启用或未出现在插件清单中')
        if not args.remote:
            expected = json.loads((PLUGIN / 'plugin.json').read_text(encoding='utf-8'))['version']
            if actual['version'] != expected:
                raise RuntimeError('安装后的 engineering-workflow 版本与当前源码不一致')
        print(PLUGIN_ID + ' ' + actual['version'] + ' (ready)')
        return 0
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
