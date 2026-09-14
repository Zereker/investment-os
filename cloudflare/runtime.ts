const VALID_CAPABILITY_STATES = new Set([
  "available",
  "unavailable",
  "stale",
  "conflicting"
]);

const REQUIRED_SECTIONS = [
  "identity",
  "snapshot",
  "capabilities",
  "observations",
  "account_summary",
  "balances",
  "positions",
  "open_orders",
  "cash_transactions",
  "market_inputs",
  "alert_inventory",
  "standing_automations",
  "reconciliation"
] as const;

type JsonObject = Record<string, unknown>;

function object(value: unknown): JsonObject | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as JsonObject)
    : null;
}

function number(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function timestamp(value: unknown): number | null {
  if (typeof value !== "string" || value.trim() === "") return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) && /(?:Z|[+-]\d\d:\d\d)$/.test(value)
    ? parsed
    : null;
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
    const candidate = record
      ? (record.market_value ?? record.marketValue)
      : item;
    const parsed = number(candidate);
    if (parsed === null) return null;
    values.push(parsed);
  }
  return values;
}

export function validateBrokerRuntime(
  runtime: JsonObject,
  requiredCapabilities: string[],
  maxAgeSeconds = 300,
  nowMs = Date.now()
) {
  const issues: string[] = [];
  for (const section of REQUIRED_SECTIONS) {
    if (!(section in runtime)) issues.push(`missing runtime section: ${section}`);
  }

  const capabilities = object(runtime.capabilities);
  if (!capabilities) issues.push("capabilities must be an object");
  const observations = object(runtime.observations);
  if (!observations) issues.push("observations must be an object");

  const observedTimes: number[] = [];
  for (const name of requiredCapabilities) {
    const state = capabilities?.[name];
    if (typeof state !== "string" || !VALID_CAPABILITY_STATES.has(state)) {
      issues.push(`required capability ${name} is not declared`);
      continue;
    }
    if (state !== "available") {
      issues.push(`required capability ${name} is ${state}`);
      const value = runtime[name];
      const disguisedMissing =
        value === 0 ||
        value === "" ||
        (Array.isArray(value) && value.length === 0) ||
        (object(value) !== null && Object.keys(value as JsonObject).length === 0);
      if (disguisedMissing) {
        issues.push(
          `unavailable capability ${name} must use null, not an empty or zero value`
        );
      }
      continue;
    }
    if (runtime[name] === null || runtime[name] === undefined) {
      issues.push(`available capability ${name} has no value`);
    }
    const observation = object(observations?.[name]);
    if (!observation) {
      issues.push(`available capability ${name} has no observation metadata`);
      continue;
    }
    if (!observation.source) {
      issues.push(`observation ${name}.source is required`);
    }
    const observedAt = timestamp(observation.observed_at);
    if (observedAt === null) {
      issues.push(
        `observation ${name}.observed_at must be an ISO-8601 timezone-aware timestamp`
      );
      continue;
    }
    const ageSeconds = (nowMs - observedAt) / 1000;
    if (ageSeconds < -5) {
      issues.push(`observation ${name} timestamp is in the future`);
    } else if (ageSeconds > maxAgeSeconds) {
      issues.push(
        `observation ${name} is stale (${Math.trunc(ageSeconds)}s old; limit ${maxAgeSeconds}s)`
      );
    }
    observedTimes.push(observedAt);
  }

  const snapshot = object(runtime.snapshot);
  if (!snapshot) {
    issues.push("snapshot must be an object");
  } else {
    const asOf = timestamp(snapshot.as_of);
    if (asOf === null) {
      issues.push("snapshot.as_of must be an ISO-8601 timezone-aware timestamp");
    } else {
      const ageSeconds = (nowMs - asOf) / 1000;
      if (ageSeconds < -5) issues.push("snapshot timestamp is in the future");
      else if (ageSeconds > maxAgeSeconds) {
        issues.push(
          `snapshot is stale (${Math.trunc(ageSeconds)}s old; limit ${maxAgeSeconds}s)`
        );
      }
    }
    if (!snapshot.source) issues.push("snapshot.source is required");
    if (!snapshot.timezone) issues.push("snapshot.timezone is required");
    if (!snapshot.currency_basis) {
      issues.push("snapshot.currency_basis is required");
    }
  }

  const reconciliation = object(runtime.reconciliation);
  if (!reconciliation) {
    issues.push("reconciliation must be an object");
  } else {
    if (reconciliation.status !== "PASS") {
      issues.push("reconciliation status is not PASS");
    }
    if (Array.isArray(reconciliation.issues)) {
      for (const issue of reconciliation.issues) {
        if (typeof issue === "string") issues.push(`reconciliation: ${issue}`);
      }
    }
  }

  const summary = object(runtime.account_summary);
  const balances = object(runtime.balances);
  const nav = number(summary?.net_liquidation);
  const cash = number(balances?.total_cash ?? balances?.cash);
  const positions = positionValues(runtime.positions);
  if (nav === null || cash === null || positions === null) {
    issues.push("actual reconciliation inputs are unavailable");
  } else {
    const difference = Math.abs(nav - (cash + positions.reduce((a, b) => a + b, 0)));
    const tolerance = Math.max(1, Math.abs(nav) * 0.0001);
    if (difference > tolerance) {
      issues.push(
        `NAV reconciliation failed: difference ${difference.toFixed(2)} exceeds tolerance ${tolerance.toFixed(2)}`
      );
    }
  }

  let observationSkewSeconds: number | null = null;
  if (observedTimes.length > 0) {
    observationSkewSeconds =
      (Math.max(...observedTimes) - Math.min(...observedTimes)) / 1000;
    if (observationSkewSeconds > maxAgeSeconds) {
      issues.push(
        `required capability observations are not a coherent snapshot (${Math.trunc(observationSkewSeconds)}s skew; limit ${maxAgeSeconds}s)`
      );
    }
  }

  return {
    runtime_status: issues.length === 0 ? "PASS" : "DATA INCOMPLETE",
    blocking_issues: issues,
    observation_skew_seconds: observationSkewSeconds
  };
}
