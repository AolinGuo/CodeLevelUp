# CodeLevelUp

CodeLevelUp 是一个 skill-first 的本地代码自升级和漏洞修补项目。它不是让用户记住一组命令，
而是让 Agent 从 `skills/codelevelup/SKILL.md` 进入，再根据 reference 工作流完成需求澄清、
本地代码图构建、图查询、代码修改、验证和人工审核。

## 快速入口

```bash
bin/codelevelup-agent doctor --json
bin/codelevelup-agent mcp
```

安装 helper 后也可以使用 `codelevelup-agent`。helper 是可选加速层；没有 helper 时，
Agent 仍应使用 `git`、`rg`、文件阅读、manifest、lockfile 和项目原生命令完成任务。

## 结构

- `AGENT_GUIDE.md`：Agent 路由索引。
- `skills/codelevelup/`：可分发的 agent skill。
- `skills/codelevelup/references/code-graph-workflow.md`：本地代码图流程。
- `skills/codelevelup/references/graph-query-patterns.md`：图查询模式。
- `skills/codelevelup/references/self-upgrade-workflow.md`：代码自升级流程。
- `skills/codelevelup/references/vulnerability-remediation-workflow.md`：SCA 漏洞修补流程。
- `skills/codelevelup/references/verification-review-workflow.md`：验证和人工审核流程。
- `src/codelevelup/`：位于 skill 背后的可选 helper 实现。
- `.codelevelup/`：写在目标项目内的图谱和运行状态目录。

详细说明见 `README.md`、`docs/architecture.md` 和 `docs/usage.md`。
