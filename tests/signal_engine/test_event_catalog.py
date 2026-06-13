from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.signal_engine import (
    add_event_hypothesis_columns,
    build_named_event_catalog,
    filter_directional_event_catalog,
    infer_named_event_direction,
    infer_named_event_family,
    validate_event_catalog,
)


def test_direction_inference_is_deterministic() -> None:
    cases = {
        "event_vwap_reclaim_bullish": "long",
        "event_trailing_breakout_20": "long",
        "event_structure_higher_low": "long",
        "event_trend_continuation_up_context": "long",
        "event_vwap_rejection_bearish": "short",
        "event_trailing_breakdown_20": "short",
        "event_structure_lower_high": "short",
        "event_false_break_up": "short",
        "event_structure_context_range_or_unknown": "neutral",
        "event_high_volatility_regime": "neutral",
        "event_any_support_retest_touch": "neutral",
        "event_unrecognized_pattern": "unknown",
    }

    for event_name, expected in cases.items():
        assert infer_named_event_direction(event_name) == expected
        assert infer_named_event_direction(event_name) == expected

    with pytest.raises(ValueError, match="event_name"):
        infer_named_event_direction("")


def test_family_inference_is_deterministic() -> None:
    cases = {
        "event_vwap_reclaim_bullish": "vwap",
        "event_ema_reclaim_bullish": "ema",
        "event_prior_day_high_break_above": "zone",
        "event_bullish_structure_break": "structure",
        "event_breakout_retest_hold_20": "retest",
        "event_failed_breakout_20": "false_break",
        "event_volume_confirmed_momentum_up_3_20": "momentum_volume",
        "event_trend_continuation_down_context": "trend_continuation",
        "event_directional_regime_bullish": "regime",
        "event_unknown_ambiguous": "unknown",
    }

    for event_name, expected in cases.items():
        assert infer_named_event_family(event_name) == expected
        assert infer_named_event_family(event_name) == expected


def test_build_catalog_from_explicit_event_columns() -> None:
    catalog = build_named_event_catalog(
        event_columns=[
            "event_vwap_reclaim_bullish",
            "event_vwap_loss_bearish",
            "event_any_support_retest_touch",
            "forward_return_5m",
        ]
    )

    assert catalog["event_column"].tolist() == [
        "event_vwap_reclaim_bullish",
        "event_vwap_loss_bearish",
        "event_any_support_retest_touch",
    ]
    assert catalog["event_name"].tolist() == catalog["event_column"].tolist()
    assert catalog["event_family"].tolist() == ["vwap", "vwap", "retest"]
    assert catalog["event_direction"].tolist() == ["long", "short", "neutral"]
    assert catalog["is_directional"].tolist() == [True, True, False]


def test_build_catalog_from_dataframe_excludes_non_event_and_forward_columns() -> None:
    df = pd.DataFrame(
        {
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000],
            "event_vwap_reclaim_bullish": [True],
            "event_failed_breakout_20": [False],
            "event_forward_label_leak": [True],
            "event_profit_outcome": [0.1],
            "forward_return_5m": [0.01],
            "target_direction": [1],
        }
    )
    original = df.copy(deep=True)

    catalog = build_named_event_catalog(df=df)

    assert catalog["event_column"].tolist() == [
        "event_vwap_reclaim_bullish",
        "event_failed_breakout_20",
    ]
    assert catalog["is_directional"].tolist() == [True, True]
    pd.testing.assert_frame_equal(df, original)


def test_validate_event_catalog_raises_on_invalid_catalogs() -> None:
    catalog = build_named_event_catalog(
        event_columns=["event_vwap_reclaim_bullish", "event_range_bound_regime"]
    )

    pd.testing.assert_frame_equal(validate_event_catalog(catalog), catalog)

    with pytest.raises(ValueError, match="Missing required columns"):
        validate_event_catalog(catalog.drop(columns=["event_direction"]))

    invalid_direction = catalog.copy()
    invalid_direction.loc[0, "event_direction"] = "sideways"
    with pytest.raises(ValueError, match="event_direction"):
        validate_event_catalog(invalid_direction)

    invalid_flag = catalog.copy()
    invalid_flag.loc[0, "is_directional"] = False
    with pytest.raises(ValueError, match="is_directional"):
        validate_event_catalog(invalid_flag)

    neutral_only = catalog.loc[catalog["event_direction"] == "neutral"].copy()
    with pytest.raises(ValueError, match="directional"):
        validate_event_catalog(neutral_only, require_directional=True)


def test_filter_directional_event_catalog_supports_direction_selection() -> None:
    catalog = build_named_event_catalog(
        event_columns=[
            "event_vwap_reclaim_bullish",
            "event_vwap_loss_bearish",
            "event_any_support_retest_touch",
        ]
    )

    assert filter_directional_event_catalog(catalog)["event_column"].tolist() == [
        "event_vwap_reclaim_bullish",
        "event_vwap_loss_bearish",
    ]
    assert filter_directional_event_catalog(catalog, directions=("short",))[
        "event_column"
    ].tolist() == ["event_vwap_loss_bearish"]

    with pytest.raises(ValueError, match="directions"):
        filter_directional_event_catalog(catalog, directions=("neutral",))


def test_add_event_hypothesis_columns_adds_metadata_helpers_without_mutation() -> None:
    df = pd.DataFrame(
        {
            "event_vwap_reclaim_bullish": [False, True, True],
            "event_vwap_loss_bearish": [False, True, False],
            "event_any_support_retest_touch": [True, False, False],
        },
        index=pd.Index(["a", "b", "c"], name="row"),
    )
    catalog = build_named_event_catalog(df=df)
    original = df.copy(deep=True)

    result = add_event_hypothesis_columns(df, catalog)

    assert result["event_hypothesis_vwap_reclaim_bullish"].tolist() == [
        "neutral",
        "long",
        "long",
    ]
    assert result["event_hypothesis_vwap_loss_bearish"].tolist() == [
        "neutral",
        "short",
        "neutral",
    ]
    assert "event_hypothesis_any_support_retest_touch" not in result.columns
    assert result.index.equals(df.index)
    assert len(result) == len(df)
    assert not any(
        word in column
        for column in result.columns
        for word in ("buy", "sell", "entry", "exit", "confidence")
    )
    pd.testing.assert_frame_equal(df, original)

    with pytest.raises(ValueError, match="Missing required columns"):
        add_event_hypothesis_columns(
            df.drop(columns=["event_vwap_loss_bearish"]),
            catalog,
        )
