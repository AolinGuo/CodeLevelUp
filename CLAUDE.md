# CodeLevelUp For Claude

This repository is not Codex-only. Claude can use CodeLevelUp through CLI or
MCP after a local editable install:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## CLI

```bash
codelevelup probe --json /path/to/repo
codelevelup search /path/to/repo "target_symbol" --json
codelevelup gitnexus status /path/to/repo --json
codelevelup gitnexus analyze /path/to/repo --dry-run --json
```

## MCP

Configure Claude Desktop or another MCP client to run:

```bash
/absolute/path/to/CodeLevelUp/.venv/bin/codelevelup-mcp
```

The MCP server exposes:

- `probe_project`
- `search_code`
- `gitnexus_status`
- `gitnexus_analyze_command`

Use these tools before editing when you need local repository orientation,
literal code search, or GitNexus command discovery.
