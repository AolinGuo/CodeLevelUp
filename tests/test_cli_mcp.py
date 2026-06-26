import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV = {"PYTHONPATH": str(ROOT / "src")}


class CodeLevelUpCliMcpTests(unittest.TestCase):
    def test_internal_probe_reports_project_and_graph_state(self):
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
        self.assertEqual(".codelevelup", payload["codelevelup"]["state_dir"])
        self.assertFalse(payload["code_graph"]["graph_present"])

    def test_internal_search_finds_local_code_without_graph_dependency(self):
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

    def test_internal_graph_build_and_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "service.py").write_text("def level_up():\n    return True\n", encoding="utf-8")
            build = run_cli("graph", "build", str(root), "--json")
            query = run_cli("graph", "query", str(root), "level_up", "--json")

        self.assertEqual(build.returncode, 0, build.stderr)
        self.assertEqual(query.returncode, 0, query.stderr)
        payload = json.loads(query.stdout)
        self.assertEqual(payload["matches"][0]["path"], "src/service.py")

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
                        "name": "build_code_graph",
                        "arguments": {"root": str(root)},
                    },
                },
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "query_code_graph",
                        "arguments": {"root": str(root), "query": "Searchable"},
                    },
                },
            ]

            result = subprocess.run(
                [sys.executable, "-m", "codelevelup.mcp_server"],
                input="\n".join(json.dumps(message) for message in messages) + "\n",
                text=True,
                capture_output=True,
                check=False,
                env=ENV,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        tool_names = {tool["name"] for tool in responses[1]["result"]["tools"]}
        self.assertIn("probe_project", tool_names)
        self.assertIn("search_code", tool_names)
        self.assertIn("build_code_graph", tool_names)
        self.assertIn("query_code_graph", tool_names)
        self.assertNotIn("gitnexus_status", tool_names)
        call_payload = json.loads(responses[3]["result"]["content"][0]["text"])
        self.assertEqual(call_payload["matches"][0]["path"], "src/service.py")


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "codelevelup.cli", *args],
        text=True,
        capture_output=True,
        check=False,
        env=ENV,
    )


if __name__ == "__main__":
    unittest.main()
