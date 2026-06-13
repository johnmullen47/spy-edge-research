import json

import pytest

from spy_edge_research.instruments import (
    InstrumentDefinition,
    build_instrument_registry,
    create_instrument_definition,
    filter_instruments_by_role,
    get_instrument_definition,
    list_instruments,
    read_instrument_registry,
    validate_instrument_registry,
    write_instrument_registry,
)


def test_build_default_registry_is_deterministic_and_research_only():
    registry = build_instrument_registry()

    assert [instrument.symbol for instrument in list_instruments(registry)] == [
        "DIA",
        "IWM",
        "QQQ",
        "SPY",
    ]
    assert get_instrument_definition(registry, "spy").role == "primary"
    assert registry.to_dict()["metadata"]["registry_caveat"] == (
        "research_registry_only_not_tradability_or_execution_support"
    )


def test_create_definition_normalizes_symbol_and_preserves_metadata():
    definition = create_instrument_definition(
        symbol=" qqq ",
        name="Invesco QQQ Trust",
        asset_class="ETF",
        role="index_confirmation",
        metadata={"source": "unit-test"},
    )

    assert definition == InstrumentDefinition(
        symbol="QQQ",
        name="Invesco QQQ Trust",
        asset_class="ETF",
        role="index_confirmation",
        market="US",
        session="regular_and_extended",
        timezone="America/New_York",
        notes="",
        metadata={"source": "unit-test"},
    )


def test_registry_rejects_duplicate_symbols():
    spy = create_instrument_definition(
        symbol="SPY",
        name="SPY",
        asset_class="ETF",
        role="primary",
    )
    duplicate = create_instrument_definition(
        symbol="spy",
        name="Duplicate SPY",
        asset_class="ETF",
        role="index_confirmation",
    )

    with pytest.raises(ValueError, match="Duplicate instrument symbols"):
        build_instrument_registry([spy, duplicate])


def test_filter_by_role_and_missing_symbol_errors():
    registry = build_instrument_registry()

    confirmations = filter_instruments_by_role(registry, "index_confirmation")
    assert [instrument.symbol for instrument in confirmations] == ["DIA", "IWM", "QQQ"]

    with pytest.raises(KeyError, match="Instrument symbol not found"):
        get_instrument_definition(registry, "XLK")


def test_registry_round_trips_json(tmp_path):
    registry = build_instrument_registry(metadata={"run_id": "test"})
    output_path = tmp_path / "registry.json"

    write_instrument_registry(registry, output_path)
    loaded = read_instrument_registry(output_path)

    assert loaded == validate_instrument_registry(json.loads(output_path.read_text()))
    assert loaded.metadata["run_id"] == "test"

    with pytest.raises(FileExistsError):
        write_instrument_registry(registry, output_path)
