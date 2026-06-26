# Agent Entry Layer

Skill-first means the agent starts from `skills/codelevelup/SKILL.md` and this
contract. Project helper tools are optional accelerators behind the skill; the
upgrade workflow does not require Python.

## Decision Order

1. **Skill mode**: always available. Read `skills/codelevelup/SKILL.md`, this file, and the relevant
   reference workflow. Use normal repository inspection commands and direct file
   reads.
2. **MCP mode**: use when an MCP client is configured. Run `codelevelup-agent mcp`
   from an installed environment or `bin/codelevelup-agent mcp` from this repo.

Do not run implementation modules directly from `src/`. They sit behind the
unified entry layer.

Store durable run artifacts inside the target repository when needed:

```text
.codelevelup/
├── graph/
│   └── graph.json
├── runs/
└── policy.yaml
```

## Skill-Only Fallback

If Python or the helper package is unavailable, continue with the skill:

```bash
git status --short
rg --files
rg -n "<query>"
```

Inspect manifests such as `pyproject.toml`, `package.json`, `go.mod`,
`Cargo.toml`, lockfiles, README files, CI config, and Makefiles. Identify setup,
test, lint, build, and security commands from the project itself. Install
dependencies only inside the target project's virtual environment, container, or
other explicit sandbox.

For code search, treat `rg` results as locators only. Read the source files and
trace affected call paths before changing code.

## Optional Helper Boundary

When helper runtime is available, prefer MCP tools exposed by
`codelevelup-agent mcp` instead of calling implementation scripts. Expected tool
semantics:

- `probe_project`: inspect manifests, lockfiles, setup, verification, security,
  and `.codelevelup` state.
- `build_code_graph`: write a local graph under `.codelevelup/graph/`.
- `query_code_graph`: locate files, symbols, imports, packages, and likely
  impact paths.
- `search_code`: fallback literal search when graph data is missing.

For a source checkout without installation, replace `codelevelup-agent` with
`bin/codelevelup-agent`.
