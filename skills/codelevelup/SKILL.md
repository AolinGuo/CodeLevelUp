---
name: code-level-up
description: Use when a local codebase needs code self-upgrade, vulnerability repair, dependency modernization, graph-backed code understanding, local verification, MCP helper access, or CodeLevelUp maintenance.
---

# CodeLevelUp

## Operating Contract

Use CodeLevelUp as a skill-first local upgrade assistant for code self-upgrade
and vulnerability repair. Clarify the request, build or approximate a local code
graph, query the graph to locate affected files and symbols, make one narrow
change, verify locally, then prepare human review. Commit only when requested or
approved. Do not push or merge unless the user asks.

Respect user work. Inspect `git status --short` before editing, never stage
unrelated changes, and never revert files you did not change.

This project is not Codex-only. Use it as an agent skill first:

- this bundled skill file in Codex or any agent that reads `skills/codelevelup/SKILL.md`;
- the unified entry contract in `skills/codelevelup/references/agent-entry-layer.md`;
- `codelevelup-agent mcp` or `bin/codelevelup-agent mcp` for Claude and other
  MCP clients when optional helper tools are available.

Files under `src/codelevelup/` are implementation modules. Do not ask agents to
run those modules directly.

## Quick Start

1. Read `skills/codelevelup/references/agent-entry-layer.md` and choose skill-only
   or MCP helper mode based on what the local environment supports.
2. If helper runtime is unavailable, continue in skill-only mode with `git`, `rg`,
   direct file reads, and project-native verification commands.
3. Store durable run artifacts in the target repository under `.codelevelup/`
   when traceability is needed.
4. Read `skills/codelevelup/references/code-graph-workflow.md` before code
   understanding, impact lookup, code self-upgrade, or vulnerability repair.
5. Read `skills/codelevelup/references/graph-query-patterns.md` to query symbols,
   packages, imports, files, tests, and affected paths.
6. Read `skills/codelevelup/references/self-upgrade-workflow.md` for dependency
   modernization, API migration, refactoring, or toolchain upgrades.
7. Read `skills/codelevelup/references/vulnerability-remediation-workflow.md`
   for SCA, CVE, vulnerable dependency, CI, and human-review remediation work.
8. Read `skills/codelevelup/references/verification-review-workflow.md` before
   claiming readiness, committing, or preparing merge.
9. Read `skills/codelevelup/references/upgrade-loop.md` for the general end-to-end code improvement loop.
10. Patch one scoped improvement, run verification, stage explicit paths, and
    commit only when requested or approved.

## Modes

- **Probe mode**: detect manifests, lockfiles, setup commands, verification
  commands, security commands, and available local `.codelevelup` graph state.
- **Code graph mode**: build or approximate a local graph of files, symbols,
  imports, packages, manifests, tests, and verification commands.
- **Graph query mode**: use graph queries first for impact lookup, then read the
  returned source files directly.
- **Impact audit mode**: check blast radius before modifying or committing code.
- **Vulnerability repair mode**: run incremental SCA, find a fixed version,
  update dependencies in the target sandbox, run CI-equivalent verification, and
  prepare human review before merge.
- **Self-upgrade mode**: use the requirements gate, code understanding, release
  notes, and impact checks to modernize APIs, dependencies, tooling, or code
  structure in small verified patches.
- **Repair loop mode**: when verification fails after a patch, use
  `codelevelup repair` (or MCP `repair_loop`) to run structured
  test-verify-fix cycles. The module reports failures (error type, file, line,
  suggestion) without modifying code. The Agent proposes and applies patches;
  CodeLevelUp closes the observation loop. Use `repair_memory` (or MCP
  `repair_hints`) to consult past repairs before each new attempt. Max 5 rounds
  by default.
- **Self-maintenance mode**: when improving this skill, update only this folder,
  run project tests and skill validation, then commit the skill change.

## Stop Conditions

Stop and ask when:

- optional graph helper access fails and the fallback search cannot bound the
  upgrade decision;
- verification requires production services or destructive data changes;
- the diff includes unrelated user changes;
- the code search or impact check shows a broader architectural decision is
  needed before patching;
- the requested publication would expose private code or secrets.
