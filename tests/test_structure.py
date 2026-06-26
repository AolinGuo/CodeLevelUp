import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ProjectStructureTests(unittest.TestCase):
    def test_aris_style_skill_bundle_exists(self):
        expected = [
            "AGENT_GUIDE.md",
            "skills/codelevelup/SKILL.md",
            "skills/codelevelup/references/agent-entry-layer.md",
            "skills/codelevelup/references/code-graph-workflow.md",
            "skills/codelevelup/references/graph-query-patterns.md",
            "skills/codelevelup/references/code-search-workflow.md",
            "skills/codelevelup/references/self-upgrade-workflow.md",
            "skills/codelevelup/references/vulnerability-remediation-workflow.md",
            "skills/codelevelup/references/verification-review-workflow.md",
            "skills/codelevelup/references/upgrade-loop.md",
        ]

        missing = [path for path in expected if not (ROOT / path).is_file()]

        self.assertEqual([], missing)

    def test_skill_project_is_not_gitnexus_or_cli_centered(self):
        checked_paths = [
            "README.md",
            "README_CN.md",
            "AGENTS.md",
            "CLAUDE.md",
            "AGENT_GUIDE.md",
            "skills/codelevelup/SKILL.md",
            "skills/codelevelup/references/agent-entry-layer.md",
            "skills/codelevelup/references/code-search-workflow.md",
            "skills/codelevelup/references/code-graph-workflow.md",
            "skills/codelevelup/references/graph-query-patterns.md",
        ]

        violations = []
        for path in checked_paths:
            doc = ROOT / path
            if not doc.exists():
                violations.append(f"missing: {path}")
                continue
            text = doc.read_text(encoding="utf-8")
            if "GitNexus" in text or "gitnexus" in text:
                violations.append(f"{path}: GitNexus is runtime-facing")
            if "codelevelup-agent cli" in text or " codelevelup " in text:
                violations.append(f"{path}: exposes user-facing CLI subcommands")

        self.assertEqual([], violations)

    def test_core_workflows_are_explicitly_centered(self):
        skill_text = (ROOT / "skills/codelevelup/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("code-graph-workflow.md", skill_text)
        self.assertIn("graph-query-patterns.md", skill_text)
        self.assertIn("self-upgrade-workflow.md", skill_text)
        self.assertIn("vulnerability-remediation-workflow.md", skill_text)
        self.assertIn("verification-review-workflow.md", skill_text)

        self_upgrade = (
            ROOT / "skills/codelevelup/references/self-upgrade-workflow.md"
        ).read_text(encoding="utf-8")
        vulnerability = (
            ROOT / "skills/codelevelup/references/vulnerability-remediation-workflow.md"
        ).read_text(encoding="utf-8")

        self.assertIn("code self-upgrade", self_upgrade)
        self.assertIn("requirements gate", self_upgrade)
        self.assertIn("vulnerability repair", vulnerability)
        self.assertIn("human review", vulnerability)

        graph = (
            ROOT / "skills/codelevelup/references/code-graph-workflow.md"
        ).read_text(encoding="utf-8")
        self.assertIn(".codelevelup/graph", graph)
        self.assertIn("code graph", graph)

    def test_aris_outer_files_are_optional_not_required(self):
        verifier_text = (ROOT / "tools/verify_skill_structure.py").read_text(encoding="utf-8")
        required_section = verifier_text.split("REQUIRED_FILES = [", 1)[1].split("]", 1)[0]

        self.assertNotIn('"README_CN.md"', required_section)
        self.assertNotIn('"CONTRIBUTING.md"', required_section)
        self.assertNotIn('"assets/README.md"', required_section)

    def test_root_skill_is_only_a_compatibility_shim(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("skills/codelevelup/SKILL.md", text)
        self.assertLess(len(text.splitlines()), 30)

    def test_runtime_code_and_tests_are_separated(self):
        expected_runtime = [
            "src/codelevelup/__init__.py",
            "src/codelevelup/agent.py",
            "src/codelevelup/code_graph.py",
            "src/codelevelup/cli.py",
            "src/codelevelup/mcp_server.py",
            "src/codelevelup/probe.py",
        ]
        missing_runtime = [path for path in expected_runtime if not (ROOT / path).is_file()]
        script_tests = sorted(path.name for path in (ROOT / "scripts").glob("test_*.py"))

        self.assertEqual([], missing_runtime)
        self.assertEqual([], script_tests)

    def test_structure_verifier_and_ci_gate_exist(self):
        expected = [
            "tools/verify_skill_structure.py",
            ".github/workflows/verify.yml",
        ]
        missing = [path for path in expected if not (ROOT / path).is_file()]

        self.assertEqual([], missing)

    def test_user_docs_are_split_from_internal_plans(self):
        expected_docs = [
            "docs/architecture.md",
            "docs/usage.md",
            "docs/sca-workflow.md",
            "internal/superpowers/plans/2026-06-25-upgrade-request-gate.md",
            "internal/superpowers/specs/2026-06-25-upgrade-request-gate-design.md",
        ]
        missing = [path for path in expected_docs if not (ROOT / path).is_file()]

        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
