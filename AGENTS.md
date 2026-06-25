# CodeLevelUp Agent Guide

Use CodeLevelUp as a local upgrade assistant with three portable entrypoints:

- Codex skill: read `SKILL.md` and invoke `$code-level-up`.
- CLI: run `python scripts/codelevelup.py --help` or the installed `codelevelup`.
- MCP: run `python scripts/codelevelup_mcp.py` or the installed
  `codelevelup-mcp` as a stdio MCP server.

Before editing a target repository:

1. Run `python scripts/codelevelup.py probe --json <target-repo>`.
2. Use `python scripts/codelevelup.py search <target-repo> <query> --json` to locate code.
3. If GitNexus is available or desired, inspect `gitnexus status` and run `gitnexus analyze`.
4. Patch one narrow change.
5. Run the detected verification commands.
6. Stage explicit files only and commit with verification evidence.

Do not treat search results or optional index summaries as replacements for
reading the source files involved in the change.
