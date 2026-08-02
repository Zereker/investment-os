#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"missing frontmatter: {path}"
    raw = text.split("---\n", 2)[1]
    data: dict[str, str] = {}
    for line in raw.splitlines():
        if line.strip():
            key, sep, value = line.partition(":")
            assert sep, f"invalid frontmatter: {path}: {line}"
            data[key.strip()] = value.strip()
    return data


def discover() -> dict[str, Path]:
    found: dict[str, Path] = {}
    for path in sorted(SKILLS.glob("*/SKILL.md")):
        meta = frontmatter(path)
        name = meta.get("name", "")
        assert name == path.parent.name, f"skill name mismatch: {path}"
        assert meta.get("description", "").startswith("Use when "), path
        assert name not in found, f"duplicate skill name: {name}"
        found[name] = path
    return found


def dependency_graph(skills: dict[str, Path]) -> dict[str, set[str]]:
    graph = {name: set() for name in skills}
    pattern = re.compile(r"\*\*REQUIRED SUB-SKILL:\*\* `([a-z0-9-]+)`")
    for name, path in skills.items():
        for dependency in pattern.findall(path.read_text(encoding="utf-8")):
            assert dependency in skills, f"{name} references missing skill {dependency}"
            graph[name].add(dependency)
    return graph


def assert_acyclic(graph: dict[str, set[str]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise AssertionError(f"skill dependency cycle at {node}")
        if node in visited:
            return
        visiting.add(node)
        for child in graph[node]:
            visit(child)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)


def test_manifests() -> None:
    claude = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
    codex = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())
    version = (ROOT / ".plugin-version").read_text(encoding="utf-8").strip()
    assert claude["name"] == codex["name"] == "investment-os"
    assert claude["version"] == codex["version"] == version
    assert codex["skills"] == "./skills/"
    hooks = json.loads((ROOT / "hooks/hooks.json").read_text())
    command = hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    assert "session-start" in command


def test_bootstrap() -> None:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(ROOT)
    result = subprocess.run(["bash", str(ROOT / "hooks/session-start")], check=True, capture_output=True, text=True, env=env)
    payload = json.loads(result.stdout)
    context = payload["hookSpecificOutput"]["additionalContext"]
    assert "INVESTMENT_OS_BOOTSTRAP" in context
    assert "using-investment-os" in context
    assert "only policy authority" in context
    assert "DATA INCOMPLETE" not in context


def main() -> None:
    skills = discover()
    expected = {
        "using-investment-os", "broker-runtime", "execution-runtime",
        "reconstructing-portfolio-state", "validating-drawdown-state",
        "enforcing-behavioral-controls", "running-daily-review",
        "running-monthly-review", "evaluating-transaction-candidates",
        "routing-investment-research", "auditing-investment-os",
    }
    assert expected <= set(skills), f"missing skills: {sorted(expected - set(skills))}"
    graph = dependency_graph(skills)
    assert_acyclic(graph)
    assert graph["using-investment-os"] >= {
        "broker-runtime", "execution-runtime", "reconstructing-portfolio-state",
        "validating-drawdown-state", "enforcing-behavioral-controls", "running-daily-review",
    }
    assert graph["reconstructing-portfolio-state"] == {"broker-runtime"}
    broker_text = skills["broker-runtime"].read_text(encoding="utf-8")
    assert "broker-neutral" in broker_text
    assert "Missing open orders" in broker_text
    assert "Missing cash transactions" in broker_text
    assert "persist real account data" in broker_text
    execution_text = skills["execution-runtime"].read_text(encoding="utf-8")
    assert "single-operation-current-session" in execution_text
    assert "read back authoritative broker state" in execution_text
    assert "no silent retry" in execution_text
    test_manifests()
    test_bootstrap()
    print("Skill system integration tests passed.")


if __name__ == "__main__":
    main()
