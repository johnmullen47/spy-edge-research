from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_candidate_edge_registry,
    create_candidate_edge,
    rank_candidate_edges,
    read_candidate_edge_registry,
    validate_candidate_edge,
    write_candidate_edge_registry,
)


def candidate_record(candidate_id: str = "event_vwap_reclaim_5m") -> dict[str, object]:
    return create_candidate_edge(
        candidate_id=candidate_id,
        candidate_type="event",
        name="event_vwap_reclaim_bullish",
        direction="long",
        horizon="5m",
        context={"session_bucket": "open", "volatility_context": "normal"},
        sample_size=42,
        baseline_sample_size=390,
        expectancy=0.0015,
        baseline_expectancy=0.0004,
        hit_rate=0.57,
        baseline_hit_rate=0.51,
        caveats=["research-only", "not statistically validated"],
        data_start="2024-01-02",
        data_end="2024-03-29",
        reproducibility_metadata={"run_id": "run_001", "data_hash": "abc123"},
    )


def test_create_candidate_edge_builds_required_record_with_differences() -> None:
    record = candidate_record()

    assert record["candidate_id"] == "event_vwap_reclaim_5m"
    assert record["candidate_type"] == "event"
    assert record["direction"] == "long"
    assert record["expectancy_difference"] == pytest.approx(0.0011)
    assert record["hit_rate_difference"] == pytest.approx(0.06)
    assert record["context"] == {"session_bucket": "open", "volatility_context": "normal"}
    assert record["caveats"] == ["research-only", "not statistically validated"]


def test_validate_candidate_edge_rejects_invalid_records() -> None:
    record = candidate_record()

    with pytest.raises(KeyError, match="required fields"):
        validate_candidate_edge({key: value for key, value in record.items() if key != "horizon"})

    invalid_type = record.copy()
    invalid_type["candidate_type"] = "strategy"
    with pytest.raises(ValueError, match="candidate_type"):
        validate_candidate_edge(invalid_type)

    invalid_direction = record.copy()
    invalid_direction["direction"] = "sideways"
    with pytest.raises(ValueError, match="direction"):
        validate_candidate_edge(invalid_direction)

    invalid_caveats = record.copy()
    invalid_caveats["caveats"] = "none"
    with pytest.raises(TypeError, match="caveats"):
        validate_candidate_edge(invalid_caveats)


def test_build_candidate_edge_registry_sorts_and_rejects_duplicate_ids() -> None:
    registry = build_candidate_edge_registry(
        [
            candidate_record("z_candidate"),
            candidate_record("a_candidate"),
        ]
    )

    assert registry["candidate_id"].tolist() == ["a_candidate", "z_candidate"]
    assert registry.columns.tolist()[0:4] == [
        "candidate_id",
        "candidate_type",
        "name",
        "direction",
    ]

    with pytest.raises(ValueError, match="duplicate"):
        build_candidate_edge_registry(
            [candidate_record("duplicate"), candidate_record("duplicate")]
        )


def test_rank_candidate_edges_sorts_for_research_review_and_filters_sample_size() -> None:
    strong = candidate_record("strong")
    weak = candidate_record("weak")
    weak["expectancy"] = 0.0002
    weak["expectancy_difference"] = -0.0002
    weak["sample_size"] = 8
    registry = build_candidate_edge_registry([weak, strong])

    ranked = rank_candidate_edges(registry, min_sample_size=10)

    assert ranked["candidate_id"].tolist() == ["strong"]
    assert ranked["research_rank"].tolist() == [1]

    ranked_all = rank_candidate_edges(registry)
    assert ranked_all["candidate_id"].tolist() == ["strong", "weak"]


def test_write_and_read_candidate_edge_registry_round_trips_json(tmp_path: Path) -> None:
    registry = build_candidate_edge_registry([candidate_record()])
    output_path = tmp_path / "candidate_edges.json"

    written = write_candidate_edge_registry(
        registry,
        output_path,
        metadata={"research_run_id": "run_001"},
    )
    payload = json.loads(output_path.read_text())
    loaded = read_candidate_edge_registry(output_path)

    assert written == output_path
    assert payload["metadata"] == {"research_run_id": "run_001"}
    assert payload["candidate_edges"][0]["candidate_id"] == "event_vwap_reclaim_5m"
    pd.testing.assert_frame_equal(loaded, registry)

    with pytest.raises(FileExistsError, match="already exists"):
        write_candidate_edge_registry(registry, output_path)


def test_read_candidate_edge_registry_validates_payload(tmp_path: Path) -> None:
    missing = tmp_path / "missing_candidate_edges.json"
    missing.write_text(json.dumps({"metadata": {}}), encoding="utf-8")

    with pytest.raises(KeyError, match="candidate_edges"):
        read_candidate_edge_registry(missing)


def test_candidate_registry_does_not_create_trading_readiness_columns() -> None:
    registry = build_candidate_edge_registry([candidate_record()])
    ranked = rank_candidate_edges(registry)

    forbidden = ("buy", "sell", "entry", "exit", "approved", "live", "trade_signal")
    assert not any(word in column for column in registry.columns for word in forbidden)
    assert not any(word in column for column in ranked.columns for word in forbidden)
