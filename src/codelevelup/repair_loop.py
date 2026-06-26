#!/usr/bin/env python3
"""Iterative test-verify-fix repair loop for CodeLevelUp.

This module does NOT modify code. It runs verification commands, parses failures,
and reports structured failure context so the Agent can propose and apply patches.
The Agent is responsible for code edits; this module closes the verify→learn loop.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


TRACEBACK_RE = re.compile(
    r"^(Traceback \(most recent call last\):.*)",
    re.DOTALL | re.MULTILINE,
)

PYTEST_FAIL_RE = re.compile(
    r"^(FAILED|ERROR) (.*?)(?::(\d+))?:(.*)$", re.MULTILINE
)

RUST_COMPILE_RE = re.compile(
    r"^error\[.*?\]: (.*?)\n\s+-->\s+([^:]+):(\d+):(\d+)", re.MULTILINE | re.DOTALL
)

NODE_ERROR_RE = re.compile(
    r"^(.*?):(\d+):(\d+)\n\s+(.*?)(?:\n|$)", re.MULTILINE
)

GO_ERROR_RE = re.compile(
    r"^([^:]+):(\d+):(\d+): (.*?)(?:\n|$)", re.MULTILINE
)


@dataclass
class Failure:
    """Structured failure context for one verification round."""
    round: int
    command: str
    return_code: int
    error_type: str
    file: str = ""
    line: str = ""
    message: str = ""
    raw_output: str = ""
    suggestion: str = ""


@dataclass
class RepairResult:
    """Outcome of a full repair loop."""
    passed: bool
    rounds: list[Failure] = field(default_factory=list)
    total_rounds: int = 0
    max_retries: int = 0
    final_output: str = ""
    stopped_early: bool = False
    stop_reason: str = ""


_OUTPUT_CAP_BYTES = 100 * 1024


def _cap_output(output: str) -> str:
    if len(output) <= _OUTPUT_CAP_BYTES:
        return output
    return (
        output[:_OUTPUT_CAP_BYTES]
        + f"\n\n[... output truncated at {_OUTPUT_CAP_BYTES // 1024}KB ...]"
    )


def run_verification(commands: list[str], cwd: Path) -> tuple[int, str]:
    """Run verification commands sequentially. Returns (last_return_code, combined_output)."""
    cwd = cwd.resolve()
    combined: list[str] = []
    last_code = 0
    for cmd in commands:
        logger.info("Running verification: %s", cmd)
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            last_code = proc.returncode
            stdout = _cap_output(proc.stdout.strip())
            stderr = _cap_output(proc.stderr.strip())
            output = "\n".join(filter(None, [stdout, stderr]))
            combined.append(f"$ {cmd}\n{output}\n")
        except subprocess.TimeoutExpired:
            combined.append(f"$ {cmd}\n[TIMEOUT after 300s]\n")
            last_code = 1
        except FileNotFoundError:
            combined.append(f"$ {cmd}\n[COMMAND NOT FOUND]\n")
            last_code = 1
        except OSError as exc:
            logger.warning("OS error running %s: %s", cmd, exc)
            combined.append(f"$ {cmd}\n[OS ERROR: {exc}]\n")
            last_code = 1
    raw = "\n".join(combined)
    logger.debug("Combined verification output (%d bytes)", len(raw))
    return last_code, raw


def parse_failure(output: str, language: str = "python") -> Failure:
    """Parse verification output into a structured Failure."""
    language = (language or "python").lower()

    if language in ("python",):
        return _parse_python_failure(output)
    if language in ("rust",):
        return _parse_rust_failure(output)
    if language in ("javascript", "typescript", "node", "js", "ts"):
        return _parse_node_failure(output)
    if language in ("go", "golang"):
        return _parse_go_failure(output)
    return _parse_generic_failure(output)


def _parse_python_failure(output: str) -> Failure:
    tb_match = TRACEBACK_RE.search(output)
    if tb_match:
        tb_text = tb_match.group(1)
        lines = tb_text.strip().splitlines()
        last_line = lines[-1] if lines else ""
        error_match = re.search(r"([A-Za-z_][\w]*Error|Exception): (.+)$", last_line)
        if error_match:
            error_type = error_match.group(1)
            message = error_match.group(2)
        else:
            error_type = last_line.split(":")[0].strip() if ":" in last_line else "Unknown"
            message = last_line

        file_match = re.search(r'File "([^"]+)", line (\d+)', tb_text)
        if file_match:
            return Failure(
                round=0, command="", return_code=1,
                error_type=error_type, file=file_match.group(1),
                line=file_match.group(2), message=message,
                raw_output=output, suggestion=_suggest_python_fix(error_type, message),
            )
        return Failure(round=0, command="", return_code=1,
                       error_type=error_type, message=message,
                       raw_output=output, suggestion=_suggest_python_fix(error_type, message))

    fail_match = PYTEST_FAIL_RE.search(output)
    if fail_match:
        kind, path, line, msg = fail_match.groups()
        return Failure(round=0, command="", return_code=1,
                       error_type=f"pytest {kind.lower()}",
                       file=path or "", line=line or "", message=msg.strip(),
                       raw_output=output,
                       suggestion="Check the test assertion and the code under test.")

    return Failure(round=0, command="", return_code=1,
                   error_type="unknown", message="No recognizable failure pattern.",
                   raw_output=output, suggestion="Inspect the full output above.")


def _parse_rust_failure(output: str) -> Failure:
    match = RUST_COMPILE_RE.search(output)
    if match:
        msg, path, line, col = match.groups()
        return Failure(round=0, command="", return_code=1,
                       error_type="compile_error", file=path, line=line,
                       message=msg.strip(), raw_output=output,
                       suggestion="Fix the type or borrow error indicated.")
    return _parse_generic_failure(output)


def _parse_node_failure(output: str) -> Failure:
    match = NODE_ERROR_RE.search(output)
    if match:
        path, line, col, msg = match.groups()
        return Failure(round=0, command="", return_code=1,
                       error_type="runtime_error", file=path, line=line,
                       message=msg.strip(), raw_output=output,
                       suggestion="Check the stack trace and the referenced line.")
    return _parse_generic_failure(output)


def _parse_go_failure(output: str) -> Failure:
    match = GO_ERROR_RE.search(output)
    if match:
        path, line, col, msg = match.groups()
        return Failure(round=0, command="", return_code=1,
                       error_type="compile_error", file=path, line=line,
                       message=msg.strip(), raw_output=output,
                       suggestion="Fix the Go compiler error indicated.")
    return _parse_generic_failure(output)


def _parse_generic_failure(output: str) -> Failure:
    lines = output.strip().splitlines()
    msg = lines[-1] if lines else "Unknown failure"
    return Failure(round=0, command="", return_code=1,
                   error_type="unknown", message=msg,
                   raw_output=output, suggestion="Inspect the full output above.")


def _suggest_python_fix(error_type: str, message: str) -> str:
    suggestions = {
        "ImportError": "Check that the module is installed and the import path is correct.",
        "ModuleNotFoundError": "Install the missing package or fix the import path.",
        "SyntaxError": "Fix the Python syntax error on the indicated line.",
        "IndentationError": "Fix the indentation — Python is whitespace-sensitive.",
        "TypeError": "Check argument types and counts against the function signature.",
        "AttributeError": "Verify the object has the expected attribute or method.",
        "KeyError": "Check dictionary key existence before access.",
        "IndexError": "Check list/tuple bounds before indexing.",
        "ValueError": "Validate input values before passing them.",
        "FileNotFoundError": "Verify the file path exists or create the file.",
        "PermissionError": "Check file/directory permissions.",
        "ZeroDivisionError": "Add a guard against division by zero.",
        "AssertionError": "Review the test assertion and expected behavior.",
        "NotImplementedError": "Implement the method or remove the placeholder.",
    }
    for key, suggestion in suggestions.items():
        if key in error_type:
            return suggestion
    if "assert" in message.lower():
        return "Check the test assertion and the code under test."
    return "Inspect the error and traceback above to locate the root cause."


def repair_loop(
    commands: list[str],
    cwd: Path,
    language: str = "python",
    max_retries: int = 5,
    on_failure: Optional[Callable[[Failure], None]] = None,
) -> RepairResult:
    """Run verification commands in a loop, reporting structured failures.

    Args:
        commands: verification commands to run (e.g., ["python -m pytest"]).
        cwd: target repository root.
        language: language hint for failure parsing.
        max_retries: maximum number of repair rounds.
        on_failure: optional callback invoked after each failure with the Failure object.

    Returns:
        RepairResult with all rounds and final status.
    """
    cwd = cwd.resolve()
    rounds: list[Failure] = []

    for attempt in range(1, max_retries + 1):
        return_code, output = run_verification(commands, cwd)

        if return_code == 0:
            return RepairResult(
                passed=True,
                rounds=rounds,
                total_rounds=attempt - 1,
                max_retries=max_retries,
                final_output=output,
            )

        failure = parse_failure(output, language)
        failure.round = attempt
        failure.command = "; ".join(commands)
        rounds.append(failure)

        if on_failure:
            on_failure(failure)

        if attempt == max_retries:
            return RepairResult(
                passed=False,
                rounds=rounds,
                total_rounds=attempt,
                max_retries=max_retries,
                final_output=output,
                stop_reason=f"exhausted {max_retries} retries",
            )


def repair_loop_report(result: RepairResult) -> dict[str, Any]:
    """Serialize a RepairResult to a JSON-friendly dict for CLI/MCP output."""
    return {
        "passed": result.passed,
        "total_rounds": result.total_rounds,
        "max_retries": result.max_retries,
        "stopped_early": result.stopped_early,
        "stop_reason": result.stop_reason,
        "rounds": [
            {
                "round": f.round,
                "command": f.command,
                "return_code": f.return_code,
                "error_type": f.error_type,
                "file": f.file,
                "line": f.line,
                "message": f.message,
                "suggestion": f.suggestion,
            }
            for f in result.rounds
        ],
        "final_output_preview": result.final_output[:2000] if result.final_output else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Iterative test-verify-fix repair loop.")
    parser.add_argument("commands", nargs="+", help="Verification commands to run in sequence.")
    parser.add_argument("--cwd", default=".", help="Target repository root.")
    parser.add_argument("--language", default="python", help="Language hint for failure parsing.")
    parser.add_argument("--max-retries", type=int, default=5, help="Maximum repair rounds.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args()

    result = repair_loop(
        commands=args.commands,
        cwd=Path(args.cwd),
        language=args.language,
        max_retries=args.max_retries,
    )

    if args.json:
        print(json.dumps(repair_loop_report(result), indent=2, sort_keys=True))
    else:
        if result.passed:
            print(f"PASS after {result.total_rounds} verification round(s).")
        else:
            print(f"FAIL after {result.total_rounds} round(s): {result.stop_reason}")
            for fr in result.rounds:
                print(f"  Round {fr.round}: {fr.error_type} in {fr.file}:{fr.line}")
                print(f"    {fr.message}")
                print(f"    Suggestion: {fr.suggestion}")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
