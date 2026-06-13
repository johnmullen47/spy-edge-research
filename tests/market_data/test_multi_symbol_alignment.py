import pandas as pd
import pytest

from spy_edge_research.market_data import (
    align_symbol_frames,
    build_multi_symbol_panel,
    filter_aligned_symbol_universe,
    prefix_symbol_columns,
    summarize_symbol_alignment,
    validate_symbol_frame_map,
)


def _frame(symbol, timestamps):
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(timestamps),
            "symbol": symbol,
            "close": range(100, 100 + len(timestamps)),
            "volume": range(1000, 1000 + len(timestamps)),
        }
    )


def test_validate_symbol_frame_map_normalizes_symbols_and_requires_keys():
    frames = validate_symbol_frame_map({"spy": _frame("SPY", ["2024-01-02 09:31"])})

    assert list(frames) == ["SPY"]

    with pytest.raises(ValueError, match="Missing required columns"):
        validate_symbol_frame_map({"SPY": pd.DataFrame({"close": [1]})})


def test_prefix_symbol_columns_keeps_keys_unprefixed():
    frame = prefix_symbol_columns(_frame("SPY", ["2024-01-02 09:31"]), "spy")

    assert list(frame.columns) == ["timestamp", "SPY_symbol", "SPY_close", "SPY_volume"]


def test_align_symbol_frames_supports_inner_and_outer_joins():
    spy = _frame("SPY", ["2024-01-02 09:31", "2024-01-02 09:32"])
    qqq = _frame("QQQ", ["2024-01-02 09:32", "2024-01-02 09:33"])

    inner = align_symbol_frames({"SPY": spy, "QQQ": qqq}, how="inner")
    outer = build_multi_symbol_panel({"SPY": spy, "QQQ": qqq}, how="outer")

    assert inner["timestamp"].tolist() == [pd.Timestamp("2024-01-02 09:32")]
    assert outer["timestamp"].tolist() == [
        pd.Timestamp("2024-01-02 09:31"),
        pd.Timestamp("2024-01-02 09:32"),
        pd.Timestamp("2024-01-02 09:33"),
    ]
    assert "SPY_close" in outer.columns
    assert "QQQ_close" in outer.columns


def test_forward_fill_is_explicit_and_caveated():
    spy = _frame("SPY", ["2024-01-02 09:31", "2024-01-02 09:32"])
    qqq = _frame("QQQ", ["2024-01-02 09:31"])

    panel = align_symbol_frames({"SPY": spy, "QQQ": qqq}, how="outer", fill_method="ffill")

    assert panel.loc[1, "QQQ_close"] == panel.loc[0, "QQQ_close"]
    assert panel.attrs["fill_caveat"] == "forward_fill_was_explicit_and_uses_prior_rows_only"


def test_summarize_alignment_and_filter_universe_surface_coverage():
    spy = _frame("SPY", ["2024-01-02 09:31", "2024-01-02 09:32", "2024-01-02 09:33"])
    qqq = _frame("QQQ", ["2024-01-02 09:31"])

    summary = summarize_symbol_alignment({"SPY": spy, "QQQ": qqq})
    filtered = filter_aligned_symbol_universe({"SPY": spy, "QQQ": qqq}, min_coverage_rate=0.75)

    assert summary.set_index("symbol").loc["QQQ", "panel_coverage_rate"] == pytest.approx(1 / 3)
    assert list(filtered) == ["SPY"]
