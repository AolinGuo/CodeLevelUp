# CodeLevelUp Architecture

CodeLevelUp is a skill-first project. The project skeleton separates agent
routing, skill contracts, references, optional helper code, tests, and docs. The
core purpose is code self-upgrade and vulnerability repair through local code
understanding.

## Layers

- `AGENT_GUIDE.md`: agent routing index.
- `skills/codelevelup/`: distributable skill bundle and workflow references.
- `skills/codelevelup/references/code-graph-workflow.md`: local code graph
  storage and build contract.
- `src/codelevelup/`: optional helper implementation behind the skill.
- `.codelevelup/`: target-project-local graph and run artifacts.
- `tests/`: regression tests for structure, helper behavior, MCP, and probing.
- `tools/`: deterministic repository maintenance utilities.

## Entry Flow

```text
Agent
  -> AGENT_GUIDE.md
  -> skills/codelevelup/SKILL.md
  -> skills/codelevelup/references/agent-entry-layer.md
  -> skill-only workflow or optional MCP helper
```

The helper is optional. If it is unavailable, the skill still instructs the
agent to inspect the repository directly with `git`, `rg`, file reads, manifests,
lockfiles, and project-native verification commands.
