# Upgrade Loop

Use this loop for each CodeLevelUp run.

## 1. Snapshot

- Run `git status --short`.
- Read `skills/codelevelup/references/agent-entry-layer.md`.
- Use optional MCP helper probing when available. In skill-only mode, inspect
  manifests, lockfiles, README, CI config, Makefiles, and package scripts
  directly.
- Record manifests, lockfiles, verification commands, and `.codelevelup` graph
  state.

## 2. Code Orientation

- Build or approximate the local code graph, then query symbols, imports,
  packages, and tests. Use `rg` as a fallback locator.
- Read source files directly before editing.
- When graph helper tooling is available, refresh `.codelevelup/graph/graph.json`
  and inspect affected files, symbols, and changed flows.

## 3. Research

For dependency, security, or API upgrades, use current primary sources:

- official release notes and migration guides;
- GitHub Security Advisories, OSV, NVD, RustSec, Go vulnerability database;
- upstream GitHub issues and pull requests;
- papers or project docs when the user asks for research-guided improvements.

## 4. Patch

Make the smallest useful change. For behavior changes, write or update the test
first and verify it fails for the expected reason before implementing.

## 4a. Repair (When Verification Fails)

If the first verification fails, enter the repair loop:

1. Run `codelevelup repair <commands> --cwd <repo> --json` to get structured
   failure context (error type, file, line, message, suggestion).
2. Check repair memory: `codelevelup repair-memory search --root <repo>
   --error-type <type> --message <msg>` or the MCP `repair_hints` tool.
3. Apply a targeted patch informed by the failure context and any past repairs.
4. Re-run the repair loop. Repeat up to `max_retries` (default 5).
5. If all retries are exhausted, surface the full failure chain to the user
   and request manual intervention.

The repair loop **never modifies code** — it only reports structured failures.
Code changes remain the Agent's responsibility.

## 5. Verify

Run commands found by the entry layer or by direct project inspection, plus any
project-specific commands from README, Makefile, CI, or package scripts. If
verification fails, enter the repair loop (Step 4a) before reverting.

## 6. Commit

Stage explicit paths only. Use a commit body with:

```text
Why:
- <upgrade reason>

Code search:
- <source files, graph evidence, or fallback note>

Verification:
- <command>: <result>

Repair (if applicable):
- <round>: <error_type> in <file>:<line> -> <fix>
```
