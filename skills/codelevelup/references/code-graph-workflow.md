# Code Graph Workflow

Use the local code graph when plain text search is too slow or too shallow for a
code self-upgrade or vulnerability repair task. The graph is built inside the
target repository and remains local.

## Storage Contract

Write durable graph state under:

```text
.codelevelup/graph/
├── graph.json
├── nodes.json
└── edges.json
```

Run-specific artifacts belong under `.codelevelup/runs/<run-id>/`.

## Graph Shape

Core node types:

- `File`
- `Function`
- `Class`
- `Symbol`
- `Import`
- `Package`
- `Manifest`
- `Finding`
- `VerificationCommand`

Core edge types:

- `defines`
- `imports`
- `depends_on`
- `references`
- `tested_by`
- `affected_by`
- `fixes`
- `verified_by`

## Build Flow

1. Confirm the requirements gate has bounded the target repo and task.
2. Probe manifests, lockfiles, source roots, tests, and existing `.codelevelup`
   state.
3. Build or refresh `.codelevelup/graph/graph.json` when helper access exists.
4. In skill-only mode, create a lightweight mental graph from `rg`, direct file
   reads, imports, manifests, and tests.
5. Query the graph before editing, then read the returned source files directly.

## Use In Repairs

For vulnerability repair, connect:

```text
Package -> Manifest -> Lockfile -> Import -> File -> Symbol -> Test
```

For code self-upgrade, connect:

```text
Target API -> Callsite -> Symbol -> File -> Test -> VerificationCommand
```

The graph is a locator and impact map. It does not replace source reading or
local verification.
