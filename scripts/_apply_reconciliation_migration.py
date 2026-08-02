#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"expected block not found in {path}: {old[:80]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


# Daily uses the shared physical reconciliation.
replace(
    "scripts/daily_brief.py",
    "from decision_packet import DecisionPacket, assert_renderer_preserves\nfrom monthly_execution import TIERS, compute\n",
    "from account_reconciliation import reconcile_nav\nfrom decision_packet import DecisionPacket, assert_renderer_preserves\nfrom monthly_execution import TIERS, compute\n",
)
replace(
    "scripts/daily_brief.py",
    '    reconciliation = abs((p["cash"] + sum(positions.values())) - nav) / nav\n\n    blockers = [name for name, ok in p["account_inputs"].items() if not ok]\n    if reconciliation > 0.005:\n        blockers.append("account reconciliation exceeds 0.5% of NAV")\n',
    '    reconciliation_result = reconcile_nav(nav, p["cash"], positions.values())\n    reconciliation = reconciliation_result.relative_difference\n\n    blockers = [name for name, ok in p["account_inputs"].items() if not ok]\n    if not reconciliation_result.passed:\n        blockers.append(reconciliation_result.issue or "account reconciliation failed")\n',
)

# Monthly must prove physical state and order state before any calculation.
replace(
    "scripts/monthly_execution.py",
    "from datetime import date\n",
    "from datetime import date\n\nfrom account_reconciliation import reconcile_nav\n",
)
replace(
    "scripts/monthly_execution.py",
    '    ap.add_argument("--lookthrough-current", action="store_true",\n                    help="当季 LOOKTHROUGH_CHECK 核查有效。不传即视为无效，SOXX 回补冻结")\n',
    '    ap.add_argument("--lookthrough-current", action="store_true",\n                    help="当季 LOOKTHROUGH_CHECK 核查有效。不传即视为无效，SOXX 回补冻结")\n    ap.add_argument("--open-orders-status", choices=("clear", "conflicting", "unknown"), default="unknown",\n                    help="权威订单核查结果；只有 clear 允许月度候选，省略即 unknown 并失败关闭")\n',
)
replace(
    "scripts/monthly_execution.py",
    '    if args.dd is not None and not (0.0 <= args.dd < 1.0):\n        print(\n            "DATA INCOMPLETE: --dd 必须使用小数且范围为 [0, 1)；例如 1.68% 应传 0.0168",\n            file=sys.stderr,\n        )\n        return 2\n\n    today = date.fromisoformat(args.today) if args.today else date.today()\n',
    '    if args.dd is not None and not (0.0 <= args.dd < 1.0):\n        print(\n            "DATA INCOMPLETE: --dd 必须使用小数且范围为 [0, 1)；例如 1.68% 应传 0.0168",\n            file=sys.stderr,\n        )\n        return 2\n    reconciliation = reconcile_nav(args.nav, args.cash, (args.spym, args.qqqm, args.soxx))\n    if not reconciliation.passed:\n        print(f"DATA INCOMPLETE: {reconciliation.issue}", file=sys.stderr)\n        return 2\n    if args.open_orders_status != "clear":\n        print(\n            f"DATA INCOMPLETE: open orders status is {args.open_orders_status}; "\n            "must be clear before monthly candidates",\n            file=sys.stderr,\n        )\n        return 2\n\n    today = date.fromisoformat(args.today) if args.today else date.today()\n',
)
replace(
    "scripts/monthly_execution.py",
    '        ("A_execution_cap 未变动（变动即属提高倾斜，须完整 IC）", True),\n',
    '        ("A_execution_cap 未变动（变动即属提高倾斜，须完整 IC）", True),\n        ("没有重复或冲突订单", inp.get("open_orders_status") == "clear"),\n',
)

# Existing CLI tests must explicitly prove the order gate is clear.
for path in ("tests/test_monthly_contribution_cli.py", "tests/test_monthly_dd_cli.py"):
    replace(
        path,
        '"--tiers-executed", "none",',
        '"--tiers-executed", "none", "--open-orders-status", "clear",',
    )

# Broker Runtime computes reconciliation instead of trusting a self-declared PASS.
replace(
    "scripts/broker_runtime.py",
    "from typing import Any, Iterable\n",
    "from typing import Any, Iterable\n\nfrom account_reconciliation import reconcile_nav\n",
)
insert = '''\n\ndef _number(value: Any) -> float | None:\n    if isinstance(value, bool) or not isinstance(value, (int, float)):\n        return None\n    return float(value)\n\n\ndef _position_values(value: Any) -> list[float] | None:\n    if isinstance(value, dict):\n        result = []\n        for item in value.values():\n            number = _number(item if not isinstance(item, dict) else item.get("market_value"))\n            if number is None:\n                return None\n            result.append(number)\n        return result\n    if isinstance(value, list):\n        result = []\n        for item in value:\n            if not isinstance(item, dict):\n                return None\n            number = _number(item.get("market_value", item.get("marketValue")))\n            if number is None:\n                return None\n            result.append(number)\n        return result\n    return None\n'''
replace(
    "scripts/broker_runtime.py",
    "\n\ndef validate_runtime(\n",
    insert + "\n\ndef validate_runtime(\n",
)
replace(
    "scripts/broker_runtime.py",
    '    reconciliation = runtime.get("reconciliation")\n    if not isinstance(reconciliation, dict):\n        issues.append("reconciliation must be an object")\n    else:\n        if reconciliation.get("status") != "PASS":\n            issues.append("reconciliation status is not PASS")\n        declared = reconciliation.get("issues", [])\n        if declared:\n            issues.extend(f"reconciliation: {item}" for item in declared)\n',
    '    reconciliation = runtime.get("reconciliation")\n    if not isinstance(reconciliation, dict):\n        issues.append("reconciliation must be an object")\n    else:\n        if reconciliation.get("status") != "PASS":\n            issues.append("reconciliation status is not PASS")\n        declared = reconciliation.get("issues", [])\n        if declared:\n            issues.extend(f"reconciliation: {item}" for item in declared)\n\n    summary = runtime.get("account_summary")\n    balances = runtime.get("balances")\n    nav = _number(summary.get("net_liquidation")) if isinstance(summary, dict) else None\n    cash = None\n    if isinstance(balances, dict):\n        cash = _number(balances.get("total_cash", balances.get("cash")))\n    positions = _position_values(runtime.get("positions"))\n    if nav is None or cash is None or positions is None:\n        issues.append("actual reconciliation inputs are unavailable")\n    else:\n        try:\n            actual = reconcile_nav(nav, cash, positions)\n        except ValueError as exc:\n            issues.append(f"actual reconciliation invalid: {exc}")\n        else:\n            if not actual.passed:\n                issues.append(actual.issue or "actual reconciliation failed")\n',
)

# Synthetic broker fixture must actually reconcile.
replace(
    "tests/test_broker_runtime.py",
    '        "positions": [],\n',
    '        "positions": [{"symbol": "SYNTHETIC", "market_value": 85000}],\n',
)

# Add the new regression suite to the canonical entry point.
replace(
    "tests/run-all.sh",
    "python3 tests/test_monthly_dd_cli.py\n",
    "python3 tests/test_monthly_dd_cli.py\npython3 tests/test_reconciliation_gates.py\n",
)
