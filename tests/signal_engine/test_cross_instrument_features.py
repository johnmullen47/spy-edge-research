import pandas as pd
import pytest

from spy_edge_research.signal_engine import (
    add_cross_instrument_confirmation_features,
    add_cross_symbol_divergence_flags,
    add_cross_symbol_trend_confirmation,
    add_cross_symbol_volume_confirmation,
    add_cross_symbol_vwap_confirmation,
    add_relative_return_features,
)


def _panel():
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-02 09:31", periods=4, freq="min"),
            "SPY_close": [100, 101, 102, 101],
            "QQQ_close": [200, 202, 204, 203],
            "IWM_close": [50, 49, 48, 49],
            "SPY_vwap": [100, 100.5, 101, 101.5],
            "QQQ_vwap": [200, 201, 202, 202.5],
            "IWM_vwap": [50, 50, 49, 48.5],
            "SPY_volume": [100, 120, 160, 140],
            "QQQ_volume": [200, 220, 260, 280],
            "IWM_volume": [80, 70, 60, 120],
        }
    )


def test_relative_return_features_use_current_and_prior_prices():
    result = add_relative_return_features(_panel(), symbols=["SPY", "QQQ", "IWM"])

    assert result.loc[1, "SPY_return_1"] == pytest.approx(0.01)
    assert result.loc[1, "QQQ_relative_return_vs_SPY_1"] == pytest.approx(0.0)
    assert pd.isna(result.loc[0, "SPY_return_1"])


def test_trend_confirmation_and_divergence_flags_are_current_row_context():
    returns = add_relative_return_features(_panel(), symbols=["SPY", "QQQ", "IWM"])
    result = add_cross_symbol_trend_confirmation(
        returns,
        primary_symbol="SPY",
        confirmation_symbols=["QQQ", "IWM"],
    )

    assert result.loc[1, "QQQ_trend_confirms_SPY"] == 1
    assert result.loc[1, "IWM_trend_diverges_from_SPY"] == 1
    assert result.loc[1, "cross_trend_context"] == "confirmed"


def test_vwap_confirmation_requires_comparison_columns():
    result = add_cross_symbol_vwap_confirmation(
        _panel(),
        primary_symbol="SPY",
        confirmation_symbols=["QQQ", "IWM"],
    )

    assert result.loc[2, "QQQ_vwap_side_confirms_SPY"] == 1
    assert result.loc[2, "IWM_vwap_side_diverges_from_SPY"] == 1

    with pytest.raises(ValueError, match="Missing required columns"):
        add_cross_symbol_vwap_confirmation(
            _panel().drop(columns=["QQQ_vwap"]),
            primary_symbol="SPY",
            confirmation_symbols=["QQQ"],
        )


def test_volume_confirmation_uses_prior_trailing_baseline():
    result = add_cross_symbol_volume_confirmation(
        _panel(),
        primary_symbol="SPY",
        confirmation_symbols=["QQQ", "IWM"],
        baseline_window=2,
    )

    assert result.loc[0, "SPY_volume_expands_vs_trailing"] == 0
    assert result.loc[2, "QQQ_volume_expansion_matches_SPY"] == 1
    assert result.loc[2, "IWM_volume_expansion_matches_SPY"] == 0


def test_combined_helper_adds_research_context_without_trade_language():
    result = add_cross_instrument_confirmation_features(
        _panel(),
        primary_symbol="SPY",
        confirmation_symbols=["QQQ", "IWM"],
        volume_baseline_window=2,
    )
    divergence = add_cross_symbol_divergence_flags(
        add_relative_return_features(_panel(), symbols=["SPY", "QQQ", "IWM"]),
        primary_symbol="SPY",
        confirmation_symbols=["QQQ", "IWM"],
    )

    assert "cross_instrument_context_caveat" in result.columns
    assert result.loc[1, "cross_volume_confirming_count"] == 1
    assert divergence.loc[1, "cross_trend_divergent_count"] == 1
    forbidden_terms = ("buy", "sell", "entry", "exit", "approval")
    assert not any(term in column.lower() for column in result.columns for term in forbidden_terms)
