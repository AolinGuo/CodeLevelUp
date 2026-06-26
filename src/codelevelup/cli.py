#!/usr/bin/env python3
"""Internal CodeLevelUp helper for repository probing, fallback search, and graph operations."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from .code_graph import EXCLUDED_DIRS, TEXT_SUFFIXES, build_code_graph, query_code_graph
from .probe import probe_project
from .repair_loop import repair_loop as _repair_loop, repair_loop_report
from .repair_memory import (
    format_repair_hints,
    load_repairs,
    mark_verified,
    record_repair,
    repair_stats,
    search_repairs,
    search_repairs_by_type,
)


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    probe_parser = subparsers.add_parser("probe", help="Inspect project commands and graph state.")
    probe_parser.add_argument("root", nargs="?", default=".", help="Target repository root.")
    probe_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    search_parser = subparsers.add_parser("search", help="Search local source files.")
    search_parser.add_argument("root", help="Target repository root.")
    search_parser.add_argument("query", help="Literal query string.")
    search_parser.add_argument("--limit", type=int, default=50, help="Maximum matches.")
    search_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    graph_parser = subparsers.add_parser("graph", help="Build or query the internal local code graph.")
    graph_subparsers = graph_parser.add_subparsers(dest="graph_command", required=True)

    graph_build_parser = graph_subparsers.add_parser("build", help="Build the local code graph.")
    graph_build_parser.add_argument("root", nargs="?", default=".", help="Target repository root.")
    graph_build_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    graph_query_parser = graph_subparsers.add_parser("query", help="Query the local code graph.")
    graph_query_parser.add_argument("root", help="Target repository root.")
    graph_query_parser.add_argument("query", help="Query string.")
    graph_query_parser.add_argument("--limit", type=int, default=50, help="Maximum matches.")
    graph_query_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    repair_parser = subparsers.add_parser("repair", help="Iterative test-verify-fix repair loop.")
    repair_parser.add_argument("commands", nargs="+", help="Verification commands to run.")
    repair_parser.add_argument("--cwd", default=".", help="Target repository root.")
    repair_parser.add_argument("--language", default="python", help="Language hint.")
    repair_parser.add_argument("--max-retries", type=int, default=5, help="Maximum repair rounds.")
    repair_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    repair_memory_parser = subparsers.add_parser("repair-memory", help="Cross-project repair memory.")
    rm_sub = repair_memory_parser.add_subparsers(dest="rm_command", required=True)

    rm_record = rm_sub.add_parser("record", help="Record a failure-repair pair.")
    rm_record.add_argument("--root", default=".", help="Repository root.")
    rm_record.add_argument("--error-type", required=True, help="Error type.")
    rm_record.add_argument("--message", required=True, help="Error message.")
    rm_record.add_argument("--fix", required=True, help="What was changed to fix it.")
    rm_record.add_argument("--files", required=True, help="Comma-separated changed files.")
    rm_record.add_argument("--round", type=int, required=True, help="Repair round number.")
    rm_record.add_argument("--language", default="python", help="Language.")
    rm_record.add_argument("--metadata", default="", help="Extra JSON metadata.")
    rm_record.add_argument("--json", action="store_true")

    rm_search = rm_sub.add_parser("search", help="Search past repairs.")
    rm_search.add_argument("--root", default=".", help="Repository root.")
    rm_search.add_argument("--error-type", required=True, help="Error type.")
    rm_search.add_argument("--message", default="", help="Error message.")
    rm_search.add_argument("--limit", type=int, default=5)
    rm_search.add_argument("--json", action="store_true")

    rm_stats = rm_sub.add_parser("stats", help="Repair memory statistics.")
    rm_stats.add_argument("--root", default=".", help="Repository root.")
    rm_stats.add_argument("--json", action="store_true")

    rm_verify = rm_sub.add_parser("verify", help="Mark a repair as verified.")
    rm_verify.add_argument("--root", default=".", help="Repository root.")
    rm_verify.add_argument("--id", type=int, required=True, help="Repair entry ID.")
    rm_verify.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if args.command == "probe":
        return emit(probe_project(Path(args.root)), args.json)
    if args.command == "search":
        return emit(search_code(Path(args.root), args.query, args.limit), args.json)
    if args.command == "graph" and args.graph_command == "build":
        return emit(build_code_graph(Path(args.root)), args.json)
    if args.command == "graph" and args.graph_command == "query":
        return emit(query_code_graph(Path(args.root), args.query, args.limit), args.json)
    if args.command == "repair":
        result = _repair_loop(
            commands=args.commands,
            cwd=Path(args.cwd),
            language=args.language,
            max_retries=args.max_retries,
        )
        report = repair_loop_report(result)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            if result.passed:
                print(f"PASS after {result.total_rounds} verification round(s).")
            else:
                print(f"FAIL after {result.total_rounds} round(s): {result.stop_reason}")
                for fr in result.rounds:
                    print(f"  Round {fr.round}: {fr.error_type} in {fr.file}:{fr.line}")
                    print(f"    {fr.message}")
                    print(f"    Suggestion: {fr.suggestion}")
        return 0 if result.passed else 1
    if args.command == "repair-memory":
        target_root = Path(args.root)
        if args.rm_command == "record":
            meta = {}
            if args.metadata:
                try:
                    meta = json.loads(args.metadata)
                except json.JSONDecodeError:
                    pass
            entry = record_repair(
                root=target_root,
                error_type=args.error_type,
                message=args.message,
                fix_description=args.fix,
                changed_files=[f.strip() for f in args.files.split(",") if f.strip()],
                round_number=args.round,
                language=args.language,
                metadata=meta,
            )
            _emit_repair(entry, args.json, "recorded")
            return 0
        if args.rm_command == "search":
            results = search_repairs(target_root, args.error_type, args.message, args.limit)
            _emit_repair({"results": results, "count": len(results)}, args.json, "search")
            return 0
        if args.rm_command == "stats":
            _emit_repair(repair_stats(target_root), args.json, "stats")
            return 0
        if args.rm_command == "verify":
            entry = mark_verified(target_root, args.id)
            if entry:
                _emit_repair(entry, args.json, "verified")
                return 0
            _emit_repair({"error": f"repair id {args.id} not found"}, args.json, "error")
            return 1
    parser.error("unsupported command")
    return 2


def emit(payload: dict[str, Any], as_json: bool) -> int:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_human(payload)
    return 0


def _emit_repair(payload: Any, as_json: bool, label: str) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if isinstance(payload, dict) and "results" in payload:
            print(f"{label}: {payload['count']} repair(s) found")
            for r in payload["results"]:
                status = "verified" if r.get("verified") else "unverified"
                print(f"  #{r['id']} {r['error_type']} (round {r.get('round_number', '?')}, {status}): {r['fix_description']}")
        elif isinstance(payload, dict) and "total" in payload:
            print(f"{label}: {payload['total']} total, {payload['verified']} verified, {payload['unverified']} unverified")
        else:
            print(f"{label}: {payload}")


def print_human(payload: dict[str, Any]) -> None:
    if "matches" in payload:
        for match in payload["matches"]:
            print(f"{match['path']}:{match['line']}: {match['text']}")
        return
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
