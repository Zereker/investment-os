import assert from "node:assert/strict";
import { operationDigest, REQUIRED_STAGES, validateBrokerExecution } from "./execution";

const operation = { type: "place_order", account: "SYNTHETIC", instrument: "TEST", side: "BUY", quantity: 1, order_type: "LIMIT", limit_price: 10, time_in_force: "DAY" };
const base = { operation, capability: "Broker.Trade.PlaceOrder", authorization: { scope: "single-operation-current-session", operation_digest: operationDigest(operation), owner_explicit: true, session_id: "synthetic-session" }, adapter: { supported_capabilities: ["Broker.Trade.PlaceOrder"] }, stages: [...REQUIRED_STAGES], submit_count: 1, write_result: { accepted: true }, read_back: { status: "Submitted" }, verification: { performed: true, passed: true, evidence: "synthetic read-back matched" }, status: "COMPLETED" };
assert.equal(validateBrokerExecution(base).passed, true);
assert.match(validateBrokerExecution({ ...base, operation: { ...operation, quantity: 2 } }).issues.join(" "), /authorization does not match/);
assert.match(validateBrokerExecution({ ...base, submit_count: 2 }).issues.join(" "), /more than once/);
assert.match(validateBrokerExecution({ ...base, read_back: null }).issues.join(" "), /read_back missing/);
assert.equal(validateBrokerExecution({ ...base, status: "EXECUTION UNKNOWN", stages: REQUIRED_STAGES.slice(0, 4), read_back: null, verification: {} }).status, "EXECUTION UNKNOWN");
console.log("Execution runtime tests passed.");
