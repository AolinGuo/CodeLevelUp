#!/usr/bin/env python3
"""Minimal stdio MCP server for CodeLevelUp local tools."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional

try:
    from codelevelup import gitnexus_analyze, gitnexus_status, search_code
    from probe_project import probe_project
except ModuleNotFoundError:  # pragma: no cover - package import path
    from .codelevelup import gitnexus_analyze, gitnexus_status, search_code
    from .probe_project import probe_project


TOOLS = [
    {
        "name": "probe_project",
        "description": "Inspect project ecosystems, verification commands, security commands, and GitNexus state.",
        "inputSchema": {
            "type": "object",
            "properties": {"root": {"type": "string"}},
            "required": ["root"],
        },
    },
    {
        "name": "search_code",
        "description": "Search local source files with a literal query string.",
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
        "name": "gitnexus_status",
        "description": "Check whether GitNexus runner/index exists and run status when available.",
        "inputSchema": {
            "type": "object",
            "properties": {"root": {"type": "string"}},
            "required": ["root"],
        },
    },
    {
        "name": "gitnexus_analyze_command",
        "description": "Return or run the GitNexus analyze command for the target repository.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string"},
                "pdg": {"type": "boolean", "default": False},
                "dry_run": {"type": "boolean", "default": True},
            },
            "required": ["root"],
        },
    },
]


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
    root = Path(arguments.get("root", "."))
    if name == "probe_project":
        payload = probe_project(root)
    elif name == "search_code":
        payload = search_code(root, arguments["query"], int(arguments.get("limit", 50)))
    elif name == "gitnexus_status":
        payload = gitnexus_status(root)
    elif name == "gitnexus_analyze_command":
        payload = gitnexus_analyze(
            root,
            pdg=bool(arguments.get("pdg", False)),
            dry_run=bool(arguments.get("dry_run", True)),
        )
    else:
        raise ValueError(f"Unknown tool: {name}")
    return {"content": [{"type": "text", "text": json.dumps(payload, indent=2, sort_keys=True)}]}


def result(request_id: Any, payload: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": payload}


def error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


if __name__ == "__main__":
    raise SystemExit(main())
