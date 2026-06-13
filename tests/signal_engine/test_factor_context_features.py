import pandas as pd
import pytest

from spy_edge_research.signal_engine import (
    add_factor_context_features,
    add_factor_dispersion_features,
    add_factor_leadership_flags,
    add_factor_relative_return_features,
)


def _panel():
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-02 09:31", periods=5, freq="min"),
            "SPY_close": [100, 101, 100, 102, 103],
            "MTUM_close": [50, 51, 52, 53, 54],
            "VLUE_close": [40, 39, 38, 39, 40],
            "USMV_close": [30, 30.3, 30.6, 30.3, 30.0],
        }
    )


def _with_returns():
    return add_factor_relative_return_features(
        _panel(),
        primary_symbol="SPY",
        factor_symbols=["MTUM", "VLUE", "USMV"],
    )


def test_factor_relative_returns_use_current_and_prior_prices():
    result = _with_returns()
    assert result.loc[1, "SPY_return_1"] == pytest.approx(0.01)
    assert result.loc[1, "MTUM_return_1"] == pytest.approx(0.02)
    assert result.loc[1, "MTUM_relative_return_vs_SPY_1"] == pytest.approx(0.01)
    assert pd.isna(result.loc[0, "SPY_return_1"])


def test_factor_leadership_flags_are_descriptive_style_context():
    result = add_factor_leadership_flags(
        _with_returns(),
        factor_symbols=["MTUM", "VLUE", "USMV"],
        factor_styles={"MTUM": "momentum", "VLUE": "value", "USMV": "low_volatility"},
    )
    assert result.loc[1, "factor_leadership_symbol"] == "MTUM"
    assert result.loc[1, "factor_laggard_symbol"] == "VLUE"
    assert result.loc[1, "factor_leadership_style"] == "momentum"
    assert "factor_style_low_volatility_mean_return" in result.columns


def test_factor_dispersion_uses_current_returns_and_trailing_threshold():
    result = add_factor_dispersion_features(
        _with_returns(),
        factor_symbols=["MTUM", "VLUE", "USMV"],
        high_dispersion_quantile_window=3,
        high_dispersion_min_periods=2,
    )
    assert result.loc[1, "factor_dispersion_return_range"] > 0
    assert result["factor_high_dispersion_context"].isin([0, 1]).all()


def test_combined_factor_context_helper_validates_columns_and_avoids_trade_language():
    result = add_factor_context_features(
        _panel(),
        primary_symbol="SPY",
        factor_symbols=["MTUM", "VLUE", "USMV"],
        factor_styles={"MTUM": "momentum", "VLUE": "value", "USMV": "low_volatility"},
        dispersion_window=3,
        dispersion_min_periods=2,
    )
    assert result.loc[1, "factor_context_caveat"] == (
        "causal_factor_context_research_only_not_allocation_or_execution"
    )
    forbidden_terms = ("buy", "sell", "entry", "exit", "signal", "approval", "allocation")
    assert not any(term in column.lower() for column in result.columns for term in forbidden_terms)

    with pytest.raises(ValueError, match="Missing required columns"):
        add_factor_context_features(
            _panel().drop(columns=["MTUM_close"]),
            primary_symbol="SPY",
            factor_symbols=["MTUM", "VLUE"],
        )
