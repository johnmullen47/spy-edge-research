"""Shared pytest fixtures for the spy_edge_research test suite.

These consolidate the most-duplicated test-data builders (a directional event +
forward-return frame and a validated event catalog) so new tests can reuse them
instead of re-declaring local `_df()` / `_catalog()` helpers. Existing tests are
left as-is; migrate opportunistically.
"""

from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def event_outcome_frame() -> pd.DataFrame:
    """A small event/forward-return frame with a context column."""
    return pd.DataFrame(
        {
            "event_vwap_reclaim": [1, 0, 1, 1, 0, 1, 1],
            "forward_return_5m": [0.3, -0.1, 0.2, -0.4, 0.1, 0.5, 0.0],
            "primary_context": [
                "confirmed",
                "confirmed",
                "divergent",
                "divergent",
                "neutral",
                "confirmed",
                "neutral",
            ],
        }
    )


@pytest.fixture
def event_catalog() -> pd.DataFrame:
    """A minimal validated-shape event catalog for one directional event."""
    return pd.DataFrame(
        {
            "event_column": ["event_vwap_reclaim"],
            "event_name": ["event_vwap_reclaim"],
            "event_family": ["vwap"],
            "event_direction": ["long"],
            "is_directional": [True],
        }
    )
