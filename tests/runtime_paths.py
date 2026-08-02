"""Resolve installed-plugin runtime tools for source-level tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "investment-os"
SKILLS = PLUGIN_ROOT / "skills"

SCRIPT_DIRS = {
    "broker": SKILLS / "broker-runtime" / "scripts",
    "reconciliation": SKILLS / "reconstructing-portfolio-state" / "scripts",
    "behavior": SKILLS / "enforcing-behavioral-controls" / "scripts",
    "daily": SKILLS / "running-daily-review" / "scripts",
    "monthly": SKILLS / "running-monthly-review" / "scripts",
    "drawdown": SKILLS / "validating-drawdown-state" / "scripts",
    "execution": SKILLS / "execution-runtime" / "scripts",
    "research": SKILLS / "routing-investment-research" / "scripts",
}

for path in SCRIPT_DIRS.values():
    sys.path.insert(0, str(path))
