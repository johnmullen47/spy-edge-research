# ChatGPT Project Handoff: Trading Theory, Research Philosophy, and Signal Thesis

**Project:** SPY Directional Edge Research / Auto-Trader SPY  
**Intended reader:** Claude Code, Codex, or another technical co-worker inheriting the project  
**Purpose:** Preserve the trading-theory context and research philosophy developed in ChatGPT project sessions, separate from the implementation details already present in GitHub.  
**Date prepared:** 2026-06-14  
**Status:** This is a theory/context handoff, not a claim that any tradable edge has been validated.

---

## 1. Executive Summary

This project began from a discretionary intraday SPY trading idea: identify short-term directional continuation in SPY over roughly the next 5–30 minutes using chart-confirmed price action rather than prediction, gut feel, or options gambling.

The original human trading frame emphasized:

- SPY as the primary instrument.
- 1-minute and 5-minute OHLCV bars.
- VWAP.
- 9 EMA.
- Bollinger Bands.
- Support and resistance.
- Prior-day levels.
- Premarket levels.
- Break of structure.
- Repeated touches of levels.
- Retests.
- False breaks.
- Momentum/volume confirmation.
- Market sentiment/news as possible future context.
- Few trades per day rather than constant trading.
- Typical intended hold time around 5–25 minutes, with research horizons generalized to 5, 10, 15, and 30 minutes.

The ChatGPT-side conclusion was that this should **not** be built first as an options bot, broker integration, alert system, screenshot reader, or live execution engine. It should first be built as a research-grade, causal, auditable directional-edge platform.

The core research question is:

> Do specific, causally detectable intraday SPY price-action events show statistically meaningful directional continuation over the next 5–30 minutes, after baselines, costs, data quality, multiple-testing risk, time splits, negative controls, and regime/context effects are accounted for?

The project should remain comfortable outputting:

> No valid edge.  
> Evidence insufficient.  
> Current regime invalid.  
> Candidate failed robustness checks.  
> No trade.

A “no trade” answer is not a failure. It is the expected behavior of a serious research system when evidence does not justify action.

---

## 2. What This Document Is and Is Not

This document captures what is known from the ChatGPT project conversations: the trading thesis, the research philosophy, the signal vocabulary, the methodological guardrails, and the practical conclusions that motivated the implementation.

It is **not** the authoritative source for:

- Current code state.
- Current test counts.
- Exact APIs.
- Exact milestone numbers.
- Current repository file paths.
- Live Git status.
- Whether a given module has already been implemented.

For implementation state, read the live repository first. In particular, read the freshest handoff and milestone documents in GitHub before making code changes.

This document should be treated as the “why” behind the project, not the current implementation ledger.

---

## 3. Original Trading Motivation

The seed idea came from a desire to make short-term SPY trading less discretionary and more rule-based.

The initial practical trading goal was something like:

- A small number of high-quality SPY trades per day.
- Potentially around five trades per day.
- Short holds, often 5–25 minutes.
- Directional confirmation rather than raw prediction.
- Eventually expressing trades through options, but only after proving the underlying directional edge.

The user’s practical dream included ideas like “tell me what is happening in SPY over the next 15 minutes,” “show confirmation levels,” and “tell me what direction has begun confirming.” But the research translation explicitly rejected the idea that the system should forecast the future in an unconstrained way.

The better framing became:

> The system is not trying to predict the future.  
> It is trying to identify moments where price has already begun confirming direction and where historical evidence shows that continuation is statistically favored over the next few minutes.

This distinction matters. The project is not a magic chart reader. It is an event-conditioned edge research platform.

---

## 4. Core Philosophical Pivot

The major ChatGPT recommendation was:

> Start with the directional signal engine and historical validation. Do not start with options, broker APIs, live execution, order routing, screenshots, or Robinhood automation.

The reasoning:

1. **Options add leverage and complexity before the base edge is proven.**  
   If the underlying SPY directional edge is weak or nonexistent, options will amplify noise, not solve it.

2. **Broker integration creates operational risk before research validity exists.**  
   A system that can place trades but cannot prove edge is worse than a spreadsheet.

3. **Screenshots and LLM chart interpretation are unreliable foundations.**  
   The project should use structured OHLCV data, deterministic features, and auditable outputs.

4. **Backtesting must come before paper trading, and paper trading must come before live trading.**  
   Historical testing cannot prove future profitability by itself, but it can eliminate bad ideas faster than waiting months in paper trading.

5. **The first serious product is not a trader. It is an evidence machine.**  
   Its job is to test hypotheses and kill weak edges.

---

## 5. The Signal Thesis in Plain English

The trading thesis can be summarized as:

> SPY may have short-lived directional continuation after certain intraday confirmation events, especially when the event aligns with intraday structure, VWAP/EMA context, level behavior, volume/momentum, volatility regime, and time of day.

The most important word is **may**.

Nothing about VWAP, EMA, Bollinger Bands, support/resistance, or break of structure is assumed to work. Every setup must be converted into a causal event and tested.

The system should not ask:

> “Does this chart look bullish?”

It should ask:

> “Historically, when this exact causal event appeared under this exact context, what happened over the next 5, 10, 15, and 30 minutes compared with a baseline?”

---

## 6. Research Translation of the Discretionary Strategy

The discretionary trader vocabulary was translated into testable components.

### 6.1 Market Context

Market context means the state of the market before or at the event row.

Examples:

- Above or below VWAP.
- Above or below 9 EMA.
- EMA slope.
- Bollinger Band compression or expansion.
- Trending up, trending down, range-bound, or unknown.
- Volatility high, normal, or low.
- Range expansion or range compression.
- Time-of-day bucket.
- Prior-day high/low/close proximity.
- Premarket high/low proximity.
- Sector or macro confirmation, in later modules.
- Cross-instrument confirmation or divergence, in later modules.

Context is not the trade trigger by itself. It conditions how a trigger should be interpreted.

### 6.2 Key Levels

The project’s theory treats levels as places where behavior matters.

Important level families:

- VWAP.
- 9 EMA.
- Prior-day high.
- Prior-day low.
- Prior-day close.
- Premarket high.
- Premarket low.
- Confirmed pivot highs/lows.
- Trailing highs/lows.
- Support/resistance zones derived only from information available at that time.

A level is not automatically a signal. The signal is the price behavior around the level.

### 6.3 Confirmation Events

The project should test events like:

- VWAP reclaim.
- VWAP loss.
- VWAP rejection.
- VWAP bounce.
- EMA reclaim/loss.
- Trailing breakout.
- Trailing breakdown.
- Prior/resistance zone breakout.
- Prior/support zone breakdown.
- Break of structure.
- Retest after break.
- Failed breakout.
- Failed breakdown.
- Momentum/volume confirmation.
- Range expansion.
- Multi-event sequences.

These are hypotheses, not facts.

### 6.4 Scalping / Short-Horizon Outcome

The expected outcome window is intentionally short:

- 5 minutes.
- 10 minutes.
- 15 minutes.
- 30 minutes.

The original user target involved short holds, often around 5–25 minutes. The implementation generalized this into research horizons.

The system should evaluate:

- Forward return.
- Directional hit rate.
- Maximum favorable excursion.
- Maximum adverse excursion.
- Time-to-follow-through.
- Whether continuation appears before adverse movement.
- Whether the event has enough magnitude to survive costs and slippage.

---

## 7. Major Signal Families

### 7.1 VWAP Signals

VWAP is central because it often acts as an intraday institutional reference level.

Hypotheses to test:

- A reclaim of VWAP after being below it may indicate bullish continuation.
- A loss of VWAP after being above it may indicate bearish continuation.
- Rejection from below VWAP may indicate continued weakness.
- Bounce from above VWAP may indicate continued strength.
- VWAP signals may matter more when combined with volume, trend, or level context.

Cautions:

- VWAP is widely watched, so naïve VWAP signals may be arbitraged away or noisy.
- “Above VWAP” alone is not enough.
- VWAP signal quality may vary heavily by time of day.
- VWAP crosses around chop may create false positives.

### 7.2 9 EMA Signals

The 9 EMA was part of the original discretionary frame as a fast trend/trade-management reference.

Hypotheses to test:

- Price reclaiming the 9 EMA during a bullish context may support continuation.
- Price losing the 9 EMA during bearish context may support continuation.
- EMA slope may help classify micro-trend.
- EMA/VWAP alignment may be stronger than either alone.

Cautions:

- Fast EMAs are extremely sensitive to noise.
- EMA crosses can overfit quickly.
- EMA behavior must be tested against baselines and negative controls.

### 7.3 Bollinger Band Signals

Bollinger Bands were included in the initial trader vocabulary as a way to understand expansion, compression, and stretched price behavior.

Hypotheses to test:

- Band compression may precede expansion.
- Band expansion after a level break may confirm momentum.
- Touches or closes outside bands may behave differently depending on trend context.
- Mean reversion versus continuation around bands may be regime-dependent.

Cautions:

- Bollinger signals are easy to misuse.
- A band touch is not automatically reversal or continuation.
- The context determines whether the event is meaningful.

### 7.4 Support / Resistance and Zones

Support and resistance must be causal.

Allowed level sources include:

- Prior completed day levels.
- Premarket levels as they become known.
- Confirmed pivots only after confirmation.
- Trailing highs/lows computed without leaking the current or future bar.
- Zones formed only from information available at or before the current row.

Forbidden:

- Drawing obvious levels using the full future chart.
- Using the day’s final high/low during the day.
- Backdating pivot levels to when they visually occurred instead of when they were confirmed.
- Treating manually obvious hindsight levels as valid research inputs.

Hypotheses to test:

- Break of resistance may produce short-term continuation.
- Break of support may produce short-term continuation.
- Repeated touches may weaken or strengthen a level depending on context.
- Retests after break may be better confirmation than the initial break.
- False breaks may produce opposite-direction continuation.

### 7.5 Break of Structure

Break of structure captures whether price has exceeded a causally known swing or pivot reference.

Hypotheses:

- Bullish structure break may predict short-term upward continuation.
- Bearish structure break may predict short-term downward continuation.
- Structure break aligned with VWAP/EMA/regime may be stronger.
- Structure break during chop may fail more often.

Cautions:

- Pivot confirmation can require later bars.
- The event can only be emitted when confirmation is available.
- Never backdate the structure break to make it look earlier or cleaner.

### 7.6 Retests

The project treats retests as potentially higher-quality confirmation events.

Hypotheses:

- Break above resistance followed by a successful retest may indicate bullish continuation.
- Break below support followed by a successful retest may indicate bearish continuation.
- Retest behavior may filter out some false breakouts.
- Retests near VWAP/EMA confluence may be more meaningful.

Cautions:

- Retest definitions must be explicit and deterministic.
- “Looks like a retest” is not enough.
- Retests can overfit if zone width or timing windows are tuned too freely.

### 7.7 False Breaks

False breaks are important because failed continuation attempts may themselves create directional edge in the opposite direction.

Hypotheses:

- Failed breakout above resistance may predict downside continuation.
- Failed breakdown below support may predict upside continuation.
- False breaks near prior-day or premarket levels may be meaningful.
- False breaks may be more powerful when accompanied by momentum failure.

Causal rule:

- A false break can only be emitted when the failure is known.
- It must not be backdated to the original break candle.

### 7.8 Momentum and Volume Confirmation

The original discretionary frame included “momentum,” “sentiment,” and “confirmation.” In structured research, the easiest measurable parts are price range and volume.

Hypotheses:

- Range expansion confirms breakouts better than small candles.
- Volume expansion confirms directional moves.
- Momentum plus level break may outperform level break alone.
- Volume without directional follow-through may signal exhaustion instead.

Cautions:

- Volume data quality matters.
- Some feeds may understate real market volume.
- Momentum filters often reduce sample size and increase overfitting risk.

### 7.9 Time-of-Day Effects

The system should not assume all minutes are equivalent.

Likely buckets:

- Open.
- Post-open.
- Mid-morning.
- Lunch.
- Afternoon.
- Power hour.
- Outside regular session.

Hypotheses:

- Breakout continuation may be stronger near the open or power hour.
- Lunch may be choppier or lower-quality.
- VWAP behavior may differ by time of day.
- Premarket levels may matter differently at the open than later in the day.

Cautions:

- Time-of-day filtering can create small samples.
- It must be evaluated chronologically, not optimized by hindsight.

### 7.10 Volatility and Range Context

Volatility context matters because the same price move can mean different things in different regimes.

Hypotheses:

- Continuation setups may work better in high-volatility expansion regimes.
- Mean reversion may dominate in low-volatility range-bound regimes.
- Stop/target assumptions should vary by volatility.
- Minimum economic edge should be judged relative to realistic movement and cost.

Cautions:

- Volatility filters can accidentally become hindsight filters if computed incorrectly.
- Rolling windows must use only past/current information.

### 7.11 Sequence-Based Signals

Many discretionary traders do not trade a single event; they trade a sequence:

> rejection → pullback → reclaim → retest → continuation

The project’s research frame supports testing event sequences.

Hypotheses:

- A sequence of events may have more signal than any single event.
- VWAP reclaim followed by EMA hold and resistance break may be stronger than VWAP reclaim alone.
- False break followed by structure reversal may be meaningful.
- Retest confirmation after break may improve event quality.

Cautions:

- Sequence mining creates massive multiple-testing risk.
- Support thresholds and FDR/negative controls are required.
- Complex sequences may look great in-sample and vanish out-of-sample.

---

## 8. Context Layers Beyond SPY

The project eventually expanded conceptually beyond SPY-only intraday chart features.

These expansions should be treated as context and filters, not magic predictors.

### 8.1 Multi-Instrument Confirmation

Potential related instruments:

- QQQ.
- IWM.
- DIA.
- VIX-related proxies.
- Sector ETFs.
- Rates, credit, commodity, or macro proxies in later research.

Hypotheses:

- SPY breakout with QQQ confirmation may be stronger than SPY alone.
- SPY weakness with sector breadth weakness may be stronger.
- Divergence may warn against low-quality continuation.
- Macro/rates context may explain why SPY setups work or fail.

### 8.2 Sector Context

Sector behavior can condition SPY moves.

Hypotheses:

- SPY bullish setup with broad sector confirmation may be higher quality.
- SPY bullish setup driven by only one sector may be more fragile.
- Sector rotation may explain intraday index chop or continuation.

### 8.3 Macro Regime

Macro context can influence whether intraday patterns persist.

Possible contexts:

- Rates up/down.
- Dollar strength/weakness.
- Credit risk proxies.
- Volatility regime.
- Commodity/risk-on/risk-off proxies.

Caution:

- Macro features are context, not a shortcut to edge.
- The more context filters added, the greater the risk of data mining.

### 8.4 Value / Quality / Momentum Research

The project also considered expanding into value, quality, and momentum research. This is conceptually distinct from the original intraday SPY scalping thesis.

The correct interpretation:

- VQM research is a broader research-platform extension.
- It should not be mixed casually with intraday SPY trading.
- It may help later if the platform evolves into broader ETF/equity research.
- It does not validate short-term SPY directional continuation.

---

## 9. Required Causal Discipline

Causal safety is the project’s central rule.

A feature at time `t` may use only information available at or before time `t`.

Forward-looking columns are allowed only as labels or outcomes for evaluation. They must never feed event generation, feature generation, candidate selection, or live decision logic.

Forbidden patterns:

- Using future candles to define current support/resistance.
- Using full-day high/low intraday.
- Using final session statistics intraday.
- Backdating pivots.
- Backdating retests.
- Backdating false breaks.
- Letting forward returns influence event definitions.
- Tuning thresholds on the full dataset and then pretending the result is causal.
- Ranking candidates by future performance without proper train/test separation.

The project should treat lookahead bias as a fatal research defect, not a minor bug.

---

## 10. Research Methodology

The project’s method should follow this chain:

1. Load and validate OHLCV data.
2. Generate causal indicators and event features.
3. Generate evaluation-only forward labels/outcomes.
4. Map raw event features to named event hypotheses.
5. Run event studies over 5/10/15/30-minute horizons.
6. Compare event outcomes against baselines.
7. Segment by context and regime.
8. Measure sample size and uncertainty.
9. Run statistical tests.
10. Adjust for multiple hypotheses.
11. Run negative controls.
12. Run chronological splits and walk-forward validation.
13. Register candidate edges only if they survive evidence filters.
14. Simulate historical trades only after candidate evidence exists.
15. Use paper/live decision support only after readiness gates pass.

At every stage, the default answer should be skepticism.

---

## 11. Baselines Matter

A setup is not meaningful merely because it has a positive average return.

It must beat relevant baselines, such as:

- Always long.
- Always short.
- Random direction.
- VWAP relation baseline.
- EMA relation baseline.
- Context-only baseline.
- Same time-of-day baseline.
- Same regime baseline.
- Event component baseline, for sequence events.

Example:

If “VWAP reclaim during high volatility” has positive forward returns, the system must ask whether all high-volatility upward contexts had similar returns. The event has edge only if it adds information beyond the context.

---

## 12. Multiple-Testing and Data-Mining Risk

This project has severe data-mining risk because it can generate many possible combinations:

- Many events.
- Multiple directions.
- Multiple horizons.
- Multiple time buckets.
- Multiple regimes.
- Multiple volatility contexts.
- Multiple instruments.
- Multiple sequence definitions.
- Multiple thresholds.

Therefore, unadjusted “good-looking” results are not enough.

The research framework must use:

- Minimum sample-size rules.
- Train/test splits.
- Walk-forward validation.
- Negative controls.
- Multiple-hypothesis correction.
- Economic significance floors.
- Out-of-sample confirmation.
- Human-readable caveats.

The project should assume most apparent edges are false until proven otherwise.

---

## 13. Economic Significance

A statistically positive result is not automatically tradable.

For an intraday SPY strategy, the edge must survive:

- Spread.
- Slippage.
- Fees, if applicable.
- Bad fills.
- Latency.
- Missed signals.
- Position sizing constraints.
- Psychological execution errors, if human-approved.
- Taxes, if evaluating after-tax goals.
- Opportunity cost.

The ChatGPT project explicitly challenged the idea that consistent average daily gains of +0.5% to +1.0% of portfolio value after taxes are a reasonable baseline expectation. That target is extremely aggressive, especially at larger capital sizes, and should not be treated as a design requirement.

The more professional target is:

> Find whether any repeatable edge exists first.  
> Then quantify its size, capacity, drawdowns, costs, and failure modes.  
> Only then discuss return targets.

The project should be oriented toward quantified and controlled risk, not uncontrolled and unquantified risk.

---

## 14. Backtesting vs Paper Trading

The ChatGPT project concluded that historical backtesting can reduce the need to wait a full year before learning anything. With enough clean historical intraday data, many hypotheses can be rejected quickly.

But backtesting does not eliminate the need for paper trading.

Backtesting is good for:

- Killing weak hypotheses.
- Measuring historical event behavior.
- Comparing contexts.
- Detecting obvious overfitting.
- Testing execution assumptions.
- Building confidence in research plumbing.

Paper trading is still needed for:

- Live data handling.
- Signal timing.
- Human review workflow.
- Operational reliability.
- Fill assumptions.
- Slippage realism.
- Psychological pressure.
- End-to-end dry runs.

Backtesting answers:

> Did this event historically have edge under controlled assumptions?

Paper trading answers:

> Can the system detect, present, and manage this setup in real time without breaking?

These are different questions.

---

## 15. Data Sourcing Reality

The project should not assume free data is good enough for final validation.

Important data concerns:

- 1-minute bars may hide intrabar path.
- Feed choice affects volume and apparent liquidity.
- Some free feeds have incomplete volume.
- Recent SIP data may require paid access.
- Corporate actions and session handling must be correct.
- Premarket and regular-session boundaries must be explicit.
- Timezones must be handled carefully.
- Missing bars must be detected.
- Data provenance must be recorded.

For early research, free or low-cost data can be enough to build and test infrastructure. For serious validation, data quality becomes a major gating issue.

---

## 16. Options Layer: Deferred by Design

The original dream involved options, but the project intentionally deferred options.

Reasons:

- Options introduce strike selection.
- Expiration selection.
- Delta/gamma/theta/vega exposure.
- Spread/slippage complexity.
- Liquidity constraints.
- Volatility surface effects.
- Assignment/exercise considerations.
- Nonlinear P&L.
- Greater risk of overtrading.

The correct sequence is:

1. Prove directional SPY edge in the underlying.
2. Prove it survives costs and slippage.
3. Prove it survives paper-trading workflow.
4. Only then research options expression.

The options layer should answer:

> Given a validated underlying directional edge, what is the best risk-defined way to express it?

It should not be used to rescue an unvalidated underlying signal.

---

## 17. Broker / Live Execution: Also Deferred or Gated

The project’s philosophy is that broker integration is a late-stage operational layer.

Broker code should not exist to make the project feel exciting. It should exist only when the research and readiness gates justify it.

Any live or paper broker layer must be:

- Human-approved.
- Kill-switch protected.
- Limit-controlled.
- Audit-logged.
- Sandbox-first.
- Incapable of accidental live trading by default.
- Explicit about “not investment advice” and “not an autonomous trader.”

The human should approve every order unless and until a future, separate, much stricter standard is met.

---

## 18. Frontend / Dashboard Philosophy

The first useful interface should be a research review interface, not a flashing trade dashboard.

Useful first frontend features:

- Load SPY data.
- Run signal engine.
- Display chart with VWAP, EMA, zones, and events.
- Show detected setups.
- Show forward-outcome stats.
- Show candidate edge ranking with caveats.
- Show backtest reports.
- Inspect trades/signals.
- Export audit/report files.
- Clearly indicate “not ready” or “no valid edge.”

Dangerous frontend features:

- Buy/sell buttons.
- Urgent alerts.
- Confidence scores that look like trade instructions.
- Green/red dashboards implying action without validated edge.
- LLM-generated market opinions.
- Screenshot-driven discretionary trade calls.

The interface should make bad evidence obvious.

---

## 19. What “Bullish / Bearish / Neutral” Should Mean

If the system eventually emits a directional interpretation, it should not mean “trade now.”

A proper output should include:

- Direction hypothesis: bullish, bearish, or neutral.
- Evidence source: which event(s) triggered.
- Context: VWAP/EMA/regime/time/volatility/levels.
- Historical sample size.
- Forward horizon.
- Baseline comparison.
- Expected edge or expectancy.
- Confidence interval or uncertainty.
- Caveats.
- Invalidation level or condition.
- Readiness status.
- Human review requirement.

A good output might say:

> Bullish hypothesis detected, but candidate is not trade-ready due to insufficient out-of-sample evidence and failed negative-control checks.

That is a successful system response.

---

## 20. Professional Realism

ChatGPT repeatedly pushed the project away from unrealistic expectations.

Important realism points:

- A strategy that reliably earns $250/day with small capital and few trades is not impossible, but it is not something to assume.
- Consistent +0.5% to +1.0% average daily portfolio growth after taxes is extremely aggressive.
- Professional quant shops invest heavily in data, infrastructure, execution, risk, and validation.
- Most simple technical-analysis rules do not survive robust testing.
- The project should not imitate influencer trading claims.
- The project should be designed to discover that an idea does not work.
- Risk-adjusted evidence matters more than exciting UI or automation.

The honest goal is not:

> Build a money printer.

The honest goal is:

> Build a system capable of proving or disproving whether these intraday SPY event hypotheses contain exploitable directional information.

---

## 21. Current High-Level Research Posture

From the ChatGPT project context, the correct posture is:

1. The user is interested in a semi-autonomous SPY trading system eventually.
2. The current intellectual foundation is directional-edge research, not autonomous trading.
3. The original signal vocabulary is discretionary but has been translated into causal event hypotheses.
4. The platform should keep expanding only when the evidence and governance justify it.
5. The system should prefer “no edge found” over false confidence.
6. Any candidate edge must survive robustness, cost, and operational checks.
7. The project’s most important asset is not any one signal but the research discipline.

---

## 22. Known Signal Hypotheses to Preserve

Future agents should preserve these as hypotheses worth testing or extending, not as proven strategies:

### VWAP / EMA

- VWAP reclaim after below-VWAP weakness.
- VWAP loss after above-VWAP strength.
- VWAP rejection from below.
- VWAP bounce from above.
- EMA reclaim/loss as micro-trend confirmation.
- VWAP + EMA alignment.
- VWAP/EMA disagreement as chop or transition.

### Levels

- Break above prior-day high.
- Break below prior-day low.
- Reclaim/loss of prior-day close.
- Break above/below premarket high/low.
- Confirmed pivot break.
- Trailing high/low break.
- Retest of broken level.
- Repeated touches of support/resistance.
- False breakout/failure.
- False breakdown/failure.

### Structure

- Bullish break of structure.
- Bearish break of structure.
- Higher-high/higher-low context.
- Lower-low/lower-high context.
- Structure break aligned with VWAP/EMA.
- Structure break against regime, as possible low-quality signal.

### Momentum / Volume

- Range expansion on break.
- Volume expansion on break.
- Momentum continuation after reclaim.
- Failed momentum after breakout.
- Exhaustion after stretched move.

### Regime

- Trend-up context.
- Trend-down context.
- Range-bound context.
- High-volatility context.
- Low-volatility context.
- Time-of-day concentration.

### Sequences

- Break → retest → continuation.
- False break → reversal structure break.
- VWAP reclaim → EMA hold → resistance break.
- Premarket level break → retest → trend continuation.
- Support/resistance rejection → structure break in opposite direction.

### External Context

- SPY move confirmed by QQQ/IWM/DIA.
- SPY move confirmed by sectors.
- SPY move contradicted by sector divergence.
- Macro regime filters.
- Volatility/rates/credit context.

---

## 23. Known Non-Goals and Rejected Shortcuts

Future agents should not revive these without explicit user authorization and strong reason:

- Screenshot-based trading from Robinhood images.
- LLM discretionary chart interpretation.
- Buy/sell alert bot.
- Live broker execution before validation.
- Options-first build.
- Strategy based only on one indicator cross.
- Full automation before human-approved paper workflow.
- Tuning rules until historical results look good.
- Ignoring costs because SPY is liquid.
- Treating high hit rate as sufficient without expectancy.
- Treating a pretty chart as evidence.
- Treating in-sample results as validation.
- Treating “AI confidence” as a trading signal.

---

## 24. How Claude/Codex Should Think While Continuing

A good co-worker should reason this way:

1. **Assume no edge until evidence says otherwise.**
2. **Convert every discretionary idea into a deterministic causal event.**
3. **Separate features from labels.**
4. **Separate event detection from outcome evaluation.**
5. **Separate research evidence from trade decisions.**
6. **Prefer boring tests over clever trading logic.**
7. **Add caveats instead of hiding uncertainty.**
8. **Treat data quality as part of the research result.**
9. **Reject accidental live-trading paths.**
10. **Do not optimize the system into overfit nonsense.**

---

## 25. Recommended Language for Project Outputs

Good language:

- “Candidate hypothesis.”
- “Research event.”
- “Forward outcome.”
- “Baseline comparison.”
- “Out-of-sample result.”
- “Not ready.”
- “Failed readiness gate.”
- “Insufficient evidence.”
- “Human review required.”
- “No validated edge.”

Bad language:

- “Guaranteed setup.”
- “Buy now.”
- “Sell now.”
- “High-confidence trade” without validated readiness.
- “This will move up.”
- “AI predicts.”
- “Profit signal.”
- “Autopilot trade.”

The project should sound like a research lab, not a trading Discord.

---

## 26. Practical Next Research Directions

If the implementation is already current, the most useful theory-aligned next directions are probably:

### 26.1 Better Candidate Generation

The existing candidate set may be too simple, too broad, or poorly conditioned. Future research could generate more precise hypotheses, but only with strict multiple-testing control.

Examples:

- More specific retest definitions.
- Better failed-break taxonomies.
- Regime-specific candidate definitions.
- Time-of-day-specific but predeclared hypotheses.
- Sequence candidates with minimum support rules.

### 26.2 Better Data

If current testing used limited or imperfect data, data quality may be the next bottleneck.

Questions:

- Is volume complete?
- Is the feed representative?
- Are premarket bars reliable?
- Do results change across feeds?
- Does tick or second-level data alter path assumptions?
- Are high-impact news days handled separately?

### 26.3 Better Execution Modeling

If any edge appears, it must be tested against conservative execution assumptions.

Include:

- Spread.
- Slippage.
- Entry delay.
- Exit delay.
- Missed fills.
- Stop/target mechanics.
- Realistic order types.
- Partial fills if relevant.
- Human approval delay.

### 26.4 Better Regime Segmentation

Some setups may only work in specific regimes.

But regime segmentation must be predeclared or validated carefully to avoid overfitting.

Useful dimensions:

- Volatility.
- Trend.
- Time of day.
- Macro/rates context.
- Sector breadth.
- Prior-day range.
- Gap day versus non-gap day.
- News/FOMC/CPI days, if reliable calendars are added.

### 26.5 Failure Analysis

If candidates fail, inspect why.

Failure categories:

- No raw edge.
- Edge exists but below cost.
- Edge exists only in-sample.
- Edge disappears after FDR correction.
- Edge driven by small sample.
- Edge driven by one period.
- Edge is actually context effect, not event effect.
- Edge is sensitive to data feed.
- Edge is killed by execution delay.

This failure analysis is valuable. It tells the project what not to build.

---

## 27. Stale Documentation Suggestions for Repo Maintainers

This section is included only because future agents may otherwise inherit stale assumptions from old root docs.

As of the latest known repo inspection from ChatGPT, some root documentation appears stale relative to the live project handoff and milestone state.

Suggested cleanup:

1. **Update `CODEX_MASTER_DESK.md`.**  
   It appears to reference completion through Milestone 69 and an older test baseline. That is no longer sufficient for current project state.

2. **Update `MASTER_PROJECT_BRIEF.md`.**  
   It still contains valuable philosophy, but its “current repository status” section appears old. Keep the principles; refresh the milestone/status language.

3. **Update `README.md`.**  
   The README has a long milestone narrative and may not clearly reflect the current later-stage modules. Consider replacing the long incremental history with:
   - project purpose,
   - quickstart,
   - architecture map,
   - current status pointer,
   - safety boundaries,
   - how to run tests,
   - links to handoff/milestones.

4. **Update `docs/HANDOFF.md` if public/private status changed.**  
   If the repo is now public, remove or revise any line saying the remote is private.

5. **Create a clear hierarchy of authority.**  
   Suggested hierarchy:
   - `docs/HANDOFF.md` for current operational state,
   - `PROJECT_MILESTONES.md` for milestone ledger,
   - `MASTER_PROJECT_BRIEF.md` for durable philosophy,
   - this document for ChatGPT-side trading-theory context,
   - old module briefs as historical records only.

---

## 28. One-Sentence Inheritance Summary

This project is a disciplined attempt to determine whether causally detectable intraday SPY price-action events—especially around VWAP, 9 EMA, support/resistance, structure breaks, retests, false breaks, momentum, volume, regime, and time of day—contain real short-horizon directional edge after baselines, costs, robustness checks, and operational constraints; until such evidence exists, the correct output is “no valid trade.”
