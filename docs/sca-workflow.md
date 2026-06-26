# SCA Workflow

The planned SCA remediation loop follows the same skill-first discipline as
normal code upgrades. The executable agent-facing version lives in
`skills/codelevelup/references/vulnerability-remediation-workflow.md`.
Use `skills/codelevelup/references/code-graph-workflow.md` to connect vulnerable
packages to manifests, imports, files, symbols, and tests.

## Flow

1. Clarify the upgrade request and scope before changing code.
2. Detect dependency manifests and lockfiles for the affected service.
3. Run incremental project-local audit tools inside the target sandbox.
4. Compare vulnerable ranges with fixed versions and reachability evidence.
5. Apply the smallest dependency change.
6. Run CI-equivalent local verification.
7. Prepare a human-reviewed merge request with CVE identifiers, severity, files
   changed, test output, and residual risk.

## Fuse Policy

- Passing CI can mark a change as mergeable, but automation must not merge.
- CI failure routes the change to a human.
- Three consecutive CI failures stop automatic alerting for the same finding
  until a human reviews the failure mode.
