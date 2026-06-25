# Upgrade Loop

Use this loop for each CodeLevelUp run.

## 1. Snapshot

- Run `git status --short`.
- Run `python scripts/probe_project.py --json <target_repo>` when outside the
  target repo, or `python scripts/probe_project.py --json` from the target repo
  if the script is available there.
- Record manifests, lockfiles, verification commands, and GitNexus status.

## 2. Graph Orientation

- Bootstrap or refresh GitNexus.
- Read repository context.
- Query clusters, processes, and symbols related to the requested change.
- For existing diffs, run `detect_changes` and inspect affected flows.

## 3. Research

For dependency, security, or API upgrades, use current primary sources:

- official release notes and migration guides;
- GitHub Security Advisories, OSV, NVD, RustSec, Go vulnerability database;
- upstream GitHub issues and pull requests;
- papers or project docs when the user asks for research-guided improvements.

## 4. Patch

Make the smallest useful change. For behavior changes, write or update the test
first and verify it fails for the expected reason before implementing.

## 5. Verify

Run the commands recommended by `probe_project.py`, plus any project-specific
commands from README, Makefile, CI, or package scripts. If verification fails,
fix forward or revert only this run's files.

## 6. Commit

Stage explicit paths only. Use a commit body with:

```text
Why:
- <upgrade reason>

GitNexus:
- <context/impact/detect_changes evidence or fallback note>

Verification:
- <command>: <result>
```
