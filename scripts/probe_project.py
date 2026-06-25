#!/usr/bin/env python3
"""Probe a repository and suggest setup, verification, security, and GitNexus commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


LOCKFILES = [
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lockb",
    "uv.lock",
    "poetry.lock",
    "Pipfile.lock",
    "requirements.lock",
    "Cargo.lock",
    "go.sum",
]

GITNEXUS_INDEX_MARKERS = [
    "graph.json",
    "graph.db",
    "index.json",
    "registry.json",
]


def probe_project(root: Path) -> dict[str, Any]:
    root = root.resolve()
    report: dict[str, Any] = {
        "root": str(root),
        "ecosystems": [],
        "manifests": [],
        "setup_commands": [],
        "verification_commands": [],
        "security_commands": [],
        "incremental_search_targets": {
            "manifests": [],
            "lockfiles": [],
            "notable_paths": [],
        },
        "sandbox": {
            "supports_docker": (root / "Dockerfile").exists() or any(root.glob("compose*.y*ml")),
            "dependency_install_rule": (
                "Install dependencies only inside an existing project virtual environment, "
                "a freshly-created local .venv, a container, or another explicit sandbox."
            ),
        },
        "gitnexus": build_gitnexus_report(root),
    }

    detect_python(root, report)
    detect_node(root, report)
    detect_go(root, report)
    detect_rust(root, report)
    detect_notable_paths(root, report)
    detect_lockfiles(root, report)

    return report


def build_gitnexus_report(root: Path) -> dict[str, Any]:
    gitnexus_dir = root / ".gitnexus"
    runner = gitnexus_dir / "run.cjs"
    index_present = gitnexus_dir.exists() and any((gitnexus_dir / name).exists() for name in GITNEXUS_INDEX_MARKERS)
    return {
        "runner_present": runner.exists(),
        "index_present": index_present,
        "bootstrap_command": "npx gitnexus analyze",
        "commands": [
            {"command": "node .gitnexus/run.cjs status", "reason": "Check GitNexus index freshness."},
            {"command": "node .gitnexus/run.cjs analyze", "reason": "Build or refresh the code knowledge graph."},
            {
                "command": "node .gitnexus/run.cjs analyze --pdg",
                "reason": "Build taint, control-dependence, and data-dependence layers.",
            },
            {"command": "node .gitnexus/run.cjs wiki", "reason": "Generate graph-backed repository documentation."},
        ],
        "mcp_resources": [
            "gitnexus://repo/{name}/context",
            "gitnexus://repo/{name}/clusters",
            "gitnexus://repo/{name}/processes",
            "gitnexus://repo/{name}/schema",
        ],
        "mcp_tools": [
            "query",
            "context",
            "impact",
            "trace",
            "detect_changes",
            "check",
            "explain",
            "pdg_query",
        ],
    }


def detect_python(root: Path, report: dict[str, Any]) -> None:
    pyproject = root / "pyproject.toml"
    requirements = root / "requirements.txt"
    if not pyproject.exists() and not requirements.exists():
        return

    add_unique(report["ecosystems"], "python")
    if pyproject.exists():
        add_manifest(report, "pyproject.toml")
        text = pyproject.read_text(encoding="utf-8", errors="ignore")
        add_command(
            report,
            "setup_commands",
            "python -m venv .venv && . .venv/bin/activate && python -m pip install -e \".[dev]\"",
            "Install editable project and dev dependencies in a local virtual environment.",
        )
        if "pytest" in text or "[tool.pytest" in text:
            add_command(report, "verification_commands", "python -m pytest", "Run Python tests.")
        if "ruff" in text or "[tool.ruff" in text:
            add_command(report, "verification_commands", "python -m ruff check .", "Run Ruff lint.")
        add_command(
            report,
            "security_commands",
            "python -m pip_audit",
            "Audit Python packages after installing pip-audit in the sandbox.",
        )
    if requirements.exists():
        add_manifest(report, "requirements.txt")
        add_command(
            report,
            "setup_commands",
            "python -m venv .venv && . .venv/bin/activate && python -m pip install -r requirements.txt",
            "Install requirements in a local virtual environment.",
        )
        add_command(report, "security_commands", "python -m pip_audit", "Audit Python packages.")


def detect_node(root: Path, report: dict[str, Any]) -> None:
    package_json = root / "package.json"
    if not package_json.exists():
        return

    add_unique(report["ecosystems"], "node")
    add_manifest(report, "package.json")
    manager = detect_node_manager(root)
    install_command = {
        "pnpm": "pnpm install --frozen-lockfile",
        "yarn": "yarn install --immutable",
        "bun": "bun install --frozen-lockfile",
        "npm": "npm ci",
    }[manager]
    add_command(report, "setup_commands", install_command, "Install Node dependencies from lockfile.")

    scripts = read_package_scripts(package_json)
    for script_name in ("test", "lint", "build", "typecheck"):
        if script_name in scripts:
            add_command(
                report,
                "verification_commands",
                f"{manager} {script_name}",
                f"Run package.json {script_name} script.",
            )

    audit_command = {
        "pnpm": "pnpm audit --audit-level moderate",
        "yarn": "yarn npm audit --severity moderate",
        "bun": "bun audit",
        "npm": "npm audit --audit-level=moderate",
    }[manager]
    add_command(report, "security_commands", audit_command, "Audit Node dependencies.")


def detect_go(root: Path, report: dict[str, Any]) -> None:
    if not (root / "go.mod").exists():
        return

    add_unique(report["ecosystems"], "go")
    add_manifest(report, "go.mod")
    add_command(report, "setup_commands", "go mod download", "Download Go modules.")
    add_command(report, "verification_commands", "go test ./...", "Run Go tests.")
    add_command(report, "security_commands", "govulncheck ./...", "Audit Go vulnerabilities.")


def detect_rust(root: Path, report: dict[str, Any]) -> None:
    if not (root / "Cargo.toml").exists():
        return

    add_unique(report["ecosystems"], "rust")
    add_manifest(report, "Cargo.toml")
    add_command(report, "setup_commands", "cargo fetch", "Fetch Rust dependencies.")
    add_command(report, "verification_commands", "cargo test", "Run Rust tests.")
    add_command(report, "verification_commands", "cargo clippy --all-targets", "Run Rust lints.")
    add_command(report, "security_commands", "cargo audit", "Audit Rust dependencies.")


def detect_notable_paths(root: Path, report: dict[str, Any]) -> None:
    for name in (
        ".gitnexus",
        "Dockerfile",
        "compose.yaml",
        "compose.yml",
        "docker-compose.yaml",
        "docker-compose.yml",
    ):
        if (root / name).exists():
            report["incremental_search_targets"]["notable_paths"].append(name)


def detect_lockfiles(root: Path, report: dict[str, Any]) -> None:
    for name in LOCKFILES:
        if (root / name).exists():
            report["incremental_search_targets"]["lockfiles"].append(name)


def detect_node_manager(root: Path) -> str:
    if (root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (root / "yarn.lock").exists():
        return "yarn"
    if (root / "bun.lockb").exists():
        return "bun"
    return "npm"


def read_package_scripts(package_json: Path) -> dict[str, str]:
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    scripts = data.get("scripts", {})
    return scripts if isinstance(scripts, dict) else {}


def add_manifest(report: dict[str, Any], name: str) -> None:
    add_unique(report["manifests"], name)
    add_unique(report["incremental_search_targets"]["manifests"], name)


def add_command(report: dict[str, Any], bucket: str, command: str, reason: str) -> None:
    if all(item["command"] != command for item in report[bucket]):
        report[bucket].append({"command": command, "reason": reason})


def add_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="Repository root to probe.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args()

    report = probe_project(Path(args.root))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_human_report(report)
    return 0


def print_human_report(report: dict[str, Any]) -> None:
    print(f"Root: {report['root']}")
    print(f"Ecosystems: {', '.join(report['ecosystems']) or 'none detected'}")
    print("\nGitNexus:")
    print(f"- bootstrap: {report['gitnexus']['bootstrap_command']}")
    for item in report["gitnexus"]["commands"]:
        print(f"- {item['command']}  # {item['reason']}")
    for title, key in (
        ("Setup", "setup_commands"),
        ("Verification", "verification_commands"),
        ("Security", "security_commands"),
    ):
        print(f"\n{title}:")
        for item in report[key]:
            print(f"- {item['command']}  # {item['reason']}")


if __name__ == "__main__":
    raise SystemExit(main())
