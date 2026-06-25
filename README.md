# CodeLevelUp

CodeLevelUp is a project-local Codex skill for upgrading local codebases with a
GitNexus-first understanding loop. It helps an agent build or refresh a local
knowledge graph, inspect code impact before changes, run local verification, and
commit narrow improvements.

Inspired by the local GitNexus skills and the
[abhigyanpatwari/GitNexus](https://github.com/abhigyanpatwari/GitNexus) project.

## Use

Install this folder as a Codex skill, then invoke:

```text
Use $code-level-up to inspect this repo with GitNexus, plan an upgrade, verify it, and commit.
```

From a target repository, the helper can suggest setup, verification, security,
and GitNexus commands:

```bash
python scripts/probe_project.py --json
```

## Validate

```bash
python scripts/test_probe_project.py
python /Users/olym/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```
