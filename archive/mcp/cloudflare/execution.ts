import { createHash } from "node:crypto";

type JsonObject = Record<string, unknown>;

export const REQUIRED_STAGES = [
  "PREPARED", "CAPABILITY_CHECKED", "AUTHORIZED", "EXECUTED",
  "READ_BACK", "VERIFIED", "COMPLETED"
] as const;

const TERMINAL = new Set(["COMPLETED", "NOT EXECUTED", "EXECUTION UNKNOWN", "VERIFICATION FAILED"]);

function object(value: unknown): JsonObject | null {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? value as JsonObject : null;
}

function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value !== null && typeof value === "object") {
    return `{${Object.entries(value as JsonObject).sort(([a], [b]) => a.localeCompare(b))
      .map(([key, item]) => `${JSON.stringify(key)}:${canonical(item)}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

export function operationDigest(operation: JsonObject): string {
  return createHash("sha256").update(canonical(operation), "utf8").digest("hex");
}

export function validateBrokerExecution(record: JsonObject) {
  const operation = object(record.operation);
  if (!operation || Object.keys(operation).length === 0) {
    return { status: "NOT EXECUTED", issues: ["missing normalized operation"], passed: false };
  }
  const issues: string[] = [];
  const authorization = object(record.authorization) ?? {};
  if (authorization.scope !== "single-operation-current-session") issues.push("authorization scope must be single-operation-current-session");
  if (authorization.operation_digest !== operationDigest(operation)) issues.push("authorization does not match normalized operation");
  if (!authorization.owner_explicit) issues.push("explicit owner authorization missing");
  if (!authorization.session_id) issues.push("authorization session_id missing");
  const adapter = object(record.adapter) ?? {};
  const supported = new Set(Array.isArray(adapter.supported_capabilities) ? adapter.supported_capabilities : []);
  const capability = record.capability;
  if (typeof capability !== "string" || !capability.startsWith("Broker.")) issues.push("invalid broker capability");
  else if (!supported.has(capability)) issues.push("adapter does not support required capability");
  const status = typeof record.status === "string" ? record.status : "NOT EXECUTED";
  if (!TERMINAL.has(status)) issues.push("invalid terminal status");
  const count = record.submit_count;
  if (!Number.isInteger(count) || (count as number) < 0) issues.push("invalid submit_count");
  if (typeof count === "number" && count > 1) issues.push("operation submitted more than once");
  if (issues.length) return { status: count === 0 ? "NOT EXECUTED" : "EXECUTION UNKNOWN", issues, passed: false };
  if (status === "NOT EXECUTED") {
    if (count !== 0) issues.push("NOT EXECUTED conflicts with submit_count");
    return { status, issues, passed: false };
  }
  if (count !== 1) issues.push("executed terminal state requires exactly one submit");
  const stages = Array.isArray(record.stages) ? record.stages : [];
  if (stages.some((stage, index) => stage !== REQUIRED_STAGES[index])) issues.push("execution stages are out of order or skipped");
  const verification = object(record.verification) ?? {};
  if (status === "COMPLETED" || status === "VERIFICATION FAILED") {
    if (!object(record.write_result)) issues.push("write_result missing");
    if (!object(record.read_back)) issues.push("authoritative read_back missing");
    if (!verification.performed) issues.push("verification not performed");
    if (typeof verification.evidence !== "string" || !verification.evidence.trim()) issues.push("verification evidence missing");
  }
  if (status === "COMPLETED") {
    if (stages.length !== REQUIRED_STAGES.length) issues.push("COMPLETED requires full lifecycle");
    if (verification.passed !== true) issues.push("COMPLETED requires passed verification");
  } else if (status === "VERIFICATION FAILED" && verification.passed !== false) issues.push("VERIFICATION FAILED requires failed verification");
  else if (status === "EXECUTION UNKNOWN") {
    if (!stages.includes("EXECUTED")) issues.push("EXECUTION UNKNOWN requires a possible submission");
    if (stages.includes("VERIFIED") || stages.includes("COMPLETED")) issues.push("unknown execution cannot be verified or completed");
  }
  return { status, issues, passed: status === "COMPLETED" && issues.length === 0 };
}
