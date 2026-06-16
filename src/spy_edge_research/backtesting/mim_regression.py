"""Literature-faithful Market Intraday Momentum (MIM) predictive regression (M127).

This is the canonical MIM test as run in the source papers: a predictive OLS of the
**last-30-minute** return on a single intraday predictor, with **Newey-West (HAC)**
standard errors, reporting beta, t-statistic, R^2, and the Pearson correlation
(Fisher-z). Two co-primary, named published predictors:

- **H_a (Gao, Han, Li & Zhou 2018, JFE 129(2)):** first-30-minute return measured
  **from the prior close** -> ``r_ha = log(P_1000 / P_prev_close)``.
- **H_b (Baltussen, Da, Lammers & Martens 2021, JFE 142(1)):** rest-of-day return,
  prior close -> start of the final 30 minutes -> ``r_hb = log(P_1530 / P_prev_close)``
  (identical to the ``r_rod`` predictor already in ``mim_baltussen_features``).

Target (both): the final-30-minute return ``y = log(P_1600 / P_1530)``.

Strictly causal: each predictor uses only prices at/through its measurement clock
time (10:00 for H_a, 15:30 for H_b), both at or before the start of the target
window, so no future information enters the predictor. The target is an outcome
label only. One observation per trading day (the literature's daily aggregation).

Pure numpy/pandas (no statsmodels in-repo). Research-only measurement; authorizes
no trade.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

RTH_OPEN = "09:30"
FIRST30_END = "10:00"
LAST30_START = "15:30"
RTH_CLOSE = "16:00"


@dataclass(frozen=True)
class MimRegressionResult:
    """Outcome of one predictive regression (HAC OLS + correlation)."""

    label: str
    predictor: str
    n: int
    beta: float
    hac_se: float
    t_stat: float
    r_squared: float
    corr: float
    fisher_z: float
    nw_lags: int
    caveat: str = "research_diagnostic_not_trade_authorization"

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label, "predictor": self.predictor, "n": int(self.n),
            "beta": _f(self.beta), "hac_se": _f(self.hac_se), "t_stat": _f(self.t_stat),
            "r_squared": _f(self.r_squared), "corr": _f(self.corr),
            "fisher_z": _f(self.fisher_z), "nw_lags": int(self.nw_lags),
            "caveat": self.caveat,
        }


def build_mim_daily_frame(
    df: pd.DataFrame,
    *,
    timestamp_col: str = "timestamp",
    close_col: str = "close",
    timezone: str = "America/New_York",
) -> pd.DataFrame:
    """Build the one-row-per-trading-day MIM predictor/target frame (causal).

    Columns (date-indexed): ``prev_close``, ``p_1000``, ``p_1530``, ``p_1600``,
    ``r_ha`` (H_a predictor), ``r_hb`` (H_b predictor), ``target`` (last-30-min
    return), ``rod_rvol`` (rest-of-day realized vol 09:30->15:30, causal, for the
    high-volatility conditioning split). Days lacking any required price are dropped.
    """
    _require(df, [timestamp_col, close_col])
    local = _local(df[timestamp_col], timezone)
    date = pd.Series(local.dt.date, index=df.index)
    mod = pd.Series(local.dt.hour * 60 + local.dt.minute, index=df.index)
    in_rth = (mod >= _m(RTH_OPEN)) & (mod <= _m(RTH_CLOSE))
    close = df[close_col].where(in_rth)

    per_date_last = close.groupby(date).last()  # ~16:00 print
    prev_close = per_date_last.shift(1)
    p_1000 = _first_at_or_after(close, date, mod, _m(FIRST30_END))
    p_1530 = _first_at_or_after(close, date, mod, _m(LAST30_START))

    # Rest-of-day realized vol (09:30->15:30), causal — known at 15:30.
    pre_last30 = in_rth & (mod < _m(LAST30_START))
    one_min_ret = np.log(
        close.where(pre_last30).div(close.where(pre_last30).groupby(date).shift(1))
    )
    rod_rvol = np.sqrt((one_min_ret.pow(2)).groupby(date).sum())

    out = pd.DataFrame({
        "prev_close": prev_close,
        "p_1000": p_1000,
        "p_1530": p_1530,
        "p_1600": per_date_last,
        "rod_rvol": rod_rvol,
    })
    out["r_ha"] = np.log(out["p_1000"] / out["prev_close"])
    out["r_hb"] = np.log(out["p_1530"] / out["prev_close"])
    out["target"] = np.log(out["p_1600"] / out["p_1530"])
    return out.dropna(subset=["r_ha", "r_hb", "target"])


def newey_west_t(y: np.ndarray, x: np.ndarray, *, lags: int | None = None) -> dict[str, float]:
    """Bivariate OLS ``y = a + b·x`` with Newey-West (HAC) SE on the slope.

    Returns beta, hac_se, t_stat, r_squared, n, nw_lags. Pure numpy. Default lag
    truncation follows the standard rule ``floor(4*(n/100)^(2/9))``.
    """
    y = np.asarray(y, float); x = np.asarray(x, float)
    mask = np.isfinite(y) & np.isfinite(x)
    y, x = y[mask], x[mask]
    n = y.size
    if n < 10 or np.std(x) == 0:
        return {"beta": np.nan, "hac_se": np.nan, "t_stat": np.nan,
                "r_squared": np.nan, "n": n, "nw_lags": 0}
    X = np.column_stack([np.ones(n), x])
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ (X.T @ y)
    resid = y - X @ beta
    L = lags if lags is not None else int(np.floor(4 * (n / 100.0) ** (2.0 / 9.0)))
    # HAC meat: S = sum_t u_t^2 x_t x_t' + Bartlett-weighted lagged cross-products.
    u = resid[:, None] * X  # n x 2 score
    S = u.T @ u
    for l in range(1, L + 1):
        w = 1.0 - l / (L + 1.0)
        G = u[l:].T @ u[:-l]
        S += w * (G + G.T)
    cov = XtX_inv @ S @ XtX_inv
    se_b = float(np.sqrt(cov[1, 1]))
    yhat = X @ beta
    ss_res = float(np.sum((y - yhat) ** 2)); ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return {"beta": float(beta[1]), "hac_se": se_b,
            "t_stat": float(beta[1] / se_b) if se_b > 0 else np.nan,
            "r_squared": r2, "n": n, "nw_lags": L}


def run_mim_regression(
    frame: pd.DataFrame, *, predictor: str, label: str,
    target: str = "target", mask: pd.Series | None = None,
) -> MimRegressionResult:
    """Run one MIM predictive regression (optionally on a conditioning subsample)."""
    sub = frame if mask is None else frame[mask.reindex(frame.index, fill_value=False)]
    x = sub[predictor].to_numpy(); y = sub[target].to_numpy()
    ols = newey_west_t(y, x)
    fin = np.isfinite(x) & np.isfinite(y)
    r = float(np.corrcoef(x[fin], y[fin])[0, 1]) if fin.sum() > 2 and np.std(x[fin]) > 0 else np.nan
    z = float(np.arctanh(np.clip(r, -0.999999, 0.999999)) * np.sqrt(max(fin.sum() - 3, 1))) if np.isfinite(r) else np.nan
    return MimRegressionResult(
        label=label, predictor=predictor, n=ols["n"], beta=ols["beta"],
        hac_se=ols["hac_se"], t_stat=ols["t_stat"], r_squared=ols["r_squared"],
        corr=r, fisher_z=z, nw_lags=ols["nw_lags"],
    )


def high_volatility_mask(frame: pd.DataFrame, *, quantile: float = 2.0 / 3.0,
                         vol_col: str = "rod_rvol") -> pd.Series:
    """Pre-registered high-vol split: days above the given quantile of rest-of-day
    realized vol (causal — the vol is measured 09:30->15:30, known at 15:30)."""
    thresh = frame[vol_col].quantile(quantile)
    return frame[vol_col] > thresh


# --- negative controls (Step 3; all seeded) ---------------------------------

def negative_controls(frame: pd.DataFrame, *, predictor: str, target: str = "target",
                      seed: int = 0) -> dict[str, MimRegressionResult]:
    """Four seeded negative controls; each should show no meaningful effect.

    - ``date_shuffled``: predictor values shuffled across dates.
    - ``permuted_target``: target shuffled across dates.
    - ``randomized_timestamps``: predictor replaced by a random normal of equal scale.
    - ``lag_permuted``: predictor circularly shifted by a random lag (breaks alignment).
    """
    rng = np.random.default_rng(seed)
    f = frame.dropna(subset=[predictor, target]).copy()
    x = f[predictor].to_numpy(); y = f[target].to_numpy(); n = len(f)
    out: dict[str, MimRegressionResult] = {}

    def _res(name, xx, yy):
        g = pd.DataFrame({predictor: xx, target: yy})
        return run_mim_regression(g, predictor=predictor, label=f"control:{name}", target=target)

    out["date_shuffled"] = _res("date_shuffled", rng.permutation(x), y)
    out["permuted_target"] = _res("permuted_target", x, rng.permutation(y))
    out["randomized_timestamps"] = _res(
        "randomized_timestamps", rng.normal(x.mean(), x.std() if x.std() > 0 else 1.0, n), y)
    shift = int(rng.integers(1, max(2, n - 1)))
    out["lag_permuted"] = _res("lag_permuted", np.roll(x, shift), y)
    return out


# --- internals ---------------------------------------------------------------

def _first_at_or_after(close: pd.Series, date: pd.Series, mod: pd.Series, minute: int) -> pd.Series:
    at = close.where(mod >= minute)
    return at.groupby(date).first()


def _local(ts: pd.Series, tz: str) -> pd.Series:
    p = pd.to_datetime(ts)
    p = p.dt.tz_localize(tz) if p.dt.tz is None else p.dt.tz_convert(tz)
    return pd.Series(p, index=ts.index)


def _m(clock: str) -> int:
    h, m = clock.split(":"); return int(h) * 60 + int(m)


def _require(df: pd.DataFrame, cols: list[str]) -> None:
    miss = [c for c in cols if c not in df.columns]
    if miss:
        raise ValueError(f"Missing required columns: {miss}")


def _f(v: Any) -> float | None:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if np.isfinite(v) else None
