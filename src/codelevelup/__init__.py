"""CodeLevelUp package exports.

Uses lazy imports to avoid loading unused modules when only a subset
of functionality is needed (e.g., skill-only mode doesn't need MCP).
"""

__all__ = [
    "build_code_graph",
    "format_repair_hints",
    "load_repairs",
    "mark_verified",
    "probe_project",
    "query_code_graph",
    "record_repair",
    "repair_loop",
    "repair_loop_report",
    "repair_stats",
    "save_repairs",
    "search_code",
    "search_repairs",
    "search_repairs_by_type",
]

_LAZY_IMPORTS: dict[str, str] = {
    "probe_project": "codelevelup.probe",
    "build_code_graph": "codelevelup.code_graph",
    "query_code_graph": "codelevelup.code_graph",
    "search_code": "codelevelup.cli",
    "repair_loop": "codelevelup.repair_loop",
    "repair_loop_report": "codelevelup.repair_loop",
    "record_repair": "codelevelup.repair_memory",
    "load_repairs": "codelevelup.repair_memory",
    "save_repairs": "codelevelup.repair_memory",
    "mark_verified": "codelevelup.repair_memory",
    "search_repairs": "codelevelup.repair_memory",
    "search_repairs_by_type": "codelevelup.repair_memory",
    "format_repair_hints": "codelevelup.repair_memory",
    "repair_stats": "codelevelup.repair_memory",
}


def __getattr__(name: str) -> object:
    if name in _LAZY_IMPORTS:
        import importlib
        module = importlib.import_module(_LAZY_IMPORTS[name])
        return getattr(module, name)
    raise AttributeError(f"module 'codelevelup' has no attribute {name!r}")
