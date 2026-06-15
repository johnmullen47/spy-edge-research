# Research E — Type I / Type II Balance and the Signal-Discovery Layer

**From:** Research session (Cowork)
**To:** Build Master (Code session) — review and commit
**Date:** 2026-06-15
**Status:** Design brief. Captures a tension and proposes architecture. No gate changes.
**Context:** Build 4 @ M113, 892 tests passing; M114 (regime-aware cost model) in flight.
Active signal under test: MIM — realized-early-session-volatility-gated intraday momentum on
SPY (per `RESEARCH_C_DECISION.md` §4.3). **Hard Gate A remains negative (0/42 on real SPY
data) and stays in place. Nothing here lowers a gate.**

---

## 1. The tension

The harness is tuned to protect **capital-deployment safety** — it is conservative against
**Type I error** (a false positive: registering a signal that is really noise, the precursor to
deploying a loser). That is correct and non-negotiable. But a conservative Type I posture, when
paired with a *narrow search space*, raises **Type II error** (a false negative: a real,
exploitable pattern exists but never enters the funnel, or enters underpowered and is killed).

The asymmetry is deliberate — a deployed loser costs real money; a missed signal costs only
opportunity — so we keep the bias. The empirical fact that disciplined quant programs *do*
extract durable alpha is, however, proof that real intraday/short-horizon patterns exist. A 0/42
result is therefore strong evidence that **these 42 chart-pattern candidates** carry no
cost-surviving edge; it is **silent** on patterns we never searched. The risk we are flagging is
the second clause: concluding "no edge" when the truthful statement is "no edge *in the small,
mostly-folklore region we looked at*."

## 2. Current harness calibration — and why each gate exists (unchanged)

- **Deflated Sharpe Ratio, N = full trial budget.** Deflates the Sharpe benchmark
  `Φ⁻¹(1 − 1/N)` against *every configuration / regime cell ever evaluated*, not OOS survivors
  (the M109 N-fix). Controls selection bias under multiple testing. *Stays.*
- **PBO ≤ 50% via CSCV.** Rejects strategy-selection procedures whose picks underperform the
  median out-of-sample. Controls overfit-by-selection. *Stays.*
- **SPA (Hansen), report-only.** Snooping-robust check across the candidate family. *Stays.*
- **Chronological walk-forward OOS + regime-aware cost model (M114).** No-lookahead, costs
  charged at point-of-fill and scaled to the volatility/time-of-day regime the trade lives in.
  *Stays.*
- **Hard Gate A on real SPY data.** Final economic-significance floor net of costs. *Stays.*

These gates are the project's credibility. They are out of scope for any change in this brief.

## 3. The risk, stated precisely

Two design choices jointly drive Type II error, and **only the first is healthy to touch**:

1. **Search-space breadth** (how many *distinct, well-motivated* signal families we examine).
   Currently narrow: one chart-pattern menu (killed) plus one MIM signal (in test).
2. **Gate height** (the DSR/PBO/Hard-Gate-A bar). Appropriately high. **Do not touch.**

The remedy for Type II is to widen (1), never to lower (2). But widening (1) is not free: every
candidate evaluated **increases N**, which *raises* the DSR deflation hurdle. Brute-force search
is therefore self-defeating — it inflates the bar faster than it finds signal. Expansion must be
**theory-guided** (raising the prior hit-rate per candidate) rather than exhaustive, and every
trial must be counted honestly toward N. This is the same §4.3 principle that drove the M109 fix,
applied to discovery: you may look in more places, but you pay for each look in deflation.

## 4. Recommended architecture — a two-stage funnel

Insert a **discovery pre-screen** *before* the full harness; leave the full harness untouched
behind it.

**Stage 0 — Discovery pre-screen (looser, cheap, non-authorizing).**
- Purpose: cheaply *nominate* candidates from an expanded family set into the real harness, and
  cheaply *discard* obvious noise before it consumes expensive OOS/CSCV compute.
- Looser criteria are permitted here (e.g., in-sample sign consistency, raw effect-size and
  sample-count thresholds, robustness to one perturbation) **only because Stage 0 cannot
  register, gate, or authorize anything.** Its single output is a ranked nomination list.
- **Honest-N ledger:** Stage 0 logs *every* configuration it evaluates. That count flows into
  the Stage-1 DSR N (or a pre-registered, separately-tracked discovery budget). A pre-screen that
  hides its trial count is a false-discovery laundromat; this one is auditable by construction.

**Stage 1 — Full harness (unchanged).**
- Nominated candidates face the exact DSR(full-N) / PBO≤50% / SPA / walk-forward / regime-cost /
  Hard-Gate-A stack already in place. No criterion is relaxed. Hard Gate A still decides.

**Expanded candidate set (the point of all this).** Beyond the killed chart-pattern menu and the
single MIM signal, add *theory-motivated, mechanism-backed* families — additional regime gates for
MIM-type signals (VIX level/term structure, overnight-gap magnitude, scheduled-macro dates,
options-dealer-gamma sign), and the open-to-close / overnight-return decomposition on SPY. These
are scoped and pre-registered in Task 2 (`RESEARCH_F…`) and Task 3 (per-hypothesis
pre-registration docs), not here.

**Pre-registration (audit spine).** Each new hypothesis ships a pre-registration doc — signal
definition precise enough to implement unambiguously, success criteria fixed *before* any result
is seen, and an honest expected range (Sharpe, DSR, active days, probability of clearing the
harness if real vs. if noise). Following `RESEARCH_C_DECISION.md` discipline, each search
increment is documented, counted toward N, and auditable. Per the pre-registration integrity rule,
a committed spec is immutable — revisions ship as amendment files, never edits.

## 5. Explicit guardrail statement

The gates are **not** being lowered, softened, or bypassed. Stage 0 has **zero authority** — it
only nominates into the unchanged Stage 1. Every gate in §2 stays exactly as calibrated, Hard
Gate A included. The only thing this architecture changes is the **breadth and documentation of
what we search**, and it makes the project *pay* for that breadth through honest trial-count
deflation. We are widening the net, not loosening the mesh.

## 6. Next

- **Task 2** → `RESEARCH_F_signal_discovery_survey.md`: literature survey of regime-conditioned
  intraday patterns beyond MIM, SPY overnight/intraday predictability, pre-screening practice, and
  the appropriate trial budget N (with its DSR implications).
- **Task 3** → one pre-registration doc per surviving hypothesis, in `RESEARCH_C_DECISION` format,
  for Build Master to review and commit before any implementation.

**HANDOFF status note (for Build Master to incorporate; Research does not edit HANDOFF.md):**
Research E filed — Type I/II tension documented, two-stage discovery funnel proposed, gates
unchanged. Task 2 (signal-discovery survey) and Task 3 (per-hypothesis pre-registrations) pending.

*Research only. No order routing, broker, options, position sizing, or live execution. Strongest
permitted verdict: `eligible_for_paper_consideration`. Where this conflicts with
`MASTER_PROJECT_BRIEF.md`, `CHATGPT_RESEARCH_PHASE_BRIEF.md`, or `README.md`, those are
authoritative.*
