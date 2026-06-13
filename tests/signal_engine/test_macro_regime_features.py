import pandas as pd
import pytest

from spy_edge_research.signal_engine import (
    add_commodity_regime_features,
    add_credit_regime_features,
    add_macro_regime_features,
    add_macro_relative_return_features,
    add_rates_regime_features,
    add_risk_on_risk_off_features,
    add_volatility_proxy_regime_features,
)


def _panel():
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-02 09:31", periods=5, freq="min"),
            "SPY_close": [100, 101, 100, 99, 100],
            "TLT_close": [90, 89, 90, 91, 90],
            "IEF_close": [95, 94.5, 95, 95.5, 95],
            "HYG_close": [80, 80.8, 80.0, 79.0, 79.8],
            "LQD_close": [100, 100.2, 100.1, 100.3, 100.4],
            "GLD_close": [180, 181, 182, 181, 183],
            "USO_close": [70, 71, 70.5, 70.0, 72.0],
            "UUP_close": [25, 25.1, 25.0, 25.2, 25.1],
            "VIXY_close": [20, 19, 20.5, 21.5, 20.0],
            "VXX_close": [30, 29, 31, 32, 30],
        }
    )


def _with_returns():
    return add_macro_relative_return_features(
        _panel(),
        primary_symbol="SPY",
        macro_symbols=["TLT", "IEF", "HYG", "LQD", "GLD", "USO", "UUP", "VIXY", "VXX"],
    )


def test_macro_relative_returns_use_current_and_prior_prices():
    result = _with_returns()

    assert result.loc[1, "SPY_return_1"] == pytest.approx(0.01)
    assert result.loc[1, "TLT_return_1"] == pytest.approx(-1 / 90)
    assert result.loc[1, "TLT_relative_return_vs_SPY_1"] == pytest.approx((-1 / 90) - 0.01)
    assert pd.isna(result.loc[0, "SPY_return_1"])


def test_rates_regime_describes_duration_proxy_context():
    result = add_rates_regime_features(_with_returns(), duration_symbols=["TLT", "IEF"])

    assert result.loc[1, "macro_rates_context"] == "rates_up"
    assert result.loc[2, "macro_rates_context"] == "rates_down"


def test_credit_commodity_and_volatility_contexts_are_descriptive():
    result = add_credit_regime_features(_with_returns())
    result = add_commodity_regime_features(result, commodity_symbols=["GLD", "USO"])
    result = add_volatility_proxy_regime_features(result, volatility_symbols=["VIXY", "VXX"])

    assert result.loc[1, "macro_credit_context"] == "credit_risk_on"
    assert result.loc[3, "macro_credit_context"] == "credit_risk_off"
    assert result.loc[1, "macro_commodity_context"] == "commodity_up"
    assert result.loc[1, "macro_volatility_proxy_context"] == "volatility_proxy_down"
    assert result.loc[3, "macro_volatility_proxy_context"] == "volatility_proxy_up"


def test_risk_on_risk_off_context_uses_existing_macro_context_columns():
    result = _with_returns()
    result["macro_credit_context"] = [
        "credit_mixed",
        "credit_risk_on",
        "credit_mixed",
        "credit_risk_off",
        "credit_risk_on",
    ]
    result["macro_volatility_proxy_context"] = [
        "volatility_proxy_mixed",
        "volatility_proxy_down",
        "volatility_proxy_mixed",
        "volatility_proxy_up",
        "volatility_proxy_down",
    ]

    result = add_risk_on_risk_off_features(result)

    assert result.loc[1, "macro_risk_context"] == "risk_on"
    assert result.loc[3, "macro_risk_context"] == "risk_off"
    assert result.loc[2, "macro_risk_context"] == "risk_mixed"


def test_combined_macro_regime_helper_validates_columns_and_avoids_trade_language():
    result = add_macro_regime_features(_panel())

    assert result.loc[1, "macro_regime_context_caveat"] == (
        "causal_macro_regime_context_research_only_not_allocation_or_execution"
    )
    assert set(result["macro_risk_context"].dropna()).issubset({"risk_on", "risk_off", "risk_mixed"})
    forbidden_terms = ("buy", "sell", "entry", "exit", "signal", "approval")
    assert not any(term in column.lower() for column in result.columns for term in forbidden_terms)

    with pytest.raises(ValueError, match="Missing required columns"):
        add_macro_regime_features(_panel().drop(columns=["HYG_close"]))


def test_macro_symbol_configuration_rejects_duplicates():
    with pytest.raises(ValueError, match="duplicate symbols"):
        add_macro_relative_return_features(
            _panel(),
            primary_symbol="SPY",
            macro_symbols=["TLT", "tlt"],
        )
