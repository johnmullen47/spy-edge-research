# Pre-Registration F8 — Opening Range Breakout (ORB)

**From:** Research session (Cowork) · **To:** Build Master (Project Build 5) — review and commit
**Date:** 2026-06-15 · Frozen before implementation; immutable once committed.
**Lineage:** RESEARCH_I — method #4 (intraday breakout / structural bucket).
**Family (per RESEARCH_H):** NEW Family 5 — Opening Range Breakout. Adds ~1 effective trial.
**Status:** Specification only. Authorizes nothing.

## 1. Executive Summary
**Hypothesis:** If SPY breaks out of its opening range (first N minutes' high/low), intraday momentum
continues in the breakout direction into the close (Zarattini & Aziz 2023).

**Honest expected range — modest with a sharp caveat:** headline ORB results are on leveraged
ETFs / stocks-in-play, not plain SPY; and ORB-type rules fail data-snooping-adjusted testing
(Sullivan et al. 1999). On un-leveraged SPY: **Deflated Sharpe ~0.1–0.4; P(clear net) ~10–20%.**
Trades daily → cost-sensitive.

**Data:** SPY 1-min. No purchase. Not blocked.

## 2. Scope
- In scope: opening-range breakout entry on SPY 1-min, intraday hold to close; causal labels.
- Out of scope: leverage / leveraged ETFs (explicitly not replicated), multi-symbol selection, options.

## 3. Frozen configuration grid
- **Opening range:** first N minutes; N ∈ {5, 15, 30} (range = high/low of bars ≤ 09:30+N).
- **Entry (causal):** first 1-min close beyond OR high (long) / OR low (short) after OR window; one
  entry/day; exit at 16:00 (EOD-flat).
- **Trend filter:** {none, price vs prior-day close, price vs session VWAP at entry}.
- **Grid:** 3 OR windows × 3 trend filters × direction {long+short} = **9 candidates** (×2 if
  close-confirmation entry variant added = 18), frozen, booked into trial budget.

## 4. Anti-snooping controls
- Walk-forward OOS, calmer sub-period — decisive (ORB documented decay).
- DSR with effective-N (RESEARCH_H) + Holm. **Binding given ORB's data-snooping history.**
- PBO via CSCV ≤ 0.50; Hansen SPA report-only.

## 5. Placebo controls
- Scrambled-range placebo (randomize OR levels; edge must vanish).
- Random-direction placebo.
- **Cost/bounce check (binding):** net edge must be distinguishable from the half-spread at entry bar.

## 6. Cost model
Regime-aware per PREREG_MIM_BALTUSSEN §6; **entry-bar half-spread charged in full** (breakout crosses
the spread).

## 7. Acceptance criteria (ALL)
Net edge after costs (distinguishable from half-spread) · DSR + Holm · PBO ≤ 0.50 · Walk-forward ·
Both placebos survived.

## 8. What would falsify F8
DSR/PBO/walk-forward fail; or net edge ≈ half-spread; or edge survives only with leverage (out of scope).

## 9. Non-goals
No leverage / leveraged ETFs; no multi-symbol; no options; no sizing.

**HANDOFF note:** PREREG_F8 — un-leveraged SPY ORB, NEW Family 5, 9–18 cells, data on hand.
Honest caveat: published edge uses leverage/stocks-in-play. Binding controls: DSR + half-spread cost test.

## Sources
- Zarattini & Aziz, SSRN 4416622 (2023). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4416622
- Zarattini, Barbon & Aziz, SSRN 4729284 (2024). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729284
- Sullivan, Timmermann & White, JF 54(5) (1999). https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00163
- Internal: RESEARCH_H, RESEARCH_I.

*Research only. No order routing, broker, options, position sizing, or live execution.*
