import assert from "node:assert/strict";

import { validateBrokerRuntime } from "./runtime";

const now = Date.parse("2026-09-14T12:00:00Z");
const capabilities = {
  account_summary: "available",
  balances: "available",
  positions: "available",
  open_orders: "available",
  cash_transactions: "available",
  market_inputs: "available",
  alert_inventory: "available",
  standing_automations: "available"
};

const runtime = {
  identity: { account_id: "SYNTHETIC", account_type: "paper" },
  snapshot: {
    as_of: "2026-09-14T12:00:00Z",
    source: "synthetic-adapter",
    timezone: "UTC",
    currency_basis: "USD"
  },
  capabilities,
  observations: Object.fromEntries(
    Object.keys(capabilities).map((name) => [
      name,
      { source: "synthetic-adapter", observed_at: "2026-09-14T12:00:00Z" }
    ])
  ),
  account_summary: { net_liquidation: 100000 },
  balances: { cash: 15000 },
  positions: [{ symbol: "SYNTHETIC", market_value: 85000 }],
  open_orders: [],
  cash_transactions: [],
  market_inputs: {},
  alert_inventory: [],
  standing_automations: [],
  reconciliation: { status: "PASS", issues: [] }
};

const passed = validateBrokerRuntime(
  runtime,
  ["positions", "balances", "open_orders"],
  300,
  now
);
assert.equal(passed.runtime_status, "PASS");

const unavailable = structuredClone(runtime);
unavailable.capabilities.positions = "unavailable";
unavailable.positions = null as never;
const blocked = validateBrokerRuntime(
  unavailable,
  ["positions", "balances"],
  300,
  now
);
assert.equal(blocked.runtime_status, "DATA INCOMPLETE");
assert.ok(
  blocked.blocking_issues.some((issue) =>
    issue.includes("positions is unavailable")
  )
);

const stale = structuredClone(runtime);
stale.snapshot.as_of = "2026-09-14T11:00:00Z";
const staleResult = validateBrokerRuntime(stale, ["positions"], 300, now);
assert.equal(staleResult.runtime_status, "DATA INCOMPLETE");
assert.ok(
  staleResult.blocking_issues.some((issue) => issue.includes("snapshot is stale"))
);

console.log("Cloudflare runtime tests passed.");
