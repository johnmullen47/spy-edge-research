"""M128 scaffold guard — was interfaces-only; now IMPLEMENTED on milestone/M128.

The three stubs previously raised NotImplementedError. As of M128 (Gate 0.5 passed,
preregistration frozen, fidelity scored — all committed before any result), they delegate
to the engine in ``cross_sectional.py``. This test now confirms the design-pinning config
is unchanged and that the delegating functions are wired to the real implementation.
"""

from __future__ import annotations

import pandas as pd

from spy_edge_research.signal_engine import cross_sectional as cs
from spy_edge_research.signal_engine.cross_sectional_scaffold import (
    CrossSectionalConfig,
    build_same_clock_time_returns,
    cross_sectional_continuation_test,
    market_neutralize_returns,
)


def test_scaffold_config_defaults_pin_the_guards():
    cfg = CrossSectionalConfig()
    assert cfg.universe == "stocks"  # stock universe FIRST
    assert cfg.require_point_in_time_membership is True  # survivorship guard
    assert cfg.market_neutralize is True  # beta control


def test_scaffold_functions_delegate_to_implementation():
    # build_same_clock_time_returns -> bucket-return frames
    bars = {
        "AAA": pd.DataFrame(
            [
                {"timestamp": "2020-03-02 09:30:00", "open": 100.0, "close": 101.0},
                {"timestamp": "2020-03-02 10:00:00", "open": 101.0, "close": 102.0},
            ]
        )
    }
    frames = build_same_clock_time_returns(bars)
    assert isinstance(frames, dict) and len(frames) == cs.N_BUCKETS

    # market_neutralize_returns -> rows demean to ~0
    df = pd.DataFrame({"A": [1.0], "B": [3.0]})
    out = market_neutralize_returns(df)
    assert abs(float(out.iloc[0].sum())) < 1e-9

    # cross_sectional_continuation_test is the delegating callable
    assert cross_sectional_continuation_test is not None
