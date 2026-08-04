#!/usr/bin/env python3
"""Deterministic contract tests for the real Claude Code and Codex eval adapters."""

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
CODEX_VERIFIER = ROOT / "evals" / "adapters" / "codex_verifier.py"

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
    "plugin_has_evals": (plugin / "evals").exists() if plugin else None,
    "plugin_has_tests": (plugin / "tests").exists() if plugin else None,
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

FAKE_CODEX = r'''#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
if args == ["--version"]:
    print("codex-cli 0.test")
    raise SystemExit(0)

cwd = Path.cwd()
output = Path(args[args.index("--output-last-message") + 1])
schema = Path(args[args.index("--output-schema") + 1])
configured_cwd = Path(args[args.index("--cd") + 1])
record = {
    "args": args,
    "cwd": str(cwd),
    "cwd_has_git": (cwd / ".git").exists(),
    "configured_cwd": str(configured_cwd),
    "schema_exists": schema.exists(),
    "sqlite_home": os.environ.get("CODEX_SQLITE_HOME"),
    "home": os.environ.get("HOME"),
    "codex_home": os.environ.get("CODEX_HOME"),
    "xdg_config_home": os.environ.get("XDG_CONFIG_HOME"),
    "auth_exists": (Path(os.environ["HOME"]) / ".codex" / "auth.json").is_file(),
    "auth_mode": json.loads((Path(os.environ["HOME"]) / ".codex" / "auth.json").read_text()).get("auth_mode")
        if (Path(os.environ["HOME"]) / ".codex" / "auth.json").is_file() else None,
    "auth_permissions": oct((Path(os.environ["HOME"]) / ".codex" / "auth.json").stat().st_mode & 0o777)
        if (Path(os.environ["HOME"]) / ".codex" / "auth.json").is_file() else None,
    "openai_api_key_present": bool(os.environ.get("OPENAI_API_KEY")),
    "network_env": {
        name: os.environ.get(name)
        for name in (
            "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
            "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE",
        )
    },
    "unrelated_env_present": bool(os.environ.get("EVAL_UNRELATED_SECRET")),
}
fixture_dir = Path(__file__).parent
with open(fixture_dir / "codex.jsonl", "a", encoding="utf-8") as handle:
    handle.write(json.dumps(record) + "\n")

output.write_text((fixture_dir / "fake-codex-result.json").read_text(encoding="utf-8"), encoding="utf-8")
controls_path = fixture_dir / "fake-codex-controls.json"
controls = json.loads(controls_path.read_text(encoding="utf-8")) if controls_path.is_file() else {}
session = controls.get("session", "codex-verifier-session")
print(json.dumps({"type": "thread.started", "thread_id": session}))
if controls.get("tool"):
    print(json.dumps({
        "type": "item.completed",
        "item": {"id": "tool-1", "type": "command_execution", "status": "completed"},
    }))
print(json.dumps({
    "type": "item.completed",
    "item": {"id": "answer-1", "type": "agent_message", "text": "structured output"},
}))
print(json.dumps({"type": "turn.completed", "usage": {}}))
'''


class AdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="adapter-test-")
        self.temp_path = Path(self.temp.name)
        self.log = self.temp_path / "claude.jsonl"
        fake = self.temp_path / "claude"
        fake.write_text(FAKE_CLAUDE, encoding="utf-8")
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        fake_codex = self.temp_path / "codex"
        fake_codex.write_text(FAKE_CODEX, encoding="utf-8")
        fake_codex.chmod(fake_codex.stat().st_mode | stat.S_IXUSR)
        self.codex_auth = self.temp_path / "auth.json"
        self.codex_auth.write_text(json.dumps({
            "auth_mode": "chatgpt",
            "OPENAI_API_KEY": None,
            "tokens": {"refresh_token": "test-refresh-token"},
        }), encoding="utf-8")
        self.codex_auth.chmod(0o600)
        self.env = os.environ.copy()
        self.env.update({
            "PATH": f"{self.temp_path}{os.pathsep}{self.env['PATH']}",
            "FAKE_CLAUDE_LOG": str(self.log),
            "EVAL_PLUGIN_DIR": str(ROOT),
            "EVAL_CODEX_AUTH_MODE": "subscription",
            "EVAL_CODEX_AUTH_FILE": str(self.codex_auth),
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

    def configure_fake_codex(
        self,
        judgment: dict,
        *,
        session: str = "codex-verifier-session",
        tool: bool = False,
    ) -> None:
        (self.temp_path / "fake-codex-result.json").write_text(
            json.dumps(judgment), encoding="utf-8"
        )
        (self.temp_path / "fake-codex-controls.json").write_text(
            json.dumps({"session": session, "tool": tool}), encoding="utf-8"
        )

    def test_actor_uses_one_session_in_a_gitless_disposable_distribution(self) -> None:
        evidence = self.temp_path / "evidence"
        result = self.run_adapter(
            ACTOR,
            {"turns": [{"prompt": "one"}, {"prompt": "two"}]},
            EVAL_EVIDENCE_DIR=str(evidence),
        )
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
        self.assertEqual(
            {Path(record["cwd"]).resolve() for record in records},
            {Path(records[0]["plugin"]).resolve()},
        )
        self.assertTrue(all(not record["cwd_has_git"] for record in records))
        self.assertTrue(all(not record["plugin_has_git"] for record in records))
        self.assertTrue(all(not record["plugin_has_evals"] for record in records))
        self.assertTrue(all(not record["plugin_has_tests"] for record in records))
        self.assertTrue(all(not record["plugin_has_results"] for record in records))
        for index in (1, 2):
            prefix = evidence / "claude-actor" / f"turn-{index:03d}"
            self.assertTrue(prefix.with_suffix(".stdout.json").is_file())
            self.assertTrue(prefix.with_suffix(".stderr.log").is_file())
            self.assertTrue(prefix.with_suffix(".metadata.json").is_file())

    def test_actor_rejects_unverified_session_identity(self) -> None:
        result = self.run_adapter(
            ACTOR,
            {"turns": [{"prompt": "one"}]},
            FAKE_SESSION_MISMATCH="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("session identity unverified", result.stderr)

    def test_codex_verifier_is_cross_harness_clean_and_tool_free(self) -> None:
        judgment = {
            "required_checks": [{"behavior": "states the block", "passed": True, "evidence": "blocked"}],
            "forbidden_checks": [{"behavior": "creates a candidate", "triggered": False, "evidence": "no candidate"}],
        }
        self.configure_fake_codex(judgment)
        evidence = self.temp_path / "codex-evidence"
        result = self.run_adapter(
            CODEX_VERIFIER,
            self.verifier_request(),
            EVAL_CODEX_BIN=str(self.temp_path / "codex"),
            EVAL_EVIDENCE_DIR=str(evidence),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        independence = payload["independence"]
        self.assertEqual(payload["verdict"], "pass")
        self.assertTrue(independence["different_harness"])
        self.assertTrue(independence["ephemeral_session"])
        self.assertTrue(independence["isolated_home"])
        self.assertFalse(independence["host_config_inherited"])
        self.assertEqual(independence["auth_mode"], "subscription")
        self.assertEqual(independence["tools_used"], [])
        self.assertNotEqual(independence["verifier_session_id"], "actor-session")

        log = self.temp_path / "codex.jsonl"
        record = json.loads(log.read_text(encoding="utf-8"))
        args = record["args"]
        self.assertEqual(args[0], "exec")
        for flag in (
            "--json", "--ephemeral", "--ignore-user-config", "--ignore-rules",
            "--strict-config", "--skip-git-repo-check", "--output-schema",
        ):
            self.assertIn(flag, args)
        self.assertEqual(args[args.index("--sandbox") + 1], "read-only")
        self.assertFalse(record["cwd_has_git"])
        self.assertEqual(
            Path(record["cwd"]).resolve(), Path(record["configured_cwd"]).resolve()
        )
        self.assertTrue(record["schema_exists"])
        self.assertTrue(record["sqlite_home"].startswith(record["home"]))
        self.assertNotEqual(record["home"], str(Path.home()))
        self.assertIsNone(record["codex_home"])
        self.assertTrue(record["xdg_config_home"].startswith(record["home"]))
        self.assertTrue(record["auth_exists"])
        self.assertEqual(record["auth_mode"], "chatgpt")
        self.assertEqual(record["auth_permissions"], "0o600")
        self.assertFalse(record["openai_api_key_present"])
        for name in ("events.jsonl", "stderr.log", "structured-output.json", "metadata.json"):
            self.assertTrue((evidence / "codex-verifier" / name).is_file())

    def test_codex_verifier_rejects_schema_shortcuts(self) -> None:
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
                self.configure_fake_codex(judgment)
                result = self.run_adapter(
                    CODEX_VERIFIER,
                    self.verifier_request(),
                    EVAL_CODEX_BIN=str(self.temp_path / "codex"),
                )
                self.assertNotEqual(result.returncode, 0)

    def test_codex_verifier_can_use_scoped_api_key_without_copying_auth(self) -> None:
        judgment = {
            "required_checks": [{"behavior": "states the block", "passed": True, "evidence": "blocked"}],
            "forbidden_checks": [{"behavior": "creates a candidate", "triggered": False, "evidence": "none"}],
        }
        self.configure_fake_codex(judgment)
        result = self.run_adapter(
            CODEX_VERIFIER,
            self.verifier_request(),
            EVAL_CODEX_BIN=str(self.temp_path / "codex"),
            EVAL_CODEX_AUTH_MODE="api-key",
            OPENAI_API_KEY="test-only-key",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["independence"]["auth_mode"], "api-key")
        record = json.loads((self.temp_path / "codex.jsonl").read_text(encoding="utf-8"))
        self.assertFalse(record["auth_exists"])
        self.assertTrue(record["openai_api_key_present"])

    def test_codex_verifier_preserves_only_managed_network_runtime(self) -> None:
        judgment = {
            "required_checks": [{"behavior": "states the block", "passed": True, "evidence": "blocked"}],
            "forbidden_checks": [{"behavior": "creates a candidate", "triggered": False, "evidence": "none"}],
        }
        self.configure_fake_codex(judgment)
        expected = {
            "HTTP_PROXY": "http://proxy.test:8080",
            "HTTPS_PROXY": "http://proxy.test:8080",
            "ALL_PROXY": "socks5://proxy.test:1080",
            "NO_PROXY": "localhost,127.0.0.1",
            "SSL_CERT_FILE": "/managed/certs/proxy.pem",
            "REQUESTS_CA_BUNDLE": "/managed/certs/proxy.pem",
        }
        result = self.run_adapter(
            CODEX_VERIFIER,
            self.verifier_request(),
            EVAL_CODEX_BIN=str(self.temp_path / "codex"),
            EVAL_UNRELATED_SECRET="must-not-cross-isolation",
            **expected,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads((self.temp_path / "codex.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(record["network_env"], expected)
        self.assertFalse(record["unrelated_env_present"])

    def test_codex_verifier_rejects_linked_subscription_auth(self) -> None:
        link = self.temp_path / "linked-auth.json"
        link.symlink_to(self.codex_auth)
        result = self.run_adapter(
            CODEX_VERIFIER,
            self.verifier_request(),
            EVAL_CODEX_BIN=str(self.temp_path / "codex"),
            EVAL_CODEX_AUTH_FILE=str(link),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("regular file, not a link", result.stderr)

    def test_codex_verifier_rejects_shared_session_or_tool_use(self) -> None:
        judgment = {
            "required_checks": [{"behavior": "states the block", "passed": True, "evidence": "blocked"}],
            "forbidden_checks": [{"behavior": "creates a candidate", "triggered": False, "evidence": "none"}],
        }
        cases = {
            "shared session": {"session": "actor-session", "tool": False},
            "tool use": {"session": "codex-verifier-session", "tool": True},
        }
        for label, controls in cases.items():
            with self.subTest(label=label):
                codex_log = self.temp_path / "codex.jsonl"
                if codex_log.exists():
                    codex_log.unlink()
                self.configure_fake_codex(judgment, **controls)
                result = self.run_adapter(
                    CODEX_VERIFIER,
                    self.verifier_request(),
                    EVAL_CODEX_BIN=str(self.temp_path / "codex"),
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
                "harness": {"name": "claude-code", "model": "claude-sonnet-5"},
                "transcript": [
                    {"role": "user", "content": "decide"},
                    {"role": "assistant", "content": "blocked; no candidate"},
                ],
            },
        }


if __name__ == "__main__":
    unittest.main()
