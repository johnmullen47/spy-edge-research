import json

import pytest

from spy_edge_research.instruments import (
    MacroInstrumentDefinition,
    build_macro_instrument_universe,
    create_macro_instrument_definition,
    default_macro_instrument_universe,
    filter_macro_instruments,
    get_macro_instrument_definition,
    list_macro_instruments,
    read_macro_instrument_universe,
    validate_macro_instrument_universe,
    write_macro_instrument_universe,
)


def test_default_macro_instrument_universe_is_deterministic_and_research_only():
    universe = build_macro_instrument_universe()

    assert list_macro_instruments(universe) == [
        "GLD",
        "HYG",
        "IEF",
        "LQD",
        "TLT",
        "USO",
        "UUP",
        "VIXY",
        "VXX",
    ]
    assert get_macro_instrument_definition(universe, "tlt").macro_group == "rates"
    assert get_macro_instrument_definition(universe, "vixy").role == "volatility_stress_proxy"
    assert universe.to_dict()["metadata"]["universe_caveat"] == (
        "research_macro_context_only_not_allocation_or_execution_support"
    )


def test_create_macro_instrument_definition_normalizes_symbols_and_preserves_metadata():
    definition = create_macro_instrument_definition(
        symbol=" hyg ",
        name=" High Yield ",
        macro_group="credit",
        role="credit_risk_proxy",
        benchmark_symbol=" spy ",
        metadata={"source": "unit-test"},
    )

    assert definition == MacroInstrumentDefinition(
        symbol="HYG",
        name="High Yield",
        macro_group="credit",
        role="credit_risk_proxy",
        market="US",
        session="regular_and_extended",
        timezone="America/New_York",
        benchmark_symbol="SPY",
        notes="",
        metadata={"source": "unit-test"},
    )


def test_macro_universe_rejects_duplicate_symbols():
    hyg = create_macro_instrument_definition(
        symbol="HYG",
        name="High Yield",
        macro_group="credit",
        role="credit_risk_proxy",
    )
    duplicate = create_macro_instrument_definition(
        symbol="hyg",
        name="Duplicate High Yield",
        macro_group="credit",
        role="credit_risk_proxy",
    )

    with pytest.raises(ValueError, match="Duplicate macro instrument symbols"):
        build_macro_instrument_universe([hyg, duplicate])


def test_filter_macro_instruments_and_missing_definition_errors():
    universe = default_macro_instrument_universe()

    rates = filter_macro_instruments(universe, macro_group="rates")
    assert [instrument.symbol for instrument in rates] == ["IEF", "TLT"]

    benchmarked = filter_macro_instruments(universe, benchmark_symbol="spy")
    assert len(benchmarked) == 9

    with pytest.raises(KeyError, match="Macro instrument definition not found"):
        get_macro_instrument_definition(universe, "DXY")


def test_macro_universe_round_trips_json(tmp_path):
    universe = build_macro_instrument_universe(metadata={"run_id": "test"})
    output_path = tmp_path / "macro_universe.json"

    write_macro_instrument_universe(universe, output_path)
    loaded = read_macro_instrument_universe(output_path)

    assert loaded == validate_macro_instrument_universe(json.loads(output_path.read_text()))
    assert loaded.metadata["run_id"] == "test"

    with pytest.raises(FileExistsError):
        write_macro_instrument_universe(universe, output_path)
