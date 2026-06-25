# CodeLevelUp

中文 | [English](#english)

CodeLevelUp 是一个项目级 Codex skill，用于在本地代码自升级前先建立代码知识图谱，帮助 agent 更好地理解代码结构、调用关系、影响范围和验证路径。它参考了本地 GitNexus skills 的工作方式，以及 [abhigyanpatwari/GitNexus](https://github.com/abhigyanpatwari/GitNexus) 的知识图谱理念：先索引，再理解，再修改，最后验证并提交。

## 项目目标

CodeLevelUp 的目标不是替代 GitNexus，而是把 GitNexus 的代码图谱能力组织成一个可复用的 Codex skill 工作流。它让 agent 在处理本地代码升级、漏洞修复、依赖现代化、API 迁移、质量改进时，优先通过知识图谱理解代码，再做小步修改。

适用场景：

- 给本地代码建立或刷新 GitNexus 知识图谱。
- 让 agent 快速理解代码结构、模块边界和执行流程。
- 在修改代码前核查影响范围和调用链。
- 修复安全漏洞或升级依赖时确认受影响代码路径。
- 基于本地测试、lint、安全扫描结果进行验证。
- 让 agent 只提交经过验证的窄范围改动。

## 项目结构

```text
CodeLevelUp/
├── README.md
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── gitnexus-workflow.md
│   └── upgrade-loop.md
├── scripts/
│   ├── probe_project.py
│   └── test_probe_project.py
└── .gitignore
```

### 根目录

| 路径 | 作用 |
| --- | --- |
| `README.md` | 项目说明文档，包含中英双语介绍、目录结构、安装、使用和验证方式。 |
| `SKILL.md` | Codex skill 的核心入口。包含 skill 名称、触发描述、工作契约、GitNexus 优先流程、使用模式和停止条件。 |
| `.gitignore` | 忽略 Python 缓存、虚拟环境、GitNexus 本地索引、Node 依赖和构建产物。 |

### `agents/`

`agents/` 保存 Codex UI 或运行时使用的 skill 元数据。

| 路径 | 作用 |
| --- | --- |
| `agents/openai.yaml` | 定义显示名称 `CodeLevelUp`、简短描述、默认调用提示和是否允许隐式触发。 |

### `references/`

`references/` 存放按需读取的长流程说明。这样 `SKILL.md` 可以保持精简，agent 只有在需要时才加载细节。

| 路径 | 作用 |
| --- | --- |
| `references/gitnexus-workflow.md` | 说明如何安装、初始化、刷新和使用 GitNexus 图谱；包含 `analyze`、`status`、`--pdg`、MCP 资源和图谱查询工具。 |
| `references/upgrade-loop.md` | 说明完整代码升级循环：快照、图谱理解、研究、补丁、验证和提交。 |

### `scripts/`

`scripts/` 存放确定性辅助脚本。脚本默认只做静态探测，不联网、不安装依赖、不修改目标项目。

| 路径 | 作用 |
| --- | --- |
| `scripts/probe_project.py` | 探测目标仓库生态、manifest、lockfile、验证命令、安全扫描命令和 GitNexus 状态。输出 JSON 或人类可读报告。 |
| `scripts/test_probe_project.py` | `probe_project.py` 的单元测试，覆盖 Python、Node、Go、Rust 和 GitNexus runner/index 检测。 |

## Skill 名称与调用

Codex skill 的触发名使用小写连字符形式：

```text
$code-level-up
```

UI 展示名和 GitHub 项目名使用：

```text
CodeLevelUp
```

示例调用：

```text
Use $code-level-up to inspect this repo with GitNexus, plan an upgrade, verify it, and commit.
```

## 工作流

### 1. 探测项目

在目标仓库运行：

```bash
python /path/to/CodeLevelUp/scripts/probe_project.py --json /path/to/target-repo
```

脚本会输出：

- 检测到的语言生态，例如 Python、Node、Go、Rust。
- manifest 和 lockfile，例如 `pyproject.toml`、`package.json`、`Cargo.toml`。
- 推荐的安装命令。
- 推荐的验证命令，例如 `python -m pytest`、`python -m ruff check .`。
- 推荐的安全扫描命令，例如 `python -m pip_audit`、`pnpm audit`、`cargo audit`。
- GitNexus runner 是否存在。
- GitNexus index 是否存在。
- GitNexus bootstrap 命令和 MCP 资源入口。

### 2. 建立 GitNexus 知识图谱

如果目标仓库还没有 `.gitnexus/run.cjs`：

```bash
npx gitnexus analyze
```

如果已经有 runner：

```bash
node .gitnexus/run.cjs status
node .gitnexus/run.cjs analyze
```

需要控制流、数据流或 taint 分析时：

```bash
node .gitnexus/run.cjs analyze --pdg
```

### 3. 让 agent 通过图谱理解代码

优先读取：

```text
gitnexus://repo/{name}/context
gitnexus://repo/{name}/clusters
gitnexus://repo/{name}/processes
gitnexus://repo/{name}/schema
```

常用工具：

```text
query
context
impact
trace
detect_changes
check
explain
pdg_query
```

### 4. 修改、验证、提交

CodeLevelUp 推荐每次只做一个窄范围改动：

1. 记录当前 `git status --short`。
2. 用 GitNexus 查询相关模块、符号、流程和影响范围。
3. 修改最小必要文件。
4. 运行探测脚本推荐的测试、lint、build 或安全扫描。
5. 只 stage 本次改动文件。
6. 提交时在 commit body 中写明 GitNexus 证据和验证命令。

## 本地验证

在 CodeLevelUp 仓库根目录运行：

```bash
python scripts/test_probe_project.py
python /Users/olym/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
python scripts/probe_project.py --json /Users/olym/Documents/resume_project
```

## 与 GitNexus 的关系

CodeLevelUp 不是 GitNexus 的 fork，也不包含 GitNexus 源码。它是一个围绕 GitNexus 使用方式设计的 Codex skill 项目：

- GitNexus 负责生成和查询代码知识图谱。
- CodeLevelUp 负责告诉 agent 何时建立图谱、如何使用图谱、如何结合验证和提交完成本地代码升级。

参考项目：

- [abhigyanpatwari/GitNexus](https://github.com/abhigyanpatwari/GitNexus)

---

## English

CodeLevelUp is a project-local Codex skill for upgrading local codebases with a
GitNexus-first knowledge graph workflow. It helps an agent understand repository
structure, module boundaries, execution flows, impact radius, and verification
paths before making code changes.

It is inspired by the local GitNexus skills and by the
[abhigyanpatwari/GitNexus](https://github.com/abhigyanpatwari/GitNexus) project:
index first, understand the graph, patch narrowly, verify locally, then commit.

## Project Goals

CodeLevelUp does not replace GitNexus. It packages a GitNexus-oriented workflow
as a reusable Codex skill so agents can use graph-backed code intelligence during
local upgrades, security fixes, dependency modernization, API migrations, and
quality improvements.

Use it to:

- Build or refresh a GitNexus knowledge graph for a local repository.
- Help an agent understand architecture, module boundaries, and execution flows.
- Check impact radius and call chains before editing code.
- Confirm affected paths when fixing vulnerabilities or upgrading dependencies.
- Run local tests, lint checks, builds, and security scans.
- Commit only narrow, verified changes.

## Project Structure

```text
CodeLevelUp/
├── README.md
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── gitnexus-workflow.md
│   └── upgrade-loop.md
├── scripts/
│   ├── probe_project.py
│   └── test_probe_project.py
└── .gitignore
```

### Root

| Path | Purpose |
| --- | --- |
| `README.md` | Bilingual project documentation with structure, installation, usage, and validation notes. |
| `SKILL.md` | Main Codex skill entrypoint with frontmatter, operating contract, GitNexus-first workflow, modes, and stop conditions. |
| `.gitignore` | Ignores Python caches, virtual environments, local GitNexus indexes, Node dependencies, and build outputs. |

### `agents/`

`agents/` stores runtime and UI metadata for the skill.

| Path | Purpose |
| --- | --- |
| `agents/openai.yaml` | Defines display name `CodeLevelUp`, short description, default prompt, and implicit invocation policy. |

### `references/`

`references/` contains longer instructions loaded only when needed. This keeps
`SKILL.md` compact while still giving the agent detailed procedures.

| Path | Purpose |
| --- | --- |
| `references/gitnexus-workflow.md` | Explains how to bootstrap, refresh, and use GitNexus graphs, including `analyze`, `status`, `--pdg`, MCP resources, and graph tools. |
| `references/upgrade-loop.md` | Describes the full upgrade loop: snapshot, graph orientation, research, patch, verify, and commit. |

### `scripts/`

`scripts/` contains deterministic helper scripts. By default they only inspect
the target repository. They do not install dependencies, access the network, or
modify the target project.

| Path | Purpose |
| --- | --- |
| `scripts/probe_project.py` | Detects ecosystems, manifests, lockfiles, verification commands, security scan commands, and GitNexus runner/index state. |
| `scripts/test_probe_project.py` | Unit tests for `probe_project.py`, covering Python, Node, Go, Rust, and GitNexus runner/index detection. |

## Skill Name And Invocation

The Codex-compatible skill trigger is:

```text
$code-level-up
```

The UI and GitHub project name is:

```text
CodeLevelUp
```

Example prompt:

```text
Use $code-level-up to inspect this repo with GitNexus, plan an upgrade, verify it, and commit.
```

## Workflow

### 1. Probe The Project

Run this from anywhere:

```bash
python /path/to/CodeLevelUp/scripts/probe_project.py --json /path/to/target-repo
```

The script reports:

- detected ecosystems such as Python, Node, Go, or Rust;
- manifests and lockfiles such as `pyproject.toml`, `package.json`, or `Cargo.toml`;
- recommended setup commands;
- recommended verification commands such as `python -m pytest` or `python -m ruff check .`;
- recommended security scan commands such as `python -m pip_audit`, `pnpm audit`, or `cargo audit`;
- whether a GitNexus runner exists;
- whether a GitNexus index exists;
- GitNexus bootstrap commands and MCP resource entrypoints.

### 2. Build The GitNexus Knowledge Graph

If the target repository does not have `.gitnexus/run.cjs`:

```bash
npx gitnexus analyze
```

If the runner already exists:

```bash
node .gitnexus/run.cjs status
node .gitnexus/run.cjs analyze
```

For control-flow, data-flow, or taint analysis:

```bash
node .gitnexus/run.cjs analyze --pdg
```

### 3. Understand Code Through The Graph

Start with:

```text
gitnexus://repo/{name}/context
gitnexus://repo/{name}/clusters
gitnexus://repo/{name}/processes
gitnexus://repo/{name}/schema
```

Common tools:

```text
query
context
impact
trace
detect_changes
check
explain
pdg_query
```

### 4. Patch, Verify, Commit

CodeLevelUp encourages one narrow change at a time:

1. Record `git status --short`.
2. Use GitNexus to inspect related modules, symbols, flows, and impact radius.
3. Edit the smallest necessary set of files.
4. Run the tests, lint checks, builds, or security scans recommended by the probe.
5. Stage only the files changed for this run.
6. Include GitNexus evidence and verification commands in the commit body.

## Local Validation

Run from the CodeLevelUp repository root:

```bash
python scripts/test_probe_project.py
python /Users/olym/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
python scripts/probe_project.py --json /Users/olym/Documents/resume_project
```

## Relationship To GitNexus

CodeLevelUp is not a GitNexus fork and does not vendor GitNexus source code. It
is a Codex skill project designed around the GitNexus workflow:

- GitNexus builds and queries the code knowledge graph.
- CodeLevelUp tells the agent when to build the graph, how to use it, and how to
  combine graph evidence with local verification and commits.

Reference project:

- [abhigyanpatwari/GitNexus](https://github.com/abhigyanpatwari/GitNexus)
