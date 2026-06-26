# Graph Query Patterns

Use these patterns after the local code graph exists, or approximate them with
`rg` and source reads in skill-only mode.

## Find Symbols

Ask for nodes whose `name`, `path`, or `id` matches the target API, function,
class, package, or vulnerability finding.

Then inspect:

- defining file;
- import edges;
- caller or reference candidates;
- nearby tests.

## Trace Dependency Impact

For dependency upgrades, start from a `Package` or `Manifest` node and walk:

```text
Package <- depends_on - Manifest/File
Package <- imports - File
File - defines -> Symbol
Symbol - tested_by -> Test
```

If graph data is incomplete, fall back to manifest parsing and text search for
package names, import names, and API names.

## Bound A Patch

Before editing, produce a short patch set:

- files expected to change;
- symbols expected to change;
- tests or verification commands expected to prove the change;
- files intentionally excluded.

## Avoid False Confidence

- Query results are candidates, not proof.
- Read files before modifying them.
- Rebuild or refresh the graph after dependency or source layout changes.
- State when the graph is incomplete and what fallback search was used.
