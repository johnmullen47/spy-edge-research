# Auto-Trader SPY Event Pipeline

This repository contains a small pipeline for turning wide causal-feature data into chart-ready annotations:

```text
wide causal feature dataframe -> named event catalog -> event tape -> chart annotations
```

## Data Shapes

### Wide causal feature dataframe

One row per timestamp, one column per causal feature.

```text
timestamp            spy_gap_up  vix_spike
2026-06-10 09:30     1           0.2
2026-06-10 09:31     0           1.7
```

### Named event catalog

Maps feature columns to event names and display metadata.

```python
from causal_events import EventDefinition, build_event_catalog

catalog = build_event_catalog([
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
        threshold=1.5,
        direction="above",
        color="#dc2626",
        marker="circle",
    ),
])
```

### Event tape

One row per triggered event.

```python
from causal_events import build_event_tape

tape = build_event_tape(features, catalog, timestamp_column="timestamp")
```

### Chart annotations

Display records for plotting libraries.

```python
from causal_events import build_chart_annotations

annotations = build_chart_annotations(tape, timestamp_column="timestamp")
```

## Full Pipeline

```python
from causal_events import EventDefinition, wide_features_to_chart_annotations

catalog, tape, annotations = wide_features_to_chart_annotations(
    features,
    [
        EventDefinition(feature="spy_gap_up", name="gap_up", label="Gap up"),
        EventDefinition(
            feature="vix_spike",
            name="vix_spike",
            label="VIX spike",
            threshold=1.5,
            direction="above",
        ),
    ],
    timestamp_column="timestamp",
)
```

Install dependencies with:

```bash
python3 -m pip install -e ".[dev]"
```

Run tests with:

```bash
python3 -m pytest -q
```
