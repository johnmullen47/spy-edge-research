from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.risk import compute_event_mask_overlap, summarize_signal_overlap


def test_overlap_pairwise_metrics() -> None:
    df = pd.DataFrame(
        {
            "sig_a": [True, True, False, False],
            "sig_b": [True, False, True, False],
            "sig_c": [True, True, False, False],
        }
    )
    table = compute_event_mask_overlap(df, ["sig_a", "sig_b", "sig_c"])
    assert len(table) == 3

    ab = table[(table.left_signal == "sig_a") & (table.right_signal == "sig_b")].iloc[0]
    assert ab["both_count"] == 1
    assert ab["either_count"] == 3
    assert ab["jaccard"] == pytest.approx(1 / 3)

    ac = table[(table.left_signal == "sig_a") & (table.right_signal == "sig_c")].iloc[0]
    assert ac["both_count"] == 2
    assert ac["jaccard"] == pytest.approx(1.0)
    assert ac["correlation"] == pytest.approx(1.0)


def test_overlap_requires_two_columns() -> None:
    with pytest.raises(ValueError, match="at least two"):
        compute_event_mask_overlap(pd.DataFrame({"x": [True]}), ["x"])


def test_summarize_signal_overlap_counts_redundant_pairs() -> None:
    df = pd.DataFrame(
        {
            "a": [True, True, False],
            "b": [True, True, False],
            "c": [False, False, True],
        }
    )
    table = compute_event_mask_overlap(df, ["a", "b", "c"])
    summary = summarize_signal_overlap(table, jaccard_threshold=0.9).iloc[0]
    assert summary["pair_count"] == 3
    assert summary["max_jaccard"] == pytest.approx(1.0)
    assert summary["redundant_pair_count"] == 1


def test_summarize_signal_overlap_rejects_bad_threshold() -> None:
    df = pd.DataFrame({"a": [True, False], "b": [False, True]})
    table = compute_event_mask_overlap(df, ["a", "b"])
    with pytest.raises(ValueError, match="between 0 and 1"):
        summarize_signal_overlap(table, jaccard_threshold=1.5)
