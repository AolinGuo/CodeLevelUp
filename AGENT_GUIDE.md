# CodeLevelUp Agent Guide

This guide is a router for agents. The authoritative workflow lives in
`skills/codelevelup/SKILL.md`. If this guide and the skill disagree, follow the
skill.

## Entry Order

1. Read `skills/codelevelup/SKILL.md`.
2. Read `skills/codelevelup/references/agent-entry-layer.md`.
3. Use skill-only mode by default. If an MCP client is configured, the optional
   helper may expose project probing and local code graph tools.
4. Store durable run artifacts in the target repository under `.codelevelup/`
   when the task needs traceability.

## Route By Task

| User asks for | Read next |
| --- | --- |
| unclear upgrade or broad change | `requirements-gate.md` section in the active workflow |
| faster code location or impact lookup | `code-graph-workflow.md`, then `graph-query-patterns.md` |
| dependency/API/tooling modernization | `self-upgrade-workflow.md` |
| SCA, CVE, vulnerable dependency repair | `vulnerability-remediation-workflow.md` |
| local CI, review, merge readiness | `verification-review-workflow.md` |

## Helper Boundary

Do not ask the user to remember helper commands. Treat helper runtime access as
an implementation detail behind the skill and MCP. If helper access is missing,
use `git`, `rg`, file reads, manifests, lockfiles, README, and project-native
verification commands.
