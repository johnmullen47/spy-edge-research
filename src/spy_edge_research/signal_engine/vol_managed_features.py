"""F7 — volatility-managed exposure (M125).

Pre-registered in ``docs/PREREG_F7.md`` (immutable). NEW Family 4, pre-registered as
a likely-fail adjudication of a contested effect (Moreira-Muir 2017 vs. Cederburg et
al. 2020 / DeMiguel et al. 2024). The inverse-vol weight ``w = clip(sigma_target /
sigma_hat, 0, 1)`` de-risks in high vol; in this binary event harness that maps to a
**full-exposure (long) regime when ``sigma_hat < sigma_target``** (weight saturates
at 1), flat otherwise — the timing content of the managed rule. Whether holding on
those low-vol days actually improves the outcome is exactly what Hard Gate A tests.

Causal (event on each session's last bar; sigma_hat known through that close):
- estimators ``sigma_hat`` (annualized): ``realized`` (trailing 21-session intraday
  realized vol), ``vix`` (VIX/100), ``garch`` (GARCH(1,1) conditional vol, the same
  causal frozen-parameter estimator as MIM-Baltussen).
- ``sigma_target``: ``median`` (trailing rolling median of sigma_hat, ``.shift(1)``)
  or ``ten`` (10% annualized).
3 estimators x 2 targets = 6 long columns; the registry pairs them with the
1-session (daily) and 5-session (weekly) horizons (12 candidates). Research-only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from spy_edge_research.signal_engine._daily import (
    build_daily_session_context,
    map_date_flag_to_last_bar,
)
from spy_edge_research.signal_engine._rest_of_day import validate_positive_int
from spy_edge_research.signal_engine.mim_baltussen_features import _garch11_conditional_vol

F7_EVENT_PREFIX = "event_f7_"
F7_ESTIMATORS: tuple[str, ...] = ("realized", "vix", "garch")
F7_TARGETS: tuple[str, ...] = ("median", "ten")
_ANNUALIZE = float(np.sqrt(252.0))
_RV_WINDOW = 21
_TEN_PCT = 0.10


def add_vol_managed_features(
    df: pd.DataFrame,
    *,
    vix_frame: pd.DataFrame | None = None,
    estimators: tuple[str, ...] = F7_ESTIMATORS,
    targets: tuple[str, ...] = F7_TARGETS,
    timestamp_col: str = "timestamp",
    close_col: str = "close",
    timezone: str = "America/New_York",
    session_open: str = "09:30",
    session_close: str = "16:00",
    target_lookback_days: int = 60,
    garch_burnin_days: int = 60,
) -> pd.DataFrame:
    """Add causal F7 vol-managed full-exposure event columns (per session last bar)."""
    validate_positive_int(target_lookback_days, "target_lookback_days")
    for e in estimators:
        if e not in F7_ESTIMATORS:
            raise ValueError(f"unknown F7 estimator: {e!r}")
    for t in targets:
        if t not in F7_TARGETS:
            raise ValueError(f"unknown F7 target: {t!r}")

    ctx = build_daily_session_context(
        df, timestamp_col=timestamp_col, close_col=close_col, timezone=timezone,
        session_open=session_open, session_close=session_close,
    )
    result = df.copy()
    result["f7_last_bar"] = ctx.last_bar

    sigma: dict[str, pd.Series] = {}
    if "realized" in estimators:
        rv_mean = ctx.daily_realized_var.rolling(_RV_WINDOW, min_periods=_RV_WINDOW).mean()
        sigma["realized"] = np.sqrt(rv_mean) * _ANNUALIZE
    if "vix" in estimators:
        if vix_frame is not None:
            sigma["vix"] = pd.to_numeric(
                vix_frame.reindex(ctx.per_date_dates).get("vix"), errors="coerce"
            ) / 100.0
        else:
            sigma["vix"] = pd.Series(np.nan, index=ctx.per_date_dates, dtype="float64")
    if "garch" in estimators:
        sigma["garch"] = _garch11_conditional_vol(
            ctx.daily_log_return, burnin=garch_burnin_days
        ) * _ANNUALIZE

    for est in estimators:
        s = sigma[est]
        for tgt in targets:
            if tgt == "median":
                target = s.rolling(target_lookback_days, min_periods=target_lookback_days).median().shift(1)
            else:  # ten
                target = pd.Series(_TEN_PCT, index=s.index, dtype="float64")
            low_vol = (s < target) & np.isfinite(s) & np.isfinite(target)
            result[f"{F7_EVENT_PREFIX}{est}_{tgt}_long"] = map_date_flag_to_last_bar(
                low_vol.fillna(False).astype(bool),
                last_bar=ctx.last_bar, trading_date=ctx.trading_date, index=result.index,
            )
    return result


def find_f7_event_columns(df: pd.DataFrame) -> list[str]:
    """Return the F7 event columns present in ``df`` (sorted)."""
    return sorted(c for c in df.columns if c.startswith(F7_EVENT_PREFIX))
