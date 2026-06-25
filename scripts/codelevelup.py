#!/usr/bin/env python3
"""CodeLevelUp local CLI for repository probing, code search, and GitNexus commands."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

try:
    from probe_project import probe_project
except ModuleNotFoundError:  # pragma: no cover - package import path
    from .probe_project import probe_project


EXCLUDED_DIRS = {
    ".git",
    ".gitnexus",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}

TEXT_SUFFIXES = {
    ".c",
    ".cc",
    ".cfg",
    ".cpp",
    ".css",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mjs",
    ".py",
    ".rs",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".vue",
    ".yaml",
    ".yml",
}


def search_code(root: Path, query: str, limit: int = 50) -> dict[str, Any]:
    root = root.resolve()
    matches: list[dict[str, Any]] = []
    for path in iter_searchable_files(root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, start=1):
            if query in line:
                matches.append(
                    {
                        "path": str(path.relative_to(root)),
                        "line": number,
                        "text": line.strip(),
                    }
                )
                if len(matches) >= limit:
                    return {"root": str(root), "query": query, "matches": matches, "truncated": True}
    return {"root": str(root), "query": query, "matches": matches, "truncated": False}


def iter_searchable_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        if path.suffix and path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        yield path


def gitnexus_status(root: Path) -> dict[str, Any]:
    root = root.resolve()
    report = probe_project(root)["gitnexus"]
    if not report["runner_present"]:
        return {
            "root": str(root),
            "runner_present": False,
            "index_present": report["index_present"],
            "bootstrap_command": report["bootstrap_command"],
            "status": "missing_runner",
        }

    result = subprocess.run(
        ["node", ".gitnexus/run.cjs", "status"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "root": str(root),
        "runner_present": True,
        "index_present": report["index_present"],
        "status": "ok" if result.returncode == 0 else "error",
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def gitnexus_analyze(root: Path, pdg: bool = False, dry_run: bool = False) -> dict[str, Any]:
    root = root.resolve()
    command = gitnexus_analyze_command(root, pdg)
    if dry_run:
        return {"root": str(root), "command": " ".join(command), "dry_run": True}

    result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    return {
        "root": str(root),
        "command": " ".join(command),
        "dry_run": False,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def gitnexus_analyze_command(root: Path, pdg: bool = False) -> list[str]:
    runner = root.resolve() / ".gitnexus" / "run.cjs"
    if runner.exists():
        command = ["node", ".gitnexus/run.cjs", "analyze"]
    else:
        command = ["npx", "gitnexus", "analyze"]
    if pdg:
        command.append("--pdg")
    return command


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    probe_parser = subparsers.add_parser("probe", help="Inspect project commands and GitNexus state.")
    probe_parser.add_argument("root", nargs="?", default=".", help="Target repository root.")
    probe_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    search_parser = subparsers.add_parser("search", help="Search local source files.")
    search_parser.add_argument("root", help="Target repository root.")
    search_parser.add_argument("query", help="Literal query string.")
    search_parser.add_argument("--limit", type=int, default=50, help="Maximum matches.")
    search_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    gitnexus_parser = subparsers.add_parser("gitnexus", help="Run or preview GitNexus commands.")
    gitnexus_subparsers = gitnexus_parser.add_subparsers(dest="gitnexus_command", required=True)

    status_parser = gitnexus_subparsers.add_parser("status", help="Check GitNexus index status.")
    status_parser.add_argument("root", nargs="?", default=".", help="Target repository root.")
    status_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    analyze_parser = gitnexus_subparsers.add_parser("analyze", help="Build or refresh GitNexus index.")
    analyze_parser.add_argument("root", nargs="?", default=".", help="Target repository root.")
    analyze_parser.add_argument("--pdg", action="store_true", help="Include PDG layers.")
    analyze_parser.add_argument("--dry-run", action="store_true", help="Only print the command.")
    analyze_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    args = parser.parse_args()
    if args.command == "probe":
        return emit(probe_project(Path(args.root)), args.json)
    if args.command == "search":
        return emit(search_code(Path(args.root), args.query, args.limit), args.json)
    if args.command == "gitnexus" and args.gitnexus_command == "status":
        return emit(gitnexus_status(Path(args.root)), args.json)
    if args.command == "gitnexus" and args.gitnexus_command == "analyze":
        return emit(gitnexus_analyze(Path(args.root), args.pdg, args.dry_run), args.json)
    parser.error("unsupported command")
    return 2


def emit(payload: dict[str, Any], as_json: bool) -> int:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_human(payload)
    return 0


def print_human(payload: dict[str, Any]) -> None:
    if "matches" in payload:
        for match in payload["matches"]:
            print(f"{match['path']}:{match['line']}: {match['text']}")
        return
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
