# CodeLevelUp

CodeLevelUp is a local code upgrade assistant packaged as an agent skill, a CLI,
and a stdio MCP server. It helps an agent inspect a repository, locate code,
plan a small upgrade, run local verification, and prepare an intentional commit.

CodeLevelUp 是一个本地代码自升级助手，提供 agent skill、CLI 和 stdio MCP
三种入口。它用于帮助智能体检查仓库、定位代码、规划小步升级、在本地验证，并准备
有边界的提交。

## What It Provides / 能力范围

- Agent skill instructions for code upgrade workflows.
- Local CLI commands for project probing, code search, and upgrade preparation.
- A stdio MCP server that Claude Desktop, Claude Code, Codex, or other MCP
  clients can call locally.
- Repository probing for Python, Node, Go, and Rust projects.
- Local verification command discovery.
- Security audit command suggestions.
- A strict local-first workflow: dependencies and generated state stay inside
  the target project sandbox.

- 面向代码升级工作流的 agent skill 说明。
- 面向项目探测、代码定位和升级准备的本地 CLI。
- 可被 Claude Desktop、Claude Code、Codex 或其他 MCP 客户端本地调用的 stdio
  MCP 服务。
- 支持探测 Python、Node、Go、Rust 项目。
- 自动发现本地验证命令。
- 给出安全扫描命令建议。
- 坚持本地优先：依赖和生成状态只放在目标项目的沙盒中。

## Install / 安装

From this project directory:

在当前项目目录执行：

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

After installation:

安装后可直接使用：

```bash
codelevelup --help
codelevelup-mcp
```

The scripts also work without installation:

也可以不安装，直接运行脚本：

```bash
python scripts/codelevelup.py --help
python scripts/codelevelup_mcp.py
```

## CLI / 命令行

Probe a target repository:

探测目标仓库：

```bash
codelevelup probe --json /path/to/repo
```

Search local source files:

搜索本地源码：

```bash
codelevelup search /path/to/repo "target_symbol" --json
```

## MCP / MCP 接入

Run the local stdio MCP server:

运行本地 stdio MCP 服务：

```bash
codelevelup-mcp
```

For Claude Desktop, copy and edit:

Claude Desktop 可参考并修改：

```text
mcp/claude_desktop_config.example.json
```

Available MCP tools:

可用 MCP 工具：

- `probe_project`
- `search_code`

Additional code-search index tools are described in the next section.

额外的代码搜寻索引工具见下一节。

## Code Search / 代码搜寻

The code search part references GitNexus-style graph-backed code location: first
find the relevant files and symbols, then read source and check impact before
editing. CodeLevelUp does not vendor GitNexus and is not a GitNexus fork. When a
target repository already has GitNexus or you allow installing it in that
project sandbox, CodeLevelUp can discover or preview:

代码搜寻部分参考 GitNexus 的图谱化代码定位思路：先定位相关文件和符号，再阅读源码
并检查影响范围，然后再修改。CodeLevelUp 不内置 GitNexus，也不是 GitNexus 的 fork。
如果目标仓库已经配置 GitNexus，或你允许在该项目沙盒中安装它，CodeLevelUp 可以发现
或预览：

```bash
codelevelup gitnexus status /path/to/repo --json
codelevelup gitnexus analyze /path/to/repo --pdg --dry-run --json
```

MCP exposes the same optional code-search index helpers:

MCP 也暴露同样的可选代码搜寻索引辅助工具：

- `gitnexus_status`
- `gitnexus_analyze_command`

If that tooling is unavailable, use the built-in literal search and normal file
reads, then state that no graph-backed audit was run.

如果该工具不可用，就使用内置字面量搜索和普通文件阅读，并明确说明没有运行图谱审计。

## Project Structure / 项目结构

```text
CodeLevelUp/
├── README.md
├── SKILL.md
├── AGENTS.md
├── CLAUDE.md
├── pyproject.toml
├── agents/
│   └── openai.yaml
├── mcp/
│   └── claude_desktop_config.example.json
├── references/
│   ├── code-search-workflow.md
│   └── upgrade-loop.md
├── scripts/
│   ├── codelevelup.py
│   ├── codelevelup_mcp.py
│   ├── probe_project.py
│   ├── test_cli_mcp.py
│   └── test_probe_project.py
└── .gitignore
```

- `SKILL.md`: agent-facing workflow contract.
- `AGENTS.md`: portable agent instructions.
- `CLAUDE.md`: Claude-specific CLI and MCP notes.
- `pyproject.toml`: editable local install and console entry points.
- `scripts/codelevelup.py`: local CLI implementation.
- `scripts/codelevelup_mcp.py`: stdio MCP server implementation.
- `scripts/probe_project.py`: project ecosystem and command detector.
- `references/code-search-workflow.md`: optional graph-backed code search notes.
- `references/upgrade-loop.md`: upgrade, verification, and commit loop.
- `mcp/claude_desktop_config.example.json`: Claude Desktop MCP example.

- `SKILL.md`：面向 agent 的工作流约束。
- `AGENTS.md`：跨 agent 的通用说明。
- `CLAUDE.md`：Claude 使用 CLI 和 MCP 的说明。
- `pyproject.toml`：本地 editable 安装和命令入口。
- `scripts/codelevelup.py`：本地 CLI 实现。
- `scripts/codelevelup_mcp.py`：stdio MCP 服务实现。
- `scripts/probe_project.py`：项目生态和命令探测器。
- `references/code-search-workflow.md`：可选的图谱化代码搜寻说明。
- `references/upgrade-loop.md`：升级、验证和提交循环。
- `mcp/claude_desktop_config.example.json`：Claude Desktop MCP 配置示例。

## Validation / 验证

Run the project checks:

运行项目检查：

```bash
python scripts/test_probe_project.py
python scripts/test_cli_mcp.py
python /Users/olym/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

Smoke test CLI and MCP locally:

本地烟测 CLI 和 MCP：

```bash
codelevelup probe --json /path/to/repo
codelevelup search /path/to/repo "CodeLevelUp" --json
codelevelup-mcp
```

## Upgrade Discipline / 升级纪律

1. Inspect `git status --short` before editing.
2. Probe the target repository.
3. Locate relevant code and read source before patching.
4. Make one scoped change.
5. Run detected verification commands.
6. Stage explicit files only.
7. Commit with the reason and verification result.

1. 修改前先检查 `git status --short`。
2. 探测目标仓库。
3. 先定位相关代码并阅读源码，再打补丁。
4. 每次只做一个边界清晰的改动。
5. 运行发现到的验证命令。
6. 只暂存明确需要提交的文件。
7. 提交信息写清原因和验证结果。
