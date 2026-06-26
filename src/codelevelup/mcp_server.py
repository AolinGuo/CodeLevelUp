#!/usr/bin/env python3
"""Minimal stdio MCP server for CodeLevelUp local tools."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional

from .cli import search_code
from .code_graph import build_code_graph, query_code_graph
from .probe import probe_project
from .repair_loop import repair_loop, repair_loop_report
from .repair_memory import (
    format_repair_hints,
    record_repair,
    repair_stats,
    search_repairs,
)


TOOLS = [
    {
        "name": "probe_project",
        "description": "Inspect project ecosystems, verification commands, security commands, and CodeLevelUp graph state.",
        "inputSchema": {
            "type": "object",
            "properties": {"root": {"type": "string"}},
            "required": ["root"],
        },
    },
    {
        "name": "search_code",
        "description": "Search local source files with a literal query string as a fallback locator.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string"},
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
            },
            "required": ["root", "query"],
        },
    },
    {
        "name": "build_code_graph",
        "description": "Build a local CodeLevelUp code graph under the target repository's .codelevelup directory.",
        "inputSchema": {
            "type": "object",
            "properties": {"root": {"type": "string"}},
            "required": ["root"],
        },
    },
    {
        "name": "query_code_graph",
        "description": "Query the local CodeLevelUp code graph for symbols, files, imports, or packages.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string"},
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
            },
            "required": ["root", "query"],
        },
    },
    {
        "name": "repair_loop",
        "description": "Run verification commands in an iterative loop, reporting structured failures with file/line/suggestion. Does NOT modify code — reports failures so the Agent can propose patches.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string", "description": "Target repository root."},
                "commands": {"type": "array", "items": {"type": "string"}, "description": "Verification commands to run."},
                "language": {"type": "string", "default": "python", "description": "Language hint for failure parsing."},
                "max_retries": {"type": "integer", "default": 5, "description": "Maximum repair rounds."},
            },
            "required": ["root", "commands"],
        },
    },
    {
        "name": "record_repair",
        "description": "Record a failure-repair pair to the persistent repair memory under .codelevelup/repairs.json.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string"},
                "error_type": {"type": "string"},
                "message": {"type": "string"},
                "fix": {"type": "string"},
                "files": {"type": "string"},
                "round": {"type": "integer"},
                "language": {"type": "string", "default": "python"},
            },
            "required": ["root", "error_type", "message", "fix", "files", "round"],
        },
    },
    {
        "name": "search_repairs",
        "description": "Search persistent repair memory for similar past failures.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string"},
                "error_type": {"type": "string"},
                "message": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["root", "error_type"],
        },
    },
    {
        "name": "repair_hints",
        "description": "Get formatted repair memory hints for a given error type and message. Returns human-readable hints for the Agent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string"},
                "error_type": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["root", "error_type"],
        },
    },
    {
        "name": "repair_stats",
        "description": "Get aggregate statistics about stored repairs (total, verified, by error type, by language).",
        "inputSchema": {
            "type": "object",
            "properties": {"root": {"type": "string"}},
            "required": ["root"],
        },
    },
]


_PROGRESS_SUPPORTED_TOOLS = {"build_code_graph", "repair_loop"}


def _send_progress(progress_token: Any, current: int, total: int, message: str = "") -> None:
    notification = {
        "jsonrpc": "2.0",
        "method": "notifications/progress",
        "params": {
            "progressToken": progress_token,
            "progress": current,
            "total": total,
        },
    }
    if message:
        notification["params"]["message"] = message
    sys.stdout.write(json.dumps(notification) + "\n")
    sys.stdout.flush()


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        request = json.loads(line)
        response = handle_request(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
    return 0


def handle_request(request: dict[str, Any]) -> Optional[dict[str, Any]]:
    method = request.get("method")
    request_id = request.get("id")
    try:
        if method == "initialize":
            requested_protocol = request.get("params", {}).get("protocolVersion")
            protocol = requested_protocol if requested_protocol else "2025-06-18"
            return result(
                request_id,
                {
                    "protocolVersion": protocol,
                    "serverInfo": {"name": "CodeLevelUp", "version": "0.1.0"},
                    "capabilities": {"tools": {}},
                },
            )
        if method == "tools/list":
            return result(request_id, {"tools": TOOLS})
        if method == "tools/call":
            params = request.get("params", {})
            return result(request_id, call_tool(params.get("name"), params.get("arguments", {})))
        if method == "notifications/initialized":
            return None
        return error(request_id, -32601, f"Unsupported method: {method}")
    except Exception as exc:  # pragma: no cover - defensive MCP boundary
        return error(request_id, -32000, str(exc))


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    progress_token = arguments.get("_progressToken")
    root = Path(arguments.get("root", "."))
    if name == "probe_project":
        payload = probe_project(root)
    elif name == "search_code":
        payload = search_code(root, arguments["query"], int(arguments.get("limit", 50)))
    elif name == "build_code_graph":
        if progress_token:
            _send_progress(progress_token, 0, 100, "Building code graph...")
        payload = build_code_graph(root)
        if progress_token:
            _send_progress(progress_token, 100, 100, "Code graph complete")
    elif name == "query_code_graph":
        payload = query_code_graph(root, arguments["query"], int(arguments.get("limit", 50)))
    elif name == "repair_loop":
        max_retries = int(arguments.get("max_retries", 5))
        if progress_token:
            _send_progress(progress_token, 0, max_retries, "Starting repair loop...")
        result = repair_loop(
            commands=arguments["commands"],
            cwd=root,
            language=arguments.get("language", "python"),
            max_retries=max_retries,
        )
        payload = repair_loop_report(result)
        if progress_token:
            _send_progress(progress_token, max_retries, max_retries,
                           "Repair loop complete: " + ("passed" if result.passed else "failed"))
    elif name == "record_repair":
        payload = record_repair(
            root=root,
            error_type=arguments["error_type"],
            message=arguments["message"],
            fix_description=arguments["fix"],
            changed_files=[f.strip() for f in arguments["files"].split(",") if f.strip()],
            round_number=int(arguments["round"]),
            language=arguments.get("language", "python"),
        )
    elif name == "search_repairs":
        payload = {
            "results": search_repairs(
                root,
                arguments["error_type"],
                arguments.get("message", ""),
                int(arguments.get("limit", 5)),
            )
        }
    elif name == "repair_hints":
        payload = {"hints": format_repair_hints(root, arguments["error_type"], arguments.get("message", ""))}
    elif name == "repair_stats":
        payload = repair_stats(root)
    else:
        raise ValueError(f"Unknown tool: {name}")
    return {"content": [{"type": "text", "text": json.dumps(payload, indent=2, sort_keys=True)}]}


def result(request_id: Any, payload: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": payload}


def error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


if __name__ == "__main__":
    raise SystemExit(main())
