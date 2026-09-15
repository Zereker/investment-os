import assert from "node:assert/strict";
import { calculateMonthlyDeployment } from "./monthly";

const base = { nav: 100000, cash: 34000, positions: { spym: 40000, qqqm: 20000, soxx: 6000 }, legacy: 0,
  contribution: 0, open_orders_status: "clear" as const, drawdown_as_of: "2026-08-01", today: "2026-08-02",
  drawdowns: { spym: 0.04, qqqm: 0.21 }, tiers_executed: { spym: [], qqqm: [] } };
const result = calculateMonthlyDeployment(base);
assert.equal(result.status, "PASS");
assert.ok(Math.abs(result.drawdown_deployment.allocation.qqqm - 3600) < 1e-9);
assert.deepEqual(result.drawdown_deployment.consumed_tiers.qqqm, ["T1", "T2", "T3"]);
assert.equal(result.drawdown_deployment.allocation.spym, 0);
assert.equal(result.execution_authorized, false);
assert.equal(calculateMonthlyDeployment({ ...base, contribution: null }).status, "DATA INCOMPLETE");
assert.equal(calculateMonthlyDeployment({ ...base, open_orders_status: "unknown" }).status, "DATA INCOMPLETE");
assert.equal(calculateMonthlyDeployment({ ...base, drawdowns: { spym: 1.68 } }).status, "DATA INCOMPLETE");
const noGap = calculateMonthlyDeployment({ ...base, positions: { spym: 35000, qqqm: 30000, soxx: 1000 }, drawdowns: { qqqm: 0.25 }, tiers_executed: { qqqm: [] } });
assert.equal(noGap.drawdown_deployment.allocation.qqqm, 0);
assert.deepEqual(noGap.drawdown_deployment.consumed_tiers.qqqm, []);
console.log("Monthly deployment tests passed.");
