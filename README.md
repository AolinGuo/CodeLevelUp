# CodeLevelUp

CodeLevelUp is a skill-first local code self-upgrade and vulnerability repair
project. Agents start from `skills/codelevelup/SKILL.md`, use the reference
workflows to understand the target repository, build or approximate a local code
graph, patch narrowly, verify locally, and prepare human review.

CodeLevelUp 是一个以 agent skill 为主入口的本地代码自升级和漏洞修补项目。Agent
先阅读 `skills/codelevelup/SKILL.md`，再按 reference 工作流理解目标仓库、构建或近似
本地代码图、进行小步修改、本地验证，并准备人工审核。

## What It Provides / 能力范围

- A portable agent skill for code self-upgrade and vulnerability repair.
- `AGENT_GUIDE.md` as the agent routing index; `SKILL.md` remains authoritative.
- Local code graph guidance and optional helper support under `.codelevelup/`.
- SCA repair flow: incremental scan, dependency fix, local verification, human
  review before merge.
- Self-upgrade flow: requirements gate, graph query, smallest patch,
  verification, review.
- Optional stdio MCP helper tools for agents that support MCP.
- Skill-only fallback that uses `git`, `rg`, file reads, manifests, lockfiles,
  and project-native verification commands.

- 可迁移的代码自升级和漏洞修补 agent skill。
- `AGENT_GUIDE.md` 作为 Agent 路由索引；真正权威契约仍是 `SKILL.md`。
- 本地代码图工作流，以及写入 `.codelevelup/` 的可选 helper 状态。
- SCA 修补流程：增量扫描、依赖修复、本地验证、人工审核合并。
- 自升级流程：需求门禁、图查询、最小补丁、验证、审核。
- 面向支持 MCP 的 Agent 的可选 stdio MCP helper。
- 无 helper 时可用 skill-only 降级：使用 `git`、`rg`、文件阅读、manifest、lockfile
  和项目原生命令。

## Install Optional Helper / 安装可选 Helper

The skill itself does not require Python. Install the helper only when an agent
needs local MCP tools:

Skill 本身不要求 Python。只有当 Agent 需要本地 MCP 工具时才安装 helper：

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

In restricted sandboxes:

受限沙盒中：

```bash
python -m pip install -e . --no-deps --no-build-isolation
```

Smoke test the single helper entry:

烟测唯一 helper 入口：

```bash
codelevelup-agent doctor --json
codelevelup-agent mcp
```

From a source checkout without install:

不安装时可使用源码仓库 wrapper：

```bash
bin/codelevelup-agent doctor --json
bin/codelevelup-agent mcp
```

## Agent Entry / Agent 入口

1. Read `AGENT_GUIDE.md`.
2. Read `skills/codelevelup/SKILL.md`.
3. Read `skills/codelevelup/references/agent-entry-layer.md`.
4. Select the workflow reference:
   - `code-graph-workflow.md`
   - `graph-query-patterns.md`
   - `self-upgrade-workflow.md`
   - `vulnerability-remediation-workflow.md`
   - `verification-review-workflow.md`
5. Use MCP helper tools only as internal accelerators. Do not ask the user to
   remember helper commands.

## Local State / 本地状态

When a run needs durable traceability, write artifacts inside the target
repository:

当一次运行需要可追踪状态时，将产物写入目标项目：

```text
.codelevelup/
├── graph/
│   ├── graph.json
│   ├── nodes.json
│   └── edges.json
├── runs/
│   └── <run-id>/
│       ├── request.json
│       ├── findings.json
│       ├── patch-plan.md
│       ├── verification.json
│       └── review.md
└── policy.yaml
```

## Project Structure / 项目结构

```text
CodeLevelUp/
├── AGENT_GUIDE.md
├── AGENTS.md
├── CLAUDE.md
├── README.md
├── README_CN.md
├── SKILL.md
├── pyproject.toml
├── bin/
│   └── codelevelup-agent
├── docs/
│   ├── architecture.md
│   ├── sca-workflow.md
│   └── usage.md
├── skills/
│   └── codelevelup/
│       ├── SKILL.md
│       └── references/
│           ├── agent-entry-layer.md
│           ├── code-graph-workflow.md
│           ├── code-search-workflow.md
│           ├── graph-query-patterns.md
│           ├── self-upgrade-workflow.md
│           ├── upgrade-loop.md
│           ├── verification-review-workflow.md
│           └── vulnerability-remediation-workflow.md
├── src/
│   └── codelevelup/
│       ├── agent.py
│       ├── code_graph.py
│       ├── mcp_server.py
│       └── probe.py
├── tests/
├── tools/
│   └── verify_skill_structure.py
└── mcp/
    └── claude_desktop_config.example.json
```

- `AGENT_GUIDE.md`: routing index for agents.
- `skills/codelevelup/SKILL.md`: authoritative skill contract.
- `skills/codelevelup/references/code-graph-workflow.md`: local graph build and
  storage contract.
- `skills/codelevelup/references/graph-query-patterns.md`: graph query patterns
  for code understanding and impact lookup.
- `src/codelevelup/`: optional helper implementation behind the skill.
- `.codelevelup/`: target-project-local graph and run state.

- `AGENT_GUIDE.md`：Agent 路由索引。
- `skills/codelevelup/SKILL.md`：权威 skill 契约。
- `skills/codelevelup/references/code-graph-workflow.md`：本地图构建和存储契约。
- `skills/codelevelup/references/graph-query-patterns.md`：代码理解和影响分析的图查询模式。
- `src/codelevelup/`：位于 skill 背后的可选 helper 实现。
- `.codelevelup/`：目标项目内的图谱和运行状态目录。

## Validation / 验证

```bash
PYTHONPATH=src python -m unittest discover -s tests
python tools/verify_skill_structure.py
python /Users/olym/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/codelevelup
```
