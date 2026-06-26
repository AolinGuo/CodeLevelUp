#!/usr/bin/env python3
"""Unified entry point for CodeLevelUp.

Routes to the appropriate mode:
- ``skill``          – print skill entry instructions (no Python runtime needed)
- ``mcp``            – start the stdio MCP server
- ``doctor``         – describe available modes and capabilities
- ``probe`` / ``search`` / ``graph`` / ``repair`` / ``repair-memory`` –
  delegate to the internal CLI for projects that need helper tooling
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

logger = logging.getLogger(__name__)


HELPER_COMMANDS = {"probe", "search", "graph", "repair", "repair-memory"}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print_help()
        return 0

    mode = args[0]

    if mode == "skill":
        print_skill_instructions()
        return 0

    if mode == "mcp":
        if len(args) > 1:
            sys.stderr.write("codelevelup-agent mcp does not accept extra arguments.\n")
            return 2
        return _run_mcp()

    if mode == "doctor":
        return _run_doctor(args[1:])

    if mode in HELPER_COMMANDS:
        return _run_cli(args)

    sys.stderr.write(f"Unknown mode: {mode!r}\n\n")
    print_help(stream=sys.stderr)
    return 2


def _run_mcp() -> int:
    from codelevelup import mcp_server
    return mcp_server.main()


def _run_cli(args: list[str]) -> int:
    from codelevelup.cli import main as cli_main
    sys.argv = ["codelevelup-agent", *args]
    return cli_main()


def _run_doctor(cli_args: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Inspect the CodeLevelUp agent entry layer.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    parsed = parser.parse_args(cli_args)

    payload: dict[str, Any] = {
        "entrypoint": "codelevelup-agent",
        "skill_first": True,
        "modes": ["skill", "mcp", "doctor"],
        "helper_commands": sorted(HELPER_COMMANDS),
        "python_required_for": ["mcp"],
        "skill_reference": "skills/codelevelup/references/agent-entry-layer.md",
        "recommended_mcp_args": ["mcp"],
        "fallback": (
            "If Python is unavailable, keep using the agent skill: read skills/codelevelup/SKILL.md, "
            "read skills/codelevelup/references/agent-entry-layer.md, then inspect files with git, rg, "
            "and project-native verification commands. Store run artifacts under the target repository's "
            ".codelevelup directory when the task needs a durable local trace."
        ),
    }
    if parsed.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("CodeLevelUp agent entry layer")
        print("Skill-first: yes")
        print("Modes: " + ", ".join(["skill", "mcp", "doctor"]))
        print("Helper commands: " + ", ".join(sorted(HELPER_COMMANDS)))
        print("Python required for: mcp, " + ", ".join(sorted(HELPER_COMMANDS)))
        print("Reference: skills/codelevelup/references/agent-entry-layer.md")
    return 0


def print_skill_instructions() -> None:
    print("Skill-only mode — no Python runtime required.")
    print("1. Read skills/codelevelup/SKILL.md")
    print("2. Read skills/codelevelup/references/agent-entry-layer.md")
    print("3. Choose a workflow reference from the SKILL.md entry section")
    print("4. Use git, rg, file reads, and project-native verification commands")
    print("   Store durable artifacts under .codelevelup/ in the target repo")


def print_help(stream=sys.stdout) -> None:
    stream.write(
        "Usage: codelevelup-agent <mode> [args]\n\n"
        "Modes:\n"
        "  skill            Print skill entry instructions (no Python required).\n"
        "  mcp              Run the stdio MCP server for agent clients.\n"
        "  doctor           Describe available modes and capabilities.\n"
        "  probe <root>     Inspect project ecosystems and graph state.\n"
        "  search <root> <query>  Search local source files.\n"
        "  graph build <root>     Build the local code graph.\n"
        "  graph query <root> <q> Query the code graph.\n"
        "  repair <cmds>   Run iterative test-verify-fix loop.\n"
        "  repair-memory record|search|stats|verify  Persistent repair memory.\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())
