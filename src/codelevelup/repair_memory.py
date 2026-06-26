#!/usr/bin/env python3
"""Persistent cross-project repair memory for CodeLevelUp.

Stores failure-repair pairs under the target repository's
`.codelevelup/repairs.json` so future upgrade runs can retrieve
historical fixes for similar error patterns.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


STATE_DIR = ".codelevelup"
REPAIRS_FILE = ".codelevelup/repairs.json"


def _normalize_error(error_type: str, message: str) -> str:
    """Create a coarse lookup key from error type and message.

    Preserves identifiers (CamelCase/PascalCase names) so that different
    errors like ``cannot import name 'Buffer'`` and ``cannot import name 'Response'``
    produce distinct keys. Version numbers are normalized to VERSION; bare digits
    to N; string literal content to X.
    """
    error_type = re.sub(r"\d+", "N", error_type.strip())
    # Preserve CamelCase / PascalCase identifiers (class names, module names).
    identifier_re = re.compile(r"\b[A-Z][a-zA-Z0-9_]*\b")
    protected: list[str] = []

    def protect_identifiers(m: re.Match) -> str:
        token = f"__IDENT_{len(protected)}__"
        protected.append(m.group(0))
        return token

    message = identifier_re.sub(protect_identifiers, message)
    # Normalize version numbers (e.g. 1.2.3, 0.4.11).
    message = re.sub(r"\b\d+\.\d+(?:\.\d+)?\b", "VERSION", message)
    # Replace string literal content with X.
    message = re.sub(r"'[^']*'", "'X'", message)
    message = re.sub(r'"[^"]*"', '"X"', message)
    # Replace remaining bare numbers.
    message = re.sub(r"\d+", "N", message)
    # Restore preserved identifiers.
    for i, ident in enumerate(protected):
        message = message.replace(f"__IDENT_{i}__", ident)
    message = re.sub(r"\s+", " ", message).strip().lower()
    return f"{error_type}:{message[:120]}"


def repairs_path(root: Path) -> Path:
    return root.resolve() / STATE_DIR / "repairs.json"


def load_repairs(root: Path) -> list[dict[str, Any]]:
    path = repairs_path(root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def save_repairs(root: Path, repairs: list[dict[str, Any]]) -> None:
    path = repairs_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(repairs, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


def record_repair(
    root: Path,
    error_type: str,
    message: str,
    fix_description: str,
    changed_files: list[str],
    round_number: int,
    language: str = "python",
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Record a failure-repair pair.

    Args:
        root: target repository root.
        error_type: error category (e.g., "ImportError").
        message: the error message.
        fix_description: what the Agent changed to fix it.
        changed_files: list of files modified.
        round_number: which repair round this was.
        language: language hint.
        metadata: optional extra fields (verification command, etc.).

    Returns:
        The recorded repair entry dict.
    """
    repairs = load_repairs(root)
    entry = {
        "id": len(repairs) + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "language": language,
        "error_type": error_type,
        "error_message": message,
        "lookup_key": _normalize_error(error_type, message),
        "fix_description": fix_description,
        "changed_files": changed_files,
        "round_number": round_number,
        "verified": False,
    }
    if metadata:
        entry.update(metadata)
    repairs.append(entry)
    save_repairs(root, repairs)
    return entry


def mark_verified(root: Path, repair_id: int) -> Optional[dict[str, Any]]:
    """Mark a repair as verified (verification passed after the fix)."""
    repairs = load_repairs(root)
    for entry in repairs:
        if entry.get("id") == repair_id:
            entry["verified"] = True
            entry["verified_at"] = datetime.now(timezone.utc).isoformat()
            save_repairs(root, repairs)
            return entry
    return None


def search_repairs(root: Path, error_type: str, message: str, limit: int = 5) -> list[dict[str, Any]]:
    """Search for similar past repairs.

    Args:
        root: target repository root.
        error_type: current error type.
        message: current error message.
        limit: max results.

    Returns:
        List of matching repair entries, sorted by recency.
    """
    lookup = _normalize_error(error_type, message)
    repairs = load_repairs(root)
    matches = [r for r in repairs if r.get("lookup_key") == lookup]
    matches.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return matches[:limit]


def search_repairs_by_type(root: Path, error_type: str, limit: int = 5) -> list[dict[str, Any]]:
    """Search for past repairs by error type only (broader match)."""
    repairs = load_repairs(root)
    matches = [r for r in repairs if r.get("error_type", "").lower() == error_type.lower()]
    matches.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return matches[:limit]


def repair_stats(root: Path) -> dict[str, Any]:
    """Get aggregate statistics about stored repairs."""
    repairs = load_repairs(root)
    if not repairs:
        return {"total": 0, "verified": 0, "by_error_type": {}, "by_language": {}}

    by_type: dict[str, int] = {}
    by_lang: dict[str, int] = {}
    verified = 0
    for r in repairs:
        et = r.get("error_type", "unknown")
        lang = r.get("language", "unknown")
        by_type[et] = by_type.get(et, 0) + 1
        by_lang[lang] = by_lang.get(lang, 0) + 1
        if r.get("verified"):
            verified += 1

    return {
        "total": len(repairs),
        "verified": verified,
        "unverified": len(repairs) - verified,
        "by_error_type": dict(sorted(by_type.items(), key=lambda x: -x[1])),
        "by_language": dict(sorted(by_lang.items(), key=lambda x: -x[1])),
    }


def format_repair_hints(root: Path, error_type: str, message: str) -> str:
    """Format repair hints as a human-readable string for the Agent."""
    matches = search_repairs(root, error_type, message)
    if not matches:
        type_matches = search_repairs_by_type(root, error_type)
        if not type_matches:
            return ""
        matches = type_matches

    lines = ["## Repair Memory Hints", ""]
    seen = set()
    for r in matches:
        key = r.get("lookup_key", "")
        if key in seen:
            continue
        seen.add(key)
        status = "verified" if r.get("verified") else "unverified"
        lines.append(f"- **{r['error_type']}** (round {r.get('round_number', '?')}, {status}): {r['fix_description']}")
        if r.get("changed_files"):
            lines.append(f"  Changed: {', '.join(r['changed_files'])}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Cross-project repair memory.")
    sub = parser.add_subparsers(dest="command", required=True)

    record = sub.add_parser("record", help="Record a failure-repair pair.")
    record.add_argument("--root", default=".", help="Repository root.")
    record.add_argument("--error-type", required=True, help="Error type.")
    record.add_argument("--message", required=True, help="Error message.")
    record.add_argument("--fix", required=True, help="What was changed to fix it.")
    record.add_argument("--files", required=True, help="Comma-separated changed files.")
    record.add_argument("--round", type=int, required=True, help="Repair round number.")
    record.add_argument("--language", default="python", help="Language.")
    record.add_argument("--metadata", default="", help="Extra JSON metadata.")
    record.add_argument("--json", action="store_true")

    search = sub.add_parser("search", help="Search past repairs.")
    search.add_argument("--root", default=".", help="Repository root.")
    search.add_argument("--error-type", required=True, help="Error type.")
    search.add_argument("--message", default="", help="Error message.")
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--json", action="store_true")

    stats = sub.add_parser("stats", help="Repair memory statistics.")
    stats.add_argument("--root", default=".", help="Repository root.")
    stats.add_argument("--json", action="store_true")

    verify = sub.add_parser("verify", help="Mark a repair as verified.")
    verify.add_argument("--root", default=".", help="Repository root.")
    verify.add_argument("--id", type=int, required=True, help="Repair entry ID.")
    verify.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "record":
        meta = {}
        if args.metadata:
            try:
                meta = json.loads(args.metadata)
            except json.JSONDecodeError:
                pass
        entry = record_repair(
            root=Path(args.root),
            error_type=args.error_type,
            message=args.message,
            fix_description=args.fix,
            changed_files=[f.strip() for f in args.files.split(",") if f.strip()],
            round_number=args.round,
            language=args.language,
            metadata=meta,
        )
        _emit(entry, args.json, "recorded")
        return 0

    if args.command == "search":
        results = search_repairs(Path(args.root), args.error_type, args.message, args.limit)
        _emit({"results": results, "count": len(results)}, args.json, "search")
        return 0

    if args.command == "stats":
        _emit(repair_stats(Path(args.root)), args.json, "stats")
        return 0

    if args.command == "verify":
        entry = mark_verified(Path(args.root), args.id)
        if entry:
            _emit(entry, args.json, "verified")
            return 0
        _emit({"error": f"repair id {args.id} not found"}, args.json, "error")
        return 1

    parser.error("unsupported command")
    return 2


def _emit(payload: Any, as_json: bool, label: str) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if isinstance(payload, dict) and "results" in payload:
            print(f"{label}: {payload['count']} repair(s) found")
            for r in payload["results"]:
                status = "verified" if r.get("verified") else "unverified"
                print(f"  #{r['id']} {r['error_type']} (round {r.get('round_number', '?')}, {status}): {r['fix_description']}")
        else:
            print(f"{label}: {payload}")


if __name__ == "__main__":
    raise SystemExit(main())
