# engineering-workflow 仓库说明

## 解决什么问题

`engineering-workflow` 是一个 Codex 插件，用于把一次工程需求组织成可追溯的协作过程。它不限制业务项目使用的语言、框架、数据库或部署平台，而是提供一套统一方法，让每个参与角色清楚知道：本次要解决什么、可以修改哪些文件、哪些行为不能改变、如何证明工作完成。

它支持简单、一般、工程三级。简单级处理单点问题，一般级处理常规开发，工程级用于需要多人或多角色协作、保留交接和验收依据的复杂任务，例如架构调整、发布准备和跨模块重构。

它不替代项目的代码、测试、CI 或部署工具。项目仍然自行维护架构文档、接口约定、验证命令和发布流程。

## 核心概念

| 概念 | 含义 | 解决的问题 |
| --- | --- | --- |
| 项目适配 | 记录某个项目的真实工作流、规范、角色文档和 Cycle 根目录。 | 避免把一个项目的技术栈和约束误用到另一个项目。 |
| Cycle | 围绕一个目标保存基线、任务契约、交接和验收证据的目录。 | 让任务可以暂停、恢复和审查，而不依赖聊天上下文。 |
| 任务契约 | 明确负责人、允许和禁止修改路径、不变量、依赖、验收与交接对象。 | 防止范围漂移、多人覆盖同一文件和未验证交付。 |
| 角色 | 针对产品、架构、实现、测试、审查和验证的职责模板。 | 按问题选择需要的专业能力，而不是固定启动一组角色。 |
| 证据 | 实际执行的命令、退出码、关键结果和可复查的产物。 | 区分“文件存在”与“功能已经验证”。 |

## 协作过程

默认采用“一般”级；用户可明确指定级别。只有工程级默认执行下面的完整链路，其他级别按 [执行级别](../plugins/engineering-workflow/skills/engineering-workflow/references/levels.md) 缩减流程。Matt Pocock 的技能按任务选择，不在每个任务中全部运行。

```text
明确目标
  -> 调查项目事实和现有约束
  -> 建立或恢复 Cycle
  -> 冻结任务契约
  -> 实施与测试
  -> 独立审查
  -> 验收证据核对
  -> 按项目规则交付或等待发布授权
```

每个任务只能有一个写入负责人。共享配置、路由、数据库、全局样式和部署文件等共享区域需要串行修改。只有目录、接口和契约都相互独立的任务才适合并行。

实施完成后，独立审查应由没有负责该实现写入的角色执行。未执行的验证标记为 `PENDING`，缺少上下文或项目依据标记为 `NEEDS_CONTEXT`；这些状态不能被静态文件检查替代。

## 角色如何选择

| 角色类型 | 角色 | 负责内容 |
| --- | --- | --- |
| 能力角色 | product、architecture | 目标、范围、模块边界、接口和验收约束。 |
| 能力角色 | frontend、backend、database | 界面、用例/API、数据结构/迁移等具体实现。 |
| 能力角色 | test、delivery | 可重复测试证据，以及构建、发布工具和授权范围内交付。 |
| 治理角色 | orchestrator | 任务分配、依赖管理和路径写入边界。 |
| 治理角色 | reviewer、verifier | 独立审查差异与规格，核对证据和适用门禁。 |
| 治理角色 | debugger、architecture_auditor、ui_auditor | 按需定位故障、审查架构和界面质量。 |

角色模板定义职责，但不会自行启动多个 Agent。执行时需要根据当前运行环境、任务契约和项目规则实际派发；没有独立审查能力时，必须把该缺口记录到 Cycle 中。

## Python 环境与暂停规则

初始化脚本采用 Python 标准库完成参数解析、JSON 读写、文件操作、路径安全检查和内容摘要计算，因此不需要 `pip install` 任何第三方库。这里的“需要 Python”指需要 Python 解释器，不是需要额外的 Python 依赖包。

环境要求分为两档：

| 操作 | 最低版本 | 说明 |
| --- | --- | --- |
| 预览、初始化、检查项目 | Python 3.9+ | 运行 `initialize.py`。 |
| 运行仓库测试 | Python 3.11+ | 测试使用 Python 3.11 才加入标准库的 `tomllib`。 |

开始初始化前先执行：

```bash
python3 --version
python3 -c 'import argparse, hashlib, json, pathlib; print("Python 标准库可用")'
```

如果找不到 `python3`、版本低于当前操作要求，或标准库检查失败，工作流必须暂停在环境准备阶段：

1. 告知使用人员需要安装 Python 3.11+。初始化只要求 3.9+，但统一使用 3.11+ 可以同时满足初始化和测试。
2. 说明不需要额外安装 `tomllib`、`json` 等同名 pip 包；这些是 Python 标准库组件。Python 3.9/3.10 缺少 `tomllib` 时，应升级或切换 Python，而不是修改测试依赖。
3. 提供两种路径：使用人员自行安装完成后回复继续，或明确要求协助安装。
4. 在使用人员自行安装时，不执行初始化、写入项目文件或继续下一步；收到“已安装”后重新检查版本和标准库，再继续。
5. 在协助安装时，先检查操作系统、CPU 架构、内存、磁盘空间、现有 Python 和可用包管理器，再选择官方安装包或系统包管理器。安装完成后必须重新执行版本检查；验证失败时停留在环境准备阶段。

## 首次接入一个项目

先安装本插件，再在目标项目中调用 Skill：

```text
使用 $engineering-workflow 初始化当前项目的工程协作。
先调查实际技术栈、目录和已有规范，保留已有配置并建立本项目适配。
```

初始化工具默认只预览，确认无冲突后才创建项目文件：

```bash
python3 <Skill实际路径>/scripts/initialize.py --project /path/to/project --dry-run
python3 <Skill实际路径>/scripts/initialize.py --project /path/to/project --apply
python3 <Skill实际路径>/scripts/initialize.py --project /path/to/project --check
```

其中 `--apply` 会创建以下项目内文件，不会改写已有业务代码、`AGENTS.md`、项目规范或自定义角色：

```text
docs/agent-workflow/project-adapter.json
.codex/agents/engineering_*.toml
.codex/engineering-workflow.lock.json
```

新生成的适配如果缺少项目真实架构、规范或角色依据，会显示 `NEEDS_CONTEXT`。先补充项目自己的事实，再开始业务实施。

## 日常使用

开始复杂需求时：

```text
使用 $engineering-workflow，按工程级为“具体需求”建立新 Cycle。
先调查现有实现和接口，按需要组织实施、测试和独立审查。
完成实现与验证，部署前等待我的确认。
```

只想做评估而不改代码时：

```text
使用 $engineering-workflow，分析“具体需求”的实现方案。
本轮只做调查、方案和任务拆分，不修改业务代码。
```

继续中断的工作时：

```text
使用 $engineering-workflow，继续 docs/agent-workflow/cycles/具体目录/。
读取已有契约、交接和验证结果，从未完成任务继续。
```

## 验证范围

本插件的文件检查、插件安装状态、会话能否发现角色、角色名称能否路由、业务测试、浏览器验收和发布，分别是不同的验证项。

`--check` 只能确认项目适配、生成角色和版本锁的一致性，不能证明业务功能正确，也不能代替真实测试或发布确认。发布应遵循项目规则和已有授权；用户未回复不构成发布批准。

## 仓库结构

```text
.agents/plugins/marketplace.json     插件 marketplace 分发入口
plugins/engineering-workflow/
  plugin.json                         插件元数据和 Codex 界面信息
  skills/engineering-workflow/        Skill、角色模板、参考文档和初始化脚本
  tests/                              初始化工具测试
docs/overview.md                      本说明文档
```

插件的安装命令、维护方式和测试命令见仓库根目录的 [README](../README.md)。
