# Pre-Registration F10 — FOMC-Cycle Equity-Premium Timing

**From:** Research session (Cowork) · **To:** Build Master (Project Build 5) — review and commit
**Date:** 2026-06-15 · Frozen before implementation; immutable once committed.
**Lineage:** RESEARCH_I — method #1 (macro/calendar bucket).
**Family (per RESEARCH_H):** NEW Family 7 — FOMC-cycle timing. Adds ~1 effective trial.
**Status:** Specification only. Authorizes nothing.

## 1. Executive Summary
**Hypothesis:** Since 1994 the U.S. equity premium has been earned entirely in even weeks (0,2,4,6)
of FOMC-cycle time, with odd weeks flat/negative — causally tied to the Fed (Cieslak, Morse &
Vissing-Jorgensen 2019, JF). F10 holds SPY in even cycle weeks and stands aside (or shorts) in odd.

**Honest expected range:** deflated Sharpe ~0.3–0.6; **P(clear net) ~25–35%** (higher than F7/F8/F9:
cheap, low-turnover, strong prior), tempered by: (i) post-publication decay risk; (ii) small-sample
power — ~2yr gives few independent cycles.

**Data:** SPY daily + scheduled FOMC meeting calendar (public; Federal Reserve). No purchase. Not blocked.

## 2. Scope
- In scope: FOMC-cycle-phase timing rule on SPY at weekly granularity; causal labels.
- Out of scope: intraday execution, options, leverage; emergency/unscheduled FOMC actions.

## 3. Frozen configuration grid
- **Predictor (causal):** `cycle_week_t` = business-days since last scheduled FOMC decision, binned
  into even/odd cycle weeks (calendar known years ahead → strictly causal).
- **Position:** even cycle weeks → long SPY; odd weeks → {flat, short} per variant.
- **Phase-definition variants:** {strict day-count from last meeting; ±1-day shift; inter-meeting
  midpoint split} (3 variants — robustness to exact phase boundary).
- **Granularity:** {hold whole even week; daily within even week}.
- **Grid:** 2 odd-week schemes × 3 phase definitions × 2 granularities = **12 candidates**, frozen.

## 4. Anti-snooping controls
- Walk-forward OOS, calmer sub-period — and report number of independent FOMC cycles; "insufficient
  power" verdict if too few.
- DSR with effective-N (RESEARCH_H) + Holm — binding given small-sample power risk.
- PBO via CSCV ≤ 0.50; Hansen SPA report-only.

## 5. Placebo controls
- **Scrambled-calendar placebo (binding):** assign even/odd phase to random week boundaries; edge must
  vanish (random calendar must not "work").
- Random-direction placebo.
- **Sub-period stability check:** estimate effect pre- and post-2015 separately; material decay is a
  tradability flag (not auto-kill).

## 6. Cost model
Regime-aware per PREREG_MIM_BALTUSSEN §6; turnover is low (weekly), cost is second-order.

## 7. Acceptance criteria (ALL)
Net edge after costs · DSR + Holm (with adequate cycle count) · PBO ≤ 0.50 · Walk-forward · Both
placebos survived.

## 8. What would falsify F10
DSR/PBO/walk-forward fail; or net edge ≈ 0; or too few independent cycles; or scrambled-calendar
placebo also "works." Material post-2015 decay weakens but does not alone kill the verdict.

## 9. Non-goals
No intraday execution; no options; no leverage; no other macro calendars in this freeze.

**HANDOFF note:** PREREG_F10 — FOMC-cycle even-week SPY timing, NEW Family 7, 12 cells, data on hand
(Fed calendar, free). Strong prior; binding risks: small cycle count + post-publication decay.
Distinct from F5 (pre-FOMC-eve gate).

## Sources
- Cieslak, Morse & Vissing-Jorgensen, JF 74(5) (2019). https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12818
- McLean & Pontiff, JF (2016). https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12365
- Internal: RESEARCH_C §4.4, RESEARCH_H, RESEARCH_I.

*Research only. No order routing, broker, options, position sizing, or live execution.*
