#!/usr/bin/env python3
import json
import os
import sys

request = json.load(sys.stdin)
scenario = request["scenario"]
actor_session_id = request["actor"]["session_id"]
scenario_name = scenario["name"]
forced_failure = os.environ.get("FAKE_EVAL_FAIL_SCENARIO") == scenario_name
required_checks = [
    {
        "behavior": behavior,
        "passed": not (forced_failure and index == 0),
        "evidence": "forced regression evidence" if forced_failure and index == 0 else "synthetic fixture evidence",
    }
    for index, behavior in enumerate(scenario["required"])
]
json.dump({
    "verdict": "fail" if forced_failure else "pass",
    "required_checks": required_checks,
    "forbidden_checks": [
        {"behavior": behavior, "triggered": False, "evidence": "synthetic fixture evidence"}
        for behavior in scenario["forbidden"]
    ],
    "independence": {
        "separate_process": True,
        "separate_session": True,
        "different_harness": True,
        "session_identity_verified": True,
        "isolated_home": True,
        "host_config_inherited": False,
        "actor_session_id": actor_session_id,
        "verifier_session_id": f"verifier-clean-session-{scenario_name}"
    }
}, sys.stdout)
