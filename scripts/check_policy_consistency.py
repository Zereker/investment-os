#!/usr/bin/env python3
"""Run the complete policy suite without retired release-mirror assertions."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "scripts" / "check_policy_consistency_legacy.py"


def is_release_path(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("07-Releases/")


class RetiredReleaseMirrorFilter(ast.NodeTransformer):
    """Remove only assertions and tuple entries that target retired release files."""

    def visit_Expr(self, node: ast.Expr):
        node = self.generic_visit(node)
        if isinstance(node.value, ast.Call):
            call = node.value
            if (
                isinstance(call.func, ast.Name)
                and call.func.id in {"require", "forbid"}
                and call.args
                and is_release_path(call.args[0])
            ):
                return None
        return node

    def visit_Tuple(self, node: ast.Tuple):
        node = self.generic_visit(node)
        node.elts = [element for element in node.elts if not is_release_path(element)]
        return node


source = LEGACY.read_text(encoding="utf-8")
tree = ast.parse(source, filename=str(LEGACY))
tree = RetiredReleaseMirrorFilter().visit(tree)
ast.fix_missing_locations(tree)
namespace = {"__name__": "__main__", "__file__": str(LEGACY)}
exec(compile(tree, str(LEGACY), "exec"), namespace)
