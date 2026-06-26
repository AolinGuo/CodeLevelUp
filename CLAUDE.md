# CodeLevelUp For Claude

Claude should use CodeLevelUp as a skill-first project:

1. Read `AGENT_GUIDE.md`.
2. Read `skills/codelevelup/SKILL.md`.
3. Read `skills/codelevelup/references/agent-entry-layer.md`.
4. Use skill-only mode by default, or run `codelevelup-agent mcp` when an MCP
   client is configured.

Optional local helper install:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e . --no-deps --no-build-isolation
codelevelup-agent doctor --json
```

The MCP server exposes project probing, local code graph build/query, and
fallback source search tools. Treat those tools as internal accelerators behind
the skill, not as user-facing commands.
