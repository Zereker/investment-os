#!/usr/bin/env python3
"""One-shot migration: remove retired release assertions and restore one direct checker."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "scripts" / "check_policy_consistency_legacy.py"
DIRECT = ROOT / "scripts" / "check_policy_consistency.py"
GOVERNANCE = ROOT / "scripts" / "check_release_governance.py"

source = LEGACY.read_text(encoding="utf-8")
tree = ast.parse(source)
remove_lines: set[int] = set()
removed_calls = 0
removed_tuple_items = 0

for node in ast.walk(tree):
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        call = node.value
        if (
            isinstance(call.func, ast.Name)
            and call.func.id in {"require", "forbid"}
            and call.args
            and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, str)
            and call.args[0].value.startswith("07-Releases/")
        ):
            remove_lines.update(range(node.lineno, node.end_lineno + 1))
            removed_calls += 1

    if isinstance(node, ast.Tuple):
        for item in node.elts:
            if (
                isinstance(item, ast.Constant)
                and isinstance(item.value, str)
                and item.value.startswith("07-Releases/")
            ):
                remove_lines.update(range(item.lineno, item.end_lineno + 1))
                removed_tuple_items += 1

if (removed_calls, removed_tuple_items) != (8, 1):
    raise SystemExit(
        f"expected to remove 8 retired calls and 1 tuple item; got "
        f"{removed_calls} calls and {removed_tuple_items} tuple items"
    )

lines = source.splitlines()
cleaned = "\n".join(
    line for lineno, line in enumerate(lines, 1) if lineno not in remove_lines
) + "\n"

if "07-Releases/" in cleaned:
    raise SystemExit("retired release path remains after direct-source cleanup")

DIRECT.write_text(cleaned, encoding="utf-8")
LEGACY.unlink()

text = GOVERNANCE.read_text(encoding="utf-8")
anchor = '    release_dir = ROOT / "07-Releases"\n'
checks = '''    legacy_checker = ROOT / "scripts" / "check_policy_consistency_legacy.py"\n    if legacy_checker.exists():\n        raise AssertionError("legacy policy checker must not exist")\n\n    checker = (ROOT / "scripts" / "check_policy_consistency.py").read_text(encoding="utf-8")\n    for forbidden in ("ast.NodeTransformer", "exec(compile", "check_policy_consistency_legacy.py"):\n        if forbidden in checker:\n            raise AssertionError(f"policy checker must execute directly; found {forbidden!r}")\n\n'''
if checks not in text:
    if anchor not in text:
        raise SystemExit("release governance insertion anchor not found")
    text = text.replace(anchor, checks + anchor, 1)
    GOVERNANCE.write_text(text, encoding="utf-8")

print("Flattened policy checker: removed 8 calls and 1 tuple item.")
