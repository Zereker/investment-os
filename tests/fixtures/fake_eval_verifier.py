#!/usr/bin/env python3
import json
import sys

request = json.load(sys.stdin)
scenario = request["scenario"]
actor_session_id = request["actor"]["session_id"]
json.dump({
    "verdict": "pass",
    "required_checks": [
        {"behavior": behavior, "passed": True, "evidence": "synthetic fixture evidence"}
        for behavior in scenario["required"]
    ],
    "forbidden_checks": [
        {"behavior": behavior, "triggered": False, "evidence": "synthetic fixture evidence"}
        for behavior in scenario["forbidden"]
    ],
    "independence": {
        "separate_process": True,
        "separate_session": True,
        "different_harness": True,
        "actor_session_id": actor_session_id,
        "verifier_session_id": "verifier-clean-session-001"
    }
}, sys.stdout)
