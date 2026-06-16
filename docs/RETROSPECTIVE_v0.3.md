# Retrospective — v0.3 (Milestones M100–M128)

**Phase:** M100 → M128, closed 2026-06-16 and tagged `v0.3-m128-complete`.
**Headline:** a disciplined, well-powered **null**. Hard Gate A finished NEGATIVE
(0/672 candidates eligible), the broker/live layers stayed OFF, and the
confirmatory MIM replication (M127) and exploratory cross-sectional HKS study
(M128) both failed to clear. The value of this phase is not an edge — it is a
clean, auditable answer to "is there one here, in what we looked at?" and a set of
lessons that should change how the next phase is sequenced and engineered.

This document is a lessons-learned review for future workers. Read it before
starting implementation on a new milestone.

---

## 1. Research strategy

The most important strategic lesson is about **what we chose to test, and in what
order**. We spent the phase testing post-publication effects and, unsurprisingly,
found post-publication decay. In retrospect this is nearly tautological: the MIM
signal was published in 2018 and the HKS intraday-periodicity result in 2010 —
both have been in the open literature long enough for any capturable edge to be
arbitraged away. Confirming that a widely-published, decade-old effect no longer
clears costs on liquid SPY is close to a foregone conclusion, and we committed real
engineering milestones to reaching it.

The corrective is to **weight recency and obscurity of a hypothesis before
committing a milestone to it**. The overnight/intraday return decomposition now
queued as M129 should arguably have been tested *before* the MIM replication: it is
less published, costs nothing to run on data we already own, and probes a part of
the return distribution we had not touched. Sequencing research by
expected-information-per-dollar — favouring the obscure, cheap, and untested over
the famous and already-arbitraged — would have front-loaded the experiments with
the highest residual chance of carrying signal.

What worked, and should be kept, is the **discipline layer around the
experiments**. Preregistration kept every null interpretable — because success
criteria were fixed before results were seen, a null could not be quietly
re-narrated into a near-miss. **Gate 0.5 (power-gating before implementation)** was
genuinely valuable: it stopped us from spending engineering effort building out
underpowered designs whose nulls would have been uninformative, and it meant the
nulls we did produce were well-powered enough to mean something (M127 ran at power
>0.999). The **EXPLORATORY-vs-confirmatory labelling** earned its keep at M128 —
tagging the cross-sectional study EXPLORATORY prevented its null from being misread
as a definitive verdict on the effect, which would have over-claimed from a single
universe and window. And **Hard Gate A itself was an effective forcing function**:
a hard, pre-committed economic-significance bar that nothing reached, which is
exactly why no premature move toward live trading was possible.

## 2. Project architecture

The **multi-agent worktree protocol is sound in principle but generated real
friction in practice**. Across the phase it produced orphaned worktrees, naming
mismatches between sessions, and several cases where multiple recovery sessions
were needed to finish work a single session had started. The protocol's isolation
guarantees are worth keeping, but the coordination state lived only in prose
HANDOFF documents and in the heads of individual sessions. A **machine-readable
state file** (a small JSON/YAML artifact committed on main) that every session
reads on entry and updates on exit — current milestone, branch, suite count, gate
status, open worktrees — would sharply reduce the recovery overhead, because a
session resuming after a failure could reconstruct "what remains" mechanically
rather than by re-deriving it.

The **README went stale** — it described the M107 state while the project was at
M128. This is a documentation-architecture problem, not a discipline failure: a
state section maintained by hand will always drift. The repository's
human-readable state (README and the snapshot at the top of the handoff) should be
**generated from a single source-of-truth artifact** — ideally the same state file
proposed above — so that "what milestone are we on" has exactly one authoritative
home and cannot disagree with itself across documents.

Finally, **Build Master should be used as the task distributor and kept
continuously in sync on project state.** Several coordination gaps in this phase
traced directly to sessions being spawned ad hoc without routing through Build
Master, which then had to catch up on state after the fact. The hub-and-spoke model
only works if everything goes through the hub.

## 3. Implementation and code engineering

The **stub-first approach used at M128** — scaffold the module interface, write
tests against the stubs, then fill in the implementation — forced clear thinking
about module boundaries before any real logic was written, and it should be the
**standard for new signal modules** going forward. Designing the seams first made
the eventual implementation a matter of satisfying an already-agreed contract.

**Rate limiting during the Alpaca data fetch was an expensive lesson.** The
practical ceiling turned out to be roughly **3.7 requests/second regardless of
worker count** — adding parallelism bought nothing past that point. The design
principle to carry forward is to **find the throughput ceiling empirically on a
small batch first, then build the fetcher around that number** with explicit
throttling and checkpointing baked in from the start, rather than discovering the
ceiling by hitting it mid-run. Relatedly, the **gitignored, resumable bar cache was
the right pattern**, but it was added *reactively* after fetches had already been
interrupted. Resumability should be a first-class design requirement for any data
acquisition, not a patch applied after the first failure.

On the safety side, the **`SPY_EDGE_ALLOW_LIVE=1` environment flag plus the
per-order human-approval-token pattern is good architecture** and should be kept
as-is. It makes reaching a live order path structurally impossible without an
explicit, auditable, human action — the right default for a research system that is
one config flag away from touching a broker.

## 4. Testing

The **synthetic planted-slope tests for the Fama-MacBeth machinery were the right
kind of test**: they validate the statistical engine against a known ground truth
(a slope we planted, which the estimator must recover) rather than merely asserting
that the code runs without error. Any new statistical module should ship with this
style of ground-truth validation — it is the only way to know the math is right, as
opposed to merely non-crashing.

The phase's clearest testing gap was **degenerate-input coverage**. An
ONC / zero-denominator bug introduced at M122 was not caught until M126 — four
milestones later — because the suite was strong on happy-path behaviour and light
on numerical edge cases. The lesson is concrete: every statistical module should,
**from the start**, carry tests for the degenerate inputs that actually occur in
market data — zero-variance windows, all-NaN windows, single-observation buckets,
and the zero-denominator cases that produce silent NaNs or infinities. The
1,060-test suite is a genuine strength on happy-path coverage, but its lighter
degenerate-input coverage is where the next latent bug is most likely hiding.

## 5. Multi-agent coordination

**Long-running monolithic operations are the single highest failure risk in this
project.** The ~2.5-hour data fetch was the worst offender: any operation running
longer than roughly **20 minutes needs a checkpoint** so it can resume rather than
restart, and that resumability has to be designed in before the first run, not
bolted on after the first kill.

The **worst coordination failure of the phase was an API error in the middle of a
merge sequence.** Recovery did work — each new session inspected the repository
state and completed only the part that remained — but it took **three sessions to
land one operation.** The mitigation is to **keep operations atomic at the git
level**: structure work so that a session dying mid-way leaves the repository in a
clean, well-defined state (either fully applied or trivially abandonable), never
half-merged. This is the same lesson as the long-fetch checkpointing, applied to
git history instead of to data.

Underlying both is the coordination point from §2: **Build Master must be the
single coordination hub for all code sessions.** Spawning sessions without informing
Build Master created state gaps that then required manual catch-up — exactly the
catch-up this retrospective itself was written after. Routing every code session
through one coordinator, backed by a machine-readable state file, is the structural
fix for the recovery overhead that recurred throughout v0.3.
