# Self-Repair Loop

Use this reference when CodeLevelUp enters iterative repair mode: the agent has
already patched code once, verification failed, and the agent needs structured
failure context to propose the next patch.

## When to Use

Use this loop after the first verification failure in an upgrade or
vulnerability-repair run. Do NOT use it for initial one-shot patches — use
`upgrade-loop.md` instead.

## Contract

CodeLevelUp's `repair_loop` module **never modifies code**. It runs verification
commands, parses failures, and returns structured `Failure` objects. The Agent
is responsible for reading the failure context and applying the next patch.

## Repair Loop Steps

```
Patch (Agent applies change)
    ↓
verify → repair_loop(commands, cwd, max_retries=N)
    ↓
passed? → STOP — verification succeeded
    ↓
failed → Failure(error_type, file, line, message, suggestion)
    ↓
Agent reads failure context
    ↓
Agent proposes next patch (informed by previous fix attempt)
    ↓
verify → repair_loop(...)
    ↓
... (repeat up to max_retries)
    ↓
exhausted → STOP — report all rounds, suggest manual intervention
```

## CLI Usage

```bash
# Run repair loop with default settings (5 retries, Python)
codelevelup repair "python -m pytest" --cwd /path/to/repo

# With language hint and custom retry count
codelevelup repair "npm test" --cwd /path/to/repo --language node --max-retries 3

# JSON output for Agent consumption
codelevelup repair "python -m pytest" --cwd /path/to/repo --json
```

JSON output shape:

```json
{
  "passed": false,
  "total_rounds": 2,
  "max_retries": 5,
  "rounds": [
    {
      "round": 1,
      "command": "python -m pytest",
      "return_code": 1,
      "error_type": "ImportError",
      "file": "src/app.py",
      "line": "3",
      "message": "No module named 'foo'",
      "suggestion": "Install the missing package or fix the import path."
    }
  ]
}
```

## MCP Usage

The `repair_loop` MCP tool accepts the same arguments and returns the same JSON
shape. Call it after each failed patch to get structured failure context:

```json
{
  "name": "repair_loop",
  "arguments": {
    "root": "/path/to/repo",
    "commands": ["python -m pytest"],
    "language": "python",
    "max_retries": 5
  }
}
```

## Repair Memory Integration

Before or after each repair round, query persistent repair memory for similar
past fixes:

```bash
# Search for similar past repairs
codelevelup repair-memory search --root /path/to/repo \
  --error-type "ImportError" \
  --message "No module named 'foo'"

# Record a successful fix
codelevelup repair-memory record --root /path/to/repo \
  --error-type "ImportError" \
  --message "No module named 'foo'" \
  --fix "Added 'foo' to dependencies in pyproject.toml" \
  --files "pyproject.toml" \
  --round 2 \
  --language python
```

Or via MCP:

```json
{ "name": "repair_hints", "arguments": { "root": "/path/to/repo", "error_type": "ImportError" } }
{ "name": "record_repair", "arguments": { "root": "/path/to/repo", "error_type": "ImportError", "fix": "...", "files": "...", "round": 2 } }
```

## Stop Conditions

Stop the repair loop and surface the full failure chain to the user when:

- All `max_retries` rounds are exhausted;
- The same error type persists across all rounds (suggests wrong root cause);
- A new, different error appears each round (suggests the patch is destabilizing);
- Verification requires production services or destructive data changes;
- The error is a security finding that needs human review.

## Failure Parsing

The repair loop parses failures for these languages:

| Language | Patterns Detected |
|----------|-------------------|
| Python | Traceback (exception type, file, line), pytest FAILED/ERROR |
| Rust | Compile errors with file:line |
| Node/TypeScript | Runtime errors with file:line |
| Go | Compile errors with file:line:col |
| Generic | Last line of output |

Each parsed failure includes a heuristic `suggestion` field to accelerate the
Agent's next patch attempt.

## Isolation from Code Modification

This module intentionally does NOT:

- write patches;
- run AI models to generate fixes;
- modify any files in the target repository;
- commit changes.

It is a **structured observation layer** between verification and the Agent's
patch decision. Code modification remains the Agent's responsibility.
