#!/usr/bin/env python3
"""Ensure the installed mattpocock-skills plugin meets this workflow's baseline."""
import argparse
import json
import re
import subprocess
import sys

PLUGIN_ID = 'mattpocock-skills@mattpocock'
MARKETPLACE = 'mattpocock'
BASELINE = '1.3.1'
SOURCE = 'https://github.com/mattpocock/skills.git'


class DependencyError(Exception):
    pass


def version_key(value):
    if not isinstance(value, str):
        raise DependencyError('无法比较插件版本: ' + str(value))
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?', value)
    if not match:
        raise DependencyError('无法比较插件版本: ' + str(value))
    # Only compare against a stable baseline; build metadata does not affect precedence.
    return tuple(int(match.group(i)) for i in range(1, 4)) + (0 if match.group(4) else 1,)


def run(*args):
    try:
        result = subprocess.run(['codex', 'plugin', *args], capture_output=True,
                                text=True, timeout=150, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise DependencyError('无法执行 Codex 插件命令: ' + str(error)) from error
    if result.returncode:
        raise DependencyError('Codex 插件命令失败 (' + ' '.join(args) + '): '
                              + (result.stderr.strip() or result.stdout.strip()))
    return result.stdout


def plugin_state():
    try:
        installed = json.loads(run('list', '--json'))['installed']
        return next((item for item in installed if item['pluginId'] == PLUGIN_ID), None)
    except (ValueError, KeyError, TypeError) as error:
        raise DependencyError('无法读取 Codex 插件清单') from error


def require_official_source(source):
    location = source.get('source') if isinstance(source, dict) else None
    if not isinstance(location, str) or source.get('sourceType') != 'git' or \
            location.rstrip('/') not in (SOURCE, SOURCE.removesuffix('.git')):
        raise DependencyError('mattpocock marketplace 来源与官方仓库不同，保留现有配置并停止自动更新')


def marketplace_ready():
    try:
        markets = json.loads(run('marketplace', 'list', '--json'))['marketplaces']
        market = next((item for item in markets if item['name'] == MARKETPLACE), None)
    except (ValueError, KeyError, TypeError) as error:
        raise DependencyError('无法读取 Codex marketplace 清单') from error
    if market is None:
        run('marketplace', 'add', 'mattpocock/skills')
        return
    require_official_source(market.get('marketplaceSource'))


def ensure():
    state = plugin_state()
    if state and version_key(state['version']) >= version_key(BASELINE):
        require_official_source(state.get('marketplaceSource'))
        if not state.get('enabled'):
            raise DependencyError(PLUGIN_ID + ' 已安装但未启用；请检查当前插件设置')
        return state['version'], False
    marketplace_ready()
    run('marketplace', 'upgrade', MARKETPLACE, '--json')
    state = plugin_state()
    if not state or version_key(state['version']) < version_key(BASELINE):
        run('add', PLUGIN_ID, '--json')
        state = plugin_state()
    if not state or version_key(state['version']) < version_key(BASELINE) or not state.get('enabled'):
        raise DependencyError(PLUGIN_ID + ' 未达到最低版本 ' + BASELINE + ' 或未启用')
    return state['version'], True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hook', action='store_true', help='Emit UserPromptSubmit hook output')
    args = parser.parse_args()
    try:
        version, changed = ensure()
    except (DependencyError, KeyError) as error:
        message = str(error)
        if args.hook:
            print(json.dumps({'systemMessage': message,
                              'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit',
                                                     'additionalContext': 'mattpocock-skills 版本门禁未通过；本轮不要调用其技能。'}},
                             ensure_ascii=False))
            return 0
        print('ERROR: ' + message, file=sys.stderr)
        return 1
    if args.hook:
        if changed:
            print(json.dumps({'systemMessage': 'mattpocock-skills 已更新到 ' + version +
                              '；若技能列表仍是旧版本，请开启新会话后调用。'}, ensure_ascii=False))
    else:
        print(PLUGIN_ID + ' ' + version + (' (updated)' if changed else ' (ready)'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
