# Upgrade Request Gate Design

## Purpose

CodeLevelUp must reduce unnecessary code spending before an agent upgrades code,
fixes vulnerabilities, migrates APIs, repairs tests, or refactors a project. The
agent must first prove that the request is clear enough to act on. If the
request is incomplete, CodeLevelUp must return missing fields and clarifying
questions instead of allowing the workflow to proceed into code changes.

## Scope

This design adds a pre-upgrade requirement gate. It does not implement automatic
code modification, vulnerability research, dependency installation, test
execution, Git commits, or GitNexus indexing. Future workflows can reuse the
gate, but this design only establishes the contract that decides whether work may
begin.

## Requirements

- The gate must be usable from CLI, MCP, and agent-skill workflows.
- The gate must support JSON and Markdown request files.
- The gate must produce deterministic structured output.
- The gate must reject incomplete requests.
- The gate must explain what information is missing.
- The gate must provide concrete clarifying questions.
- The gate must normalize valid requests into one common structure.
- No command in this feature may modify a target repository.
- No command in this feature may install dependencies, run network requests, or
  commit code.

## Required Request Fields

Every upgrade request must include:

- `objective`: the concrete problem to solve.
- `change_type`: one of `security_fix`, `dependency_upgrade`, `refactor`,
  `quality`, `api_migration`, or `test_repair`.
- `scope`: files, directories, modules, packages, or dependencies that may be
  changed.
- `out_of_scope`: files, directories, modules, features, or behaviors that must
  not be changed.
- `verification`: commands to run after the change, or an explicit
  `auto_detect` value that allows CodeLevelUp to discover verification commands
  with `probe_project`.
- `risk_level`: one of `low`, `medium`, or `high`.

The optional `notes` field can hold user instructions such as "minimal patch
only" or "do not migrate frameworks."

## Request File Formats

### JSON

The JSON format is the canonical machine-readable format:

```json
{
  "objective": "Fix the vulnerable FastAPI dependency without changing API behavior.",
  "change_type": "security_fix",
  "scope": ["pyproject.toml", "requirements.txt", "src/api"],
  "out_of_scope": ["UI", "database schema", "authentication flow"],
  "verification": ["python -m pytest"],
  "risk_level": "medium",
  "notes": "Use the smallest dependency and code change that resolves the issue."
}
```

### Markdown

The Markdown format is for humans and agents that prefer text files:

```markdown
# Upgrade Request

objective: Fix the vulnerable FastAPI dependency without changing API behavior.
change_type: security_fix
scope:
- pyproject.toml
- requirements.txt
- src/api
out_of_scope:
- UI
- database schema
- authentication flow
verification:
- python -m pytest
risk_level: medium
notes: Use the smallest dependency and code change that resolves the issue.
```

The Markdown parser only needs to support this simple heading plus `key: value`
and `key:` followed by list items. It should not attempt to parse arbitrary
prose as a request.

## Core Module

Create `scripts/upgrade_request.py`.

Responsibilities:

- `request_template(format_name: str) -> str`: return a JSON or Markdown
  template.
- `load_request(path: Path) -> dict[str, object]`: read `.json` or `.md`
  request files and return raw data.
- `validate_request(data: dict[str, object]) -> dict[str, object]`: return the
  readiness report.
- `check_request(path: Path) -> dict[str, object]`: load and validate a file.

The readiness report shape is:

```json
{
  "ready": false,
  "missing_fields": ["scope", "verification"],
  "invalid_fields": [],
  "clarifying_questions": [
    "Which files, directories, modules, packages, or dependencies may be changed?",
    "Which verification commands must pass, or should CodeLevelUp auto-detect them?"
  ],
  "normalized_request": null
}
```

When `ready` is `true`, `normalized_request` contains all required fields with
string lists normalized as lists. When `ready` is `false`, `normalized_request`
is `null`.

## CLI Design

Add a new `request` command group to `scripts/codelevelup.py`.

Commands:

```bash
codelevelup request init --format json --output upgrade-request.json
codelevelup request init --format markdown --output upgrade-request.md
codelevelup request check upgrade-request.json --json
codelevelup request check upgrade-request.md
```

Behavior:

- `request init` writes a template to `--output`.
- `request init` prints the template to stdout when `--output` is omitted.
- `request check` exits with code `0` when `ready` is `true`.
- `request check` exits with code `1` when `ready` is `false`.
- `request check --json` prints the readiness report as JSON.
- human-readable `request check` output lists missing fields, invalid fields,
  and clarifying questions.

## MCP Design

Add one MCP tool to `scripts/codelevelup_mcp.py`:

```json
{
  "name": "check_upgrade_request",
  "description": "Validate that an upgrade or vulnerability-fix request is clear enough before code changes begin.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "path": {"type": "string"}
    },
    "required": ["path"]
  }
}
```

The MCP tool returns the same readiness report as the CLI. MCP clients must treat
`ready: false` as a stop condition for upgrade and vulnerability-fix workflows.

## Agent Workflow Rules

Update `SKILL.md`, `AGENTS.md`, `CLAUDE.md`, and `README.md`:

- Before `security_fix`, `dependency_upgrade`, `api_migration`, `refactor`,
  `quality`, or `test_repair` work, run `request check`.
- If no request file exists, create one with `request init` and ask the user to
  fill or approve it.
- If `ready` is `false`, ask only the clarifying questions returned by the
  readiness report.
- Do not modify target repository code until `ready` is `true`.
- After `ready` is `true`, proceed to probe, search, optional graph-backed code
  lookup, patching, and verification.

## Error Handling

- Unknown file extensions return an invalid report with a question asking for
  JSON or Markdown.
- Invalid JSON returns an invalid report with the parse error summarized.
- Unsupported Markdown shapes return an invalid report explaining that only the
  documented key/list format is accepted.
- Unknown `change_type` values return an invalid field entry listing the allowed
  values.
- Unknown `risk_level` values return an invalid field entry listing `low`,
  `medium`, and `high`.
- Empty strings and empty lists count as missing fields.

## Testing

Create `scripts/test_upgrade_request.py`.

Tests must cover:

- JSON template generation.
- Markdown template generation.
- valid JSON request passes validation.
- valid Markdown request passes validation.
- missing required fields produce `ready: false`.
- empty strings and empty lists count as missing.
- invalid `change_type` is rejected.
- invalid `risk_level` is rejected.
- CLI `request check --json` returns expected JSON and exit code.
- MCP `check_upgrade_request` returns the readiness report.

Run the existing tests as regression checks:

```bash
python3 scripts/test_probe_project.py
python3 scripts/test_cli_mcp.py
python3 scripts/test_upgrade_request.py
python /Users/olym/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

## Future Extension

A future `codelevelup upgrade --request <file>` command may call
`check_request()` before doing anything else. That future command should refuse
to run when the readiness report is not ready, then reuse the normalized request
to constrain file edits, research, verification, and commit messages.
