# 工程协作插件

面向 Codex 的可复用工程协作插件：通过项目适配、角色分工、任务 Cycle 和可复核证据，让多角色协作在不同技术栈项目中保持边界清晰、过程可追溯。

`engineering-workflow` 将通用协作方法与项目自身事实分开维护：通用角色提供方法，项目适配提供架构与技术栈事实，当前任务契约决定修改范围和验收条件。

一个入口 Skill 提供简单、一般、工程三级执行方式，以及项目初始化、任务调度和证据验证，配套 7 个能力角色与 6 个治理角色。按任务需要选择角色；角色文件本身不会自动启动多智能体。

## 文档

- [仓库与工作流说明](docs/overview.md)：了解适用场景、核心概念、角色职责和完整使用链路。
- [初始化与项目适配](plugins/engineering-workflow/skills/engineering-workflow/references/initialization.md)：了解初始化生成的文件、冲突处理与升级边界。
- [调度与交接](plugins/engineering-workflow/skills/engineering-workflow/references/coordination.md)：了解任务派发、唯一写入人和独立验收要求。

## 安装

从 GitHub 获取本仓库并联合安装两个插件（Python 3.9+、Codex CLI）：

```bash
git clone https://github.com/XUHUIisxh/engineering-workflow.git
cd engineering-workflow
python3 scripts/install.py
codex plugin list --json
```

需要安装已发布的远程 `main` 时：

```bash
python3 scripts/install.py --remote
```

安装器默认使用当前检出的源码；`--remote` 使用已发布的远程版本，发布新版本前不适用于验证本地改动。安装器先检查 marketplace 来源是否匹配，再确保 `mattpocock-skills@mattpocock` 至少为 1.3.1 并安装本插件；来源不符时停止，不覆盖用户配置。直接使用 `codex plugin add engineering-workflow@engineering-tools` 只能安装本插件，下一轮 hook 在获得信任后才会补齐上游依赖。安装后在 Codex 中审查并信任插件 hook，打开新会话，确认两个插件均为 enabled 且技能可见。hook 未获信任时，调用本 Skill 仍会执行版本检查。

hook 在每轮用户消息前检查本机已安装版本；达到基线时不联网，低于基线或缺失时才刷新 `mattpocock` marketplace 并尝试更新。更新失败不会覆盖既有 marketplace，也不会调用不满足基线的上游技能。插件升级后当前会话的技能列表可能尚未刷新，此时开启新会话再调用。

## 使用

简单或一般级直接指定即可：

```text
使用 $engineering-workflow，按简单级处理“具体问题”。
使用 $engineering-workflow，按一般级完成“具体需求”。
```

需要工程级时，在目标业务项目中首次接入：

```text
使用 $engineering-workflow 初始化当前项目的工程协作。
先调查实际技术栈、目录和已有规范，保留已有配置并建立本项目适配。
系统目标是：……；先完成需求和架构设计，再组织实现与验证。
```

开始需求：

```text
使用 $engineering-workflow，按工程级为“具体需求”建立新 Cycle。
先调查现有实现和接口，按需要组织实施、测试和独立审查。
完成实现与验证，部署前等待我的确认。
```

只做方案：

```text
使用 $engineering-workflow，分析“具体需求”的实现方案。
本轮只做调查、方案和任务拆分，不修改业务代码。
```

继续已有任务：

```text
使用 $engineering-workflow，继续 docs/agent-workflow/cycles/具体目录/。
读取已有契约、交接和验证结果，从未完成任务继续。
```

Cycle 保存一次目标的基线、契约、任务、交接和验收。插件安装一次，工程级项目接入一次；复用协作方法，项目自行维护架构、接口、目录及验收命令。

默认按“一般”级处理常规任务；“简单”级直接完成低风险工作，“工程”级才默认使用项目适配、Cycle、角色派发和独立审查。级别控制工作流深度，不改变 Codex 模型的 `model_reasoning_effort`。上游技能仅在可用且满足调用条件时使用；用户显式调用型技能不会被本插件自动触发。安装插件不会自动运行 `setup-matt-pocock-skills` 改写业务仓库。详见 [执行级别](plugins/engineering-workflow/skills/engineering-workflow/references/levels.md)。

## 项目初始化工具

脚本使用 Python 3.9+ 标准库，不需要安装任何第三方 Python 包。运行前先确认解释器：

```bash
python3 --version
python3 -c 'import argparse, hashlib, json, pathlib; print("Python 标准库可用")'
```

初始化要求 Python 3.9+；运行仓库测试要求 Python 3.11+。如果没有 Python，或版本低于当前操作所需版本，应先停止后续初始化，向使用人员说明需要安装 Python 3.11+，等待其自行安装完成；使用人员明确要求协助时，再先检查操作系统、CPU 架构、内存、磁盘空间和可用包管理器，选择合适的安装方式并验证版本。不要通过安装同名 pip 包来替代 Python 标准库。

环境确认后，直接从本仓库执行时，显式指定目标项目根：

```bash
python3 plugins/engineering-workflow/skills/engineering-workflow/scripts/initialize.py --project /path/to/project --dry-run
python3 plugins/engineering-workflow/skills/engineering-workflow/scripts/initialize.py --project /path/to/project --apply
python3 plugins/engineering-workflow/skills/engineering-workflow/scripts/initialize.py --project /path/to/project --check
```

生成项目适配 `docs/agent-workflow/project-adapter.json`、13 个 `.codex/agents/engineering_*.toml` 和 `.codex/engineering-workflow.lock.json`。适配引用该项目自己的工作流、规范和角色文档；未知项报告 `NEEDS_CONTEXT`，补齐实际项目依据后再实施业务。

默认预览；已有文件内容冲突时终止，保留项目定制文件。详情见 [初始化与适配](plugins/engineering-workflow/skills/engineering-workflow/references/initialization.md) 和 [调度与交接](plugins/engineering-workflow/skills/engineering-workflow/references/coordination.md)。

## 测试与维护

测试需要 Python 3.11+：

```bash
python3 -m unittest discover -s plugins/engineering-workflow/tests -v
```

如果测试环境只有 Python 3.9 或 3.10，初始化脚本仍可使用，但测试不能宣称完整通过；先安装或切换到 Python 3.11+，再重新执行测试。

生产资源位于 `plugins/engineering-workflow/plugin.json`、`skills/` 与 `hooks/`；分发入口为 `.agents/plugins/marketplace.json`。角色模板不作为插件清单的自动注册项，需要按工程级或用户要求逐项目初始化。

当前版本为 0.2.0。写入模式支持 macOS/Linux 的 POSIX 目录句柄；已有 macOS 实测，Linux 尚未执行验证。初始化期间目标目录保持唯一写入人，异常清理为尽力处理。本插件自身不提供自动升级或卸载迁移；既有项目的角色与版本锁需人工比较并备份后迁移。安装与文件检查分别验证，不能代替运行时发现、自定义角色名称派发或业务验收。

格式依据：[官方插件文档](https://developers.openai.com/plugins/build/plugins)。
