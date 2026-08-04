"""Resolve installed-plugin runtime tools for source-level tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT
SKILLS = PLUGIN_ROOT / "skills"
SCRIPTS = SKILLS / "investment-os" / "scripts"

SCRIPT_DIRS = {
    "broker": SCRIPTS,
    "reconciliation": SCRIPTS,
    "monthly": SCRIPTS,
    "drawdown": SCRIPTS,
    "execution": SCRIPTS,
}

sys.path.insert(0, str(SCRIPTS))
