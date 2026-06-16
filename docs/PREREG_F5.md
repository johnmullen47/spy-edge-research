# Pre-Registration F5 — Pre-FOMC Calendar Gate (Placebo / Decay Monitor)

**From:** Research session (Cowork)
**To:** Build Master (Project Build 4) — review and commit
**Date:** 2026-06-15
**Format:** `PREREG_F1`/`PREREG_F2` anatomy, adapted for a **negative control**. Frozen before
implementation. Immutable once committed; revisions ship as `PREREG_F5_AMENDMENT_1.md`.
**Lineage:** `RESEARCH_F` candidate **F5**, and `RESEARCH_C_DECISION` §4.4 (macro-calendar gate as a
placebo expected to FAIL).
**Family (per `RESEARCH_H`):** Family 1 — Intraday Momentum, **variant** (calendar gate). Counts as a
trial in the effective-N budget like any other, even though it is a control.
**Status:** Specification only. **This is a pre-registered placebo, not an edge candidate.** Its
designed-for outcome is *no incremental edge*.

> **⚠ READ FIRST — inverted interpretation.** Unlike F3/F4, F5 is **not** expected or intended to
> produce a tradable edge. The pre-FOMC drift (Lucca & Moench 2015) was real in-sample but
> **disappeared after ~2015** (the "disappearing pre-FOMC drift" follow-up). F5 exists to (a)
> **monitor that decay** on the project's own data, and (b) serve as a **negative-control guard**: the
> primary MIM/Baltussen and F3/F4 results must **not** depend on the FOMC gate to reach significance.
> A "good" F5 result is a **null**.

> **⚠ OPEN QUESTION — base predictor (flagged, default chosen).** Conditions the **live Baltussen
> MIM predictor** (`PREREG_MIM_BALTUSSEN` Config A); confirm or override before commit.

---

## 1. Executive Summary (bottom line first)

**Hypothesis under test (expected to be rejected):** restricting / conditioning the live MIM signal on
**scheduled-FOMC-eve days** adds directional edge. Per the post-2015 evidence, it should **not**.

**Two pre-registered roles:**
1. **Decay monitor:** estimate the pre-FOMC-eve effect on SPY over the sample and confirm it is
   statistically indistinguishable from zero post-2015 (the literature's finding, re-tested on our
   data).
2. **Negative-control guard:** verify that the MIM-Baltussen / F3 / F4 candidates do **not** require
   the FOMC gate to clear the harness. If any primary candidate's significance **depends** on the
   FOMC gate, that primary result is treated as **fragile and is killed** (per RESEARCH_C §4.4).

**Honest expected range (pre-registered):** **net edge ≈ 0; not eligible.** If F5 *does* show
significant incremental edge, that is a **flag** — either a genuine regime revival (unlikely) or a
harness false-positive to investigate — not an automatic candidate.

**Data:** SPY 1-min (on hand) + the **scheduled FOMC meeting calendar** (public; Federal Reserve).
**Not blocked.**

## 2. Scope
- **In scope:** a binary scheduled-FOMC-eve flag as a conditioning gate on the live MIM predictor;
  read-only forward labels; the negative-control guard test on the primary candidates.
- **Out of scope:** treating F5 as a tradable edge; unscheduled/emergency FOMC actions; other macro
  releases (CPI/NFP) — a separate question if ever pursued; sizing; execution.

## 3. The frozen, pre-registered configuration
- **Base signal:** `PREREG_MIM_BALTUSSEN` Config A (predictor prev close→15:30; trade 15:30→16:00;
  threshold grid {0, 0.10%, 0.25%, 0.50%}).
- **Gate (causal):** `is_fomc_eve_t` = 1 if date `t` is the session **before** a scheduled FOMC
  decision (calendar known years in advance → strictly causal). Pre-declared variants:
  - **C1 — restrict:** trade only on FOMC-eve days.
  - **C2 — exclude:** trade only on non-FOMC-eve days (the complement; used for the guard test).
- **Guard test (binding, RESEARCH_C §4.4):** for each primary candidate (MIM-Baltussen, F3, F4),
  compare significance **with vs. without** FOMC-eve days. If a primary clears **only** with the FOMC
  contribution, that primary is killed.
- **Grid:** 4 thresholds × 2 calendar variants (C1/C2) = **8 candidates**, frozen, booked into the
  trial budget (clustered per RESEARCH_H).

## 4. Anti-snooping controls
- **Walk-forward OOS on a calmer held-out sub-period.**
- **Deflated Sharpe Ratio with N = effective-N (`RESEARCH_H`)** — F5's 8 cells enter ONC clustering;
  within-cluster **Holm-Bonferroni** at candidacy. (Counting the placebo as trials is deliberate — it
  must not be a free shot.)
- **PBO via CSCV** ≤ 0.50; **Hansen's SPA** report-only.

## 5. Interpretation rules (replaces the usual acceptance criteria)
- **Expected / "healthy" outcome:** F5 (C1) shows **no** significant net edge → confirms post-2015
  decay; primary candidates are **unaffected** by removing FOMC-eve days (C2 ≈ full sample).
- **Flag outcome:** F5 (C1) shows significant net edge after the full harness → **do not** trade it;
  open an investigation (regime revival vs. false positive). It does **not** become
  `eligible_for_paper_consideration` without a separate, explicit decision.
- **Kill outcome:** any primary candidate clears **only** with FOMC-eve days included → that primary
  is killed as fragile (RESEARCH_C §4.4).

## 6. Cost model
Identical regime-aware model to `PREREG_MIM_BALTUSSEN` §6. (FOMC-eve sessions can carry elevated
spreads; charged honestly — relevant only if F5 unexpectedly flags.)

## 7. Negative / placebo controls
- **Scrambled-calendar placebo:** permute the FOMC-eve flags to random dates; any apparent F5 effect
  must vanish (if a *random* calendar "works," F5's apparent effect is noise — reinforcing the null).
- **Random-direction placebo.**

## 8. What this control establishes
- Confirms (or challenges) the pre-FOMC-drift decay on the project's own data.
- Guarantees the primary MIM family is not secretly leaning on a demonstrably decayed calendar effect.
- A clean F5 null **strengthens** confidence in any primary candidate that clears without it.

## 9. Non-goals
No treating F5 as an edge; no other macro calendars; no sizing; no execution. One frozen placebo, full
harness, inverted interpretation.

**HANDOFF status note (Research does not edit HANDOFF.md):** PREREG_F5 filed — pre-FOMC calendar
**placebo / decay monitor** on the live Baltussen MIM (8 frozen cells), expected to be null.
Dual role: decay check + negative-control guard (kills any primary that needs the FOMC gate to clear).
Data on hand (Fed calendar); not blocked. **Not an edge candidate.**

---

## Sources
- Lucca & Moench, "The Pre-FOMC Announcement Drift," *Journal of Finance* 70(1):329–371 (2015). https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12196
- "The disappearing pre-FOMC announcement drift" (post-2015 decay). https://www.sciencedirect.com/science/article/abs/pii/S1544612320315956
- Internal: `RESEARCH_C_DECISION.md` §4.4, `PREREG_MIM_BALTUSSEN.md`, `RESEARCH_H_N_Count_Correction_DSR_Amendment.md`, `RESEARCH_F_Signal_Discovery.md`.

*Research only. No order routing, broker, options, position sizing, or live execution. Where this
conflicts with the authoritative briefs, those govern.*
