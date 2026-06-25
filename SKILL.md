---
name: code-level-up
description: Upgrade and audit local codebases with portable agent instructions, CLI commands, MCP tools, local code search, optional GitNexus-backed indexing, verification, and intentional commits. Use when the user asks to level up code, understand local code before changing it, inspect impact or execution flows, fix vulnerabilities, modernize dependencies, improve code quality, verify locally, commit changes, or maintain this CodeLevelUp project.
---

# CodeLevelUp

## Operating Contract

Use CodeLevelUp as a local-first upgrade assistant. Probe the target repository,
locate the relevant code, inspect affected symbols and flows, make one narrow
improvement, verify locally, then commit only the intended files. Do not push
unless the user asks.

Respect user work. Inspect `git status --short` before editing, never stage
unrelated changes, and never revert files you did not change.

This project is not Codex-only. Use it through:

- this skill file in Codex or any agent that reads `SKILL.md`;
- `python scripts/codelevelup.py` or the installed `codelevelup` CLI;
- `python scripts/codelevelup_mcp.py` or the installed `codelevelup-mcp` stdio
  MCP server for Claude and other MCP clients.

## Quick Start

1. Run `python scripts/codelevelup.py probe --json <target_repo>` from this
   project directory, or run `codelevelup probe --json <target_repo>` after
   `python -m pip install -e .`.
2. Read `references/code-search-workflow.md` when code lookup needs graph-backed
   indexing or impact checks.
3. Read `references/upgrade-loop.md` for the end-to-end code improvement loop.
4. Use `python scripts/codelevelup.py search <target_repo> <query> --json` for
   literal local search when no MCP graph tool is available.
5. If GitNexus is available or desired, use
   `python scripts/codelevelup.py gitnexus status <target_repo> --json` and
   `python scripts/codelevelup.py gitnexus analyze <target_repo> --dry-run --json`
   to inspect or preview indexing commands.
6. Patch one scoped improvement, run verification, stage explicit paths, and
   commit.

## Modes

- **Probe mode**: detect manifests, lockfiles, setup commands, verification
  commands, security commands, and available local index state.
- **Code search mode**: use local literal search first, then optional graph-backed
  lookup when the target repo supports it.
- **Impact audit mode**: check blast radius before modifying or committing code.
- **Security mode**: combine dependency scanners with source inspection and
  optional impact checks to confirm whether vulnerable code paths are reachable.
- **Upgrade mode**: use release notes plus graph impact to modernize APIs,
  dependencies, or code structure in small verified commits.
- **Self-maintenance mode**: when improving this skill, update only this folder,
  run script tests and skill validation, then commit the skill change.

## Stop Conditions

Stop and ask when:

- optional indexing requires credentials or fails in a way that changes the
  upgrade decision;
- verification requires production services or destructive data changes;
- the diff includes unrelated user changes;
- the code search or impact check shows a broader architectural decision is
  needed before patching;
- the requested publication would expose private code or secrets.
