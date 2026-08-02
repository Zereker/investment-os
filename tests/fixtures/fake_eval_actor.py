#!/usr/bin/env python3
import json
import sys

request = json.load(sys.stdin)
transcript = []
for turn in request["turns"]:
    transcript.append({"role": "user", "content": turn["prompt"]})
    transcript.append({"role": "assistant", "content": "DATA INCOMPLETE. No transaction candidate or quantity is authorized."})
json.dump({
    "session_id": "actor-clean-session-001",
    "harness": "synthetic-test-actor",
    "transcript": transcript,
}, sys.stdout)
