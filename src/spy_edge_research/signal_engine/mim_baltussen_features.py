"""MIM-Baltussen rest-of-day intraday-momentum features (M121).

Path-2 sibling signal pre-registered in ``docs/PREREG_MIM_BALTUSSEN.md`` (lineage
``RESEARCH_F`` / RESEARCH_H Family 1 — Intraday Momentum, *variant*). It supersedes
the dead Gao first-30-min/overnight formulation with the **live** Baltussen, Da,
Lammers & Martens (2021, JFE) predictor: the **cumulative rest-of-day return**
positively predicts the last-window return, because option-market-maker gamma
hedging and leveraged-ETF rebalancing impose *structural, forced* end-of-day
trading in the direction of the day's move.

Strictly causal / no-lookahead, mirroring the MIM and F2 constructions:

- **Predictor.** ``r_rod`` = cumulative SPY log return from the **prior session's
  close to the cutoff** (Config A 15:30 ET, Config B 15:00 ET), measured at the
  *decision bar* (the first regular bar at/after the cutoff). The prior close is
  known from the session's first bar; the cutoff-bar close has timestamp ≤ cutoff.
  No bar after the cutoff enters the feature.
- **Position (momentum).** ``long if r_rod > +tau ; short if r_rod < -tau ; flat
  otherwise`` — emitted on the decision bar, held into the 16:00 close (resolved by
  the separate to-close forward label). A magnitude-scaled variant is DEFERRED per
  the pre-registration and is **not** emitted here.
- **Regime gate (causal; measured at the prior-session close so known pre-trade).**
  One of {``unconditional``, ``VIX > 20``, ``VIX > trailing rolling median``,
  ``GARCH(1,1) conditional vol > trailing median``}. The two VIX gates require a
  daily VIX series; when none is supplied (the SPY-only Hard Gate A pipeline) those
  gates are inactive and their event columns simply never fire. The GARCH gate is
  computed from the SPY daily closes themselves — a frozen-parameter (burn-in MLE,
  variance-targeted) GARCH(1,1) recursion, which is causal because the conditional
  variance for session t uses only returns through t-1.

The module emits boolean ``event_mimb_*`` columns so the 32-cell frozen grid (4
thresholds x 4 regime gates x 2 configs) flows through the SAME candidate /
edge-measurement / Hard-Gate-A pipeline as every other family — a new set of
candidates through the same gate, not a new gate. Each cell emits a ``long`` and a
``short`` column (the harness's directional event-mask convention), so the 32 cells
are encoded as 64 directional event columns.

Research-only feature engineering: no trade signal, order, sizing, or
authorization. Descriptive context columns only.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

MIMB_EVENT_PREFIX = "event_mimb_"

# Frozen pre-registered grid (docs/PREREG_MIM_BALTUSSEN.md §3).
GATE_UNCONDITIONAL = "unconditional"
GATE_VIX_GT_20 = "vix_gt_20"
GATE_VIX_GT_MEDIAN = "vix_gt_trailing_median"
GATE_GARCH_GT_MEDIAN = "garch_gt_trailing_median"
MIMB_REGIME_GATES: tuple[str, ...] = (
    GATE_UNCONDITIONAL,
    GATE_VIX_GT_20,
    GATE_VIX_GT_MEDIAN,
    GATE_GARCH_GT_MEDIAN,
)

# Thresholds tau in (log) return units: 0, 0.10%, 0.25%, 0.50%.
MIMB_THRESHOLDS: tuple[float, ...] = (0.0, 0.0010, 0.0025, 0.0050)


@dataclass(frozen=True)
class MimBaltussenConfigSpec:
    """Frozen trade-window config (no overlap with the predictor; no lookahead).

    ``hold_minutes`` is the number of 1-minute bars from the decision bar to the
    session's final bar, i.e. the forward horizon whose label resolves at the close
    (15:59 bar ~ official 16:00 print). Config A: 15:30 -> 15:59 = 29; Config B:
    15:00 -> 15:59 = 59.
    """

    name: str
    cutoff_time: str
    hold_minutes: int


MIMB_CONFIG_A = MimBaltussenConfigSpec(name="a", cutoff_time="15:30", hold_minutes=29)
MIMB_CONFIG_B = MimBaltussenConfigSpec(name="b", cutoff_time="15:00", hold_minutes=59)
MIMB_CONFIGS: tuple[MimBaltussenConfigSpec, ...] = (MIMB_CONFIG_A, MIMB_CONFIG_B)

VOL_REGIME_HIGH = "high"
VOL_REGIME_NORMAL = "normal"
VOL_REGIME_UNKNOWN = "unknown"


def mim_baltussen_to_close_horizons(
    configs: tuple[MimBaltussenConfigSpec, ...] = MIMB_CONFIGS,
) -> tuple[int, ...]:
    """Return the to-close forward horizons each config needs (sorted, unique)."""
    return tuple(sorted({spec.hold_minutes for spec in configs}))


def add_mim_baltussen_features(
    df: pd.DataFrame,
    *,
    configs: tuple[MimBaltussenConfigSpec, ...] = MIMB_CONFIGS,
    gates: tuple[str, ...] = MIMB_REGIME_GATES,
    thresholds: tuple[float, ...] = MIMB_THRESHOLDS,
    vix_daily: pd.Series | None = None,
    timestamp_col: str = "timestamp",
    close_col: str = "close",
    timezone: str = "America/New_York",
    session_open: str = "09:30",
    session_close: str = "16:00",
    vix_threshold: float = 20.0,
    regime_lookback_days: int = 60,
    garch_burnin_days: int = 60,
) -> pd.DataFrame:
    """Add causal MIM-Baltussen rest-of-day momentum features and event columns.

    For each (config, gate, threshold) cell the module emits, on the decision bar:

      - ``event_mimb_{config}_{gate}_{tau}_long`` — ``r_rod > +tau`` and gate active.
      - ``event_mimb_{config}_{gate}_{tau}_short`` — ``r_rod < -tau`` and gate active.

    plus, per config, descriptive decision-bar context columns
    (``mimb_{config}_decision_bar``, ``mimb_{config}_r_rod``) and, per gate, a
    boolean active mask (``mimb_{config}_gate_{gate}``).

    ``vix_daily`` is an optional Series indexed by ``datetime.date`` of the daily VIX
    *level at each session's close*; when omitted the two VIX gates are inactive and
    their event columns never fire. The GARCH gate is derived from the SPY daily
    closes and needs no external data.
    """
    _require_columns(df, [timestamp_col, close_col])
    _validate_positive_int(regime_lookback_days, "regime_lookback_days")
    _validate_positive_int(garch_burnin_days, "garch_burnin_days")
    for gate in gates:
        if gate not in MIMB_REGIME_GATES:
            raise ValueError(f"unknown regime gate: {gate!r}")
    for tau in thresholds:
        if not isinstance(tau, (int, float)) or isinstance(tau, bool) or tau < 0:
            raise ValueError("thresholds must be non-negative numbers")

    open_min = _minute_of_day_from_clock(session_open, "session_open")
    close_min = _minute_of_day_from_clock(session_close, "session_close")

    result = df.copy()
    local = _local_datetime(result[timestamp_col], timezone)
    trading_date = pd.Series(local.dt.date, index=result.index)
    minute_of_day = pd.Series(local.dt.hour * 60 + local.dt.minute, index=result.index)
    in_session = (minute_of_day >= open_min) & (minute_of_day <= close_min)

    # Prior-session close: the last regular-session close of the *previous* trading
    # date, broadcast across every bar of the current date. Known causally from the
    # current session's first bar (it is yesterday's print).
    close_in_session = result[close_col].where(in_session)
    session_last_close = close_in_session.groupby(trading_date).transform("last")
    per_date_last = (
        close_in_session.groupby(trading_date).last()
    )
    prior_close_by_date = per_date_last.shift(1)
    prior_session_close = trading_date.map(prior_close_by_date)

    # Per-session daily log return (close-to-close), for the GARCH gate.
    daily_log_return = np.log(
        per_date_last.div(per_date_last.shift(1).replace(0, np.nan))
    )

    # Regime series, all indexed by trading date and made pre-trade-known by using
    # the value measured at the *prior* session's close (``.shift(1)``).
    garch_vol_by_date = _garch11_conditional_vol(
        daily_log_return, burnin=garch_burnin_days
    )
    garch_active_by_date = _gt_trailing_median(
        garch_vol_by_date, lookback=regime_lookback_days
    )
    if vix_daily is not None:
        vix_by_date = _align_daily_series(vix_daily, per_date_last.index)
        vix_prior = vix_by_date.shift(1)
        vix_gt_20_by_date = vix_prior > vix_threshold
        vix_gt_median_by_date = _gt_trailing_median(
            vix_prior, lookback=regime_lookback_days
        )
    else:
        empty = pd.Series(False, index=per_date_last.index, dtype=bool)
        vix_gt_20_by_date = empty
        vix_gt_median_by_date = empty

    gate_by_date: dict[str, pd.Series] = {
        GATE_UNCONDITIONAL: pd.Series(True, index=per_date_last.index, dtype=bool),
        GATE_VIX_GT_20: vix_gt_20_by_date.astype(bool),
        GATE_VIX_GT_MEDIAN: vix_gt_median_by_date.astype(bool),
        GATE_GARCH_GT_MEDIAN: garch_active_by_date.astype(bool),
    }

    for spec in configs:
        cutoff_min = _minute_of_day_from_clock(spec.cutoff_time, f"cutoff[{spec.name}]")
        if not open_min < cutoff_min < close_min:
            raise ValueError(
                f"config {spec.name!r} cutoff must satisfy open < cutoff < close"
            )
        decision_bar = _first_bar_at_or_after(
            in_session=in_session,
            minute_of_day=minute_of_day,
            trading_date=trading_date,
            minute=cutoff_min,
        )
        result[f"mimb_{spec.name}_decision_bar"] = decision_bar

        # r_rod = log(close[decision] / prior_session_close); both terms <= cutoff.
        cutoff_close = result[close_col].where(decision_bar)
        ratio = cutoff_close.div(
            prior_session_close.where(decision_bar).replace(0, np.nan)
        )
        r_rod = np.log(ratio.where(ratio > 0))
        result[f"mimb_{spec.name}_r_rod"] = r_rod

        # Map each gate's per-date active flag onto this config's decision bars.
        gate_active_on_bar: dict[str, pd.Series] = {}
        for gate in gates:
            active = decision_bar & trading_date.map(gate_by_date[gate]).fillna(False).astype(bool)
            gate_active_on_bar[gate] = active
            result[f"mimb_{spec.name}_gate_{gate}"] = _safe_bool(active, result.index)

        for gate in gates:
            active = gate_active_on_bar[gate]
            for tau in thresholds:
                tag = _threshold_tag(tau)
                long_mask = active & (r_rod > tau)
                short_mask = active & (r_rod < -tau)
                base = f"{MIMB_EVENT_PREFIX}{spec.name}_{gate}_{tag}"
                result[f"{base}_long"] = _safe_bool(long_mask, result.index)
                result[f"{base}_short"] = _safe_bool(short_mask, result.index)

    # Suppress unused-variable lint on the broadcast helper kept for clarity.
    del session_last_close
    return result


def find_mim_baltussen_event_columns(df: pd.DataFrame) -> list[str]:
    """Return the MIM-Baltussen event columns present in ``df`` (sorted)."""
    return sorted(c for c in df.columns if c.startswith(MIMB_EVENT_PREFIX))


def _garch11_conditional_vol(daily_return: pd.Series, *, burnin: int) -> pd.Series:
    """Causal GARCH(1,1) conditional volatility per date (pure numpy).

    Parameters are estimated **once** on the first ``burnin`` daily returns by
    variance-targeted MLE over a frozen (alpha, beta) grid, then the variance
    recursion ``sigma2_t = omega + alpha*r_{t-1}^2 + beta*sigma2_{t-1}`` is run
    forward. The recursion is causal (sigma_t uses only r_{t-1}, sigma_{t-1}); the
    conditional vol for dates inside the burn-in window is returned as NaN so the
    gate never relies on in-sample-fit sessions.
    """
    returns = daily_return.to_numpy(dtype="float64")
    n = len(returns)
    out = pd.Series(np.nan, index=daily_return.index, dtype="float64")
    finite = returns[np.isfinite(returns)]
    if len(finite) <= burnin or len(finite) < 10:
        return out

    train = finite[:burnin]
    sample_var = float(np.var(train, ddof=1))
    if not np.isfinite(sample_var) or sample_var <= 0:
        return out

    alpha, beta = _fit_garch_alpha_beta(train, sample_var)
    omega = sample_var * (1.0 - alpha - beta)

    # Forward recursion over the full (date-ordered) series; first finite return
    # seeds sigma2 at the unconditional variance.
    sigma2 = np.full(n, np.nan, dtype="float64")
    prev_sigma2 = sample_var
    prev_r = None
    count_finite = 0
    for i in range(n):
        r = returns[i]
        if not np.isfinite(r):
            continue
        if prev_r is None:
            cur = sample_var
        else:
            cur = omega + alpha * prev_r * prev_r + beta * prev_sigma2
        cur = max(cur, 1e-12)
        sigma2[i] = cur
        prev_sigma2 = cur
        prev_r = r
        count_finite += 1
        # Mask the in-sample burn-in span so the gate only sees frozen-param,
        # out-of-fit conditional vols.
        if count_finite <= burnin:
            sigma2[i] = np.nan

    out.iloc[:] = np.sqrt(sigma2)
    return out


def _fit_garch_alpha_beta(returns: np.ndarray, sample_var: float) -> tuple[float, float]:
    """Variance-targeted GARCH(1,1) (alpha, beta) by coarse-grid Gaussian MLE."""
    alphas = np.linspace(0.02, 0.30, 15)
    betas = np.linspace(0.50, 0.97, 24)
    best = (0.10, 0.85)
    best_ll = -np.inf
    for alpha in alphas:
        for beta in betas:
            if alpha + beta >= 0.999:
                continue
            omega = sample_var * (1.0 - alpha - beta)
            if omega <= 0:
                continue
            ll = _garch_log_likelihood(returns, omega, alpha, beta, sample_var)
            if ll > best_ll:
                best_ll = ll
                best = (float(alpha), float(beta))
    return best


def _garch_log_likelihood(
    returns: np.ndarray, omega: float, alpha: float, beta: float, seed_var: float
) -> float:
    sigma2 = seed_var
    ll = 0.0
    for i in range(len(returns)):
        if i > 0:
            sigma2 = omega + alpha * returns[i - 1] ** 2 + beta * sigma2
        sigma2 = max(sigma2, 1e-12)
        ll += -0.5 * (np.log(2.0 * np.pi * sigma2) + returns[i] ** 2 / sigma2)
    return float(ll)


def _gt_trailing_median(series: pd.Series, *, lookback: int) -> pd.Series:
    """Boolean: value strictly exceeds its trailing rolling median (causal).

    The rolling median is ``.shift(1)`` so a session is judged against history
    *before* it; NaN history yields False (gate inactive until enough data).
    """
    median = series.rolling(lookback, min_periods=lookback).median().shift(1)
    active = series > median
    return active.fillna(False).astype(bool)


def _align_daily_series(vix_daily: pd.Series, dates: pd.Index) -> pd.Series:
    """Align an external daily series onto the pipeline's per-date index."""
    src = vix_daily.copy()
    src.index = [
        d.date() if isinstance(d, (pd.Timestamp,)) else d for d in src.index
    ]
    return pd.Series([src.get(d, np.nan) for d in dates], index=dates, dtype="float64")


def _threshold_tag(tau: float) -> str:
    """Compact basis-point tag for a threshold, e.g. 0.0025 -> ``t25``."""
    return f"t{int(round(tau * 10000))}"


def _first_bar_at_or_after(
    *,
    in_session: pd.Series,
    minute_of_day: pd.Series,
    trading_date: pd.Series,
    minute: int,
) -> pd.Series:
    at_or_after = in_session & (minute_of_day >= minute)
    previously_after = at_or_after.groupby(trading_date).shift(1).fillna(False).astype(bool)
    return at_or_after & (~previously_after)


def _local_datetime(timestamps: pd.Series, timezone: str) -> pd.Series:
    parsed = pd.to_datetime(timestamps)
    if parsed.dt.tz is None:
        parsed = parsed.dt.tz_localize(timezone)
    else:
        parsed = parsed.dt.tz_convert(timezone)
    return pd.Series(parsed, index=timestamps.index)


def _minute_of_day_from_clock(clock: str, name: str) -> int:
    try:
        hour_str, minute_str = clock.split(":")
        hour, minute = int(hour_str), int(minute_str)
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"{name} must be a 'HH:MM' clock string") from exc
    if not (0 <= hour < 24 and 0 <= minute < 60):
        raise ValueError(f"{name} must be a valid 'HH:MM' clock time")
    return hour * 60 + minute


def _safe_bool(values: pd.Series, index: pd.Index) -> pd.Series:
    return pd.Series(values, index=index).fillna(False).astype(bool)


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _validate_positive_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be an integer greater than or equal to 1")
