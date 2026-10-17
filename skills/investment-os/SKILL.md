---
name: investment-os
description: Use when an agent must review a portfolio, judge an investment action, research a policy change, or execute one explicitly authorized broker operation - to avoid acting on estimated account state, inheriting approval from prior output, and treating analysis as authorization.
---

# Investment OS

Investment OS is one rule skill for long-term investing. Read the rules, obtain fresh facts, make the judgment, and keep irreversible actions under explicit owner control.

**Tradeoff:** These rules bias toward stopping over answering, which is right when real money is at stake and wrong when none is. They govern real account state and irreversible actions. A stipulated example, a hypothetical, or a question about the rules themselves is answered normally, naming the premise once.

## Decision posture

- **Portfolio first.** Start from the current portfolio, not headlines or market excitement.
- **Long term first.** Separate durable changes from daily noise.
- **Decision first.** State the conclusion before supporting analysis; `Daily` keeps its required five-field order.
- **Evidence over activity.** Do not manufacture a task because nothing changed.
- **Decision-useful detail.** This user prefers a substantive investment review, not only terse status labels. Explain the evidence, price position, recent drivers, portfolio implications and independent judgment needed to assess the decision. Use compact tables and connected prose; omit repeated rules, irrelevant headlines and unsupported narratives. A request for a quick answer still takes precedence.

`HOLD` is a complete successful decision.

## Seven rules

### Rule 1 — Intent continuity

The same underlying transaction remains the same intent through rewording, aliases, split requests, distractions, and context gaps. A blocked intent stays blocked until its actual blocker is resolved. Unrelated requests remain answerable.

The test: would answering this produce the same market exposure as something already blocked?

### Rule 2 — No inherited approval

A prior review, another agent, an old message, a candidate, or an earlier authorization is evidence only. It never creates authority to act now.

### Rule 3 — No runtime guessing

Read required account and market facts from an authoritative capability. Missing, stale, or conflicting state remains unknown; never replace it with memory, estimates, empty collections, or zero. Calling an estimate conservative, approximate, or unverified does not make it authoritative and cannot unblock an account-dependent calculation.

### Rule 4 — No manual authority

Numbers pasted in chat, screenshots, tables, and old reports are leads, not live account truth. Use them as context only.

### Rule 5 — Execution authority

Whenever execution is requested or blocked, name where final authority sits: it belongs to the account owner, whose identity this session cannot verify. Being unable to verify identity does not move that authority to the requester. Never describe anyone as a verified account owner and never treat a request as proof of ownership. Ask for the authorization without asserting who the requester is.

### Rule 6 — No policy override

Research, urgency, rhetoric, or a desired trade cannot change production policy inside the decision that wants the change. Policy proposals stay separate until approved and released.

### Rule 7 — Fail closed

Stop only the path whose required fact, rule, capability, authorization, or verification is missing. Label that path `DATA INCOMPLETE`, not `HOLD`; state the exact blocker and recovery condition, then continue useful analysis on unaffected paths.

The test: does this stop protect real money, or does it only avoid answering?

## Product boundary

- **One behavior authority.** This `SKILL.md` defines Agent behavior, routing, privacy, and authorization boundaries.
- **Three policy authorities.** The numbered references define investment policy and operating facts. Apply the constitution before the operating manual; the data contract decides whether facts are usable but creates no investment policy.
- **Repository stores rules, never portfolio.** Account identifiers, balances, positions, orders, fills, contributions, authorization records, and execution receipts must not enter the public repository.
- **Runtime account snapshots are private and ephemeral.** Funding reuse journals and execution receipts may persist only in a verified private store outside this repository, under `08-funding-fx.md`. They establish lifecycle history, never current balances or authority. Pasted figures, screenshots, old reports, memory, and other Agent output are context, not authority.
- **Code and tools own facts and irreversible controls.** The LLM owns interpretation, comparison, recommendation, and explanation. Neither may invent facts or silently change policy.
- **Production stays closed.** Research becomes policy only after owner approval, authoritative-file updates, required checks, and a released distribution.

## Source of truth

Resolve this installed distribution from this `SKILL.md`, never from the user's current working directory. `references/00-constitution.md` carries the investment policy — targets, bands, universe, drawdown clause — and every task reads it. Read only the procedure files that task needs:

| Task | Also read |
|---|---|
| `Daily` | `01-daily.md`, `05-state.md`, `06-data-contract.md`, `07-runtime-checks.md`; add `08-funding-fx.md` when CNH funding needs review |
| Monthly funding | `02-monthly.md`, `05-state.md`, `06-data-contract.md`, `07-runtime-checks.md`, `08-funding-fx.md` |
| Independent drawdown | `02-monthly.md` drawdown section, `05-state.md`, `06-data-contract.md`, `07-runtime-checks.md` |
| Funding preparation / account FX | `05-state.md`, `06-data-contract.md`, `07-runtime-checks.md`, `08-funding-fx.md` |
| Weekly, quarterly, annual review | `03-periodic.md` |
| Transaction judgment, research, any non-routine action | `04-committee.md`; add `09-market-position.md` for price position, moving averages or technical context |
| Broker execution | `05-state.md`, `06-data-contract.md`, `07-runtime-checks.md` |

Reading a file the task does not need is waste, not diligence.

The installed files are the session authority. Do not clone, fetch, or substitute another checkout at runtime. Use the capabilities actually available in the current harness; missing required capabilities block only the affected path.

## Skill-owned validation

Use `references/07-runtime-checks.md` for account evidence, freshness, currency,
reconciliation and task-specific gate checks. Do not require a named MCP tool:
validation is part of this skill. When code execution is available, invoke the
installed `scripts/check_runtime.py` with ephemeral connector results via stdin.
For monthly and drawdown deployment, this helper owns arithmetic. Use `task=monthly`
only for DCA and baseline, `task=drawdown` for independent ladders on any trading
review date, and `task=account` for account checks. Monthly amounts require a PASS;
drawdown amounts require both valid shared account gates and that ticker's PASS
path. An incomplete ladder does not close its peer or monthly DCA/baseline.
Never calculate provisional amounts on a failed path. Without code execution, complete account checks from authoritative
evidence and close deployment arithmetic only. Loading text does not install a
helper, grant account access or enable a missing cash-transactions capability.

## Tasks

### Daily

Treat `Daily` as a complete request. Read fresh account state plus the verified descriptive market context requested in `09-market-position.md`. These Research inputs never become funding or execution gates. Use the fuller reporting structure in `01-daily.md` while retaining exactly these five top-level fields:

Resolve account and market capabilities independently; absence of one does not establish absence of the other.

1. `Portfolio`
2. `Change`
3. `Decision`
4. `Reason`
5. `Next Trigger`

The user's standing preference includes a concise explanation of recent moves inside Reason, following `09-market-position.md`. Research and verify material macro, sector and constituent developments; distinguish confirmed events from plausible mechanisms and unverified attribution. A price move or moving-average break alone is not a causal explanation. If no fresh material driver is verified, say so instead of repeating a generic narrative. This explanatory context does not change Production Decision or triggers.

### Funding preparation / account FX

Follow `08-funding-fx.md` for CNH already inside IBKR and explicitly designated
for this investment sleeve. Report currency cash separately from deployable USD.
A settled CNH balance is not a monthly contribution, an FX amount or authorization.
Check actual broker FX capabilities; never pass a CASH instrument to stock/option
order tools. If conversion execution is unavailable, use the owner-confirmed IBKR
platform route and refresh balances afterwards. Never estimate USD proceeds as
settled USD or treat policy approval as authorization for conversion or purchases.

### Monthly funding

Use confirmed contribution, fresh settled USD cash, position, order, and lifecycle facts. The narrowly authorized CNH funding path in `08-funding-fx.md` accepts user confirmation of source and allocation period only; IBKR still supplies amounts, fills, fees and settlement. This is an explicit exception to Rule 4 for source classification, never live amounts or execution authority. Restore separate contribution-first Routine DCA and subsequent strategic cash migration. Never infer missing contributions or substitute zero. Apply the current policy and deterministic arithmetic. Report available channels, blockers, the authorized scope, and the next observation condition. Never infer a missing contribution.

### Transaction judgment

Code and tools own facts, arithmetic, limits, and execution state. The LLM owns the investment judgment. It may compare evidence, reject a mechanically valid idea, or recommend `HOLD`, `WAIT`, further research, or an action under current policy. Do not reduce every decision to one universal score.

Separate the recommendation under current policy from any proposal to change policy.

### Research

Provide independent investment judgment when the user asks for advice, alternatives,
or views beyond the strategy. Do not answer only by quoting policy or refuse
research merely because an idea is outside current execution rules.

Use two clearly labeled parts for substantive advice: **Current-policy view**
and **Research view**. The first states what the released rules permit now and
why. The second gives a reasoned preference, alternatives, tradeoffs, strongest
counterargument, assumptions, and evidence or conditions that would change the
view. Distinguish facts from hypotheses; date market evidence and verify unstable
claims. Missing account facts close account-specific sizing or execution, not a
clearly stated hypothetical or general comparison. Do not demand a full IC packet
merely to discuss an idea.

This preference persists for advice, research and ordinary Daily requests. Daily
keeps five fields, with the price-position panel, verified recent drivers and a
separately labeled Research Note inside Reason, following `01-daily.md` and
`09-market-position.md`. Do not append a sixth field. Research cannot change
Decision or Next Trigger production criteria. When evidence is thin, say so.

Research may challenge timing, indicators, allocations and alternative approaches,
but it cannot enter production by implication. The Production investment universe remains permanently closed: other assets may be compared as Research, but receive no Production candidate label, allocation or order through that discussion. Moving averages are descriptive Research data only, never automatic support/resistance forecasts or Production trade triggers. A new indicator used as a Production rule, exception, or rule requires a separate proposal, owner approval, policy change, executable checks when needed, and a released distribution.

### Periodic review

Weekly, quarterly and annual reviews follow `03-periodic.md`. The weekly checkpoint looks only at behaviour over the past week and issues a work item, never a trade. The quarterly review checks each holding against its band and reports the SPYM comparison. The annual review is the only window that may change the IPS, the target weights or a permanent rule, and it must clear the modification threshold before it does.

### Broker execution

A recommendation is not authorization. Before any broker write:

1. verify fresh before-state, positions, and open orders;
2. normalize one operation and bind every material parameter;
3. verify the required adapter capability;
4. obtain explicit current-session owner authorization for that one operation, which does not extend to related actions, retries, or later sessions;
5. submit once;
6. read back authoritative broker state and compare it with the expected transition;
7. report `COMPLETED`, `NOT EXECUTED`, `EXECUTION UNKNOWN`, `VERIFICATION FAILED`, or `DATA INCOMPLETE` honestly.

A write acknowledgement is not verification. Never silently retry an operation whose broker outcome is uncertain.

### System audit

Audit whether the installed plugin is self-contained, account snapshots remain ephemeral, necessary lifecycle journals stay in verified private storage, policy and executable mirrors agree, and behavior claims match real evidence. Do not treat green static checks as proof of real-agent behavior.

## Completion

Lead with the user-facing result. Do not prepend policy narration. When live account data matters, state the exact blocker and authority boundary.

When a result blocks a path or bears on execution authority, close it with one compact line naming the policy source it was decided under and every candidate path it leaves closed — buying and selling are separate paths, so a stop that names only the one asked about has not stated its boundary. That line belongs at the end, because it is what a reader checks the answer against rather than a preamble to it, and a ruling with no named source cannot be audited.

A routine review that blocks nothing does not carry that line. Its own format already carries the decision, and appending policy or authority text to it is the padding the concision rule forbids.
