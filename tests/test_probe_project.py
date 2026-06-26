import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from codelevelup import probe_project


class ProbeProjectTests(unittest.TestCase):
    def test_detects_python_verification_security_and_codelevelup_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            (root / "pyproject.toml").write_text(
                """
[project]
dependencies = ["fastapi"]

[project.optional-dependencies]
dev = ["pytest", "ruff"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
""".strip(),
                encoding="utf-8",
            )

            report = probe_project(root)

        self.assertIn("python", report["ecosystems"])
        self.assertIn(
            'python -m venv .venv && . .venv/bin/activate && python -m pip install -e ".[dev]"',
            command_strings(report, "setup_commands"),
        )
        self.assertIn("python -m pytest", command_strings(report, "verification_commands"))
        self.assertIn("python -m ruff check .", command_strings(report, "verification_commands"))
        self.assertIn("python -m pip_audit", command_strings(report, "security_commands"))
        self.assertEqual(".codelevelup", report["codelevelup"]["state_dir"])
        self.assertEqual(".codelevelup/graph", report["code_graph"]["graph_dir"])
        self.assertFalse(report["code_graph"]["graph_present"])

    def test_python_setup_command_omits_missing_dev_extra(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                "[project]\nname = \"demo\"\ndependencies = []\n",
                encoding="utf-8",
            )

            report = probe_project(root)

        self.assertIn(
            "python -m venv .venv && . .venv/bin/activate && python -m pip install -e .",
            command_strings(report, "setup_commands"),
        )

    def test_detects_existing_codelevelup_graph_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            graph_dir = root / ".codelevelup" / "graph"
            graph_dir.mkdir(parents=True)
            (graph_dir / "graph.json").write_text("{}", encoding="utf-8")

            report = probe_project(root)

        self.assertTrue(report["code_graph"]["graph_present"])
        self.assertIn(".codelevelup", report["incremental_search_targets"]["notable_paths"])

    def test_detects_node_package_manager_scripts_and_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(
                json.dumps(
                    {
                        "scripts": {
                            "test": "vitest run",
                            "lint": "eslint .",
                            "build": "vite build",
                        }
                    }
                ),
                encoding="utf-8",
            )
            (root / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")

            report = probe_project(root)

        self.assertIn("node", report["ecosystems"])
        self.assertIn("pnpm install --frozen-lockfile", command_strings(report, "setup_commands"))
        self.assertIn("pnpm test", command_strings(report, "verification_commands"))
        self.assertIn("pnpm lint", command_strings(report, "verification_commands"))
        self.assertIn("pnpm build", command_strings(report, "verification_commands"))
        self.assertIn(
            "pnpm audit --audit-level moderate", command_strings(report, "security_commands")
        )

    def test_detects_go_and_rust_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "go.mod").write_text("module example.com/app\n", encoding="utf-8")
            (root / "Cargo.toml").write_text(
                "[package]\nname = \"demo\"\nversion = \"0.1.0\"\n", encoding="utf-8"
            )

            report = probe_project(root)

        self.assertIn("go", report["ecosystems"])
        self.assertIn("rust", report["ecosystems"])
        self.assertIn("go test ./...", command_strings(report, "verification_commands"))
        self.assertIn("cargo test", command_strings(report, "verification_commands"))
        self.assertIn("govulncheck ./...", command_strings(report, "security_commands"))
        self.assertIn("cargo audit", command_strings(report, "security_commands"))


def command_strings(report, key):
    return [item["command"] for item in report[key]]


if __name__ == "__main__":
    unittest.main()
