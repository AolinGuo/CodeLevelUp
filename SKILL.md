---
name: code-level-up
description: Upgrade and audit local codebases with a GitNexus-first knowledge-graph workflow. Use when the user asks to level up code, understand local code before changing it, build or refresh a GitNexus index, inspect impact or execution flows, fix vulnerabilities, modernize dependencies, improve code quality, verify locally, commit changes, or maintain this CodeLevelUp skill.
---

# CodeLevelUp

## Operating Contract

Use GitNexus before risky code changes. Build or refresh the local knowledge
graph, inspect affected symbols and flows, make one narrow improvement, verify
locally, then commit only the intended files. Do not push unless the user asks.

Respect user work. Inspect `git status --short` before editing, never stage
unrelated changes, and never revert files you did not change.

## Quick Start

1. Run `python scripts/probe_project.py --json` from this skill directory to
   inspect the current target repository when the script is copied or invoked
   with a path, or run `python CodeLevelUp/scripts/probe_project.py --json`
   from the parent workspace.
2. Read `references/gitnexus-workflow.md` for indexing and graph queries.
3. Read `references/upgrade-loop.md` for the end-to-end code improvement loop.
4. If no `.gitnexus/run.cjs` exists in the target repo, run
   `npx gitnexus analyze` from the target repository root.
5. If the runner exists, run `node .gitnexus/run.cjs status`; if stale, run
   `node .gitnexus/run.cjs analyze`.
6. Use GitNexus resources and tools before edits:
   - `gitnexus://repo/{name}/context`
   - `gitnexus://repo/{name}/clusters`
   - `gitnexus://repo/{name}/processes`
   - `query`, `context`, `impact`, `trace`, `detect_changes`, `check`
7. Patch one scoped improvement, run verification, stage explicit paths, and
   commit.

## Modes

- **Knowledge graph mode**: index the repository and summarize architecture,
  clusters, processes, and key symbols for agent orientation.
- **Impact audit mode**: use `detect_changes`, `impact`, and `context` to check
  blast radius before modifying or committing code.
- **Security mode**: combine dependency scanners with GitNexus impact checks to
  confirm whether vulnerable code paths are reachable.
- **Upgrade mode**: use release notes plus graph impact to modernize APIs,
  dependencies, or code structure in small verified commits.
- **Self-maintenance mode**: when improving this skill, update only this folder,
  run script tests and skill validation, then commit the skill change.

## Stop Conditions

Stop and ask when:

- GitNexus indexing requires credentials or fails in a way that changes the
  upgrade decision;
- verification requires production services or destructive data changes;
- the diff includes unrelated user changes;
- the graph shows a broader architectural decision is needed before patching;
- the requested publication would expose private code or secrets.
