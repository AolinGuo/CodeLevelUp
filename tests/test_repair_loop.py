import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = {"PYTHONPATH": str(ROOT / "src")}


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "codelevelup.cli", *args],
        text=True,
        capture_output=True,
        check=False,
        env=ENV,
    )


def run_module(*args):
    return subprocess.run(
        [sys.executable, "-m", "codelevelup.repair_loop", *args],
        text=True,
        capture_output=True,
        check=False,
        env=ENV,
    )


def run_memory(*args):
    return subprocess.run(
        [sys.executable, "-m", "codelevelup.repair_memory", *args],
        text=True,
        capture_output=True,
        check=False,
        env=ENV,
    )


class RepairLoopTests(unittest.TestCase):
    def _make_repo(self, broken: bool = True) -> Path:
        tmp = Path(tempfile.mkdtemp())
        src = tmp / "src"
        src.mkdir()
        if broken:
            (src / "app.py").write_text("import nonexistent_module\n", encoding="utf-8")
        else:
            (src / "app.py").write_text("x = 1\n", encoding="utf-8")
        return tmp

    def test_passes_when_verification_succeeds(self):
        tmp = self._make_repo(broken=False)
        result = run_cli("repair", "echo ok", "--cwd", str(tmp), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["total_rounds"], 0)

    def test_reports_failure_when_verification_fails(self):
        tmp = self._make_repo(broken=True)
        result = run_cli("repair", "python -c 'import sys; sys.exit(1)'",
                         "--cwd", str(tmp), "--json")
        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["passed"])
        self.assertGreater(payload["total_rounds"], 0)
        self.assertEqual(payload["max_retries"], 5)

    def test_parses_python_traceback(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "src").mkdir()
        (tmp / "src" / "app.py").write_text(
            "def bad():\n    raise ValueError('test error')\nbad()\n",
            encoding="utf-8",
        )
        result = run_cli(
            "repair", f"python {tmp / 'src' / 'app.py'}",
            "--cwd", str(tmp), "--json", "--max-retries", "1",
        )
        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["passed"])
        self.assertEqual(payload["total_rounds"], 1)
        self.assertEqual(payload["max_retries"], 1)
        self.assertEqual(len(payload["rounds"]), 1)
        round_info = payload["rounds"][0]
        self.assertIn("error_type", round_info)
        self.assertIn("suggestion", round_info)

    def test_respects_max_retries(self):
        tmp = self._make_repo(broken=True)
        result = run_cli(
            "repair", "false",
            "--cwd", str(tmp), "--max-retries", "2", "--json",
        )
        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["total_rounds"], 2)
        self.assertEqual(payload["max_retries"], 2)

    def test_empty_commands_list(self):
        result = run_cli("repair", "--json")
        self.assertNotEqual(result.returncode, 0)


class RepairMemoryTests(unittest.TestCase):
    def _repo(self) -> Path:
        tmp = Path(tempfile.mkdtemp())
        (tmp / ".git").mkdir()
        return tmp

    def test_record_and_search(self):
        root = self._repo()
        record = run_memory("record", "--root", str(root),
                            "--error-type", "ImportError",
                            "--message", "No module named 'foo'",
                            "--fix", "pip install foo",
                            "--files", "requirements.txt",
                            "--round", "1", "--json")
        self.assertEqual(record.returncode, 0)
        entry = json.loads(record.stdout)
        self.assertEqual(entry["error_type"], "ImportError")
        self.assertFalse(entry["verified"])

        search = run_memory("search", "--root", str(root),
                            "--error-type", "ImportError",
                            "--message", "No module named 'foo'",
                            "--json")
        self.assertEqual(search.returncode, 0)
        results = json.loads(search.stdout)
        self.assertEqual(results["count"], 1)
        self.assertEqual(results["results"][0]["fix_description"], "pip install foo")

    def test_normalizes_error_keys(self):
        root = self._repo()
        run_memory("record", "--root", str(root),
                   "--error-type", "ModuleNotFoundError",
                   "--message", "No module named 'bar_v2'",
                   "--fix", "pip install bar",
                   "--files", "requirements.txt",
                   "--round", "1")
        results = json.loads(
            run_memory("search", "--root", str(root),
                       "--error-type", "ModuleNotFoundError",
                       "--message", "No module named 'bar_v3'",
                       "--json").stdout
        )
        self.assertEqual(results["count"], 1)

    def test_verify_updates_entry(self):
        root = self._repo()
        entry = json.loads(
            run_memory("record", "--root", str(root),
                       "--error-type", "TypeError",
                       "--message", "got int, expected str",
                       "--fix", "cast to str()",
                       "--files", "src/app.py",
                       "--round", "1", "--json").stdout
        )
        verify = run_memory("verify", "--root", str(root), "--id", str(entry["id"]), "--json")
        self.assertEqual(verify.returncode, 0)
        updated = json.loads(verify.stdout)
        self.assertTrue(updated["verified"])
        self.assertIn("verified_at", updated)

    def test_stats_counts(self):
        root = self._repo()
        run_memory("record", "--root", str(root),
                   "--error-type", "ImportError",
                   "--message", "No module named 'x'",
                   "--fix", "install x",
                   "--files", "requirements.txt",
                   "--round", "1")
        run_memory("record", "--root", str(root),
                   "--error-type", "TypeError",
                   "--message", "type mismatch",
                   "--fix", "cast type",
                   "--files", "src/app.py",
                   "--round", "2")
        stats = json.loads(
            run_memory("stats", "--root", str(root), "--json").stdout
        )
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["unverified"], 2)


class MCPRepairToolsTests(unittest.TestCase):
    def test_mcp_lists_repair_tools(self):
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ]
        result = subprocess.run(
            [sys.executable, "-m", "codelevelup.mcp_server"],
            input="\n".join(json.dumps(m) for m in messages) + "\n",
            text=True,
            capture_output=True,
            check=False,
            env=ENV,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        tool_names = {t["name"] for t in responses[1]["result"]["tools"]}
        self.assertIn("repair_loop", tool_names)
        self.assertIn("record_repair", tool_names)
        self.assertIn("search_repairs", tool_names)
        self.assertIn("repair_hints", tool_names)
        self.assertIn("repair_stats", tool_names)

    def test_mcp_repair_loop_returns_failure_report(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "src").mkdir()
        (tmp / "src" / "app.py").write_text("import nonexistent_module\n", encoding="utf-8")
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {
                "jsonrpc": "2.0", "id": 3, "method": "tools/call",
                "params": {
                    "name": "repair_loop",
                    "arguments": {
                        "root": str(tmp),
                        "commands": ["python -c 'import sys; sys.exit(1)'"],
                        "max_retries": 1,
                    },
                },
            },
        ]
        result = subprocess.run(
            [sys.executable, "-m", "codelevelup.mcp_server"],
            input="\n".join(json.dumps(m) for m in messages) + "\n",
            text=True,
            capture_output=True,
            check=False,
            env=ENV,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        payload = json.loads(responses[2]["result"]["content"][0]["text"])
        self.assertFalse(payload["passed"])
        self.assertEqual(payload["total_rounds"], 1)


if __name__ == "__main__":
    unittest.main()
