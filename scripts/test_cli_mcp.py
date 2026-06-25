import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "codelevelup.py"
MCP = ROOT / "scripts" / "codelevelup_mcp.py"


class CodeLevelUpCliMcpTests(unittest.TestCase):
    def test_cli_probe_reports_project_and_gitnexus_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            (root / "pyproject.toml").write_text(
                "[project]\nname = \"demo\"\n[project.optional-dependencies]\ndev = [\"pytest\"]\n",
                encoding="utf-8",
            )

            result = run_cli("probe", "--json", str(root))

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("python", payload["ecosystems"])
        self.assertFalse(payload["gitnexus"]["runner_present"])
        self.assertEqual("npx gitnexus analyze", payload["gitnexus"]["bootstrap_command"])

    def test_cli_search_finds_local_code_without_gitnexus_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            src.mkdir()
            (src / "app.py").write_text("def level_up():\n    return 'ready'\n", encoding="utf-8")

            result = run_cli("search", str(root), "level_up", "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["query"], "level_up")
        self.assertEqual(len(payload["matches"]), 1)
        self.assertEqual(payload["matches"][0]["path"], "src/app.py")

    def test_cli_gitnexus_analyze_dry_run_returns_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli("gitnexus", "analyze", str(tmp), "--pdg", "--dry-run", "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["command"], "npx gitnexus analyze --pdg")
        self.assertTrue(payload["dry_run"])

    def test_mcp_lists_and_calls_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "service.py").write_text("class Searchable:\n    pass\n", encoding="utf-8")
            messages = [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "search_code",
                        "arguments": {"root": str(root), "query": "Searchable"},
                    },
                },
            ]

            result = subprocess.run(
                [sys.executable, str(MCP)],
                input="\n".join(json.dumps(message) for message in messages) + "\n",
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        tool_names = {tool["name"] for tool in responses[1]["result"]["tools"]}
        self.assertIn("probe_project", tool_names)
        self.assertIn("search_code", tool_names)
        call_payload = json.loads(responses[2]["result"]["content"][0]["text"])
        self.assertEqual(call_payload["matches"][0]["path"], "src/service.py")


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        text=True,
        capture_output=True,
        check=False,
    )


if __name__ == "__main__":
    unittest.main()
