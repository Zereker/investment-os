import skill from "../skills/investment-os/SKILL.md";
import constitution from "../skills/investment-os/references/00-constitution.md";
import daily from "../skills/investment-os/references/01-daily.md";
import monthly from "../skills/investment-os/references/02-monthly.md";
import periodic from "../skills/investment-os/references/03-periodic.md";
import committee from "../skills/investment-os/references/04-committee.md";
import state from "../skills/investment-os/references/05-state.md";
import dataContract from "../skills/investment-os/references/06-data-contract.md";
import { BROKER_RUNTIME_CONTRACT, SERVER_NAME, SERVER_VERSION } from "./contract";

export const taskReferences = {
  daily: {
    "00-constitution.md": constitution,
    "01-daily.md": daily,
    "05-state.md": state
  },
  monthly_funding: {
    "00-constitution.md": constitution,
    "02-monthly.md": monthly,
    "05-state.md": state,
    "06-data-contract.md": dataContract
  },
  periodic_review: {
    "00-constitution.md": constitution,
    "03-periodic.md": periodic
  },
  transaction_judgment: {
    "00-constitution.md": constitution,
    "04-committee.md": committee
  },
  research: {
    "00-constitution.md": constitution,
    "04-committee.md": committee
  },
  broker_execution: {
    "00-constitution.md": constitution,
    "05-state.md": state,
    "06-data-contract.md": dataContract
  },
  system_audit: {
    "00-constitution.md": constitution,
    "06-data-contract.md": dataContract
  }
} as const;

export type InvestmentTask = keyof typeof taskReferences;

export function isInvestmentTask(value: string): value is InvestmentTask {
  return Object.prototype.hasOwnProperty.call(taskReferences, value);
}

export function loadTaskContext(task: InvestmentTask) {
  return {
    task,
    server: { name: SERVER_NAME, version: SERVER_VERSION },
    broker_runtime_contract: BROKER_RUNTIME_CONTRACT,
    skill,
    references: taskReferences[task],
    source: "bundled canonical Investment OS distribution",
    runtime_data_persisted: false
  };
}
