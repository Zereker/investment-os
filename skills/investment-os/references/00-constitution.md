# Investment Constitution

This file is the sole authority for all investment law in Investment OS: the mission and policy statement (IPS), the investment universe, target allocation, the transition plan, the sector tilt framework, and the tilt registry. Conflicts inside this file are resolved by part order: the earlier part prevails. It is amended only in an annual review or a formal release (the registry updates with IC decisions).

---

## Part 1: Investment Policy Statement (IPS)

### Mission and horizon

Achieve long-term wealth growth through disciplined asset allocation, a long-term QQQM growth tilt, and one strictly bounded semiconductor sector tilt. The horizon is 20 years or more; borrowing is never used to amplify the target allocation.

### Strategic structure

- Structural portfolio cash 15%;
- QQQM 28%;
- SPYM, the actual SOXX holding, and the SOXX stage reserve together form the 57% sleeve;
- SOXX is the only discretionary sector tilt vehicle, succeeding past single-stock semiconductor views such as MU and TSM. It is hard-capped industry beta, and is neither named nor evaluated as alpha;
- SOXX has a permanent hard cap of 6% (the historical 10% / 12.5% / 15% stages are void as of v4.0);
- Every other sector tilt has a target of 0%; any future semiconductor single stock must share the same 6% budget with SOXX.

### The structural cash decision, stated explicitly

15% cash is not an axiom. Its expected cost against the same portfolio held fully invested is roughly 0.45–0.75 percentage points per year, or roughly 9–14% lower terminal value over 20 years. The system pays that cost deliberately in exchange for:

1. drawdown deployment ammunition — executed mechanically by the drawdown deployment clause of this constitution;
2. a behavioral buffer — avoiding forced trades caused by volatility;
3. portfolio-level liquidity kept separate from the household emergency fund.

If the shadow benchmarks show that this cost has gone uncompensated by those functions over the long run, the annual review must reopen the 15% target itself.

### Invariant risk constraints

- Capture the long-term compounding of the US equity market while retaining enough liquidity to avoid forced trades during volatility.
- Accept the normal drawdowns of equity markets and of a growth tilt; do not accept uncapped industry, leverage, or liquidity risk.
- Known structural fact: the target Core by itself already carries roughly 18% semiconductor and roughly 40% information technology look-through exposure. The guardrails constrain additions to the discretionary tilt; the quarterly check discloses the combined figures.
- The cash buffer and the household emergency fund are managed separately; cash in this file means portfolio cash only.
- Replace forecasting and emotional decisions with a process that can be sustained for twenty years or more.

### Decision principles

1. The market creates most of the wealth, asset allocation protects it, and the growth tilt plus a bounded sector tilt enhance it.
2. The target allocation determines where money goes and its ceilings; routine DCA and the strategic baseline are entirely formula-driven, and no judgment gate may reduce or suspend them.
3. In a severe drawdown, cash is deployed in tiers under the drawdown deployment clause; the trigger looks only at price relative to the all-time-high close.
4. Risk guardrails and data integrity outrank any execution-stage target.
5. SOXX uses an ETF to reduce single-company risk, but that does not remove industry cycle, valuation, overlap, or concentration risk.
6. When a trade cannot be shown to be better than continuing to hold, do not trade.
7. New money and the published strategic baseline rebalance first; selling is the exception.
8. The system holds no valuation view; a high or low price neither reduces new money nor triggers a sale.

### Policy Benchmark

The passive policy benchmark remains:

- 15% USD Cash;
- 57% SPYM;
- 28% QQQM.

The benchmark resets to 15% / 57% / 28% only at the first pricing point of each calendar month. Within the month each sleeve drifts with its own return; it is not rebalanced on daily net-asset changes.

Monthly return:

\[
R_{B,t}=15\%\times r^{model}_{cash,t}+57\%\times r_{SPYM,t}+28\%\times r_{QQQM,t}
\]

SPYM and QQQM use total return including dividends. `r_cash_model` must take the month-start "15% of benchmark net assets, hypothetical USD cash balance" as principal and accrue monthly under the IBKR account plan, NAV-proportion rule, zero-interest threshold, currency, Segment and rate officially published for the same period (formula in the data dictionary part of `02-data-contract.md`). The cash principal must not be reset to 15% of daily benchmark net assets inside the month, and interest does not compound inside the month. Do not use a unit cash yield derived under real account constraints, and do not map real interest dollars onto the benchmark.

If the month-start hypothetical benchmark cash, the applicable account plan, or the rate cannot be reconstructed, the benchmark cash return and that period's Policy Benchmark are marked `N/A / DATA INCOMPLETE`; 0% must not be substituted silently.

The incremental value of SOXX is measured against an equal-size, same-period SPYM position, net of taxes, transaction costs, research time, and concentration cost.

### Shadow Benchmarks

Besides the Policy Benchmark, the system records two shadow benchmarks in parallel each month. They are report-only and trigger no trade:

- **SB-1, the fully invested policy portfolio**: 0% cash, 67% SPYM + 33% QQQM (the 57:28 ratio scaled up), reset at month start, with the same return rules as the Policy Benchmark. It measures the real cost of holding 15% cash.
- **SB-2, the single fund**: 100% SPYM total return including dividends, plus the same monthly contribution timing. It measures the net value of the entire system (cash, tilt, process) against the simplest workable alternative.

If any shadow-benchmark input is missing, record `N/A`; do not estimate. Shadow benchmarks participate in no trading gate.

### Governance cadence

- Monthly: in the current private session, update and report `A_actual`, `A_execution_cap`, `U`, cash, the Core gaps, execution results, and the shadow benchmarks. The execution cap may only advance one stage at a time and never above 6%.
- Quarterly: check combined look-through concentration (manual check table), whether SOXX is still warranted against SPYM, and the drawdown deployment cycle state.
- Annually: review the IPS, the target allocation, the 6% cap, the 15% cash, the Policy Benchmark, and the cumulative comparison against both shadow benchmarks.

This version does not constitute automatic trading authorization.

### Success criteria

Execute the target allocation over the long run, retain intentional growth exposure, control uncompensated risk, avoid behavioral errors, and answer whether the system creates net value with three comparisons:

1. SOXX against an equal-size, same-period SPYM position (does the tilt add value);
2. the real portfolio against the Policy Benchmark (does execution add value);
3. the Policy Benchmark against SB-1 and SB-2 (are the cash drag and the system's complexity worth their cost).

---

## Part 2: The Production Investment Universe

### 1. Current Production Scope

Investment OS currently manages exactly three purchasable instruments:

- `SPYM` — the core broad equity allocation;
- `QQQM` — the strategic growth allocation;
- `SOXX` — the only discretionary industry tilt.

Cash is a funding state and a risk buffer, not a fourth investment instrument.

### 2. Closed Universe Rule

Production is a closed investment universe. Anything other than SPYM, QQQM and SOXX:

- does not enter the daily purchase candidates;
- does not participate in target-gap calculations;
- does not enter Production because of news, popularity, a model recommendation, or a passing view;
- is not ranked for opportunity against the three production instruments;
- may only be disclosed as Legacy, an anomalous holding, or a Research subject.

The question the system answers every day is not "what in the market is worth buying", but:

> Among SPYM, QQQM and SOXX, does any instrument have authorization under the current rules today?

### 3. Treatment of Other Holdings

When other securities appear in the live account:

1. they must be listed separately in the daily report as `Legacy / Out-of-Universe`;
2. they must not be silently folded into SPYM, QQQM, or SOXX;
3. they must not automatically produce new purchase candidates;
4. selling, switching, or disposing of them must go through a full manual review or the existing transition rules;
5. an unidentifiable holding makes account health at least `WARN`, and `DATA INCOMPLETE` where required.

### 4. Admission of a New Asset

Adding a fourth production instrument requires, in order:

```text
Research → written proposal → owner approval → Constitution change
→ Operating System update → executable checks → version release
```

No AI, script, daily report, or ad-hoc session has authority to expand the investment universe on its own.

### 5. Daily Decision Boundary

Purchase conclusions in the daily report may carry only these three instrument labels:

- `BUY CANDIDATE — SPYM`
- `BUY CANDIDATE — QQQM`
- `BUY CANDIDATE — SOXX`

If no instrument qualifies, output `HOLD`, `WAIT`, or `DATA INCOMPLETE`; do not introduce another security in order to manufacture an action.

### 6. Privacy

This part defines the public policy scope only. It stores no real holdings, amounts, quantities, cost basis, or transaction records. Whether the real account holds other assets may only be read and processed inside a trusted runtime.

---

## Part 3: Target Asset Allocation

### v4.0 definitions

\[
A_{actual}=\frac{\text{SOXX live market value}}{\text{account net liquidation}}
\]

\[
A_{stage}=\text{the currently approved SOXX stage cap in the registry (Part 6 of this constitution); fixed at }6\%\text{ as of v4.0}
\]

\[
A_{basis}=\max(A_{actual},A_{stage}),\qquad
U=\max(A_{stage}-A_{actual},0)
\]

`U` is the SOXX allowance not yet filled. It is retained as a purpose label on cash, is not a separate asset layer, and authorizes no trade.

### Target math

SPYM, the actual SOXX holding, and the unfilled stage reserve together form the 57% sleeve; only when the allowance is fully used does this simplify to `SPYM + SOXX = 57%`.

| Sleeve | Target |
|---|---:|
| Structural cash | 15% |
| SOXX stage reserve | `U` |
| QQQM | 28% |
| SPYM | `57% − A_basis` |
| SOXX / sector tilt actual holding | `A_actual` |

When `A_actual≤A_stage`:

\[
15\%+U+28\%+(57\%-A_{stage})+A_{actual}=100\%
\]

If a market rise pushes `A_actual>A_stage`, then `U=0` and `A_basis=A_actual`, and the total is still 100%; additions freeze and the position enters review, with no automatic selling.

When evaluating the cash band, the physical cash target and permitted band are `15%+U` and `12%+U` to `18%+U` respectively; the drawdown deployment clause may temporarily lower the cash floor in tiers, per the drawdown deployment section. The stage reserve must not be double-counted against cash.

### The explicit cost of structural cash

The quantified cost of 15% cash and its three functions are an explicit decision of the Part 1 IPS and are not repeated here. The drawdown deployment rule is the execution mechanism for that function; if an annual review finds the cash function has been idle over the long run, the 15% target itself must be reopened.

### SOXX sector tilt authorization

- SOXX is a passive semiconductor industry ETF. Holding it is a hard-capped industry/cycle tilt (beta), not alpha; the system names and governs it accordingly.
- The permanent hard cap for SOXX is **6%** of the total portfolio (`A_stage=6%` is the final cap).
- The 10% / 12.5% / 15% governance stages once set in v3.4 are void as of v4.0. Basis: the 2026-07 measured combined look-through showed that at SOXX=15% the portfolio's semiconductor exposure would be about 31.7% and information technology about 47.4%, which is unreachable under the system's own guardrails.
- The current execution cap is `A_execution_cap=3%`; the execution cap advances 3%→4.5%→6%, one stage at a time, and never above `A_stage`.
- Every other sector tilt and every single stock carries a new-addition authorization of 0%; any future semiconductor stock or fund must share the same 6% budget with SOXX.
- A price trigger, a drawdown, or completed research never advances the execution stage on its own, and never authorizes a purchase on its own.

#### Restore-to-target vs tilt increase (v4.5)

The word "addition" used to conflate two different things; this section separates them. **The test is only whether `A_execution_cap` moved**:

> **Restore-to-target**: buying back the SOXX weight that a market decline pushed below the execution stage, **without raising** `A_execution_cap`. The risk budget is unchanged.
>
> **Tilt increase**: raising `A_execution_cap` itself (3%→4.5%→6%). The risk budget expands.

A restore is conceptually the same thing as "QQQM fell, so buy QQQM" — the target did not move, the market pushed the weight down. A restore therefore **runs on the monthly routine path**, and must satisfy **all** of:

1. after the trade, `A_actual ≤ min(A_execution_cap, A_stage)` — an existing constraint, not relaxed;
2. the current-quarter manual look-through check (`02-data-contract.md`, look-through check procedure) is valid; if it is expired or `DATA INCOMPLETE`, restores freeze;
3. the money comes only from `U`; it does not consume a drawdown deployment tranche and does not crowd out the SPYM / QQQM positive gaps;
4. the information-technology 50% freeze line and the single-issuer 10% freeze line both hold;
5. all four live IBKR reads succeed and there are no conflicting orders.

If any of these fails, the restore amount is `0` and the conclusion is `HOLD` or `DATA INCOMPLETE`; it **must not be downgraded to "buy part of it"**.

**A tilt increase still requires a full IC**, and the five-step gate in the registry part of this constitution is unchanged. The restore ceiling `min(A_execution_cap, A_stage)` is not relaxed by the restore running on the routine path; this clause adds no money and relaxes no cap.

| SOXX execution stage | SPYM target endpoint |
|---:|---:|
| 3% (current) | 51% |
| 4.5% | 51% |
| 6% (final cap) | 51% |

The SPYM target endpoint is given by `57%−A_basis`; since `A_stage` is fixed at 6%, the SPYM target is always 51%, and the execution stage only bounds `A_actual` after a single trade.

### Look-through concentration guardrails

The portfolio's combined look-through exposure is computed by the quarterly manual check (method in the look-through check procedure of `02-data-contract.md`), using each fund's latest official holdings/sector tables and combining direct holdings with ETF-embedded holdings.

Known structural fact (measured 2026-07): a Core of just 51% SPYM + 28% QQQM already carries roughly 18% semiconductor and roughly 40% information technology exposure. The guardrails therefore constrain **additions to the discretionary sector tilt**, not the existence of the Core:

- Combined information technology exposure above 45%: `WARN`, and the quarterly report must disclose it.
- Combined information technology exposure at or above 50%: freeze any discretionary tilt that would further increase technology exposure (SOXX and future equivalents); the SPYM / QQQM routine paths are not blocked by this item alone.
- Combined semiconductor and equipment exposure at or above 15% (the Core alone is roughly 18%, so this line is normally triggered): a **tilt increase** (advancing `A_execution_cap`) requires an explicit IC review and must confirm awareness of the current combined exposure in the Packet. A **restore-to-target** does not require an IC because of this line — it does not expand the risk budget, its ceiling remains the existing execution stage, and the concentration creep this line guards against is already bounded by that stage — but every restore must report post-trade combined semiconductor exposure in its output. The SPYM / QQQM routine paths are not blocked by this item alone.
- Combined single-issuer exposure above 8%: `WARN`; at or above 10%: freeze any discretionary tilt that increases that issuer's exposure, and place it under mandatory annual review.
- When missing, stale, or unclassified exposure could put a line over the limit: conclusions involving discretionary tilt additions are `WAIT / DATA INCOMPLETE`.
- A triggered guardrail restricts additions or requires review only; it never sells automatically.
- Risk guardrails outrank any SOXX execution-stage target.

### Drawdown Deployment

This clause makes structural cash genuinely deployable in a severe drawdown, and the trigger looks only at price:

- Trigger metric: the drawdown of the SPYM official/IBKR closing price relative to its all-time-high close, observed at each daily review.
- Tiers:

| Tier | Trigger | Released at this tier | Cumulative release | Cash after deployment (from 15%) |
|---:|---:|---:|---:|---:|
| T1 | `DD ≥ 10%` | 1.50pp of NAV | 1.50pp | 13.5% |
| T2 | `DD ≥ 15%` | 3.00pp | 4.50pp | 10.5% |
| T3 | `DD ≥ 20%` | 4.50pp | 9.00pp | 6.0% |
| T4 | `DD ≥ 25%` | 6.00pp | 15.00pp | **0%** |

Each tier releases a **graded fixed amount** (1:2:3:4) and buys only into SPYM / QQQM positive gaps; the four tiers total 15pp and deploy the entire 15% cash target down to the absolute floor `0+U`. **The absolute floor `0+U` is a hard stop that must never be crossed under any circumstance — cash may reach zero, but must never go negative.**

**Beyond a `DD` of 25%, no further tier unlocks.** The ammunition is spent at T4, cash stops at `0+U`, and from there it is rebuilt month by month with external new money only. Continuing declines produce **no** new deployment authorization, and **borrowing to add is forbidden** — this is not an oversight, it is the explicit v4.6 decision.

Fixed graded releases mean **the deeper the fall, the more is bought, and each purchase lands at a different price**; this clause makes no judgment about the bottom and simply increases mechanically with the decline.

The 1:2:3:4 gradient invests less in shallow drawdowns and more in deep ones, which is a trade-off the system accepts.

#### How zeroing out meets the no-margin red line

The upper bound on the deployment amount is `max(C − (0+U)×V, 0)`, leaving cash exactly at `U×V ≥ 0` after the trade — **the formula itself cannot make cash negative**. To hold the red line, execution must additionally satisfy:

- order quantities must be whole shares, and cash must not go negative after the trade **including commissions**; if an order would make cash negative, reduce it until cash ≥ 0.
- Subsequent fees, currency conversions, or dividend timing differences after cash reaches zero are covered by the owner with external contributions, and **must never be converted into margin borrowing**.
- The IPS no-leverage principle is unchanged. A deepening `DD` is not a reason to borrow (reaffirmed by the owner 2026-08-01).

**A deliberately accepted trade-off**: once cash reaches zero, the second function the IPS defines for cash — the behavioral buffer — effectively disappears at the deepest tier. This clause does not amend the IPS text; the ammunition function and the no-leverage principle both stand, and what is given up is the cushion at the deepest tier.

- Each tier executes at most once within the same drawdown cycle; the cycle resets after SPYM makes a new all-time-high close.
- Deployment runs the full data and execution checks of the monthly routine path (live IBKR, no margin, no conflicting orders, buy only into positive gaps); apart from `DD` reaching a tier, no other judgment item is introduced.
- Cash is thereafter rebuilt to `15%+U` month by month with external new money only; holdings must never be sold to rebuild cash.
- This clause uses no leverage, does not predict bottoms, and does not add deployment beyond the tiers because the decline continues.
- The cost that existed in v4.3 — "after T1 is spent at 10%, nothing further unlocks between 10% and 25%" — is eliminated: that range is now covered tier by tier by T2 (15%), T3 (20%) and T4 (25%).

The 25% endpoint and the zero floor are an explicit trade-off the system makes among ammunition utilization, entry quality, and the opportunity cost of cash.

**Known risk**: the data window reaches only 34.3% at its deepest and does not include a 2008-type decline (the S&P fell roughly 56%). Under this design cash is already at zero at `DD` 25%, and beyond that there is no deployment authorization however deep the decline goes, and no borrowing. This is a deliberately accepted trade-off; the falsification condition is in section 6 of the proposal.

#### Why the trigger uses SPYM only

This clause deploys structural cash held as crisis ammunition — four tiers totalling 15 percentage points of NAV, deploying the whole 15% cash target down to the absolute floor `0+U`, of which 12 percentage points sit below the normal cash floor of `12%+U`. The ammunition is finite, so the trigger must be a **broad market signal**; SPYM represents US large-cap equity and is this portfolio's broad-market proxy.

**Relative** moves between the Core instruments do not use this clause and are absorbed by the target weights: when one Core falls more than another, its actual weight drops below target and creates a positive gap, and `D` and `B` flow each month to the larger gap first, with no threshold and no trigger required. Drawdown deployment only unlocks the cash below the floor **additionally**, during a broad deep decline; a single Core falling while SPYM has not reached a tier is absorbed by rebalancing.

### Core instrument principles

- SPYM represents the broad US large-cap market core position.
- QQQM represents the Nasdaq-100 strategic growth engine; the 28% is a deliberate long-term growth tilt and is not mechanically trimmed because it overlaps SPYM.
- Do not switch frequently between SPY/QQQ and SPYM/QQQM for short-term liquidity, volume, or brand familiarity.
- Reopen the Core instrument selection only when fees, tracking quality, taxes, account restrictions, or product structure change materially.

### Rebalancing and selling

1. Routine DCA and the strategic baseline are computed from `A_basis` and `U` and buy only into SPYM / QQQM positive gaps; the amounts come entirely from the formulas and must not create a negative gap or exceed a target ceiling.
2. The SOXX stage reserve must not be redirected into SPYM when a guardrail triggers, and its existence must not force a SOXX purchase.
3. A **tilt increase** (advancing `A_execution_cap`) always goes through a full IC; a **restore-to-target** runs the monthly routine path under the five constraints in the section above. The test between them is only whether `A_execution_cap` moved.
4. Selling is based only on thesis falsification, permanent capital impairment, a severe hard-cap breach, a reviewed replacement, or tax, legal, or liquidity needs.
5. "It rose too much", "it fell too much", a frozen stage, or short-term news are not by themselves reasons to sell.
6. Neither price moves nor any valuation view constitutes a reason to sell; selling follows only the situations listed above.

The target allocation is amended in principle only in an annual review or a formal release.

### Complexity rule

- When adding a permanent rule, an old rule must be merged or removed, or the net increase in complexity must be justified in writing as unavoidable.
- Only one authoritative file per purpose; older versions of a rule are entirely void.
- Every release must report the net rule change; v4.0 removed roughly 3,300 lines of validator code and four JSON contracts.

---

## Part 4: Transition Plan (2026–2028)

> Conflict-resolution exception: where this part conflicts with `01-operating-manual.md`, the operating manual prevails.

### Goal

Migrate gradually from the old high-cash, mostly-single-stock portfolio to:

\[
\text{Cash }(15\%+U) + \text{QQQM }28\% + \text{SPYM }(57\%-A_{basis}) + \text{SOXX }A_{actual}
\]

Symbol definitions and thresholds take the target allocation part of this constitution as the sole authority (`A_stage` / `A_basis` / `U` / execution stage). QQQM stays at 28%; `U` is held as a stage reserve inside cash and is not invested into SPYM first. The migration prioritizes discipline, tax efficiency, and executability, uses 2028-12 as the planned completion month for the baseline, and is recomputed every month.

### Three funding channels

1. `Routine DCA`: the fixed monthly external contribution (amounts are never stored in the repository); use only the received \(F\) and execute \(D=\min(F,G_0)\), leaving \(F-D\) in cash.
2. `Strategic Baseline`: on the fixed monthly execution day, migrate historical excess cash using the \(B=\min(S/R,G)\) formula of the deployment framework (`01-operating-manual.md`); no judgment gate may suspend it.
3. `Drawdown Deployment`: when SPYM's drawdown from its all-time-high close reaches a tier, deploy cash under the tier clause of this constitution.

All three channels are driven by formulas and prices, and none depends on judgmental data. The only mechanical path for deployment beyond \(B\) is the drawdown tiers; discretionary acceleration is a rule exception and requires a full IC.

### Principles

1. Routine DCA \(D\) and the strategic baseline \(B\) enter only SPYM / QQQM positive gaps.
2. Recompute every month from live net assets, cash, SOXX-weight derived quantities, target gaps, and the number of execution rounds remaining to 2028-12.
3. Physical cash after a trade must not fall below `12%+U`, and margin must not be used.
4. SOXX does not participate in the allocation of \(D\), \(B\), or drawdown tranches; its only routine channel is the v4.5 **restore-to-target**, funded only from `U`.
5. All new tilts, **tilt increases**, and sales go through a full Investment Committee; a restore-to-target runs the routine path under the five constraints in this constitution.
6. Non-target legacy holdings and over-cap tilts exit gradually with tax awareness; nothing is sold on "high" or "low" alone.
7. Produce exactly one monthly output per month (format in section 6 of the deployment framework, `01-operating-manual.md`), delivered to the owner in chat and never written back to the repository.

### Stages

#### Stage A: build the Core

- Routine DCA \(D\) and Strategic Baseline \(B\) go into SPYM / QQQM.
- Allocate by positive gap; to reduce trades, buying only the larger gap is acceptable.
- Drawdown deployment must not replace or retroactively justify the routine baseline.

#### Stage B: handle the sector tilt and Legacy

- SOXX is held under `Hold`, with a permanent hard cap of 6%. A **tilt increase** requires the current-quarter manual look-through check and a full IC (see the tilt-increase gate in the registry part of this constitution); a **restore-to-target** runs the routine path and likewise requires a valid current-quarter check.
- For other non-Core holdings, distinguish tilt, Legacy, tax cost, investment rationale, and portfolio overlap.
- For legacy holdings confirmed for exit, plan a staged or single disposal; do not substitute price forecasts for the decision.
- If a hard-cap breach cannot be repaired by dilution, proceed to a sale review under this constitution.

#### Stage C: enter Maintenance Mode

When Cash, QQQM, and the `SPYM + SOXX + Stage Reserve` sleeve all sit inside their permitted bands for three consecutive months, and Legacy has been handled as planned, the transition is complete. From then on \(B=0\) and the allocation is maintained with new money only; positions are not switched proactively unless a selling rule triggers.

### On timing

2028-12 is the planned completion month for the strategic baseline, not a return promise and not a forced liquidation date. Market moves, taxes, contributions, and Legacy handling will change the outcome; the projected completion month may be re-estimated each quarter, but an extension must be recorded explicitly and never allowed to slip silently.

---

## Part 5: Sector Tilt / Satellite Framework

As of v4.0 the subject governed by this part is renamed the **discretionary sector tilt (Sector Tilt / Satellite)**. SOXX is a passive industry ETF: holding it is hard-capped industry/cycle beta, not alpha. The old word "Alpha" is retained only in historical records and no longer appears in current rules.

### Boundaries

- Combined hard cap: 6% of the total portfolio (merged with the SOXX cap as of v4.0; the 10% / 12.5% / 15% historical stages are void).
- Number of positions: at most 1 (SOXX); any new vehicle must first amend this rule through an annual review.
- No leverage, and no short-term technical signal used to build a long-term position.
- An approved but unfilled SOXX allowance is retained as `U`, a purpose label on cash.
- The sole registry of current classification and status is Part 6 of this constitution.

### SOXX as the only vehicle

SOXX is the only discretionary tilt vehicle; the hard cap, execution-stage advancement, and the 0% single-stock authorization are stated authoritatively in the target allocation part of this constitution. Basis for the cap (measured 2026-07): at SOXX=6% the portfolio's combined semiconductor exposure is already about 24%, and at SOXX=15% about 32%, the latter being unreachable under the system's own guardrails.

### Tilt increase and restore-to-target

The definitions of the two paths, the test between them (only whether `A_execution_cap` moved), and the five restore constraints are stated authoritatively in the target allocation part of this constitution; the five-step tilt-increase gate and the restore execution details are in the Part 6 registry. This section adds only the framework-level rules:

- A tilt increase additionally requires **a written, explicit compensating rationale for the overlapping exposure with QQQM / SPYM**; a machine-verified Look-through Evidence Bundle is no longer required — the quarterly check table plus a full IC is the current gate.
- Key boundary: **a restore does not turn the existence of `U` into an obligation to buy**. It only allows cash already labelled for SOXX to return to SOXX by formula when every constraint holds; if any condition fails the output is `0`, and partial execution is not permitted.

### Position lifecycle

1. `Research`: research only, no real money, not counted in \(A\).
2. `Hold`: the current position may be held, with no authorization to add.
3. `Frozen`: holding is allowed and additions are forbidden (data, guardrail, or research conditions unmet).
4. `Exit Review`: the selling rules are met and a full IC begins; the status itself is not authorization to sell.

Lifecycle and `A_execution_cap` changes must update the Part 6 registry first. No status changes automatically because of price, completed research, or data availability.

### Look-through concentration

Guardrail thresholds and semantics are in the target allocation part of this constitution (they constrain discretionary tilt additions and do not block Core routine paths). The quarterly manual check computes combined exposure inside the current private session; the evidence is not written into the repository. When the check is missing, SOXX remains forbidden from additions, with no automatic selling.

### Evaluation

SOXX must be compared against an equal-size, same-period SPYM position and against the IPS Policy Benchmark. Use at least three years of rolling data and include drawdown, taxes and fees, time cost, and concentration; outperformance in a single year does not demonstrate repeatable skill. If it underperforms after costs for five consecutive years, the annual review should discuss retiring this tilt and simplifying the system.

---

## Part 6: Sector Tilt Position Registry

This part is the sole registry of the current discretionary sector tilt classification, execution cap, and persistent lifecycle. Quantities, market values, and actual weights come from IBKR Positions.

### Current registration

| Instrument | Classification | Persistent lifecycle | Permanent hard cap | \(A_{stage}\) | Current execution cap \(A_{execution\_cap}\) | Current authorization |
|---|---|---|---:|---:|---:|---|
| SOXX | Sector tilt; the only semiconductor vehicle | Hold | 6% | 6% (final) | 3% | Hold only; a tilt increase requires a full IC, a restore-to-target runs the routine path |

### Execution cap governance

- The current \(A_{stage}=6\%\) is the permanent hard cap and the current \(A_{execution\_cap}=3\%\); the 10% / 12.5% / 15% historical governance stages are void as of v4.0.
- The legal order of execution caps is 3%→4.5%→6%; only one stage may advance at a time, this table must be updated first, and the IC is completed separately afterwards; a single IC must not both advance the stage and execute a trade.
- \(A_{execution\_cap}\le A_{stage}\) always holds. After a trade, `A_actual` must not exceed the execution cap or the 6% hard cap.
- If price drift pushes `A_actual` above the execution cap or the hard cap, freeze additions but do not sell automatically.
- The execution stage never advances automatically because of price, a completed check, or an IC conclusion.
- The technology 50% freeze line, the semiconductor 15% IC line, the issuer guardrails, and data integrity take priority; guardrail semantics are in the target allocation part of this constitution (they constrain discretionary tilt additions and do not block Core routine paths).
- The current new-addition authorization for every other sector tilt or semiconductor single stock is 0%.

### The tilt-increase gate (v4.0; renamed in v4.5)

This section governs only a **tilt increase** — advancing `A_execution_cap` (3%→4.5%→6%), which expands the risk budget. A **restore-to-target** (`A_execution_cap` unchanged, buying back only the weight the market pushed down) runs the routine path in the next section; the test between them is in the target allocation part of this constitution.

Every potential tilt increase must satisfy, in order:

1. the current-quarter manual look-through check is complete and within its validity period (`02-data-contract.md`, look-through check procedure);
2. live reads of Account Summary, Balances, Positions, and Open Orders all succeed;
3. after the trade `A_actual ≤ A_execution_cap`, and the technology/issuer guardrails hold; the fact that the semiconductor guardrail is already triggered is confirmed explicitly in the Packet;
4. a full IC (`01-operating-manual.md`, pre-trade decision checklist) returns `APPROVE`;
5. the account owner places the order manually in IBKR; after a fill, partial fill, or cancellation, the account is read again.

An IC approval is valid the same day; the next day the process starts over. The machine-verified Add Candidate Packet contract is no longer used.

### Restore-to-target (v4.5)

When a market decline pushes `A_actual` below the execution stage, the difference becomes `U`. Putting `U` back into SOXX is a **restore** (the authoritative statement of the definition and the five constraints is in the target allocation part of this constitution; this section lists only the execution details):

- Restore ceiling: `min(A_execution_cap, A_stage) − A_actual`, converted by NAV; the ceiling is not relaxed by running on the routine path.
- Calculation aid: `python3 skills/investment-os/scripts/monthly_execution.py --lookthrough-current`. **Omitting that flag counts as having no valid current-quarter check**, in which case the restore output is `0` and is marked `DATA INCOMPLETE`.
- Every real restore must verify and report, in the current private session, `A_actual` and `U` before and after the restore, the current-quarter check date and conclusion, and post-trade combined semiconductor exposure; account and fill facts are retained only by the broker and are never written into the repository.

The SOXX runtime state is rebuilt live from IBKR each time: when `A_actual>A_stage` it is `Hold — frozen above cap`, `U=0`, and the restore amount is `0`; otherwise it follows this table and the restore formula. The repository stores no current weight, account event, or owner trading decision. This section authorizes no trade.

Classification effective date: 2026-07-30. The v4.0 sector tilt restatement and the 6% cap take effect 2026-07-31.
