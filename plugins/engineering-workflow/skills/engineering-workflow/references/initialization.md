# 初始化与适配

脚本位于本 Skill 的 `scripts/initialize.py`，使用 Python 3.9+ 标准库；写入模式支持 macOS/Linux 的 POSIX 目录句柄，其他平台拒绝执行不安全的写入降级。以读取到的 Skill 实际位置定位脚本；不要猜缓存目录。项目根由用户上下文确认，不从插件所在工作目录推断。

## 环境准备

初始化不依赖第三方 Python 包。先检查解释器和标准库：

```bash
python3 --version
python3 -c 'import argparse, hashlib, json, pathlib; print("Python 标准库可用")'
```

初始化要求 Python 3.9+；测试要求 Python 3.11+，因为测试使用标准库 `tomllib`。如果没有 Python、版本不足或导入检查失败，必须暂停，不执行下面的初始化命令。

向使用人员说明：需要安装 Python 3.11+，不需要单独安装 `tomllib`、`json` 等 pip 包。使用人员自行安装时，等待其明确完成后重新检查；使用人员要求协助安装时，先检查操作系统、CPU 架构、内存、磁盘空间、现有 Python 和包管理器，再选择官方安装包或系统包管理器。安装后重新执行检查，只有验证通过才能继续。

```bash
python3 <Skill实际路径>/scripts/initialize.py --project <项目根> --dry-run
python3 <Skill实际路径>/scripts/initialize.py --project <项目根> --apply
python3 <Skill实际路径>/scripts/initialize.py --project <项目根> --check
```

默认是预览。全部目标和引用检查完毕后才创建，遇到冲突非零退出且不写计划文件；不同内容的既有文件、符号链接和越界路径均拒绝。不自动改写 AGENTS.md、业务文件、项目规范或已有自定义角色。

初始化及异常清理期间，目标目录必须只有一个写入人。写入通过目录句柄固定路径，并以独占创建保护已出现的冲突文件。失败时尽力清理本次创建的文件；检测到身份/内容变化或不可读时保留并报告。POSIX 没有原子的“核对后删除”，最后核对与删除之间的并发替换仍存在窗口；不得让其他进程同时改写这些路径。新建空目录可能留下，不提供文件系统事务；遇到竞争应停止其他写入后检查残留再重试。

创建项：

- `docs/agent-workflow/project-adapter.json`：仅缺失时创建，之后由项目维护；schema_version、project_name、workflow、conventions、role_documents、cycle_root。
- `.codex/agents/engineering_*.toml`：13 个原生角色，原有非同名 Agent 保留。
- `.codex/engineering-workflow.lock.json`：插件版本/内容摘要和生成文件摘要。

适配中的 workflow、conventions 为项目根相对文件列表；role_documents 将通用角色键映射到项目角色文件；cycle_root 是项目根相对目录。已有适配读取验证，不自动替换。角色键为 product、architecture、frontend、backend、database、test、delivery、orchestrator、reviewer、debugger、architecture_auditor、ui_auditor、verifier。

新项目空适配会返回 `context_status: NEEDS_CONTEXT`。先检查仓库实际结构和用户的产品目标，建立项目自有职责/架构依据，再补齐引用。不要把一个仓库的框架、数据库、目录、启动方式和凭据复制成另一个仓库的事实。`READY` 只表示基础引用已提供；使用某角色前还要确认其职责映射与本次任务契约完整。

适配准备示例：

```json
{
  "schema_version": 1,
  "project_name": "order-system",
  "workflow": ["docs/engineering/workflow.md"],
  "conventions": ["docs/engineering/architecture.md"],
  "role_documents": {"backend": "docs/engineering/backend-role.md"},
  "cycle_root": "docs/engineering/cycles"
}
```

示例文件必须确实存在才可作为引用。适配可由项目写入负责人在用户任务范围内完善；初始角色缺口先记录，不能据此扩大业务写入。

重复 apply 保持内容和时间不变。插件升级或生成角色手工编辑后，`--check` 与 `--apply` 都会报告差异；本插件不自动迁移既有项目文件。保留/备份现有文件，比较新旧模板，确认责任人与迁移方案后处理。只有 lock 和实际源插件/生成文件一致才报告工具接入通过。

验证脚本不安装插件，也不确认会话已发现 native Agent。使用仓库根目录的 `scripts/install.py` 可同时安装本插件与 `mattpocock-skills`；之后另行记录 installed、enabled、版本和缓存内容。安装不会自动运行 `setup-matt-pocock-skills`，也不会修改业务项目文件。
