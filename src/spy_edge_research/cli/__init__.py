"""Unified command-line pipeline runner (MOD 11).

Exposes the pure ``run_pipeline`` orchestration and the argparse ``main`` entry
point. Research-only: produces descriptive artifacts, never trade instructions.
"""

from spy_edge_research.cli.main import build_parser, main
from spy_edge_research.cli.pipeline import PipelineConfig, RunResult, run_pipeline
from spy_edge_research.cli.run_artifacts import RunPaths, build_run_paths

__all__ = [
    "build_parser",
    "main",
    "PipelineConfig",
    "RunResult",
    "run_pipeline",
    "RunPaths",
    "build_run_paths",
]
