# GitNexus Workflow

CodeLevelUp follows the local GitNexus skill pattern and the public
`abhigyanpatwari/GitNexus` project: create a local knowledge graph first, then
let the agent reason over architecture, execution flows, impact, and invariants.

## Bootstrap

From the target repository root:

```bash
npx gitnexus analyze
```

This creates `.gitnexus/` and a local runner. After that, prefer the runner:

```bash
node .gitnexus/run.cjs status
node .gitnexus/run.cjs analyze
node .gitnexus/run.cjs analyze --pdg
node .gitnexus/run.cjs wiki --lang english
```

Use `--pdg` when the task needs taint, control-dependence, or data-dependence
queries.

## Start Every Code Understanding Task

1. Read `gitnexus://repo/{name}/context`.
2. If the index is stale, run `node .gitnexus/run.cjs analyze`.
3. Read the most relevant resource:
   - `gitnexus://repo/{name}/clusters`
   - `gitnexus://repo/{name}/processes`
   - `gitnexus://repo/{name}/schema`
4. Query the graph:
   - `query({search_query: "<concept>"})`
   - `context({name: "<symbol>"})`
   - `impact({target: "<symbol>", direction: "upstream"})`
   - `trace({from: "<symbol>", to: "<symbol>"})`
   - `detect_changes({scope: "worktree"})`
   - `check({})`

## Review And Upgrade Checklist

- Map changed files to symbols and processes.
- Check direct callers with `context`.
- Check blast radius with `impact`.
- Check changed worktree effects with `detect_changes`.
- For security-sensitive work, use `explain` and `pdg_query` only after indexing
  with `--pdg`.
- Read source files after graph queries; do not rely on graph summaries alone.
- Include graph findings in the commit body when they affected the patch.

## Fallback

If GitNexus is unavailable, use normal code search and file reads, but state that
the graph-backed audit could not run. Do not present a non-graph audit as a
GitNexus-verified result.
