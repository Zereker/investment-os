import { reconcileNav, unavailableReconciliation } from "./reconciliation";
import { BROKER_RUNTIME_SCHEMA_VERSION, CAPABILITY_NAMES, CAPABILITY_STATES as CAPABILITY_STATE_VALUES } from "./contract";

const CAPABILITY_STATES = new Set<string>(CAPABILITY_STATE_VALUES);

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
  snapshot: { as_of: string; source: string; timezone: string; currency_basis: string };
  capabilities: Record<string, CapabilityInput>;
  required_capabilities?: string[];
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
      currency_basis: basis,
      base_currency: basis,
      selected_balance_label: selected.currency,
      selection_reason: baseRows.length > 0 ? "IBKR BASE aggregate selected for account currency basis" : "currency-basis row selected",
      by_currency: rows
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
    return unavailableReconciliation("NAV reconciliation inputs are unavailable");
  }

  return reconcileNav(nav, cash, positions);
}

export function assembleBrokerRuntime(input: BrokerRuntimeInput) {
  const runtime: JsonObject = {
    schema_version: BROKER_RUNTIME_SCHEMA_VERSION,
    identity: input.identity,
    snapshot: input.snapshot,
    capabilities: {},
    observations: {}
  };
  const states = runtime.capabilities as JsonObject;
  const observations = runtime.observations as JsonObject;
  const issues: string[] = [];
  const required = new Set(input.required_capabilities ?? []);
  const requiredIssues: string[] = [];
  const optionalIssues: string[] = [];

  for (const name of CAPABILITY_NAMES) {
    const capability = input.capabilities[name];
    if (!capability) {
      states[name] = "not_requested";
      runtime[name] = null;
      if (required.has(name)) requiredIssues.push(`${name}: required connector result was not supplied`);
      continue;
    }

    const declared = CAPABILITY_STATES.has(capability.status)
      ? capability.status
      : "unavailable";
    if (declared !== capability.status) {
      (required.has(name) ? requiredIssues : optionalIssues).push(`${name}: invalid connector status ${JSON.stringify(capability.status)}`);
    }

    if (declared === "available" && capability.data === undefined) {
      states[name] = "unavailable";
      runtime[name] = null;
      (required.has(name) ? requiredIssues : optionalIssues).push(`${name}: available connector result has no data`);
    } else if (declared === "available") {
      const normalized = normalizeConnectorData(
        name,
        capability.data,
        input.snapshot.currency_basis
      );
      if (normalized.issue) {
        states[name] = "unavailable";
        runtime[name] = null;
        (required.has(name) ? requiredIssues : optionalIssues).push(`${name}: ${normalized.issue}`);
      } else {
        states[name] = declared;
        runtime[name] = normalized.value;
      }
    } else {
      states[name] = declared;
      runtime[name] = null;
      if (declared !== "not_requested" && declared !== "not_applicable") {
        (required.has(name) ? requiredIssues : optionalIssues).push(
          `${name}: connector capability is ${declared}${capability.error ? ` (${capability.error})` : ""}`
        );
      } else if (required.has(name)) requiredIssues.push(`${name}: required capability is ${declared}`);
    }

    if (capability.source || capability.observed_at) {
      observations[name] = {
        source: capability.source,
        observed_at: capability.observed_at
      };
    }
  }

  runtime.reconciliation = reconcile(runtime);
  issues.push(...requiredIssues, ...optionalIssues);
  const requiredStatus = requiredIssues.length === 0 ? "PASS" : "DATA INCOMPLETE";
  const optionalStatus = optionalIssues.length === 0 ? "PASS" : "PARTIAL";
  return {
    adapter_status: requiredStatus === "DATA INCOMPLETE" ? "DATA INCOMPLETE" : optionalStatus === "PARTIAL" ? "PASS_WITH_OPTIONAL_GAPS" : "PASS",
    required_status: requiredStatus,
    optional_status: optionalStatus,
    adapter_issues: issues,
    runtime,
    schema_version: BROKER_RUNTIME_SCHEMA_VERSION,
    runtime_data_persisted: false
  };
}
