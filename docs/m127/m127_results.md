# m127_results — preregistered MIM replication outcome

**Milestone:** M127 · **Run:** 2026-06-16 (post-freeze) · **Artifact:** `m127_results.json`
**Design:** `docs/preregistration/M127_PREREG.yaml` (committed `62f4194`, **before** this result).
**Verdict: `NULL_NON_REPLICATION`.** Canonical MIM does **not** replicate in SPY 2016–2026 at
its published magnitude — a *well-powered, preregistered, control-clean* non-replication.

## Confirmatory tests (SPY SIP, N_full=2,625, N_highvol=875; HAC t crit = 2.498)

| Test | n | β | HAC t | R² | corr | Pass? |
|---|---|---|---|---|---|---|
| H_b full sample (PRIMARY) | 2,625 | +0.0178 | **+1.23** | 0.40% | +0.063 | fail |
| H_a full sample (PRIMARY) | 2,625 | +0.0182 | **+0.73** | 0.21% | +0.045 | fail |
| H_b high-volatility (SECONDARY) | 875 | +0.0210 | **+0.98** | 0.49% | +0.070 | fail |
| H_a high-volatility (SECONDARY) | 875 | +0.0251 | **+0.73** | 0.35% | +0.059 | fail |

- All four βs are the **correct (positive/momentum) sign** but **far below significance** —
  HAC t 0.73–1.23 vs the 2.498 Bonferroni bar.
- Observed correlations **+0.045 to +0.070 ≈ half the canonical 0.13**; R² ~0.2–0.5% vs the
  canonical ~1.6%.
- **High-volatility conditioning did not rescue the effect** (corr 0.06–0.07) — the regime
  where Gao et al. find concentration shows no material lift here. The interpretation guard
  (prereg) is satisfied vacuously: the conditioned tests are null too.

## Negative controls (full sample, seed=20260616; pass = none significant at |t|>2.498)

| Predictor | real t | date_shuffled | permuted_target | randomized_ts | lag_permuted |
|---|---|---|---|---|---|
| r_hb (H_b) | +1.23 | −0.84 | −1.16 | +1.94 | +0.69 |
| r_ha (H_a) | +0.73 | −1.60 | −0.08 | +1.94 | −0.78 |

**No control is significant** (max |t| = 1.94 < 2.498) → the harness is **not contaminated**;
the null is trustworthy. `suspicious = False`.

## Interpretation

This is the rigorous outcome the mission targeted: a result that **survives skeptical scrutiny**
because the design was powered, preregistered, faithful, and control-clean. The null **cannot**
be dismissed as:
- *underpowered* — power > 0.999 at the canonical corr 0.13 (MDE ~0.07 full / ~0.12 conditioned);
- *contaminated* — all negative controls insignificant;
- *undisciplined* — preregistered, k=4 Bonferroni, frozen before results (git-provable);
- *aimed at the weakest spec* — both co-primary predictors (Gao H_a, Baltussen H_b) **and** the
  high-volatility regime where the effect concentrates were all tested.

**Most likely explanations** (consistent with prior project analysis / RESEARCH_J):
1. **Publication decay** (McLean–Pontiff ~58%): Gao 1993–2013, Baltussen 1974–2020; our window
   is 2016–2026, post-publication. Observed corr ~half canonical is consistent with substantial
   decay rather than total absence.
2. **Instrument (H_b caveat):** Baltussen's effect is documented on **futures**; this is the SPY
   **ETF** (fidelity CLOSE, not Exact). A null for H_b here is **not** a rejection of the futures
   finding — only evidence about the ETF. Re-running on ES/MES (currently no data source) is the
   decisive next test.
3. H_a is on its native instrument (SPY ETF) over a post-publication window → this is a genuine,
   on-instrument non-replication of Gao for 2016–2026.

**What this is not:** proof MIM never existed, or that it is absent on futures / in-sample eras.
It is a clean statement that, at the published magnitude, the effect is **not present in SPY
2016–2026**.

## Integrity note (full transparency — a post-result code fix)

The first execution printed `VERDICT: SUSPICIOUS_STOP`. That was a **driver bug, not a data
finding**: the driver's suspicious flag used a loose heuristic (`|control t| ≥ 0.5×|real t|`),
which is trivially tripped when the *real* signal is itself null — it does **not** indicate
contamination. The **preregistered** negative-control criterion (`M127_PREREG.yaml`,
`negative_controls.pass`, committed `62f4194` *before* any result) is **"no control significant
at alpha_per_test"** (|t| > 2.498). I corrected the driver to that frozen criterion.

- This is a **code-to-preregistration conformance fix**, not a design change after seeing
  results. The criterion was frozen before the run; the code implemented it incorrectly.
- **The confirmatory verdict (0/4, the binding test) is unchanged** between runs.
- The control statistics are **byte-identical** across both runs (fixed seed, same data) — only
  the flag's interpretation changed. Max control |t| was 1.94 in both → never significant → the
  corrected verdict `suspicious=False` is the one the frozen criterion always implied.

Git history is the audit trail: prereg `62f4194` → harness/freeze artifacts → this result.
