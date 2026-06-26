# Code Self-Upgrade Workflow

Use this workflow for code self-upgrade work: dependency modernization, API
migration, refactoring for maintainability, toolchain updates, or small
automated quality improvements.

## Requirements Gate

The requirements gate is mandatory for every code self-upgrade request.

Do not modify code until the request is specific enough to bound cost and risk.
Clarify:

- target repository, service, package, or subsystem;
- upgrade goal, such as dependency version, CVE fix, API migration, or quality
  improvement;
- allowed files and forbidden areas;
- expected verification commands;
- whether an autonomous commit is requested.

If the request is still broad, ask for the missing boundary instead of spending
tokens on speculative edits.

## Orientation

1. Run `git status --short` and preserve unrelated user changes.
2. Read `skills/codelevelup/references/agent-entry-layer.md`.
3. Probe the project with the helper entry when available, or inspect manifests,
   lockfiles, README, CI, package scripts, Makefiles, and test config directly.
4. Build or approximate the local code graph described in
   `skills/codelevelup/references/code-graph-workflow.md`.
5. Read source files before editing. Search output is only a locator.

## Plan

Write a short implementation note before patching:

- current behavior or dependency state;
- intended smallest change;
- expected affected files and call paths;
- verification commands;
- rollback path if verification fails.

For external upgrades, prefer primary sources such as release notes, migration
guides, security advisories, and upstream changelogs.

## Patch

- Change one bounded concern at a time.
- For behavior changes, write or update a test first and watch it fail for the
  expected reason.
- Keep dependency updates minimal unless the user requested a broader upgrade.
- Do not rewrite unrelated formatting, generated files, or lockfiles outside the
  chosen package manager's normal update path.

## Verify And Commit

Run local CI-equivalent verification from the target project. If the helper
runtime is unavailable, use project-native commands discovered during
orientation. Follow
`skills/codelevelup/references/verification-review-workflow.md` before claiming
readiness.

Commit only when the user requested autonomous commit or has approved the patch.
Stage explicit paths and include:

```text
Why:
- <self-upgrade goal>

Scope:
- <affected files and dependency changes>

Verification:
- <command>: <result>
```

Never push or merge without explicit user approval.
