#!/usr/bin/env python3
from pathlib import Path

path = Path(__file__).resolve().parent / "check_policy_consistency.py"
text = path.read_text(encoding="utf-8")

broken_one = '''    # git history was rebuilt to a single commit: no document may send readers there\n        forbid(path, "查 git 历史")\n'''
fixed_one = '''    # git history was rebuilt to a single commit: no document may send readers there\n    for path in ("README.md", "CLAUDE.md"):\n        forbid(path, "查 git 历史")\n'''

broken_two = '''    frozen_state = re.compile(r"A_actual[^。\\n]{0,12}?(?:约|≈|大约)\\s*\\d+(?:\\.\\d+)?\\s*%")\n                 "Decision-Log.md", "01-Constitution/Target-Allocation.md"):\n'''
fixed_two = '''    frozen_state = re.compile(r"A_actual[^。\\n]{0,12}?(?:约|≈|大约)\\s*\\d+(?:\\.\\d+)?\\s*%")\n    for path in ("04-Alpha/Position-Registry.md",\n                 "Decision-Log.md", "01-Constitution/Target-Allocation.md"):\n'''

for broken, fixed in ((broken_one, fixed_one), (broken_two, fixed_two)):
    if broken not in text:
        raise SystemExit("expected broken direct-source fragment not found")
    text = text.replace(broken, fixed, 1)

if "07-Releases/" in text:
    raise SystemExit("retired release path remains in direct checker")

compile(text, str(path), "exec")
path.write_text(text, encoding="utf-8")
print("Repaired direct policy checker loop headers.")
