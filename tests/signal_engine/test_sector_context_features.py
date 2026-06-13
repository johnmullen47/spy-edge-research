import pandas as pd
import pytest

from spy_edge_research.signal_engine import (
    add_primary_sector_confirmation_features,
    add_sector_breadth_features,
    add_sector_context_features,
    add_sector_dispersion_features,
    add_sector_leadership_flags,
    add_sector_relative_return_features,
)


def _panel():
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-02 09:31", periods=5, freq="min"),
            "SPY_close": [100, 101, 100, 102, 103],
            "XLK_close": [50, 51, 52, 53, 54],
            "XLF_close": [40, 39, 38, 39, 40],
            "XLU_close": [30, 30.3, 30.6, 30.3, 30.0],
        }
    )


def _with_returns():
    return add_sector_relative_return_features(
        _panel(),
        primary_symbol="SPY",
        sector_symbols=["XLK", "XLF", "XLU"],
    )


def test_sector_relative_returns_use_current_and_prior_prices():
    result = _with_returns()

    assert result.loc[1, "SPY_return_1"] == pytest.approx(0.01)
    assert result.loc[1, "XLK_return_1"] == pytest.approx(0.02)
    assert result.loc[1, "XLK_relative_return_vs_SPY_1"] == pytest.approx(0.01)
    assert pd.isna(result.loc[0, "SPY_return_1"])


def test_sector_breadth_counts_positive_and_above_benchmark_context():
    result = add_sector_breadth_features(
        _with_returns(),
        sector_symbols=["XLK", "XLF", "XLU"],
        benchmark_symbol="SPY",
    )

    assert result.loc[1, "sector_breadth_positive_count"] == 2
    assert result.loc[1, "sector_breadth_fraction_positive"] == pytest.approx(2 / 3)
    assert result.loc[1, "sector_breadth_above_SPY_count"] == 1


def test_sector_leadership_flags_are_descriptive_group_context():
    result = add_sector_leadership_flags(
        _with_returns(),
        sector_symbols=["XLK", "XLF", "XLU"],
        sector_groups={"XLK": "cyclical", "XLF": "cyclical", "XLU": "defensive"},
    )

    assert result.loc[1, "sector_leadership_symbol"] == "XLK"
    assert result.loc[1, "sector_laggard_symbol"] == "XLF"
    assert result.loc[1, "sector_leadership_group"] == "cyclical"
    assert "sector_group_defensive_mean_return" in result.columns


def test_sector_dispersion_uses_current_sector_returns_and_trailing_threshold():
    result = add_sector_dispersion_features(
        _with_returns(),
        sector_symbols=["XLK", "XLF", "XLU"],
        high_dispersion_quantile_window=3,
        high_dispersion_min_periods=2,
    )

    assert result.loc[1, "sector_dispersion_return_range"] > 0
    assert result["sector_high_dispersion_context"].isin([0, 1]).all()


def test_primary_sector_confirmation_flags_describe_context():
    result = add_primary_sector_confirmation_features(
        _with_returns(),
        primary_symbol="SPY",
        sector_symbols=["XLK", "XLF", "XLU"],
    )

    assert result.loc[1, "XLK_sector_confirms_SPY"] == 1
    assert result.loc[1, "XLF_sector_diverges_from_SPY"] == 1
    assert result.loc[1, "primary_sector_context"] == "sector_confirmed"


def test_combined_sector_context_helper_validates_columns_and_avoids_trade_language():
    result = add_sector_context_features(
        _panel(),
        primary_symbol="SPY",
        sector_symbols=["XLK", "XLF", "XLU"],
        sector_groups={"XLK": "cyclical", "XLF": "cyclical", "XLU": "defensive"},
        dispersion_window=3,
        dispersion_min_periods=2,
    )

    assert result.loc[1, "sector_context_caveat"] == (
        "causal_sector_context_research_only_not_allocation_or_execution"
    )
    forbidden_terms = ("buy", "sell", "entry", "exit", "signal", "approval")
    assert not any(term in column.lower() for column in result.columns for term in forbidden_terms)

    with pytest.raises(ValueError, match="Missing required columns"):
        add_sector_context_features(
            _panel().drop(columns=["XLK_close"]),
            primary_symbol="SPY",
            sector_symbols=["XLK", "XLF"],
        )
