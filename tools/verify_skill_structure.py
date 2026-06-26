#!/usr/bin/env python3
"""Verify CodeLevelUp's ARIS-inspired skill-first project structure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "AGENT_GUIDE.md",
    "SKILL.md",
    "skills/codelevelup/SKILL.md",
    "skills/codelevelup/references/agent-entry-layer.md",
    "skills/codelevelup/references/code-graph-workflow.md",
    "skills/codelevelup/references/graph-query-patterns.md",
    "skills/codelevelup/references/code-search-workflow.md",
    "skills/codelevelup/references/self-upgrade-workflow.md",
    "skills/codelevelup/references/vulnerability-remediation-workflow.md",
    "skills/codelevelup/references/verification-review-workflow.md",
    "skills/codelevelup/references/upgrade-loop.md",
    "src/codelevelup/__init__.py",
    "src/codelevelup/agent.py",
    "src/codelevelup/code_graph.py",
    "src/codelevelup/cli.py",
    "src/codelevelup/mcp_server.py",
    "src/codelevelup/probe.py",
    "tests/test_agent_entry.py",
    "tests/test_cli_mcp.py",
    "tests/test_probe_project.py",
    "tests/test_structure.py",
    "tools/verify_skill_structure.py",
    ".github/workflows/verify.yml",
    "docs/architecture.md",
    "docs/usage.md",
    "docs/sca-workflow.md",
    "internal/superpowers/plans/2026-06-25-upgrade-request-gate.md",
    "internal/superpowers/specs/2026-06-25-upgrade-request-gate-design.md",
]

OPTIONAL_STYLE_FILES = [
    "README_CN.md",
    "CONTRIBUTING.md",
    "assets/README.md",
]

ACTIVE_DOCS = [
    "README.md",
    "README_CN.md",
    "CONTRIBUTING.md",
    "SKILL.md",
    "AGENTS.md",
    "CLAUDE.md",
    "AGENT_GUIDE.md",
    "docs/architecture.md",
    "docs/usage.md",
    "docs/sca-workflow.md",
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

BANNED_DOC_PHRASES = [
    "GitNexus",
    "gitnexus",
    "codelevelup-agent cli",
    "python scripts/codelevelup.py",
    "python3 scripts/codelevelup.py",
    "python scripts/codelevelup_mcp.py",
    "python3 scripts/codelevelup_mcp.py",
    "python scripts/probe_project.py",
    "python3 scripts/probe_project.py",
]


def verify(root: Path = ROOT) -> list[str]:
    issues: list[str] = []

    for path in REQUIRED_FILES:
        if not (root / path).is_file():
            issues.append(f"missing required file: {path}")

    root_skill = root / "SKILL.md"
    if root_skill.exists():
        text = root_skill.read_text(encoding="utf-8")
        if "skills/codelevelup/SKILL.md" not in text:
            issues.append("root SKILL.md must point to skills/codelevelup/SKILL.md")
        if len(text.splitlines()) >= 30:
            issues.append("root SKILL.md must stay a short compatibility shim")

    bundled_skill = root / "skills" / "codelevelup" / "SKILL.md"
    if bundled_skill.exists():
        text = bundled_skill.read_text(encoding="utf-8")
        if "name: code-level-up" not in text:
            issues.append("bundled skill must keep name: code-level-up")
            if "skills/codelevelup/references/agent-entry-layer.md" not in text:
                issues.append("bundled skill must reference the entry layer")
        for workflow in (
            "skills/codelevelup/references/code-graph-workflow.md",
            "skills/codelevelup/references/graph-query-patterns.md",
            "skills/codelevelup/references/self-upgrade-workflow.md",
            "skills/codelevelup/references/vulnerability-remediation-workflow.md",
            "skills/codelevelup/references/verification-review-workflow.md",
        ):
            if workflow not in text:
                issues.append(f"bundled skill must reference core workflow: {workflow}")

    scripts_dir = root / "scripts"
    if scripts_dir.exists():
        for path in scripts_dir.glob("test_*.py"):
            issues.append(f"tests must live under tests/, not scripts/: {path.name}")

    for path in ACTIVE_DOCS:
        doc = root / path
        if not doc.exists():
            continue
        text = doc.read_text(encoding="utf-8")
        for phrase in BANNED_DOC_PHRASES:
            if phrase in text:
                issues.append(f"{path} still instructs direct runtime script use: {phrase}")

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8")
        for expected in (
            'codelevelup-agent = "codelevelup.agent:main"',
            'package-dir = {"" = "src"}',
        ):
            if expected not in text:
                issues.append(f"pyproject.toml missing expected entry: {expected}")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print a JSON report.")
    args = parser.parse_args()

    issues = verify()
    if args.json:
        print(json.dumps({"ok": not issues, "issues": issues}, indent=2, sort_keys=True))
    elif issues:
        print("CodeLevelUp structure check failed:")
        for issue in issues:
            print(f"- {issue}")
    else:
        print("CodeLevelUp structure check passed.")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
