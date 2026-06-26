# Code Search Workflow

Use this page when the code graph is unavailable or incomplete. Prefer
`code-graph-workflow.md` for tasks that need impact lookup.

## Fallback Search

Start with local repository tools:

```bash
git status --short
rg --files
rg -n "<query>"
```

Search output is only a locator. Read the returned files directly before
editing, then trace imports, callsites, tests, manifests, and lockfiles by hand.

## Promote To Graph

Build or refresh `.codelevelup/graph/graph.json` when:

- the task touches multiple services or packages;
- dependency reachability matters;
- many symbols share the same name;
- vulnerability repair needs package-to-source impact evidence;
- the first fallback search returns too many candidates.

If no helper is available, record that graph-backed lookup was not run and state
which fallback searches were used.
