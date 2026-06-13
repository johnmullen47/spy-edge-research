"""Internal shared helpers for the spy_edge_research package.

Generic, behavior-preserving utilities consolidated from per-module copies
(JSON-safe serialization, column/positive-int validation, deterministic
report export plumbing). These are intentionally generic: the research-only
*forbidden-field* guards stay in each report module because every report type
has its own forbidden set.
"""
