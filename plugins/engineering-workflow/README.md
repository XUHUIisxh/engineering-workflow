# 工程协作插件包

本目录包含 `engineering-workflow` 0.1.0 的插件清单、工程协作 Skill、13 个原生角色模板、初始化工具及工具测试。

安装与使用见 [仓库 README](../../README.md)。marketplace 分发入口位于仓库根的 `.agents/plugins/marketplace.json`，本包路径相对该分发根解析。

- [工程协作 Skill](skills/engineering-workflow/SKILL.md)：初始化、启动/继续任务及验证入口。
- [初始化与项目适配](skills/engineering-workflow/references/initialization.md)：生成文件、冲突处理、项目事实与升级边界。
- [调度与交接](skills/engineering-workflow/references/coordination.md)：角色选择、唯一写入人、Cycle 证据及独立审查。
- [初始化工具](skills/engineering-workflow/scripts/initialize.py)：Python 3.9+，默认预览；显式传入目标项目根。
- [工具测试](tests/test_initialize.py)：Python 3.11+，使用临时项目验证真实文件行为。

项目自有架构、角色约束和验收记录由目标项目保存。生产摘要只包含 `plugin.json` 和 `skills/`，README 与测试的整理不改变既有项目的版本锁。
