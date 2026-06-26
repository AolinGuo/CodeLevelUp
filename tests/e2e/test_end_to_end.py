"""End-to-end integration tests for CodeLevelUp.

Each test exercises a complete workflow: graph build -> query -> repair
loop -> repair memory round-trip, using direct function calls for
reliability (no subprocess, no PYTHONPATH issues).
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from codelevelup.agent import main as agent_main
from codelevelup.code_graph import build_code_graph, query_code_graph
from codelevelup.mcp_server import main as mcp_main
from codelevelup.probe import probe_project
from codelevelup.repair_memory import mark_verified, record_repair, repair_stats, search_repairs
from codelevelup.repair_loop import repair_loop, repair_loop_report

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = str(PROJECT_ROOT / "src")


def _tmp_repo():
    tmp = Path(tempfile.mkdtemp())
    (tmp / "src").mkdir()
    (tmp / ".git").mkdir()
    return tmp


def _write(path, content):
    path.write_text(content, encoding="utf-8")


class _CaptureIO(io.StringIO):
    def flush(self):
        pass


def _invoke_agent(*args):
    """Invoke agent entry point directly, capturing stdout/stderr."""
    old_argv = sys.argv[:]
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sout, serr = _CaptureIO(), _CaptureIO()
    sys.argv = ["codelevelup-agent", *args]
    sys.stdout, sys.stderr = sout, serr
    rc = 0
    try:
        rc = agent_main()
    except SystemExit as exc:
        rc = exc.code if exc.code is not None else 0
    except Exception:
        rc = 1
    finally:
        sys.argv = old_argv
        sys.stdout, sys.stderr = old_stdout, old_stderr
    return rc, sout.getvalue(), serr.getvalue()


def _run_mcp(messages):
    """Run MCP server with given JSON-RPC messages, return parsed responses."""
    stdin_data = "\n".join(json.dumps(m) for m in messages) + "\n"
    old_stdin, old_stdout = sys.stdin, sys.stdout
    sys.stdin = _IterableIO(stdin_data)
    buf = []
    sys.stdout = type("_FakeStdout", (), {
        "write": lambda self, s: buf.append(s),
        "flush": lambda self: None,
    })()
    try:
        mcp_main()
    finally:
        sys.stdout, sys.stdin = old_stdout, old_stdin
    raw = "".join(buf)
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


class _IterableIO:
    """StringIO-like object that is iterable line-by-line."""

    def __init__(self, data):
        self._lines = data.splitlines(keepends=True)
        self._index = 0

    def read(self, n=-1):
        if n == -1:
            return "".join(self._lines[self._index:])
        return ""

    def __iter__(self):
        return self

    def __next__(self):
        if self._index >= len(self._lines):
            raise StopIteration
        line = self._lines[self._index]
        self._index += 1
        return line


class EndToEndCodeGraphTests(unittest.TestCase):
    """Full graph build -> query workflow with CALLS edge verification."""

    def test_build_and_query_returns_callers(self):
        with _tmp_repo() as root:
            _write(root / "src" / "app.py",
                   "def helper():\n    return 1\n\ndef caller():\n    return helper()\n")
            graph = build_code_graph(root)
            self.assertGreaterEqual(len(graph["nodes"]), 3)
            self.assertEqual(graph["state_dir"], ".codelevelup")

            q = query_code_graph(root, "caller")
            self.assertEqual(q["matches"][0]["name"], "caller")

            call_edges = [e for e in graph["edges"] if e["type"] == "calls"]
            self.assertEqual(len(call_edges), 1)
            self.assertIn("caller", call_edges[0]["source"])
            self.assertIn("helper", call_edges[0]["target"])

    def test_extracts_method_nodes_and_class_edges(self):
        with _tmp_repo() as root:
            _write(root / "src" / "service.py",
                   "class Service:\n    def level_up(self):\n        return 1\n")
            graph = build_code_graph(root)

            method_nodes = [n for n in graph["nodes"] if n["type"] == "Method"]
            self.assertEqual(len(method_nodes), 1)
            self.assertEqual(method_nodes[0]["name"], "level_up")

            has_method = [e for e in graph["edges"] if e["type"] == "has_method"]
            self.assertEqual(len(has_method), 1)

    def test_probe_reports_graph_state_transition(self):
        with _tmp_repo() as root:
            _write(root / "pyproject.toml",
                   "[project]\nname = 'demo'\ndependencies = []\n")
            report = probe_project(root)
            self.assertIn("python", report["ecosystems"])
            self.assertFalse(report["code_graph"]["graph_present"])

            build_code_graph(root)
            report2 = probe_project(root)
            self.assertTrue(report2["code_graph"]["graph_present"])


class EndToEndRepairLoopTests(unittest.TestCase):
    """Full repair loop -> repair memory round-trip."""

    def test_repair_loop_reports_structured_failures(self):
        with _tmp_repo() as root:
            _write(root / "src" / "app.py", "import missing_pkg\nx = 1\n")
            result = repair_loop(
                commands=["python src/app.py"],
                cwd=root,
                language="python",
                max_retries=2,
            )
            report = repair_loop_report(result)
            self.assertFalse(result.passed)
            self.assertEqual(result.total_rounds, 2)
            self.assertEqual(len(result.rounds), 2)
            self.assertEqual(result.rounds[0].error_type, "ModuleNotFoundError")
            self.assertIn("missing_pkg", result.rounds[0].message)

    def test_repair_memory_full_round_trip(self):
        with _tmp_repo() as root:
            entry = record_repair(
                root=root,
                error_type="ImportError",
                message="No module named 'missing_pkg'",
                fix_description="pip install missing-pkg",
                changed_files=["src/app.py"],
                round_number=1,
            )
            self.assertFalse(entry["verified"])

            hits = search_repairs(root, "ImportError",
                                  "No module named 'missing_pkg'")
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["fix_description"], "pip install missing-pkg")

            mark_verified(root, entry["id"])
            stats = repair_stats(root)
            self.assertEqual(stats["total"], 1)
            self.assertEqual(stats["verified"], 1)
            self.assertEqual(stats["unverified"], 0)

    def test_normalized_keys_match_across_version_numbers(self):
        with _tmp_repo() as root:
            record_repair(
                root=root,
                error_type="ModuleNotFoundError",
                message="No module named 'bar_v2'",
                fix_description="pip install bar",
                changed_files=["requirements.txt"],
                round_number=1,
            )
            hits = search_repairs(root, "ModuleNotFoundError",
                                  "No module named 'bar_v3'")
            self.assertEqual(len(hits), 1)


class EndToEndAgentEntryTests(unittest.TestCase):
    """Verify the agent entry point routes correctly."""

    def test_skill_mode_returns_instructions(self):
        rc, stdout, stderr = _invoke_agent("skill")
        self.assertEqual(rc, 0, stderr)
        self.assertIn("SKILL.md", stdout)

    def test_doctor_reports_modes_and_helper_commands(self):
        rc, stdout, stderr = _invoke_agent("doctor", "--json")
        self.assertEqual(rc, 0, stderr)
        payload = json.loads(stdout)
        self.assertIn("skill", payload["modes"])
        self.assertIn("mcp", payload["modes"])
        self.assertIn("doctor", payload["modes"])
        self.assertIn("probe", payload["helper_commands"])
        self.assertIn("repair", payload["helper_commands"])

    def test_helper_command_delegates_to_cli(self):
        with _tmp_repo() as root:
            _write(root / "src" / "app.py", "def foo():\n    pass\n")
            rc, stdout, stderr = _invoke_agent("graph", "build", str(root), "--json")
            self.assertEqual(rc, 0, stderr)
            payload = json.loads(stdout)
            self.assertIn("nodes", payload)
            self.assertIn("edges", payload)

    def test_unknown_mode_returns_error(self):
        rc, stdout, stderr = _invoke_agent("nonexistent")
        self.assertNotEqual(rc, 0)
        self.assertIn("Unknown mode", stderr)


class EndToEndMcpTests(unittest.TestCase):
    """Verify MCP protocol integration."""

    def test_mcp_lists_repair_tools(self):
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ]
        responses = _run_mcp(messages)
        tool_names = {t["name"] for t in responses[1]["result"]["tools"]}
        self.assertIn("repair_loop", tool_names)
        self.assertIn("repair_hints", tool_names)
        self.assertIn("repair_stats", tool_names)


if __name__ == "__main__":
    unittest.main()
