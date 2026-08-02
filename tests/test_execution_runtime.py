#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy

from scripts.execution_runtime import REQUIRED_STAGES, operation_digest, validate


def base_record():
    operation = {
        "type": "place_order",
        "account": "SYNTHETIC",
        "instrument": "TEST",
        "side": "BUY",
        "quantity": 1,
        "order_type": "LIMIT",
        "limit_price": 10.0,
        "time_in_force": "DAY",
    }
    return {
        "operation": operation,
        "capability": "Broker.Trade.PlaceOrder",
        "authorization": {
            "scope": "single-operation-current-session",
            "operation_digest": operation_digest(operation),
            "owner_explicit": True,
            "session_id": "actor-session-a",
        },
        "adapter": {"supported_capabilities": ["Broker.Trade.PlaceOrder"]},
        "stages": list(REQUIRED_STAGES),
        "submit_count": 1,
        "write_result": {"accepted": True, "broker_order_id": "synthetic-order"},
        "read_back": {"status": "Submitted", "broker_order_id": "synthetic-order"},
        "verification": {"performed": True, "passed": True, "evidence": "synthetic read-back matched"},
        "status": "COMPLETED",
    }


def must_fail(record, issue_fragment):
    result = validate(record)
    assert not result.passed
    assert any(issue_fragment in issue for issue in result.issues), result


def main():
    assert validate(base_record()).passed

    wrong_auth = deepcopy(base_record())
    wrong_auth["operation"]["quantity"] = 2
    must_fail(wrong_auth, "authorization does not match")

    broad_auth = deepcopy(base_record())
    broad_auth["authorization"]["scope"] = "current-session-all-trades"
    must_fail(broad_auth, "single-operation")

    unsupported = deepcopy(base_record())
    unsupported["adapter"]["supported_capabilities"] = []
    must_fail(unsupported, "does not support")

    duplicate = deepcopy(base_record())
    duplicate["submit_count"] = 2
    must_fail(duplicate, "more than once")

    no_readback = deepcopy(base_record())
    no_readback["read_back"] = None
    must_fail(no_readback, "read_back missing")

    skipped = deepcopy(base_record())
    skipped["stages"].remove("READ_BACK")
    must_fail(skipped, "out of order")

    failed = deepcopy(base_record())
    failed["status"] = "VERIFICATION FAILED"
    failed["stages"] = REQUIRED_STAGES[:-1]
    failed["verification"]["passed"] = False
    result = validate(failed)
    assert result.status == "VERIFICATION FAILED" and not result.passed and not result.issues

    unknown = deepcopy(base_record())
    unknown["status"] = "EXECUTION UNKNOWN"
    unknown["stages"] = REQUIRED_STAGES[:4]
    unknown["read_back"] = None
    unknown["verification"] = {}
    result = validate(unknown)
    assert result.status == "EXECUTION UNKNOWN" and not result.passed and not result.issues

    print("Execution runtime tests passed.")


if __name__ == "__main__":
    main()
