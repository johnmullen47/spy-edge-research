"""M128 scaffold — intraday cross-sectional continuation/reversal (NOT YET RUN).

SCAFFOLD ONLY. No experiments, no exploratory scans, no alpha search. This module
defines interfaces and TODOs for a *future* M128 study and deliberately raises
``NotImplementedError`` everywhere. It exists so the M128 design is reviewable and so
the data/controls requirements are pinned down before any cross-sectional run.

Motivation (RESEARCH_I bucket 3 / Heston-Korajczyk-Sadka 2010): intraday periodicity
and same-clock-time continuation are **cross-sectional** effects (across many stocks),
which a single instrument (M127's SPY) cannot capture. M128 would test them on a
**stock universe first**, with ETFs as negative controls.

Hard requirements pinned for M128 (do not start without these):
  * Stock universe with point-in-time membership (NO survivorship bias).
  * Liquidity screen (ADV / price floor) applied point-in-time.
  * Beta / market-factor control (cross-sectional returns must be market-neutralized
    before testing same-clock-time continuation, else it is just market autocorrelation).
  * ETFs (SPY/QQQ/...) as NEGATIVE controls: a cross-sectional effect should be weak/absent
    on a single diversified ETF (this is the M127 finding, reused as a control anchor).
  * Same preregistration / power / fidelity / freeze discipline as M127 (Gate 0.5 first).

Research-only; authorizes nothing.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CrossSectionalConfig:
    """Frozen-design placeholder for an M128 cross-sectional study (TODO: fill at M128)."""

    bucket_minutes: int = 30          # same-clock-time bucket width (HKS half-hours)
    universe: str = "stocks"          # stock universe FIRST; ETFs are controls
    require_point_in_time_membership: bool = True   # survivorship guard
    liquidity_min_adv_usd: float = 0.0              # TODO: set point-in-time liquidity floor
    market_neutralize: bool = True                  # beta control before continuation test


# M128 IMPLEMENTED (milestone/M128). The interfaces below now delegate to the engine in
# ``cross_sectional.py``. Implementation followed Gate 0.5 (data inventory, power report),
# preregistration freeze (docs/preregistration/M128_PREREG.yaml), and a fidelity report —
# all committed BEFORE any cross-sectional result was computed (execution-freeze honored).


def build_same_clock_time_returns(*args, **kwargs):  # noqa: D401, ANN
    """Per-stock, per-clock-bucket returns aligned across days. Causal.

    Delegates to :func:`cross_sectional.build_bucket_returns`.
    """
    from .cross_sectional import build_bucket_returns

    return build_bucket_returns(*args, **kwargs)


def market_neutralize_returns(*args, **kwargs):  # noqa: ANN
    """Remove the market component cross-sectionally before testing (demean per date-bucket).

    Delegates to :func:`cross_sectional.market_neutralize`.
    """
    from .cross_sectional import market_neutralize

    return market_neutralize(*args, **kwargs)


def cross_sectional_continuation_test(*args, **kwargs):  # noqa: ANN
    """Same-clock-bucket continuation across the stock cross-section (Fama-MacBeth + NW12).

    Delegates to :func:`cross_sectional.cross_sectional_continuation_test`. ETFs are run
    separately as negative controls; full harness (prereg/power/fidelity) per M127.
    """
    from .cross_sectional import cross_sectional_continuation_test as _impl

    return _impl(*args, **kwargs)
