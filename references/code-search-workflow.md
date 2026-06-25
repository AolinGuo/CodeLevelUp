# Code Search Workflow

Use this page only when code lookup needs more than direct file reads.

## Built-In Search

Start with local literal search:

```bash
python scripts/codelevelup.py search <target_repo> "<query>" --json
```

Read the returned source files before editing. Search output is a locator, not
evidence by itself.

## Optional GitNexus-Backed Lookup

The code search portion of CodeLevelUp can reference GitNexus-style graph-backed
code location. If the target repository already has a `.gitnexus/run.cjs`
runner, inspect it first:

```bash
python scripts/codelevelup.py gitnexus status <target_repo> --json
```

If the runner is missing and the user allows installing project-local tooling,
bootstrap from the target repository root:

```bash
npx gitnexus analyze
```

After bootstrap, prefer the local runner:

```bash
node .gitnexus/run.cjs status
node .gitnexus/run.cjs analyze
node .gitnexus/run.cjs analyze --pdg
```

Use `--pdg` only when the task needs taint, control-dependence, or
data-dependence inspection.

## MCP-Oriented Lookup

When a GitNexus MCP server is available for the same target repository, query
repository context before edits:

- `gitnexus://repo/{name}/context`
- `gitnexus://repo/{name}/clusters`
- `gitnexus://repo/{name}/processes`
- `gitnexus://repo/{name}/schema`

Useful query tools include:

- `query`
- `context`
- `impact`
- `trace`
- `detect_changes`
- `check`
- `explain`
- `pdg_query`

## Fallback Rule

If graph-backed lookup is unavailable, use built-in search and direct file
reading. State clearly that the result was not graph-audited.
