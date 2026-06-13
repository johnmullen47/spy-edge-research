import json

import pytest

from spy_edge_research.instruments import (
    FactorDefinition,
    build_factor_universe,
    create_factor_definition,
    default_factor_etf_universe,
    filter_factor_universe,
    get_factor_definition,
    list_factor_etfs,
    read_factor_universe,
    validate_factor_universe,
    write_factor_universe,
)


def test_default_factor_universe_is_deterministic_and_research_only():
    universe = build_factor_universe()

    assert list_factor_etfs(universe) == ["HDV", "MTUM", "QUAL", "SIZE", "USMV", "VLUE"]
    assert get_factor_definition(universe, "momentum").etf_symbol == "MTUM"
    assert get_factor_definition(universe, "usmv").factor_style == "low_volatility"
    assert universe.to_dict()["metadata"]["universe_caveat"] == (
        "research_factor_context_only_not_allocation_or_execution_support"
    )


def test_create_factor_definition_normalizes_symbols_and_preserves_metadata():
    definition = create_factor_definition(
        factor_name=" Momentum ",
        etf_symbol=" mtum ",
        factor_style="momentum",
        benchmark_symbol=" spy ",
        metadata={"source": "unit-test"},
    )

    assert definition == FactorDefinition(
        factor_name="Momentum",
        etf_symbol="MTUM",
        factor_style="momentum",
        market="US",
        session="regular_and_extended",
        timezone="America/New_York",
        benchmark_symbol="SPY",
        notes="",
        metadata={"source": "unit-test"},
    )


def test_factor_universe_rejects_duplicate_names_and_symbols():
    momentum = create_factor_definition(factor_name="Momentum", etf_symbol="MTUM", factor_style="momentum")
    duplicate_symbol = create_factor_definition(
        factor_name="Duplicate Momentum", etf_symbol="mtum", factor_style="momentum"
    )
    duplicate_name = create_factor_definition(
        factor_name=" momentum ", etf_symbol="PDP", factor_style="momentum"
    )

    with pytest.raises(ValueError, match="Duplicate factor ETF symbols"):
        build_factor_universe([momentum, duplicate_symbol])
    with pytest.raises(ValueError, match="Duplicate factor names"):
        build_factor_universe([momentum, duplicate_name])


def test_filter_factor_universe_and_missing_definition_errors():
    universe = default_factor_etf_universe()

    low_vol = filter_factor_universe(universe, factor_style="low_volatility")
    assert [factor.etf_symbol for factor in low_vol] == ["USMV"]

    spy_benchmarked = filter_factor_universe(universe, benchmark_symbol="spy")
    assert len(spy_benchmarked) == 6

    with pytest.raises(KeyError, match="Factor definition not found"):
        get_factor_definition(universe, "Carry")


def test_factor_universe_round_trips_json(tmp_path):
    universe = build_factor_universe(metadata={"run_id": "test"})
    output_path = tmp_path / "factor_universe.json"

    write_factor_universe(universe, output_path)
    loaded = read_factor_universe(output_path)

    assert loaded == validate_factor_universe(json.loads(output_path.read_text()))
    assert loaded.metadata["run_id"] == "test"

    with pytest.raises(FileExistsError):
        write_factor_universe(universe, output_path)
