#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from runtime_paths import SCRIPT_DIRS

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SCRIPT_DIRS["monthly"] / "monthly_execution.py"
BASE = [
    sys.executable, str(SCRIPT),
    "--nav", "100000", "--cash", "34000",
    "--spym", "40000", "--qqqm", "20000", "--soxx", "6000",
    "--contribution", "0", "--tiers-executed-spym", "none", "--open-orders-status", "clear",
    "--today", "2026-08-02",
]

def run(dd: str, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(BASE + ["--dd-spym", dd, *extra], capture_output=True, text=True)

def main() -> None:
    percent_mistake = run("1.68")
    assert percent_mistake.returncode != 0
    assert "--dd-spym 必须使用小数" in percent_mistake.stderr
    assert "0.0168" in percent_mistake.stderr

    # all three ladders supplied so the run is clean; SPYM at 1.68% fires nothing
    valid_decimal = run("0.0168", "--dd-as-of", "2026-08-01",
                        "--dd-qqqm", "0", "--tiers-executed-qqqm", "none",
                        "--dd-soxx", "0", "--tiers-executed-soxx", "none")
    assert valid_decimal.returncode == 0, valid_decimal.stderr + valid_decimal.stdout
    assert "DD = 1.68%" in valid_decimal.stdout
    assert "T1" in valid_decimal.stdout and "未达档" in valid_decimal.stdout

    for invalid in ("-0.01", "1", "nan", "inf"):
        result = run(invalid)
        assert result.returncode != 0, invalid
        assert "范围为 [0, 1)" in result.stderr, invalid

    # a drawdown with no as-of date cannot be checked for freshness, so it must
    # not evaluate tiers — the close could be from any date
    undated = run("0.0168")
    assert "没有 --dd-as-of" in undated.stderr, undated.stderr
    assert "回撤序列不可得" in undated.stdout, undated.stdout

    # and a close older than the freshness window is refused the same way
    stale = run("0.0168", "--dd-as-of", "2026-07-01")
    assert "本月不评估任何标的分档" in stale.stderr, stale.stderr

    # a ticker with no --dd of its own is not evaluated, and that must not stop
    # the other two: the registry localizes a missing series to its own ladder
    partial = run("0.0168", "--dd-as-of", "2026-08-01",
                  "--dd-soxx", "0.2235", "--tiers-executed-soxx", "none")
    assert partial.returncode != 0, "QQQM has no series, so its ladder is DATA INCOMPLETE"
    assert "QQQM 回撤序列不可得" in partial.stdout, partial.stdout
    assert "SPYM  阶梯 9% of NAV" in partial.stdout, partial.stdout
    assert "SOXX  阶梯 1% of NAV" in partial.stdout, partial.stdout

    # the whole point of per-ticker ladders: a sector selloff that leaves the
    # broad index untouched is answered, in proportion, and buys only that
    # ticker. SOXX is below target here so the tranche has somewhere to go.
    sector = subprocess.run([
        sys.executable, str(SCRIPT),
        "--nav", "100000", "--cash", "36000",
        "--spym", "40000", "--qqqm", "20000", "--soxx", "4000",
        "--contribution", "0", "--open-orders-status", "clear", "--today", "2026-08-02",
        "--dd-as-of", "2026-08-01",
        "--dd-spym", "0.0168", "--tiers-executed-spym", "none",
        "--dd-qqqm", "0.03", "--tiers-executed-qqqm", "none",
        "--dd-soxx", "0.2235", "--tiers-executed-soxx", "none",
    ], capture_output=True, text=True)
    assert sector.returncode == 0, sector.stderr + sector.stdout
    assert "SOXX:T1+T2+T3" in sector.stdout, sector.stdout
    # 0.6pp of a 100k NAV = 600, proportionate to a 5% sleeve — not the 4.5pp
    # the old single ladder would have released at the same depth
    assert "部署 = 600" in sector.stdout, sector.stdout
    assert "SPYM 0 ｜ QQQM 0 ｜ SOXX 600" in sector.stdout, sector.stdout

    print("Monthly drawdown CLI unit-guard tests passed.")

if __name__ == "__main__":
    main()
