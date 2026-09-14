const CAPABILITY_NAMES = [
  "account_summary",
  "balances",
  "positions",
  "open_orders",
  "cash_transactions",
  "market_inputs",
  "alert_inventory",
  "standing_automations"
] as const;

const CAPABILITY_STATES = new Set([
  "available",
  "unavailable",
  "stale",
  "conflicting"
]);

type JsonObject = Record<string, unknown>;

export type CapabilityInput = {
  status: string;
  data?: unknown;
  source?: string;
  observed_at?: string;
  error?: string;
};

export type BrokerRuntimeInput = {
  identity: JsonObject;
  snapshot: JsonObject;
  capabilities: Record<string, CapabilityInput>;
};

function object(value: unknown): JsonObject | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as JsonObject)
    : null;
}

function number(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function positionValues(value: unknown): number[] | null {
  const items = Array.isArray(value)
    ? value
    : object(value)
      ? Object.values(value as JsonObject)
      : null;
  if (!items) return null;
  const values: number[] = [];
  for (const item of items) {
    const record = object(item);
    const parsed = number(record ? record.market_value ?? record.marketValue : item);
    if (parsed === null) return null;
    values.push(parsed);
  }
  return values;
}

function reconcile(runtime: JsonObject) {
  const summary = object(runtime.account_summary);
  const balances = object(runtime.balances);
  const nav = number(summary?.net_liquidation);
  const cash = number(balances?.total_cash ?? balances?.cash);
  const positions = positionValues(runtime.positions);
  if (nav === null || cash === null || positions === null) {
    return {
      status: "DATA INCOMPLETE",
      issues: ["NAV reconciliation inputs are unavailable"]
    };
  }

  const difference = Math.abs(nav - (cash + positions.reduce((sum, value) => sum + value, 0)));
  const tolerance = Math.max(1, Math.abs(nav) * 0.0001);
  if (difference > tolerance) {
    return {
      status: "DATA INCOMPLETE",
      issues: [
        `NAV reconciliation failed: difference ${difference.toFixed(2)} exceeds tolerance ${tolerance.toFixed(2)}`
      ]
    };
  }
  return { status: "PASS", issues: [] };
}

export function assembleBrokerRuntime(input: BrokerRuntimeInput) {
  const runtime: JsonObject = {
    identity: input.identity,
    snapshot: input.snapshot,
    capabilities: {},
    observations: {}
  };
  const states = runtime.capabilities as JsonObject;
  const observations = runtime.observations as JsonObject;
  const issues: string[] = [];

  for (const name of CAPABILITY_NAMES) {
    const capability = input.capabilities[name];
    if (!capability) {
      states[name] = "unavailable";
      runtime[name] = null;
      issues.push(`${name}: connector result was not supplied`);
      continue;
    }

    const declared = CAPABILITY_STATES.has(capability.status)
      ? capability.status
      : "unavailable";
    if (declared !== capability.status) {
      issues.push(`${name}: invalid connector status ${JSON.stringify(capability.status)}`);
    }

    if (declared === "available" && capability.data === undefined) {
      states[name] = "unavailable";
      runtime[name] = null;
      issues.push(`${name}: available connector result has no data`);
    } else if (declared === "available") {
      states[name] = declared;
      runtime[name] = capability.data;
    } else {
      states[name] = declared;
      runtime[name] = null;
      issues.push(
        `${name}: connector capability is ${declared}${capability.error ? ` (${capability.error})` : ""}`
      );
    }

    if (capability.source || capability.observed_at) {
      observations[name] = {
        source: capability.source,
        observed_at: capability.observed_at
      };
    }
  }

  runtime.reconciliation = reconcile(runtime);
  return {
    adapter_status: issues.length === 0 ? "PASS" : "WARN",
    adapter_issues: issues,
    runtime,
    runtime_data_persisted: false
  };
}

