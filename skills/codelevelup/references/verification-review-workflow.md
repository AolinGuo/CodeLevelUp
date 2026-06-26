# Verification And Review Workflow

Use this workflow after a code self-upgrade or vulnerability repair patch.

## Local Verification

Run project-native commands discovered from manifests, README, Makefiles, CI
config, package scripts, and probe results. Prefer the smallest verification
that proves the touched service, then run broader checks when the blast radius
requires it.

Record:

- command;
- working directory;
- exit code;
- important output summary;
- whether the result blocks human review.

## Review Gate

Automation can prepare a review, but it must not merge. A review artifact should
include:

- original request and bounded scope;
- graph or fallback search evidence;
- files changed;
- dependency or API deltas;
- verification output;
- residual risk;
- manual checks needed before merge.

## Fuse Policy

- Passing verification may mark the change ready for human review.
- Failing verification routes to a human with logs and the failed command.
- Three consecutive failures for the same finding stop automatic retries until a
  human reviews the failure mode.
