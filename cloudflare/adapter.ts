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
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (
    typeof value === "string" &&
    /^-?(?:\d+\.?\d*|\.\d+)$/.test(value.trim())
  ) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
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

function normalizeBalances(
  value: unknown,
  currencyBasis: unknown
): { value: unknown; issue?: string } {
  const record = object(value);
  if (!record) return { value, issue: "balances data must be an object" };
  const directCash = number(record.total_cash ?? record.cash);
  if (directCash !== null) {
    return { value: { ...record, total_cash: directCash } };
  }

  const rows = Array.isArray(record.balances) ? record.balances : null;
  if (!rows) {
    return {
      value,
      issue: "balances data has no total_cash, cash, or balances array"
    };
  }
  const basis =
    typeof currencyBasis === "string" ? currencyBasis.toUpperCase() : null;
  const candidates = rows.filter((item) => {
    const row = object(item);
    const currency =
      typeof row?.currency === "string" ? row.currency.toUpperCase() : null;
    return currency === "BASE" || (basis !== null && currency === basis);
  });
  const baseRows = candidates.filter(
    (item) => {
      const currency = object(item)?.currency;
      return typeof currency === "string" && currency.toUpperCase() === "BASE";
    }
  );
  const selectedRows = baseRows.length > 0 ? baseRows : candidates;
  if (selectedRows.length !== 1) {
    return {
      value,
      issue:
        selectedRows.length === 0
          ? "balances array has no BASE or currency-basis row"
          : "balances array has multiple matching currency rows"
    };
  }

  const selected = object(selectedRows[0])!;
  const cash = number(selected.cash_balance ?? selected.cashBalance);
  if (cash === null) {
    return { value, issue: "selected balance row has no numeric cash_balance" };
  }
  const settled = number(selected.settled_cash ?? selected.settledCash);
  return {
    value: {
      total_cash: cash,
      ...(settled === null ? {} : { settled_cash: settled }),
      currency: selected.currency
    }
  };
}

function normalizePositions(value: unknown): { value: unknown; issue?: string } {
  const record = object(value);
  const rows = Array.isArray(value)
    ? value
    : Array.isArray(record?.positions)
      ? record.positions
      : null;
  if (!rows) return { value, issue: "positions data must be an array or positions envelope" };

  const normalized = [];
  for (const item of rows) {
    const position = object(item);
    if (!position) return { value, issue: "position row must be an object" };
    const marketValue = number(position.market_value ?? position.marketValue);
    if (marketValue === null) {
      return { value, issue: "position row has no numeric market_value" };
    }
    normalized.push({ ...position, market_value: marketValue });
  }
  return { value: normalized };
}

function normalizeConnectorData(
  name: string,
  value: unknown,
  currencyBasis: unknown
): { value: unknown; issue?: string } {
  if (name === "balances") return normalizeBalances(value, currencyBasis);
  if (name === "positions") return normalizePositions(value);
  return { value };
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
      const normalized = normalizeConnectorData(
        name,
        capability.data,
        input.snapshot.currency_basis
      );
      if (normalized.issue) {
        states[name] = "unavailable";
        runtime[name] = null;
        issues.push(`${name}: ${normalized.issue}`);
      } else {
        states[name] = declared;
        runtime[name] = normalized.value;
      }
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
