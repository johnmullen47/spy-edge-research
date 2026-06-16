"""M128 scaffold guard — confirms the scaffold is interfaces-only and cannot be run."""

from __future__ import annotations

import pytest

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


@pytest.mark.parametrize("fn", [build_same_clock_time_returns, market_neutralize_returns,
                                cross_sectional_continuation_test])
def test_scaffold_functions_are_not_implemented(fn):
    # Scaffold must not silently run any cross-sectional experiment.
    with pytest.raises(NotImplementedError):
        fn()
