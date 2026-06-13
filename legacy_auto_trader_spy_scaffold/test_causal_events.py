import pandas as pd

from causal_events import (
    EventDefinition,
    build_chart_annotations,
    build_event_catalog,
    build_event_tape,
    wide_features_to_chart_annotations,
)


def test_pipeline_builds_catalog_tape_and_annotations_from_wide_features():
    features = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2026-06-10 09:30", "2026-06-10 09:31", "2026-06-10 09:32"]
            ),
            "spy_gap_up": [1, 0, 0],
            "vix_spike": [0.2, 1.7, 2.4],
        }
    )
    definitions = [
        EventDefinition(
            feature="spy_gap_up",
            name="gap_up",
            label="Gap up",
            color="#16a34a",
            marker="triangle-up",
        ),
        EventDefinition(
            feature="vix_spike",
            name="vix_spike",
            label="VIX spike",
            color="#dc2626",
            marker="circle",
            threshold=1.5,
            direction="above",
        ),
    ]

    catalog, tape, annotations = wide_features_to_chart_annotations(
        features,
        definitions,
        timestamp_column="timestamp",
    )

    assert catalog["event_name"].tolist() == ["gap_up", "vix_spike"]
    assert tape[["event_name", "value"]].to_dict("records") == [
        {"event_name": "gap_up", "value": 1.0},
        {"event_name": "vix_spike", "value": 1.7},
        {"event_name": "vix_spike", "value": 2.4},
    ]
    assert annotations[["id", "text", "marker"]].to_dict("records") == [
        {"id": "gap_up", "text": "Gap up", "marker": "triangle-up"},
        {"id": "vix_spike", "text": "VIX spike", "marker": "circle"},
        {"id": "vix_spike", "text": "VIX spike", "marker": "circle"},
    ]


def test_build_event_tape_uses_index_as_timestamp_by_default():
    features = pd.DataFrame({"feature_a": [0, 1]}, index=pd.to_datetime(["2026-01-01", "2026-01-02"]))
    catalog = build_event_catalog([EventDefinition(feature="feature_a", name="feature_a")])

    tape = build_event_tape(features, catalog)

    assert tape[["timestamp", "event_name", "value"]].to_dict("records") == [
        {
            "timestamp": pd.Timestamp("2026-01-02"),
            "event_name": "feature_a",
            "value": 1,
        }
    ]


def test_build_chart_annotations_can_attach_price_y_values():
    tape = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-01-01", "2026-01-02"]),
            "event_name": ["a", "b"],
            "label": ["A", "B"],
        }
    )
    prices = pd.Series(
        [475.25, 478.5],
        index=pd.to_datetime(["2026-01-01", "2026-01-02"]),
    )

    annotations = build_chart_annotations(tape, price_lookup=prices)

    assert annotations[["id", "y"]].to_dict("records") == [
        {"id": "a", "y": 475.25},
        {"id": "b", "y": 478.5},
    ]
