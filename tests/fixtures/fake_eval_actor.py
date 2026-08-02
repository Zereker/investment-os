#!/usr/bin/env python3
import json
import sys

request = json.load(sys.stdin)
scenario_name = request["scenario_name"]
transcript = []
for turn in request["turns"]:
    transcript.append({"role": "user", "content": turn["prompt"]})
    transcript.append({"role": "assistant", "content": "DATA INCOMPLETE. No transaction candidate or quantity is authorized."})
json.dump({
    "session_id": f"actor-clean-session-{scenario_name}",
    "harness": {
        "name": "synthetic-test-actor",
        "session_identity_verified": True,
        "persistent_session": len(request["turns"]) > 1,
        "turn_observability": [
            {"cli_session_id": f"actor-clean-session-{scenario_name}"}
            for _ in request["turns"]
        ],
    },
    "transcript": transcript,
}, sys.stdout)
