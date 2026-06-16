# m127_blocker_report

**Milestone:** M127 · **Step 1D output** · **Date:** 2026-06-16
**Status: BLOCKED.** M127 cannot currently be run as a statistically powered,
literature-faithful MIM replication. Implementation halted at Gate 0.5 per the mission's
blocking rule. No pre-registration, fidelity report, implementation, controls, or M128
scaffold were produced (all gated behind Gate 0.5 passing).

## The exact blocker

**Data adequacy fails on two independent grounds, either of which is sufficient to block:**

1. **No primary instrument.** The design's primary instrument is **ES/MES** (longest clean
   history; the futures evidence base for H_b / Baltussen et al. 2021, 60+ futures
   1974–2020). The repo has **no futures intraday data** and **no way to fetch it** — the
   only acquisition tool, `scripts/fetch_spy_bars.py`, is Alpaca **stocks-only**, and the
   configured free tier serves no futures. The literature-faithful primary cannot be
   instantiated at all.

2. **All available instruments are underpowered.** The only confirmatory-eligible series are
   the two SPY feeds (~499–502 trading days each). At the canonical effect size (corr ≈ 0.13)
   and the pre-registered Bonferroni alpha (0.05/7 = 0.00714), each yields **≈ 59% power** —
   below the 0.80 threshold. Required: **733 trading days**; available: ~502. The high-vol-
   conditioned test reaches 80% only under an *undocumented* conditioned-correlation
   assumption (r ≳ 0.30), so it cannot be classified confirmatory. ETFs fetchable via the
   repo (QQQ/IWM/DIA) inherit the same short/thin-feed limits and add no qualifying power.

A skeptic reading this before any result exists would correctly conclude: a null from the
available data would be **uninterpretable** — indistinguishable from low power, and missing
the instrument where the effect is best documented. Running it would manufacture exactly the
"obviously underpowered / aimed at the weakest specification" result the mission forbids.

## What would unblock M127 (required data)

| Need | Specification | Why | Acquirability |
|---|---|---|---|
| **Primary: long-history ES/MES intraday** | 1-minute (or finer) continuous front-month with documented roll + RTH/Globex session convention; ideally back to ≥2000, target **≥ 733 RTH days** (≈3+ yrs) minimum, more for conditioning splits | Restores the mission's primary instrument and H_b's futures evidence base; longest clean history → best power | Requires a **futures-capable vendor** (e.g. Databento, CME via a broker, IQFeed, Polygon futures). **Not** Alpaca free. New `fetch_futures_bars.py` needed. |
| **Full-history SPY** | 1-minute SPY consolidated (SIP) back to ~1993 (Gao sample) or at least ≥ 733 clean full-volume days | Powers H_a/H_b on the canonical equity instrument | Paid SIP / vendor; current free-tier SIP is blocked for recent ~15 months and we hold only 2023–2024. |
| **(Secondary) QQQ/IWM/DIA full-volume intraday** | ≥ 733 full-volume RTH days each | Robustness universe | Paid SIP / vendor. |

**Estimated requirement to clear Gate 0.5:** one clean, single-feed, full-volume intraday
series of **≥ ~733 RTH trading days** (≈3 years) on a primary instrument — ES/MES preferred,
full-history SPY acceptable — plus enough extra history for the high-volatility subsample to
stand on its own (~+330 days). Practically: **acquire ≥ 5 years of clean 1-min ES/MES (or
1993– SPY) from a futures-/SIP-capable vendor.**

## Recommended next action

1. **Acquire long-history intraday futures data (ES/MES)** from a futures-capable vendor and
   add `scripts/fetch_futures_bars.py` with explicit roll + session (RTH vs Globex) handling.
   This is the single highest-value unblock and aligns with RESEARCH_J's #1 recommendation
   (re-run on a full-volume tape + ES futures).
2. Re-run Gate 0.5 (Steps 1A–1D) on the acquired data. If it passes, proceed to Step 1.5
   (freeze `M127_PREREG.yaml`), 1.6 (fidelity report), then implement — reusing the existing
   `mim_baltussen_features.py` (H_b) and `intraday_momentum_features.py` (H_a) predictors,
   which are already literature-faithful; the missing piece is then only a HAC-OLS regression
   harness, not new signal logic.
3. Until then, **do not** run M127 on SPY-only data and **do not** report any SPY-only MIM
   result as evidence for or against the canonical effect.

## What was NOT done (correctly, per the blocking rule)

- No `M127_PREREG.yaml` (Step 1.5 is post-gate).
- No `m127_fidelity_report` (Step 1.6 is post-gate).
- No M127 implementation, negative controls, or test runs (Step 2–3 are post-gate).
- No M128 scaffold (part of the gated implementation flow; "do not continue" past the blocker).

The architecture is ready (see `m127_repo_inspection.md`); M127 is blocked solely on data.

**Final: BLOCKED.**
