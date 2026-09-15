import assert from "node:assert/strict";

import { assembleBrokerRuntime, type CapabilityInput } from "./adapter";
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
assert.deepEqual(passed.reconciliation, {
  status: "PASS",
  issues: [],
  nav: 100000,
  cash: 15000,
  positions_market_value: 85000,
  component_total: 100000,
  absolute_difference: 0,
  relative_difference: 0,
  tolerance: 0.005
});

const withinTolerance = structuredClone(runtime);
withinTolerance.positions[0].market_value = 84900;
const withinToleranceResult = validateBrokerRuntime(
  withinTolerance,
  ["positions", "balances"],
  300,
  now
);
assert.equal(withinToleranceResult.runtime_status, "PASS");
assert.equal(withinToleranceResult.reconciliation?.absolute_difference, 100);
assert.equal(withinToleranceResult.reconciliation?.relative_difference, 0.001);

const outsideTolerance = structuredClone(runtime);
outsideTolerance.positions[0].market_value = 84400;
const outsideToleranceResult = validateBrokerRuntime(
  outsideTolerance,
  ["positions", "balances"],
  300,
  now
);
assert.equal(outsideToleranceResult.runtime_status, "DATA INCOMPLETE");
assert.equal(outsideToleranceResult.reconciliation?.absolute_difference, 600);
assert.ok(
  outsideToleranceResult.blocking_issues.some((issue) =>
    issue.includes("limit 0.50%")
  )
);

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
assert.equal(blocked.reconciliation.positions_market_value, null);
assert.equal(blocked.reconciliation.tolerance, 0.005);
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

const connectorCapabilities: Record<string, CapabilityInput> = Object.fromEntries(
  Object.entries(capabilities).map(([name]) => [
    name,
    {
      status: "available",
      data: runtime[name as keyof typeof runtime],
      source: "synthetic-adapter",
      observed_at: "2026-09-14T12:00:00Z"
    }
  ])
);
const assembled = assembleBrokerRuntime({
  identity: runtime.identity,
  snapshot: runtime.snapshot,
  capabilities: connectorCapabilities
});
assert.equal(assembled.adapter_status, "PASS");
assert.equal(
  validateBrokerRuntime(
    assembled.runtime,
    ["positions", "balances", "open_orders"],
    300,
    now
  ).runtime_status,
  "PASS"
);

const rawEnvelopeCapabilities = structuredClone(connectorCapabilities);
rawEnvelopeCapabilities.balances = {
  status: "available",
  data: {
    balances: [
      { currency: "BASE", cash_balance: "15000", settled_cash: "14900" },
      { currency: "USD", cash_balance: 14000, settled_cash: 13900 }
    ]
  },
  source: "IBKR Balances",
  observed_at: "2026-09-14T12:00:00Z"
};
rawEnvelopeCapabilities.positions = {
  status: "available",
  data: {
    positions: [{ symbol: "SYNTHETIC", market_value: "85000" }]
  },
  source: "IBKR Positions",
  observed_at: "2026-09-14T12:00:00Z"
};
const assembledRawEnvelope = assembleBrokerRuntime({
  identity: runtime.identity,
  snapshot: runtime.snapshot,
  capabilities: rawEnvelopeCapabilities
});
assert.equal(assembledRawEnvelope.adapter_status, "PASS");
assert.deepEqual(assembledRawEnvelope.runtime.balances, {
  total_cash: 15000,
  settled_cash: 14900,
  currency: "BASE"
});
assert.deepEqual(assembledRawEnvelope.runtime.positions, [
  { symbol: "SYNTHETIC", market_value: 85000 }
]);
assert.equal(
  validateBrokerRuntime(
    assembledRawEnvelope.runtime,
    ["positions", "balances", "open_orders"],
    300,
    now
  ).runtime_status,
  "PASS"
);

const unusableBalanceEnvelope = structuredClone(connectorCapabilities);
unusableBalanceEnvelope.balances = {
  status: "available",
  data: { balances: [{ currency: "EUR", cash_balance: 15000 }] },
  source: "IBKR Balances",
  observed_at: "2026-09-14T12:00:00Z"
};
const assembledUnusableBalance = assembleBrokerRuntime({
  identity: runtime.identity,
  snapshot: runtime.snapshot,
  capabilities: unusableBalanceEnvelope
});
assert.equal(assembledUnusableBalance.adapter_status, "WARN");
assert.equal(assembledUnusableBalance.runtime.balances, null);
assert.equal(
  (assembledUnusableBalance.runtime.capabilities as Record<string, string>)
    .balances,
  "unavailable"
);

const missingBalances = structuredClone(connectorCapabilities);
missingBalances.balances = {
  status: "unavailable",
  error: "MCP Internal error"
};
const assembledWithoutBalances = assembleBrokerRuntime({
  identity: runtime.identity,
  snapshot: runtime.snapshot,
  capabilities: missingBalances
});
assert.equal(assembledWithoutBalances.adapter_status, "WARN");
assert.equal(assembledWithoutBalances.runtime.balances, null);
assert.equal(
  validateBrokerRuntime(
    assembledWithoutBalances.runtime,
    ["balances"],
    300,
    now
  ).runtime_status,
  "DATA INCOMPLETE"
);

const staleMarketInputs = structuredClone(connectorCapabilities);
staleMarketInputs.market_inputs = {
  status: "stale",
  data: { last_bar: "2025-12-20" },
  source: "IBKR historical data",
  observed_at: "2026-09-14T12:00:00Z"
};
const assembledWithStaleMarket = assembleBrokerRuntime({
  identity: runtime.identity,
  snapshot: runtime.snapshot,
  capabilities: staleMarketInputs
});
assert.equal(assembledWithStaleMarket.runtime.market_inputs, null);
assert.equal(
  validateBrokerRuntime(
    assembledWithStaleMarket.runtime,
    ["positions", "balances"],
    300,
    now
  ).runtime_status,
  "PASS"
);
assert.equal(
  validateBrokerRuntime(
    assembledWithStaleMarket.runtime,
    ["market_inputs"],
    300,
    now
  ).runtime_status,
  "DATA INCOMPLETE"
);

console.log("Cloudflare runtime tests passed.");
