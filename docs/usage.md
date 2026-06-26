# CodeLevelUp Usage

## Skill-First

Start with:

1. `AGENT_GUIDE.md`
2. `skills/codelevelup/SKILL.md`
3. `skills/codelevelup/references/agent-entry-layer.md`

Then choose the workflow:

- `code-graph-workflow.md` for local graph construction and graph state.
- `graph-query-patterns.md` for symbol, package, import, and impact lookup.
- `self-upgrade-workflow.md` for dependency, API, refactor, or toolchain
  upgrades.
- `vulnerability-remediation-workflow.md` for SCA and CVE repair.
- `verification-review-workflow.md` for local verification and human review.

## Skill-Only Fallback

If no helper is available:

```bash
git status --short
rg --files
rg -n "<query>"
```

Read the relevant source files before editing. Search output is only a locator.
Do not start patching until the requirements gate has bounded scope and
verification.

## Optional Helper

The optional helper is exposed through `codelevelup-agent mcp`. Agents can use
MCP tools to probe the project, build `.codelevelup/graph/graph.json`, query the
graph, and fall back to literal source search.

Do not ask users to remember helper operations. They are implementation details
behind the skill.
