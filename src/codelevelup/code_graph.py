"""Build and query CodeLevelUp's local code graph."""

from __future__ import annotations

import ast
import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


STATE_DIR = ".codelevelup"
GRAPH_DIR = ".codelevelup/graph"

EXCLUDED_DIRS: set[str] = {
    ".codelevelup",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}

TEXT_SUFFIXES: set[str] = {
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


def build_code_graph(root: Path) -> dict[str, Any]:
    """Build a lightweight local code graph and persist it under `.codelevelup/graph`."""
    root = root.resolve()
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_nodes: set[str] = set()
    seen_edges: set[tuple[str, str, str]] = set()

    file_count = 0
    for path in iter_searchable_files(root):
        file_count += 1
        rel = path.relative_to(root).as_posix()
        file_id = f"file:{rel}"
        add_node(seen_nodes, nodes, {"id": file_id, "type": "File", "path": rel, "name": path.name})
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            logger.debug("Skipping binary file: %s", rel)
            continue

        if path.suffix == ".py":
            add_python_graph(path, rel, text, seen_nodes, nodes, seen_edges, edges)
        elif path.name == "package.json":
            add_package_json_graph(file_id, text, seen_nodes, nodes, seen_edges, edges)
        elif path.name in {"pyproject.toml", "requirements.txt", "go.mod", "Cargo.toml"}:
            add_manifest_node(file_id, path.name, rel, seen_nodes, nodes)
        else:
            add_text_symbol_graph(file_id, rel, text, seen_nodes, nodes, seen_edges, edges)

    logger.info("Code graph built: %d files, %d nodes, %d edges", file_count, len(nodes), len(edges))
    graph = {
        "root": str(root),
        "state_dir": STATE_DIR,
        "graph_dir": GRAPH_DIR,
        "nodes": nodes,
        "edges": edges,
    }
    write_graph(root, graph)
    return graph


def query_code_graph(root: Path, query: str, limit: int = 50) -> dict[str, Any]:
    """Query graph nodes by name, path, package, or import string."""
    root = root.resolve()
    graph = read_graph(root)
    if graph is None:
        graph = build_code_graph(root)

    needle = query.lower()
    matches: list[dict[str, Any]] = []
    for node in graph["nodes"]:
        haystack = " ".join(
            str(node.get(key, "")) for key in ("id", "type", "name", "path", "package", "module")
        ).lower()
        if needle not in haystack:
            continue
        matches.append(
            {
                "id": node["id"],
                "type": node["type"],
                "name": node.get("name"),
                "path": node.get("path"),
                "line": node.get("line"),
            }
        )
        if len(matches) >= limit:
            break

    return {
        "root": str(root),
        "query": query,
        "state_dir": STATE_DIR,
        "graph_dir": GRAPH_DIR,
        "matches": matches,
        "truncated": len(matches) >= limit,
    }


def read_graph(root: Path) -> dict[str, Any] | None:
    graph_path = root.resolve() / GRAPH_DIR / "graph.json"
    if not graph_path.exists():
        return None
    try:
        return json.loads(graph_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def write_graph(root: Path, graph: dict[str, Any]) -> None:
    graph_dir = root.resolve() / GRAPH_DIR
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / "graph.json").write_text(json.dumps(graph, indent=2, sort_keys=True), encoding="utf-8")


def iter_searchable_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        if path.suffix and path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        yield path


def add_python_graph(
    path: Path,
    rel: str,
    text: str,
    seen_nodes: set[str],
    nodes: list[dict[str, Any]],
    seen_edges: set[tuple[str, str, str]],
    edges: list[dict[str, Any]],
) -> None:
    file_id = f"file:{rel}"
    try:
        tree = ast.parse(text)
    except SyntaxError:
        add_text_symbol_graph(file_id, rel, text, seen_nodes, nodes, seen_edges, edges)
        return

    # First pass: collect all top-level names for CALLS resolution.
    file_symbols: dict[str, str] = {}
    for item in tree.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            file_symbols[item.name] = f"symbol:{rel}:{item.name}:{item.lineno}"
        elif isinstance(item, ast.ClassDef):
            class_id = f"symbol:{rel}:{item.name}:{item.lineno}"
            file_symbols[item.name] = class_id
            for method in item.body:
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    file_symbols[method.name] = f"symbol:{rel}:{method.name}:{method.lineno}"

    # Second pass: emit nodes and edges.
    for item in tree.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbol_id = f"symbol:{rel}:{item.name}:{item.lineno}"
            add_node(
                seen_nodes,
                nodes,
                {"id": symbol_id, "type": "Function", "name": item.name, "path": rel, "line": item.lineno},
            )
            add_edge(seen_edges, edges, file_id, "defines", symbol_id)
            _add_call_edges(item, symbol_id, file_symbols, seen_edges, edges)
        elif isinstance(item, ast.ClassDef):
            class_id = f"symbol:{rel}:{item.name}:{item.lineno}"
            add_node(
                seen_nodes,
                nodes,
                {"id": class_id, "type": "Class", "name": item.name, "path": rel, "line": item.lineno},
            )
            add_edge(seen_edges, edges, file_id, "defines", class_id)
            for method in item.body:
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_id = f"symbol:{rel}:{method.name}:{method.lineno}"
                    add_node(
                        seen_nodes,
                        nodes,
                        {
                            "id": method_id,
                            "type": "Method",
                            "name": method.name,
                            "path": rel,
                            "line": method.lineno,
                        },
                    )
                    add_edge(seen_edges, edges, class_id, "has_method", method_id)
                    _add_call_edges(method, method_id, file_symbols, seen_edges, edges)
        elif isinstance(item, ast.Import):
            for alias in item.names:
                add_import_edge(file_id, alias.name, seen_nodes, nodes, seen_edges, edges)
        elif isinstance(item, ast.ImportFrom) and item.module:
            add_import_edge(file_id, item.module, seen_nodes, nodes, seen_edges, edges)


def _add_call_edges(
    node: ast.AST,
    parent_id: str,
    file_symbols: dict[str, str],
    seen_edges: set[tuple[str, str, str]],
    edges: list[dict[str, Any]],
) -> None:
    """Walk an AST subtree and emit CALLS edges for known symbols."""
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Name):
            callee = func.id
        elif isinstance(func, ast.Attribute):
            callee = func.attr
        else:
            continue
        if callee in file_symbols:
            add_edge(seen_edges, edges, parent_id, "calls", file_symbols[callee])


def add_text_symbol_graph(
    file_id: str,
    rel: str,
    text: str,
    seen_nodes: set[str],
    nodes: list[dict[str, Any]],
    seen_edges: set[tuple[str, str, str]],
    edges: list[dict[str, Any]],
) -> None:
    symbol_pattern = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?(?:function|class)\s+([A-Za-z_][\w]*)")
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = symbol_pattern.search(line)
        if not match:
            continue
        name = match.group(1)
        symbol_id = f"symbol:{rel}:{name}:{line_number}"
        add_node(
            seen_nodes,
            nodes,
            {
                "id": symbol_id,
                "type": "Symbol",
                "name": name,
                "path": rel,
                "line": line_number,
            },
        )
        add_edge(seen_edges, edges, file_id, "defines", symbol_id)


def add_package_json_graph(
    file_id: str,
    text: str,
    seen_nodes: set[str],
    nodes: list[dict[str, Any]],
    seen_edges: set[tuple[str, str, str]],
    edges: list[dict[str, Any]],
) -> None:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return
    for bucket in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        values = data.get(bucket, {})
        if not isinstance(values, dict):
            continue
        for package, version in values.items():
            dep_id = f"package:{package}"
            add_node(
                seen_nodes,
                nodes,
                {
                    "id": dep_id,
                    "type": "Package",
                    "name": package,
                    "package": package,
                    "version": version,
                },
            )
            add_edge(seen_edges, edges, file_id, "depends_on", dep_id)


def add_manifest_node(
    file_id: str,
    name: str,
    rel: str,
    seen_nodes: set[str],
    nodes: list[dict[str, Any]],
) -> None:
    add_node(
        seen_nodes,
        nodes,
        {"id": f"manifest:{rel}", "type": "Manifest", "name": name, "path": rel, "file": file_id},
    )


def add_import_edge(
    file_id: str,
    module: str,
    seen_nodes: set[str],
    nodes: list[dict[str, Any]],
    seen_edges: set[tuple[str, str, str]],
    edges: list[dict[str, Any]],
) -> None:
    import_id = f"import:{module}"
    add_node(seen_nodes, nodes, {"id": import_id, "type": "Import", "name": module, "module": module})
    add_edge(seen_edges, edges, file_id, "imports", import_id)


def add_node(seen: set[str], nodes: list[dict[str, Any]], node: dict[str, Any]) -> None:
    if node["id"] in seen:
        return
    seen.add(node["id"])
    nodes.append(node)


def add_edge(
    seen: set[tuple[str, str, str]],
    edges: list[dict[str, Any]],
    source: str,
    edge_type: str,
    target: str,
) -> None:
    key = (source, edge_type, target)
    if key in seen:
        return
    seen.add(key)
    edges.append({"source": source, "type": edge_type, "target": target})
