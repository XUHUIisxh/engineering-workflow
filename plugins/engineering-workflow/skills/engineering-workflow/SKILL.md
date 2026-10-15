---
name: engineering-workflow
description: Use when the user invokes engineering-workflow, requests simple/general/engineering workflow levels, initializes project collaboration, or starts/resumes a multi-role Cycle. 不用于未要求工程流程的一次性问答。
---

# 工程协作

通用角色提供方法，项目适配提供事实，当前任务契约决定此次路径与验收。先检查用户目标、根 AGENTS.md、工作区差异和 `docs/agent-workflow/project-adapter.json`；保留既有变更和定制角色。

## 先检查依赖与级别

每次调用本 Skill，先运行 `python3 <本 Skill 实际路径>/scripts/ensure_dependency.py`。插件的 `UserPromptSubmit` hook 也会在每轮用户消息前检查；hook 未获信任、被关闭或不在受支持的本地运行环境时，以此处的检查为准。最低版本为 `mattpocock-skills@mattpocock` 1.3.1；检查失败时不要调用其技能，报告具体错误。更新后若当前会话仍只发现旧技能，开启新会话再调用。

按 [执行级别](references/levels.md) 选择 **简单、一般、工程**；用户指定的级别优先，未指定时默认“一般”，复杂度明显不符时说明并建议调整。级别控制工作流深度，不修改 Codex 当前模型的 `model_reasoning_effort`。工程级将上游的需求澄清、规格/任务、实施和审查阶段对应到本插件的 Cycle 与任务契约；仅在技能可用、触发条件满足且允许模型调用时直接调用上游技能。用户显式调用型技能由用户决定是否启用。

## Python 环境门槛

初始化工具使用 Python 标准库，不需要安装第三方 pip 包。执行初始化或检查前，先运行 `python3 --version` 和标准库导入检查；初始化要求 Python 3.9+，仓库测试要求 Python 3.11+（测试使用标准库 `tomllib`）。

如果找不到 Python、版本不满足当前操作，或标准库检查失败，暂停工作流并告诉使用人员需要安装 Python 3.11+。使用人员选择自行安装时，等待其明确安装完成，再重新检查版本后继续；不要在等待期间运行初始化或写入目标项目。使用人员明确要求协助安装时，先检查操作系统、CPU 架构、内存、磁盘空间、现有解释器和包管理器，再选择安装方式，完成后验证解释器再继续。

## 选择动作

- **首次接入/更新检查**：仅“工程”级或用户明确要求原生角色时初始化项目。先按 [初始化说明](references/initialization.md) 完成 Python 环境检查，再定位本 Skill 的 `scripts/initialize.py`，显式传入项目根，先执行 `--dry-run`。用户已要求初始化时继续 `--apply` 和 `--check`；冲突按报告核对，保留现有文件。缺少架构事实时先只读调查并建立适配/任务契约，未知项报告 `NEEDS_CONTEXT`。
- **启动/继续任务**：“工程”级先执行 `--check` 核对接入；读适配中的 workflow、conventions、当前角色的 role_documents 及指定 Cycle，再按 [调度与交接](references/coordination.md) 建立或恢复任务。一般/简单级读取现有项目约束即可，不因未初始化而强制创建角色或 Cycle。
- **验收/审查**：读取本次任务契约与交接，独立检查适用门禁；区别工具文件验证、运行时发现和业务验收。未执行标记 `PENDING`，缺上下文为 `NEEDS_CONTEXT`，失败交回责任角色。

## 执行边界

一个任务一个写入人；能力角色拥有专业产物，治理角色维护调度和证据。现有项目规则与用户授权优先。原生角色模板在 `assets/agents/`；只启用任务需要的角色，不固定技术栈、模型或部署方案。

角色文件不会自行启动多 Agent。使用当前可用运行时实际派发任务，携带任务编号、Cycle、输入、允许/禁止路径、接口不变量、验收和交接对象。只有运行时与当前规则允许的独立任务才并行，共享文件和未冻结契约串行。独立审查必须由未负责实现写入的审查 Agent 执行；没有独立执行能力时记录缺口。

安装提供 Skill；每个项目的 native Agent 需要显式初始化。安装/启用后打开新会话确认发现情况；当前工具不支持按自定义角色名调用时，读取对应 TOML 的职责并用完整任务契约派发，报告实际方式，不宣称已验证名称路由。
