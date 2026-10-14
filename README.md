# 工程协作插件

面向 Codex 的可复用工程协作插件：通过项目适配、角色分工、任务 Cycle 和可复核证据，让多角色协作在不同技术栈项目中保持边界清晰、过程可追溯。

`engineering-workflow` 将通用协作方法与项目自身事实分开维护：通用角色提供方法，项目适配提供架构与技术栈事实，当前任务契约决定修改范围和验收条件。

一个入口 Skill 提供项目初始化、任务调度和证据验证，配套 7 个能力角色与 6 个治理角色。按任务需要选择角色；角色文件本身不会自动启动多智能体。

## 文档

- [仓库与工作流说明](docs/overview.md)：了解适用场景、核心概念、角色职责和完整使用链路。
- [初始化与项目适配](plugins/engineering-workflow/skills/engineering-workflow/references/initialization.md)：了解初始化生成的文件、冲突处理与升级边界。
- [调度与交接](plugins/engineering-workflow/skills/engineering-workflow/references/coordination.md)：了解任务派发、唯一写入人和独立验收要求。

## 安装

通过 GitHub 安装：

```bash
codex plugin marketplace add XUHUIisxh/engineering-workflow --ref main
codex plugin add engineering-workflow@engineering-tools
codex plugin list --json
```

本地开发或安装：

```bash
git clone https://github.com/XUHUIisxh/engineering-workflow.git
cd engineering-workflow
codex plugin marketplace add .
codex plugin add engineering-workflow@engineering-tools
```

选择一种 marketplace 来源。同名 marketplace 已存在时，先用 `codex plugin marketplace list --json` 核对来源再切换。安装后打开新的 Codex 会话，确认技能 `engineering-workflow:engineering-workflow` 可见。

## 使用

在目标业务项目中首次接入：

```text
使用 $engineering-workflow 初始化当前项目的工程协作。
先调查实际技术栈、目录和已有规范，保留已有配置并建立本项目适配。
系统目标是：……；先完成需求和架构设计，再组织实现与验证。
```

开始需求：

```text
使用 $engineering-workflow，为“具体需求”建立新 Cycle。
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

Cycle 保存一次目标的基线、契约、任务、交接和验收。插件安装一次，每个项目接入一次；复用协作方法，项目自行维护架构、接口、目录及验收命令。

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

生产资源位于 `plugins/engineering-workflow/plugin.json` 与 `plugins/engineering-workflow/skills/`；分发入口为 `.agents/plugins/marketplace.json`。角色模板不作为插件清单的自动注册项，需要逐项目初始化。

当前版本为 0.1.1。写入模式支持 macOS/Linux 的 POSIX 目录句柄；已有 macOS 实测，Linux 尚未执行验证。初始化期间目标目录保持唯一写入人，异常清理为尽力处理。0.1.1 不提供自动升级或卸载迁移；修改生产资源时递增版本，人工比较并备份既有项目文件。安装与文件检查分别验证，不能代替运行时发现、自定义角色名称派发或业务验收。

格式依据：[官方插件文档](https://developers.openai.com/plugins/build/plugins)。
