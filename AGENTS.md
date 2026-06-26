# CodeLevelUp Agent Notes

Use CodeLevelUp as a skill-first project.

1. Read `AGENT_GUIDE.md`.
2. Read `skills/codelevelup/SKILL.md`.
3. Read `skills/codelevelup/references/agent-entry-layer.md`.
4. Build or approximate the local code graph before code self-upgrade or
   vulnerability repair.
5. Store durable artifacts under the target repository's `.codelevelup/`
   directory when traceability is needed.
6. Use optional MCP helper tools as implementation details only.

Do not ask users to remember helper commands. Do not run implementation modules
from `src/` directly. Search and graph output are locators; read source files
before editing.
