import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "bin" / "codelevelup-agent"
ENV = {"PYTHONPATH": str(ROOT / "src")}


class CodeLevelUpAgentEntryTests(unittest.TestCase):
    def test_agent_entry_mcp_mode_runs_stdio_server(self):
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ]

        result = run_entry(
            "mcp",
            input_text="\n".join(json.dumps(message) for message in messages) + "\n",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(responses[0]["result"]["serverInfo"]["name"], "CodeLevelUp")
        tool_names = {tool["name"] for tool in responses[1]["result"]["tools"]}
        self.assertIn("probe_project", tool_names)
        self.assertIn("search_code", tool_names)

    def test_agent_entry_doctor_declares_skill_first_and_python_optional(self):
        result = run_entry("doctor", "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["entrypoint"], "codelevelup-agent")
        self.assertTrue(payload["skill_first"])
        self.assertIn("skill", payload["modes"])
        self.assertIn("mcp", payload["modes"])
        self.assertIn("doctor", payload["modes"])
        self.assertNotIn("cli", payload["modes"])
        self.assertEqual(payload["python_required_for"], ["mcp"])
        self.assertEqual(payload["recommended_mcp_args"], ["mcp"])
        self.assertIn("skills/codelevelup/references/agent-entry-layer.md", payload["skill_reference"])

    def test_local_wrapper_calls_same_entry_layer(self):
        result = subprocess.run(
            [str(WRAPPER), "doctor", "--json"],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["entrypoint"], "codelevelup-agent")

    def test_active_agent_docs_do_not_instruct_raw_runtime_scripts(self):
        active_docs = [
            ROOT / "README.md",
            ROOT / "SKILL.md",
            ROOT / "AGENTS.md",
            ROOT / "CLAUDE.md",
            ROOT / "AGENT_GUIDE.md",
            ROOT / "skills" / "codelevelup" / "references" / "code-search-workflow.md",
            ROOT / "skills" / "codelevelup" / "references" / "code-graph-workflow.md",
            ROOT / "skills" / "codelevelup" / "references" / "upgrade-loop.md",
        ]
        banned = [
            "codelevelup-agent cli",
            "python scripts/codelevelup.py",
            "python3 scripts/codelevelup.py",
            "python scripts/codelevelup_mcp.py",
            "python3 scripts/codelevelup_mcp.py",
            "python scripts/probe_project.py",
            "python3 scripts/probe_project.py",
        ]

        violations = []
        for doc in active_docs:
            text = doc.read_text(encoding="utf-8")
            for phrase in banned:
                if phrase in text:
                    violations.append(f"{doc.relative_to(ROOT)}: {phrase}")

        self.assertEqual([], violations)

    def test_skill_documents_skill_first_entry_contract(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        entry_reference = (
            ROOT / "skills" / "codelevelup" / "references" / "agent-entry-layer.md"
        ).read_text(encoding="utf-8")

        self.assertIn("skills/codelevelup/SKILL.md", skill)
        self.assertIn("Skill-first", entry_reference)
        self.assertIn("does not require Python", entry_reference)
        self.assertIn("Do not run implementation modules directly from `src/`", entry_reference)
        self.assertIn(".codelevelup", entry_reference)


def run_entry(*args, input_text=None):
    return subprocess.run(
        [sys.executable, "-m", "codelevelup.agent", *args],
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
        env=ENV,
    )


if __name__ == "__main__":
    unittest.main()
