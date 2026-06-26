# Upgrade Request Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an executable pre-upgrade requirement gate so CodeLevelUp refuses to proceed with code upgrades or vulnerability fixes until the request is clear.

**Architecture:** Add a small pure-Python `upgrade_request` module that creates templates, parses JSON/Markdown request files, validates required fields, and returns deterministic readiness reports. Wire that module into the existing CLI and stdio MCP server, then update agent-facing docs so CLI, MCP, and skill usage share the same gate.

**Tech Stack:** Python 3.9+, standard library only, `unittest`, existing `argparse` CLI, existing newline-delimited stdio JSON-RPC MCP shim.

## Global Constraints

- Work only inside `/Users/olym/Documents/resume_project/CodeLevelUp`.
- Do not add runtime dependencies.
- Do not modify target repositories from this feature.
- Do not install dependencies, run network requests, or commit target code from this feature.
- Support JSON request files with `.json`.
- Support Markdown request files with `.md`.
- Required fields are `objective`, `change_type`, `scope`, `out_of_scope`, `verification`, and `risk_level`.
- Allowed `change_type` values are `security_fix`, `dependency_upgrade`, `refactor`, `quality`, `api_migration`, and `test_repair`.
- Allowed `risk_level` values are `low`, `medium`, and `high`.
- `verification` may be a non-empty list of commands or the explicit string `auto_detect`.
- Empty strings and empty lists count as missing.
- If validation fails, return clarifying questions and do not expose a normalized request.

---

## File Structure

- Create `scripts/upgrade_request.py`: pure logic for templates, file parsing, validation, and readiness reports.
- Create `scripts/test_upgrade_request.py`: unit tests for templates, JSON/Markdown parsing, validation, CLI behavior, and MCP behavior.
- Modify `scripts/codelevelup.py`: import `upgrade_request`, add `request init`, add `request check`, and human output for readiness reports.
- Modify `scripts/codelevelup_mcp.py`: import `check_request`, expose `check_upgrade_request`, and route tool calls.
- Modify `README.md`: document the upgrade request gate and CLI/MCP commands.
- Modify `SKILL.md`: make `request check` a hard gate before upgrade-like work.
- Modify `AGENTS.md`: add portable agent rule for request validation.
- Modify `CLAUDE.md`: add Claude CLI/MCP usage for the gate.

---

### Task 1: Core Upgrade Request Validator

**Files:**
- Create: `scripts/upgrade_request.py`
- Create: `scripts/test_upgrade_request.py`

**Interfaces:**
- Produces: `request_template(format_name: str) -> str`
- Produces: `load_request(path: Path) -> dict[str, object]`
- Produces: `validate_request(data: dict[str, object]) -> dict[str, object]`
- Produces: `check_request(path: Path) -> dict[str, object]`

- [ ] **Step 1: Write failing tests for templates and validation**

Add this initial content to `scripts/test_upgrade_request.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from upgrade_request import (
    ALLOWED_CHANGE_TYPES,
    ALLOWED_RISK_LEVELS,
    check_request,
    load_request,
    request_template,
    validate_request,
)


class UpgradeRequestTests(unittest.TestCase):
    def test_json_template_contains_required_fields(self):
        data = json.loads(request_template("json"))

        self.assertEqual(set(data), {
            "objective",
            "change_type",
            "scope",
            "out_of_scope",
            "verification",
            "risk_level",
            "notes",
        })
        self.assertIn(data["change_type"], ALLOWED_CHANGE_TYPES)
        self.assertIn(data["risk_level"], ALLOWED_RISK_LEVELS)

    def test_markdown_template_contains_required_fields(self):
        template = request_template("markdown")

        self.assertIn("# Upgrade Request", template)
        self.assertIn("objective:", template)
        self.assertIn("change_type:", template)
        self.assertIn("verification:", template)

    def test_valid_json_request_passes_validation(self):
        report = validate_request(valid_request())

        self.assertTrue(report["ready"])
        self.assertEqual(report["missing_fields"], [])
        self.assertEqual(report["invalid_fields"], [])
        self.assertEqual(report["clarifying_questions"], [])
        self.assertEqual(report["normalized_request"]["verification"], ["python -m pytest"])

    def test_valid_markdown_request_passes_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "upgrade-request.md"
            path.write_text(
                "\n".join([
                    "# Upgrade Request",
                    "",
                    "objective: Fix vulnerable FastAPI dependency.",
                    "change_type: security_fix",
                    "scope:",
                    "- pyproject.toml",
                    "- src/api",
                    "out_of_scope:",
                    "- UI",
                    "- database schema",
                    "verification:",
                    "- python -m pytest",
                    "risk_level: medium",
                    "notes: Minimal patch only.",
                ]),
                encoding="utf-8",
            )

            report = check_request(path)

        self.assertTrue(report["ready"])
        self.assertEqual(report["normalized_request"]["scope"], ["pyproject.toml", "src/api"])

    def test_missing_required_fields_return_questions(self):
        data = valid_request()
        data["scope"] = []
        data["verification"] = ""

        report = validate_request(data)

        self.assertFalse(report["ready"])
        self.assertIn("scope", report["missing_fields"])
        self.assertIn("verification", report["missing_fields"])
        self.assertIsNone(report["normalized_request"])
        self.assertGreaterEqual(len(report["clarifying_questions"]), 2)

    def test_invalid_change_type_and_risk_level_are_rejected(self):
        data = valid_request()
        data["change_type"] = "rewrite_everything"
        data["risk_level"] = "extreme"

        report = validate_request(data)

        self.assertFalse(report["ready"])
        self.assertIn("change_type", [item["field"] for item in report["invalid_fields"]])
        self.assertIn("risk_level", [item["field"] for item in report["invalid_fields"]])

    def test_auto_detect_verification_is_valid(self):
        data = valid_request()
        data["verification"] = "auto_detect"

        report = validate_request(data)

        self.assertTrue(report["ready"])
        self.assertEqual(report["normalized_request"]["verification"], "auto_detect")

    def test_unknown_extension_returns_invalid_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "upgrade-request.txt"
            path.write_text("objective: Fix vulnerability\n", encoding="utf-8")

            report = check_request(path)

        self.assertFalse(report["ready"])
        self.assertIn("file_type", [item["field"] for item in report["invalid_fields"]])


def valid_request():
    return {
        "objective": "Fix vulnerable FastAPI dependency without changing API behavior.",
        "change_type": "security_fix",
        "scope": ["pyproject.toml", "requirements.txt", "src/api"],
        "out_of_scope": ["UI", "database schema"],
        "verification": ["python -m pytest"],
        "risk_level": "medium",
        "notes": "Minimal patch only.",
    }


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python3 scripts/test_upgrade_request.py
```

Expected: FAIL with `ModuleNotFoundError: No module named 'upgrade_request'`.

- [ ] **Step 3: Implement the validator module**

Create `scripts/upgrade_request.py`:

```python
#!/usr/bin/env python3
"""Upgrade request templates, parsers, and readiness validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ALLOWED_CHANGE_TYPES = {
    "security_fix",
    "dependency_upgrade",
    "refactor",
    "quality",
    "api_migration",
    "test_repair",
}

ALLOWED_RISK_LEVELS = {"low", "medium", "high"}

REQUIRED_FIELDS = (
    "objective",
    "change_type",
    "scope",
    "out_of_scope",
    "verification",
    "risk_level",
)

CLARIFYING_QUESTIONS = {
    "objective": "What concrete problem should this upgrade or fix solve?",
    "change_type": "Which change type applies: security_fix, dependency_upgrade, refactor, quality, api_migration, or test_repair?",
    "scope": "Which files, directories, modules, packages, or dependencies may be changed?",
    "out_of_scope": "Which files, directories, modules, features, or behaviors must not be changed?",
    "verification": "Which verification commands must pass, or should CodeLevelUp auto-detect them?",
    "risk_level": "What risk level should this work use: low, medium, or high?",
}


def request_template(format_name: str) -> str:
    normalized = format_name.lower()
    sample = {
        "objective": "Fix the vulnerable dependency without changing runtime behavior.",
        "change_type": "security_fix",
        "scope": ["pyproject.toml", "requirements.txt", "src"],
        "out_of_scope": ["UI", "database schema"],
        "verification": ["python -m pytest"],
        "risk_level": "medium",
        "notes": "Use the smallest safe patch.",
    }
    if normalized == "json":
        return json.dumps(sample, indent=2, sort_keys=True) + "\n"
    if normalized in {"md", "markdown"}:
        return "\n".join([
            "# Upgrade Request",
            "",
            f"objective: {sample['objective']}",
            f"change_type: {sample['change_type']}",
            "scope:",
            "- pyproject.toml",
            "- requirements.txt",
            "- src",
            "out_of_scope:",
            "- UI",
            "- database schema",
            "verification:",
            "- python -m pytest",
            f"risk_level: {sample['risk_level']}",
            f"notes: {sample['notes']}",
            "",
        ])
    raise ValueError("format must be json or markdown")


def load_request(path: Path) -> dict[str, object]:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        loaded = json.loads(text)
        if not isinstance(loaded, dict):
            raise ValueError("JSON request must be an object")
        return loaded
    if suffix == ".md":
        return parse_markdown_request(text)
    raise ValueError("request file must use .json or .md")


def parse_markdown_request(text: str) -> dict[str, object]:
    data: dict[str, object] = {}
    current_key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            if current_key is None:
                raise ValueError("Markdown list item appears before a key")
            values = data.setdefault(current_key, [])
            if not isinstance(values, list):
                raise ValueError(f"Markdown key {current_key} mixes scalar and list values")
            values.append(line[2:].strip())
            continue
        if ":" not in line:
            raise ValueError("Markdown request only supports key: value lines and list items")
        key, value = line.split(":", 1)
        current_key = key.strip()
        value = value.strip()
        data[current_key] = value if value else []
    return data


def validate_request(data: dict[str, object]) -> dict[str, object]:
    missing_fields = [field for field in REQUIRED_FIELDS if is_missing(data.get(field))]
    invalid_fields: list[dict[str, object]] = []

    change_type = data.get("change_type")
    if not is_missing(change_type) and change_type not in ALLOWED_CHANGE_TYPES:
        invalid_fields.append({
            "field": "change_type",
            "message": "change_type must be one of the allowed values",
            "allowed": sorted(ALLOWED_CHANGE_TYPES),
        })

    risk_level = data.get("risk_level")
    if not is_missing(risk_level) and risk_level not in ALLOWED_RISK_LEVELS:
        invalid_fields.append({
            "field": "risk_level",
            "message": "risk_level must be low, medium, or high",
            "allowed": sorted(ALLOWED_RISK_LEVELS),
        })

    verification = data.get("verification")
    if not is_missing(verification) and not valid_verification(verification):
        invalid_fields.append({
            "field": "verification",
            "message": "verification must be auto_detect or a non-empty list of commands",
            "allowed": ["auto_detect", ["python -m pytest"]],
        })

    ready = not missing_fields and not invalid_fields
    return {
        "ready": ready,
        "missing_fields": missing_fields,
        "invalid_fields": invalid_fields,
        "clarifying_questions": questions_for(missing_fields, invalid_fields),
        "normalized_request": normalize_request(data) if ready else None,
    }


def check_request(path: Path) -> dict[str, object]:
    try:
        return validate_request(load_request(path))
    except json.JSONDecodeError as exc:
        return invalid_report("json", f"Invalid JSON: {exc.msg}")
    except ValueError as exc:
        field = "file_type" if "must use .json or .md" in str(exc) else "request_file"
        return invalid_report(field, str(exc))


def is_missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return not any(str(item).strip() for item in value)
    return False


def valid_verification(value: object) -> bool:
    if value == "auto_detect":
        return True
    if isinstance(value, list):
        return bool(value) and all(isinstance(item, str) and item.strip() for item in value)
    return False


def normalize_request(data: dict[str, object]) -> dict[str, object]:
    normalized = {field: data[field] for field in REQUIRED_FIELDS}
    normalized["scope"] = normalize_list(normalized["scope"])
    normalized["out_of_scope"] = normalize_list(normalized["out_of_scope"])
    if normalized["verification"] != "auto_detect":
        normalized["verification"] = normalize_list(normalized["verification"])
    if data.get("notes"):
        normalized["notes"] = str(data["notes"]).strip()
    return normalized


def normalize_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def questions_for(missing_fields: list[str], invalid_fields: list[dict[str, object]]) -> list[str]:
    questions = [CLARIFYING_QUESTIONS[field] for field in missing_fields]
    for item in invalid_fields:
        field = str(item["field"])
        if field in CLARIFYING_QUESTIONS and CLARIFYING_QUESTIONS[field] not in questions:
            questions.append(CLARIFYING_QUESTIONS[field])
        elif field == "file_type":
            questions.append("Can you provide the request as a .json or .md file?")
        elif field == "request_file":
            questions.append("Can you rewrite the Markdown request using the documented key/list format?")
    return questions


def invalid_report(field: str, message: str) -> dict[str, object]:
    invalid_fields = [{"field": field, "message": message}]
    return {
        "ready": False,
        "missing_fields": [],
        "invalid_fields": invalid_fields,
        "clarifying_questions": questions_for([], invalid_fields),
        "normalized_request": None,
    }
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
python3 scripts/test_upgrade_request.py
```

Expected: PASS with 8 tests.

- [ ] **Step 5: Commit Task 1**

```bash
git add scripts/upgrade_request.py scripts/test_upgrade_request.py
git commit -m "feat: add upgrade request validator"
```

---

### Task 2: CLI Request Commands

**Files:**
- Modify: `scripts/test_upgrade_request.py`
- Modify: `scripts/codelevelup.py`

**Interfaces:**
- Consumes: `request_template(format_name: str) -> str`
- Consumes: `check_request(path: Path) -> dict[str, object]`
- Produces CLI commands:
  - `codelevelup request init --format json --output <path>`
  - `codelevelup request init --format markdown --output <path>`
  - `codelevelup request check <path> --json`

- [ ] **Step 1: Add failing CLI tests**

Append these tests to `UpgradeRequestTests` in `scripts/test_upgrade_request.py`:

```python
    def test_cli_request_init_writes_json_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "upgrade-request.json"

            result = run_cli("request", "init", "--format", "json", "--output", str(output))

            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertIn("objective", data)

    def test_cli_request_check_json_reports_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "upgrade-request.json"
            path.write_text(json.dumps({"objective": "Fix vulnerability"}), encoding="utf-8")

            result = run_cli("request", "check", str(path), "--json")

            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ready"])
            self.assertIn("scope", payload["missing_fields"])

    def test_cli_request_check_json_reports_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "upgrade-request.json"
            path.write_text(json.dumps(valid_request()), encoding="utf-8")

            result = run_cli("request", "check", str(path), "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ready"])
```

Add this helper near the bottom of the file:

```python
ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "codelevelup.py"


def run_cli(*args):
    import subprocess
    import sys

    return subprocess.run(
        [sys.executable, str(CLI), *args],
        text=True,
        capture_output=True,
        check=False,
    )
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python3 scripts/test_upgrade_request.py
```

Expected: FAIL because `codelevelup.py` has no `request` command.

- [ ] **Step 3: Import upgrade request functions**

Modify the import block in `scripts/codelevelup.py`:

```python
try:
    from probe_project import probe_project
    from upgrade_request import check_request, request_template
except ModuleNotFoundError:  # pragma: no cover - package import path
    from .probe_project import probe_project
    from .upgrade_request import check_request, request_template
```

- [ ] **Step 4: Add CLI parsers**

Add this parser setup inside `main()` after the existing `gitnexus` parser setup:

```python
    request_parser = subparsers.add_parser("request", help="Create and validate upgrade request files.")
    request_subparsers = request_parser.add_subparsers(dest="request_command", required=True)

    init_parser = request_subparsers.add_parser("init", help="Create an upgrade request template.")
    init_parser.add_argument("--format", choices=("json", "markdown"), default="json", help="Template format.")
    init_parser.add_argument("--output", help="Optional path to write the template.")

    check_parser = request_subparsers.add_parser("check", help="Validate an upgrade request file.")
    check_parser.add_argument("path", help="Request file path.")
    check_parser.add_argument("--json", action="store_true", help="Print JSON output.")
```

- [ ] **Step 5: Add CLI dispatch**

Add this dispatch before `parser.error("unsupported command")`:

```python
    if args.command == "request" and args.request_command == "init":
        template = request_template(args.format)
        if args.output:
            Path(args.output).write_text(template, encoding="utf-8")
        else:
            print(template, end="")
        return 0
    if args.command == "request" and args.request_command == "check":
        report = check_request(Path(args.path))
        emit(report, args.json)
        return 0 if report["ready"] else 1
```

- [ ] **Step 6: Improve human output for readiness reports**

Add this branch at the top of `print_human()`:

```python
    if "missing_fields" in payload and "invalid_fields" in payload:
        print(f"Ready: {payload['ready']}")
        if payload["missing_fields"]:
            print("Missing fields:")
            for field in payload["missing_fields"]:
                print(f"- {field}")
        if payload["invalid_fields"]:
            print("Invalid fields:")
            for item in payload["invalid_fields"]:
                print(f"- {item['field']}: {item['message']}")
        if payload["clarifying_questions"]:
            print("Clarifying questions:")
            for question in payload["clarifying_questions"]:
                print(f"- {question}")
        return
```

- [ ] **Step 7: Run CLI tests**

Run:

```bash
python3 scripts/test_upgrade_request.py
```

Expected: PASS with 11 tests.

- [ ] **Step 8: Run existing CLI/MCP regression tests**

Run:

```bash
python3 scripts/test_cli_mcp.py
```

Expected: PASS with 4 tests.

- [ ] **Step 9: Commit Task 2**

```bash
git add scripts/codelevelup.py scripts/test_upgrade_request.py
git commit -m "feat: add upgrade request CLI gate"
```

---

### Task 3: MCP Request Gate Tool

**Files:**
- Modify: `scripts/test_upgrade_request.py`
- Modify: `scripts/codelevelup_mcp.py`

**Interfaces:**
- Consumes: `check_request(path: Path) -> dict[str, object]`
- Produces MCP tool: `check_upgrade_request`

- [ ] **Step 1: Add failing MCP test**

Append this test to `UpgradeRequestTests` in `scripts/test_upgrade_request.py`:

```python
    def test_mcp_check_upgrade_request_returns_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "upgrade-request.json"
            path.write_text(json.dumps(valid_request()), encoding="utf-8")
            messages = [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "check_upgrade_request",
                        "arguments": {"path": str(path)},
                    },
                },
            ]

            result = run_mcp(messages)

        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        tool_names = {tool["name"] for tool in responses[1]["result"]["tools"]}
        self.assertIn("check_upgrade_request", tool_names)
        payload = json.loads(responses[2]["result"]["content"][0]["text"])
        self.assertTrue(payload["ready"])
```

Add this helper near `run_cli()`:

```python
MCP = ROOT / "scripts" / "codelevelup_mcp.py"


def run_mcp(messages):
    import subprocess
    import sys

    return subprocess.run(
        [sys.executable, str(MCP)],
        input="\n".join(json.dumps(message) for message in messages) + "\n",
        text=True,
        capture_output=True,
        check=False,
    )
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python3 scripts/test_upgrade_request.py
```

Expected: FAIL because the MCP tool list does not include `check_upgrade_request`.

- [ ] **Step 3: Import request validator in MCP server**

Modify imports in `scripts/codelevelup_mcp.py`:

```python
try:
    from codelevelup import gitnexus_analyze, gitnexus_status, search_code
    from probe_project import probe_project
    from upgrade_request import check_request
except ModuleNotFoundError:  # pragma: no cover - package import path
    from .codelevelup import gitnexus_analyze, gitnexus_status, search_code
    from .probe_project import probe_project
    from .upgrade_request import check_request
```

- [ ] **Step 4: Add MCP tool schema**

Append this entry to `TOOLS`:

```python
    {
        "name": "check_upgrade_request",
        "description": "Validate that an upgrade or vulnerability-fix request is clear enough before code changes begin.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
```

- [ ] **Step 5: Add MCP call routing**

Add this branch to `call_tool()` before the final `else`:

```python
    elif name == "check_upgrade_request":
        payload = check_request(Path(arguments["path"]))
```

- [ ] **Step 6: Run MCP tests**

Run:

```bash
python3 scripts/test_upgrade_request.py
python3 scripts/test_cli_mcp.py
```

Expected: both pass.

- [ ] **Step 7: Commit Task 3**

```bash
git add scripts/codelevelup_mcp.py scripts/test_upgrade_request.py
git commit -m "feat: expose upgrade request gate over MCP"
```

---

### Task 4: Docs, Skill Rules, and Final Verification

**Files:**
- Modify: `README.md`
- Modify: `SKILL.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes CLI command: `codelevelup request init/check`
- Consumes MCP tool: `check_upgrade_request`
- Produces documented hard gate before upgrade-like work.

- [ ] **Step 1: Update README**

Add this section after `CLI / 命令行` in `README.md`:

```markdown
## Upgrade Request Gate / 升级需求门禁

Before code upgrades, dependency upgrades, vulnerability fixes, API migrations,
refactors, quality improvements, or test repairs, create and check a request:

在代码升级、依赖升级、漏洞修复、API 迁移、重构、质量改进或测试修复前，先创建并检查需求：

```bash
codelevelup request init --format json --output upgrade-request.json
codelevelup request check upgrade-request.json --json
```

The request must define `objective`, `change_type`, `scope`, `out_of_scope`,
`verification`, and `risk_level`. If `ready` is `false`, the agent must ask the
returned clarifying questions before touching code.

需求必须定义 `objective`、`change_type`、`scope`、`out_of_scope`、
`verification` 和 `risk_level`。如果 `ready` 为 `false`，agent 必须先询问返回的澄清问题，不能修改代码。
```

- [ ] **Step 2: Update SKILL.md**

Add a hard gate paragraph under `Operating Contract`:

```markdown
Before `security_fix`, `dependency_upgrade`, `api_migration`, `refactor`,
`quality`, or `test_repair` work, run `codelevelup request check <file>` or the
MCP `check_upgrade_request` tool. If no request file exists, create one with
`codelevelup request init` and ask the user to fill or approve it. If `ready` is
`false`, ask only the returned clarifying questions and do not modify target
code.
```

- [ ] **Step 3: Update AGENTS.md**

Add this rule before the numbered workflow:

```markdown
For upgrade-like work, validate an upgrade request first:

```bash
python scripts/codelevelup.py request check <request-file> --json
```

Do not patch code when the report returns `ready: false`.
```

- [ ] **Step 4: Update CLAUDE.md**

Add this under the CLI examples:

```markdown
Before code changes for upgrades or vulnerability fixes:

```bash
codelevelup request init --format json --output upgrade-request.json
codelevelup request check upgrade-request.json --json
```

Claude should continue only when the report returns `ready: true`.
```

Add `check_upgrade_request` to the MCP tool list.

- [ ] **Step 5: Run all tests and skill validation**

Run:

```bash
python3 scripts/test_probe_project.py
python3 scripts/test_cli_mcp.py
python3 scripts/test_upgrade_request.py
python /Users/olym/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
git diff --check
```

Expected:

- `test_probe_project.py`: PASS.
- `test_cli_mcp.py`: PASS.
- `test_upgrade_request.py`: PASS.
- `quick_validate.py`: `Skill is valid!`.
- `git diff --check`: no output.

- [ ] **Step 6: Smoke test installed CLI if `.venv` exists**

Run:

```bash
. .venv/bin/activate
python -m pip install -e .
codelevelup request init --format json --output /tmp/codelevelup-upgrade-request.json
codelevelup request check /tmp/codelevelup-upgrade-request.json --json
```

Expected: install succeeds, template is created, check returns `ready: true` for the generated complete sample template.

- [ ] **Step 7: Commit Task 4**

```bash
git add README.md SKILL.md AGENTS.md CLAUDE.md
git commit -m "docs: document upgrade request gate"
```

---

## Self-Review Checklist

- Spec coverage: Tasks implement core module, JSON/Markdown support, CLI gate, MCP gate, agent docs, and validation.
- Placeholder scan: This plan contains concrete implementation steps and no open-ended filler.
- Type consistency: `request_template`, `load_request`, `validate_request`, and `check_request` signatures match across tasks.
- Scope check: The plan does not implement automatic code changes, vulnerability research, dependency installation, test execution, commits for target repositories, or GitNexus indexing.
