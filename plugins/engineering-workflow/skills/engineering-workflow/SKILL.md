---
name: engineering-workflow
description: Use when initializing reusable engineering agent collaboration in a repository, starting or resuming a multi-role engineering Cycle, or checking project adapter and role handoff evidence. 不用于无工程协作需求的一次性问答。
---

# 工程协作

通用角色提供方法，项目适配提供事实，当前任务契约决定此次路径与验收。先检查用户目标、根 AGENTS.md、工作区差异和 `docs/agent-workflow/project-adapter.json`；保留既有变更和定制角色。

## 选择动作

- **首次接入/更新检查**：读 [初始化说明](references/initialization.md)，定位本 Skill 的 `scripts/initialize.py`，显式传入项目根，先执行 `--dry-run`。用户已要求初始化时继续 `--apply` 和 `--check`；冲突按报告核对，保留现有文件。缺少架构事实时先只读调查并建立适配/任务契约，未知项报告 `NEEDS_CONTEXT`。
- **启动/继续任务**：先执行 `--check` 核对接入；读适配中的 workflow、conventions、当前角色的 role_documents 及指定 Cycle，再按 [调度与交接](references/coordination.md) 建立或恢复任务。接入校验失败先处理差异。
- **验收/审查**：读取本次任务契约与交接，独立检查适用门禁；区别工具文件验证、运行时发现和业务验收。未执行标记 `PENDING`，缺上下文为 `NEEDS_CONTEXT`，失败交回责任角色。

## 执行边界

一个任务一个写入人；能力角色拥有专业产物，治理角色维护调度和证据。现有项目规则与用户授权优先。原生角色模板在 `assets/agents/`；只启用任务需要的角色，不固定技术栈、模型或部署方案。

角色文件不会自行启动多 Agent。使用当前可用运行时实际派发任务，携带任务编号、Cycle、输入、允许/禁止路径、接口不变量、验收和交接对象。只有运行时与当前规则允许的独立任务才并行，共享文件和未冻结契约串行。独立审查必须由未负责实现写入的审查 Agent 执行；没有独立执行能力时记录缺口。

安装提供 Skill；每个项目的 native Agent 需要显式初始化。安装/启用后打开新会话确认发现情况；当前工具不支持按自定义角色名调用时，读取对应 TOML 的职责并用完整任务契约派发，报告实际方式，不宣称已验证名称路由。
