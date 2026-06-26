# Contributing

CodeLevelUp keeps agent instructions, helper code, tests, and user docs in
separate directories.

Before submitting changes:

```bash
PYTHONPATH=src python -m unittest discover -s tests
python tools/verify_skill_structure.py
```

When editing the skill, update `skills/codelevelup/SKILL.md` and its references.
Keep the root `SKILL.md` as a short compatibility shim.
