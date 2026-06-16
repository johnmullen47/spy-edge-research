"""M128 — cross-sectional intraday periodicity (Heston-Korajczyk-Sadka 2010, JF).

Implements the cross-sectional same-half-hour continuation test on a stock universe.
This is the engine behind the ``cross_sectional_scaffold.py`` stubs.

Design (frozen in docs/preregistration/M128_PREREG.yaml):

  * 13 RTH half-hour buckets per day (09:30->10:00 ... 15:30->16:00), clock-keyed.
    Bucket return r[i,d,b] = log(C_{d,b} / M_{d,b-1}) where the within-day mark path is
    [open of first bar, close of bucket 0, close of bucket 1, ...]; all intraday, no
    overnight (HKS construction).
  * Market neutralization = cross-sectional demean within each (date, bucket) over the
    universe members on that date (removes the common/market component, so we test
    RELATIVE same-bucket continuation, not market autocorrelation).
  * Fama-MacBeth: for each date d, pool the demeaned (stock, bucket) pairs and regress
    today's demeaned bucket return on the same stock's demeaned bucket return L trading
    days earlier, through the origin -> one slope gamma[d] per date.
  * Inference: time-series mean of gamma[d] with Newey-West(12) HAC SE -> t-stat.

Research-only; authorizes nothing. Pure numpy/pandas.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np
import pandas as pd

# 13 RTH half-hour bucket start times (ET). Bucket index = position in this list.
BUCKET_STARTS = [
    (9, 30), (10, 0), (10, 30), (11, 0), (11, 30), (12, 0), (12, 30),
    (13, 0), (13, 30), (14, 0), (14, 30), (15, 0), (15, 30),
]
N_BUCKETS = len(BUCKET_STARTS)
_START_TO_BUCKET = {hm: i for i, hm in enumerate(BUCKET_STARTS)}


def bucket_index(ts: pd.Timestamp) -> int | None:
    """Map a 30-min bar START timestamp (ET) to its bucket index, or None if off-grid."""
    return _START_TO_BUCKET.get((ts.hour, ts.minute))


def build_bucket_returns(
    bars_by_symbol: Mapping[str, pd.DataFrame],
    *,
    timezone: str = "America/New_York",
    timestamp_col: str = "timestamp",
    open_col: str = "open",
    close_col: str = "close",
) -> dict[int, pd.DataFrame]:
    """Per-stock same-clock-time intraday bucket returns aligned across days.

    Returns a dict ``{bucket_index -> DataFrame(index=date, columns=symbol, values=ret)}``
    of log half-hour returns. Causal: each value uses only same-day prices up to that
    bucket's close. Implements scaffold ``build_same_clock_time_returns``.
    """
    # Collect per (bucket) a dict of {symbol -> {date -> ret}}
    per_bucket: dict[int, dict[str, dict[pd.Timestamp, float]]] = {
        b: {} for b in range(N_BUCKETS)
    }
    for symbol, raw in bars_by_symbol.items():
        df = raw.copy()
        ts = pd.to_datetime(df[timestamp_col])
        if ts.dt.tz is None:
            ts = ts.dt.tz_localize(timezone)
        else:
            ts = ts.dt.tz_convert(timezone)
        df = df.assign(_ts=ts).sort_values("_ts")
        df["_date"] = df["_ts"].dt.normalize()
        df["_bucket"] = df["_ts"].apply(bucket_index)
        df = df[df["_bucket"].notna()]
        for date, day in df.groupby("_date"):
            day = day.sort_values("_bucket")
            buckets = day["_bucket"].astype(int).tolist()
            opens = day[open_col].astype(float).tolist()
            closes = day[close_col].astype(float).tolist()
            # Build the within-day mark path keyed by bucket; first present bar's open seeds it.
            prev_mark = opens[0]
            for b, o, c in zip(buckets, opens, closes):
                if prev_mark > 0 and c > 0:
                    ret = float(np.log(c / prev_mark))
                    per_bucket[b].setdefault(symbol, {})[date] = ret
                prev_mark = c
    frames: dict[int, pd.DataFrame] = {}
    for b in range(N_BUCKETS):
        frames[b] = pd.DataFrame(per_bucket[b]).sort_index()
    return frames


def market_neutralize(
    frame: pd.DataFrame,
    member_mask: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Cross-sectional demean per date over universe members (market neutralization).

    Masks non-members to NaN, then subtracts the cross-sectional mean across stocks for
    each date. Implements scaffold ``market_neutralize_returns``.
    """
    f = frame.copy()
    if member_mask is not None:
        aligned = member_mask.reindex(index=f.index, columns=f.columns, fill_value=False)
        f = f.where(aligned)
    return f.sub(f.mean(axis=1, skipna=True), axis=0)


@dataclass(frozen=True)
class FamaMacBethResult:
    label: str
    lag: int
    n_days: int                 # number of FM observations (dates with a valid slope)
    n_obs_total: int            # total (stock, bucket) pairs across all dates
    mean_slope: float
    hac_se: float
    t_stat: float
    mean_cs_corr: float         # mean per-date cross-sectional Pearson corr (effect size)
    nw_lags: int
    caveat: str = "research_diagnostic_not_trade_authorization"

    def as_dict(self) -> dict[str, Any]:
        def _f(x: float) -> float | None:
            return None if x is None or (isinstance(x, float) and np.isnan(x)) else float(x)

        return {
            "label": self.label, "lag": self.lag, "n_days": self.n_days,
            "n_obs_total": self.n_obs_total, "mean_slope": _f(self.mean_slope),
            "hac_se": _f(self.hac_se), "t_stat": _f(self.t_stat),
            "mean_cs_corr": _f(self.mean_cs_corr), "nw_lags": self.nw_lags,
            "caveat": self.caveat,
        }


def newey_west_mean(series: np.ndarray, *, lags: int = 12) -> dict[str, float]:
    """HAC (Newey-West, Bartlett) standard error of a sample mean.

    Tests H0: E[gamma]=0 against the time-series of daily FM slopes.
    """
    x = np.asarray(series, dtype=float)
    x = x[~np.isnan(x)]
    n = x.size
    if n < 3:
        return {"mean": float("nan"), "se": float("nan"), "t_stat": float("nan"), "n": n}
    mean = float(x.mean())
    e = x - mean
    gamma0 = float(np.dot(e, e) / n)
    lrv = gamma0
    max_lag = min(lags, n - 1)
    for l in range(1, max_lag + 1):
        w = 1.0 - l / (max_lag + 1)
        cov = float(np.dot(e[l:], e[:-l]) / n)
        lrv += 2.0 * w * cov
    lrv = max(lrv, 0.0)
    se = float(np.sqrt(lrv / n))
    t = mean / se if se > 0 else float("nan")
    return {"mean": mean, "se": se, "t_stat": t, "n": n}


def _slope_series_for_lag(
    neutralized: dict[int, pd.DataFrame],
    *,
    lag: int,
    pair_dates: Mapping[pd.Timestamp, pd.Timestamp] | None = None,
    stock_permute_rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list]:
    """Per-date pooled FM slope gamma[d], pooling all 13 buckets.

    For date d, predictor is the same stock's neutralized bucket return at the lagged date
    (d shifted back ``lag`` rows by default, or ``pair_dates[d]`` if given for controls).
    ``stock_permute_rng`` (control) permutes the predictor's stock labels within each
    (date, bucket).
    Returns (gamma_per_date, cs_corr_per_date, n_pairs_per_date, dates).
    """
    # Common date index across buckets (union); each bucket frame may differ slightly.
    all_dates = sorted(set().union(*[set(f.index) for f in neutralized.values()]))
    pos = {d: i for i, d in enumerate(all_dates)}
    gammas, corrs, npairs, out_dates = [], [], [], []

    for d in all_dates:
        if pair_dates is not None:
            d_lag = pair_dates.get(d)
            if d_lag is None:
                continue
        else:
            i = pos[d]
            if i - lag < 0:
                continue
            d_lag = all_dates[i - lag]
        xs, ys = [], []
        for b in range(N_BUCKETS):
            f = neutralized[b]
            if d not in f.index or d_lag not in f.index:
                continue
            y = f.loc[d]
            x = f.loc[d_lag]
            common = y.index.intersection(x.index)
            yv = y[common].to_numpy(dtype=float)
            xv = x[common].to_numpy(dtype=float)
            ok = ~(np.isnan(yv) | np.isnan(xv))
            yv, xv = yv[ok], xv[ok]
            if xv.size < 5:
                continue
            if stock_permute_rng is not None:
                xv = stock_permute_rng.permutation(xv)
            xs.append(xv)
            ys.append(yv)
        if not xs:
            continue
        X = np.concatenate(xs)
        Y = np.concatenate(ys)
        denom = float(np.dot(X, X))
        if denom <= 0 or X.size < 10:
            continue
        gamma = float(np.dot(X, Y) / denom)         # slope through origin (demeaned)
        sx, sy = X.std(), Y.std()
        corr = float(np.dot(X - X.mean(), Y - Y.mean()) / (X.size * sx * sy)) if sx > 0 and sy > 0 else np.nan
        gammas.append(gamma)
        corrs.append(corr)
        npairs.append(X.size)
        out_dates.append(d)
    return np.array(gammas), np.array(corrs), np.array(npairs), out_dates


def cross_sectional_continuation_test(
    bucket_returns: dict[int, pd.DataFrame],
    member_mask: pd.DataFrame | None,
    *,
    lag: int,
    label: str | None = None,
    nw_lags: int = 12,
) -> FamaMacBethResult:
    """Primary M128 confirmatory test. Implements scaffold ``cross_sectional_continuation_test``.

    Market-neutralizes each bucket frame, builds the per-date pooled FM slope series at the
    given lag, and applies NW(12) inference to its mean.
    """
    neutralized = {b: market_neutralize(f, member_mask) for b, f in bucket_returns.items()}
    gammas, corrs, npairs, dates = _slope_series_for_lag(neutralized, lag=lag)
    nw = newey_west_mean(gammas, lags=nw_lags)
    return FamaMacBethResult(
        label=label or f"H_cs L={lag}",
        lag=lag,
        n_days=int(nw["n"]),
        n_obs_total=int(npairs.sum()) if npairs.size else 0,
        mean_slope=nw["mean"],
        hac_se=nw["se"],
        t_stat=nw["t_stat"],
        mean_cs_corr=float(np.nanmean(corrs)) if corrs.size else float("nan"),
        nw_lags=min(nw_lags, max(int(nw["n"]) - 1, 0)),
    )


def negative_controls(
    bucket_returns: dict[int, pd.DataFrame],
    member_mask: pd.DataFrame | None,
    *,
    lag: int,
    seed: int = 42,
    nw_lags: int = 12,
    random_lag_choices: tuple[int, ...] = (3, 7, 9, 11, 13),
) -> dict[str, FamaMacBethResult]:
    """Three seeded cross-sectional negative controls (M128 Step 3).

    * date_shuffled: pair each date with a RANDOM other date's lagged cross-section
      (destroys the L-day time link; within-date cross-section preserved).
    * stock_permuted: permute predictor stock identities within each (date, bucket).
    * lag_permuted: use a random lag (not L) drawn from ``random_lag_choices``.
    """
    neutralized = {b: market_neutralize(f, member_mask) for b, f in bucket_returns.items()}
    all_dates = sorted(set().union(*[set(f.index) for f in neutralized.values()]))
    rng = np.random.default_rng(seed)
    out: dict[str, FamaMacBethResult] = {}

    # date_shuffled: random predictor date per target date (excluding itself)
    shuffled_src = list(all_dates)
    perm = rng.permutation(len(shuffled_src))
    pair_dates = {all_dates[i]: all_dates[perm[i]] for i in range(len(all_dates))
                  if all_dates[perm[i]] != all_dates[i]}
    g, c, n, _ = _slope_series_for_lag(neutralized, lag=lag, pair_dates=pair_dates)
    nw = newey_west_mean(g, lags=nw_lags)
    out["date_shuffled"] = FamaMacBethResult(
        "control:date_shuffled", lag, int(nw["n"]), int(n.sum()) if n.size else 0,
        nw["mean"], nw["se"], nw["t_stat"], float(np.nanmean(c)) if c.size else float("nan"),
        min(nw_lags, max(int(nw["n"]) - 1, 0)),
    )

    # stock_permuted
    rng2 = np.random.default_rng(seed + 1)
    g, c, n, _ = _slope_series_for_lag(neutralized, lag=lag, stock_permute_rng=rng2)
    nw = newey_west_mean(g, lags=nw_lags)
    out["stock_permuted"] = FamaMacBethResult(
        "control:stock_permuted", lag, int(nw["n"]), int(n.sum()) if n.size else 0,
        nw["mean"], nw["se"], nw["t_stat"], float(np.nanmean(c)) if c.size else float("nan"),
        min(nw_lags, max(int(nw["n"]) - 1, 0)),
    )

    # lag_permuted: pick a random alternative lag != L
    choices = [l for l in random_lag_choices if l != lag] or [lag + 2]
    rlag = int(rng.choice(choices))
    g, c, n, _ = _slope_series_for_lag(neutralized, lag=rlag)
    nw = newey_west_mean(g, lags=nw_lags)
    out["lag_permuted"] = FamaMacBethResult(
        f"control:lag_permuted(L={rlag})", rlag, int(nw["n"]), int(n.sum()) if n.size else 0,
        nw["mean"], nw["se"], nw["t_stat"], float(np.nanmean(c)) if c.size else float("nan"),
        min(nw_lags, max(int(nw["n"]) - 1, 0)),
    )
    return out


def decile_long_short_bucket_returns(
    bucket_returns: dict[int, pd.DataFrame],
    member_mask: pd.DataFrame | None,
    *,
    lag: int,
    decile: float = 0.1,
) -> pd.Series:
    """Gross per-(date,bucket) return of a top-decile-long / bottom-decile-short book,
    sorted on the lagged same-bucket neutralized return. For the economic-significance
    layer (Step 4). Returns a Series indexed by (date, bucket). Gross of costs.
    """
    neutralized = {b: market_neutralize(f, member_mask) for b, f in bucket_returns.items()}
    out = {}
    for b in range(N_BUCKETS):
        f = neutralized[b]
        raw = bucket_returns[b]
        dates = list(f.index)
        pos = {d: i for i, d in enumerate(dates)}
        for d in dates:
            i = pos[d]
            if i - lag < 0:
                continue
            d_lag = dates[i - lag]
            signal = f.loc[d_lag]
            fwd = raw.loc[d] if d in raw.index else None
            if fwd is None:
                continue
            common = signal.dropna().index.intersection(fwd.dropna().index)
            if len(common) < 20:
                continue
            s = signal[common]
            r = fwd[common].astype(float)
            k = max(int(len(common) * decile), 1)
            ranked = s.sort_values()
            shorts = ranked.index[:k]
            longs = ranked.index[-k:]
            ls = r[longs].mean() - r[shorts].mean()   # continuation: long high-signal
            out[(d, b)] = float(ls)
    return pd.Series(out, name="ls_gross")
