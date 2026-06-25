import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("probe_project.py")


def load_probe_module():
    spec = importlib.util.spec_from_file_location("probe_project", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProbeProjectTests(unittest.TestCase):
    def test_detects_python_verification_security_and_gitnexus_bootstrap(self):
        probe = load_probe_module()
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

            report = probe.probe_project(root)

        self.assertIn("python", report["ecosystems"])
        self.assertIn(
            'python -m venv .venv && . .venv/bin/activate && python -m pip install -e ".[dev]"',
            command_strings(report, "setup_commands"),
        )
        self.assertIn("python -m pytest", command_strings(report, "verification_commands"))
        self.assertIn("python -m ruff check .", command_strings(report, "verification_commands"))
        self.assertIn("python -m pip_audit", command_strings(report, "security_commands"))
        self.assertFalse(report["gitnexus"]["runner_present"])
        self.assertFalse(report["gitnexus"]["index_present"])
        self.assertEqual("npx gitnexus analyze", report["gitnexus"]["bootstrap_command"])
        self.assertIn("gitnexus://repo/{name}/context", report["gitnexus"]["mcp_resources"])

    def test_python_setup_command_omits_missing_dev_extra(self):
        probe = load_probe_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                "[project]\nname = \"demo\"\ndependencies = []\n",
                encoding="utf-8",
            )

            report = probe.probe_project(root)

        self.assertIn(
            "python -m venv .venv && . .venv/bin/activate && python -m pip install -e .",
            command_strings(report, "setup_commands"),
        )

    def test_detects_existing_gitnexus_runner_and_index(self):
        probe = load_probe_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            gitnexus_dir = root / ".gitnexus"
            gitnexus_dir.mkdir()
            (gitnexus_dir / "run.cjs").write_text("// runner\n", encoding="utf-8")
            (gitnexus_dir / "graph.json").write_text("{}", encoding="utf-8")

            report = probe.probe_project(root)

        self.assertTrue(report["gitnexus"]["runner_present"])
        self.assertTrue(report["gitnexus"]["index_present"])
        self.assertIn(".gitnexus", report["incremental_search_targets"]["notable_paths"])

    def test_detects_node_package_manager_scripts_and_audit(self):
        probe = load_probe_module()
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

            report = probe.probe_project(root)

        self.assertIn("node", report["ecosystems"])
        self.assertIn("pnpm install --frozen-lockfile", command_strings(report, "setup_commands"))
        self.assertIn("pnpm test", command_strings(report, "verification_commands"))
        self.assertIn("pnpm lint", command_strings(report, "verification_commands"))
        self.assertIn("pnpm build", command_strings(report, "verification_commands"))
        self.assertIn(
            "pnpm audit --audit-level moderate", command_strings(report, "security_commands")
        )

    def test_detects_go_and_rust_commands(self):
        probe = load_probe_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "go.mod").write_text("module example.com/app\n", encoding="utf-8")
            (root / "Cargo.toml").write_text(
                "[package]\nname = \"demo\"\nversion = \"0.1.0\"\n", encoding="utf-8"
            )

            report = probe.probe_project(root)

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
