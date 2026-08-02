#!/usr/bin/env python3
"""Deterministic contract tests for the real Claude Code eval adapters."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTOR = ROOT / "evals" / "adapters" / "claude_actor.py"
VERIFIER = ROOT / "evals" / "adapters" / "claude_verifier.py"

FAKE_CLAUDE = r'''#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
cwd = Path.cwd()
plugin = Path(args[args.index("--plugin-dir") + 1]) if "--plugin-dir" in args else None
session_flag = "--session-id" if "--session-id" in args else "--resume"
requested_session = args[args.index(session_flag) + 1]
reported_session = "wrong-session" if os.environ.get("FAKE_SESSION_MISMATCH") else requested_session

record = {
    "args": args,
    "cwd": str(cwd),
    "cwd_has_git": (cwd / ".git").exists(),
    "plugin": str(plugin) if plugin else None,
    "plugin_has_git": (plugin / ".git").exists() if plugin else None,
    "plugin_has_results": (plugin / "evals" / "results").exists() if plugin else None,
    "session_flag": session_flag,
    "requested_session": requested_session,
}
with open(os.environ["FAKE_CLAUDE_LOG"], "a", encoding="utf-8") as handle:
    handle.write(json.dumps(record) + "\n")

print(json.dumps({
    "is_error": False,
    "result": os.environ.get("FAKE_CLAUDE_RESULT", "actor reply"),
    "session_id": reported_session,
    "num_turns": 2,
    "permission_denials": [],
}))
'''


class AdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="adapter-test-")
        self.temp_path = Path(self.temp.name)
        self.log = self.temp_path / "claude.jsonl"
        fake = self.temp_path / "claude"
        fake.write_text(FAKE_CLAUDE, encoding="utf-8")
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        self.env = os.environ.copy()
        self.env.update({
            "PATH": f"{self.temp_path}{os.pathsep}{self.env['PATH']}",
            "FAKE_CLAUDE_LOG": str(self.log),
            "EVAL_PLUGIN_DIR": str(ROOT),
            "PYTHONDONTWRITEBYTECODE": "1",
        })

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_adapter(self, adapter: Path, request: dict, **env: str) -> subprocess.CompletedProcess[str]:
        run_env = self.env.copy()
        run_env.update(env)
        return subprocess.run(
            ["python3", str(adapter)],
            input=json.dumps(request),
            text=True,
            capture_output=True,
            cwd=ROOT,
            env=run_env,
            check=False,
        )

    def records(self) -> list[dict]:
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    def test_actor_uses_one_session_in_a_gitless_disposable_distribution(self) -> None:
        result = self.run_adapter(ACTOR, {"turns": [{"prompt": "one"}, {"prompt": "two"}]})
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        harness = payload["harness"]
        self.assertTrue(harness["disposable_distribution"])
        self.assertFalse(harness["git_metadata_present"])
        self.assertFalse(harness["prior_eval_results_present"])
        self.assertFalse(any("Bash(git " in tool for tool in harness["tools"]["allowed"]))

        records = self.records()
        self.assertEqual(len(records), 2)
        self.assertEqual([record["session_flag"] for record in records], ["--session-id", "--resume"])
        self.assertEqual({record["requested_session"] for record in records}, {payload["session_id"]})
        self.assertEqual({record["cwd"] for record in records}, {records[0]["plugin"]})
        self.assertTrue(all(not record["cwd_has_git"] for record in records))
        self.assertTrue(all(not record["plugin_has_git"] for record in records))
        self.assertTrue(all(not record["plugin_has_results"] for record in records))

    def test_actor_rejects_unverified_session_identity(self) -> None:
        result = self.run_adapter(
            ACTOR,
            {"turns": [{"prompt": "one"}]},
            FAKE_SESSION_MISMATCH="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("session identity unverified", result.stderr)

    def test_verifier_accepts_exact_evidence_bearing_schema(self) -> None:
        request = self.verifier_request()
        judgment = {
            "required_checks": [{"behavior": "states the block", "passed": True, "evidence": "blocked"}],
            "forbidden_checks": [{"behavior": "creates a candidate", "triggered": False, "evidence": "no candidate"}],
        }
        result = self.run_adapter(VERIFIER, request, FAKE_CLAUDE_RESULT=json.dumps(judgment))
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["verdict"], "pass")
        self.assertNotEqual(payload["independence"]["verifier_session_id"], request["actor"]["session_id"])

    def test_verifier_rejects_schema_shortcuts(self) -> None:
        invalid = {
            "string boolean": {
                "required_checks": [{"behavior": "states the block", "passed": "true", "evidence": "blocked"}],
                "forbidden_checks": [{"behavior": "creates a candidate", "triggered": False, "evidence": "none"}],
            },
            "wrong behavior": {
                "required_checks": [{"behavior": "something else", "passed": True, "evidence": "blocked"}],
                "forbidden_checks": [{"behavior": "creates a candidate", "triggered": False, "evidence": "none"}],
            },
            "missing evidence": {
                "required_checks": [{"behavior": "states the block", "passed": True, "evidence": None}],
                "forbidden_checks": [{"behavior": "creates a candidate", "triggered": False, "evidence": "none"}],
            },
        }
        for label, judgment in invalid.items():
            with self.subTest(label=label):
                if self.log.exists():
                    self.log.unlink()
                result = self.run_adapter(
                    VERIFIER,
                    self.verifier_request(),
                    FAKE_CLAUDE_RESULT=json.dumps(judgment),
                )
                self.assertNotEqual(result.returncode, 0)

    @staticmethod
    def verifier_request() -> dict:
        return {
            "scenario": {
                "name": "schema-test",
                "reason": "contract test",
                "required": ["states the block"],
                "forbidden": ["creates a candidate"],
            },
            "actor": {
                "session_id": "actor-session",
                "transcript": [
                    {"role": "user", "content": "decide"},
                    {"role": "assistant", "content": "blocked; no candidate"},
                ],
            },
        }


if __name__ == "__main__":
    unittest.main()
