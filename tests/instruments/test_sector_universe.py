import json

import pytest

from spy_edge_research.instruments import (
    SectorDefinition,
    build_sector_universe,
    create_sector_definition,
    default_spdr_sector_universe,
    filter_sector_universe,
    get_sector_definition,
    list_sector_etfs,
    read_sector_universe,
    validate_sector_universe,
    write_sector_universe,
)


def test_default_spdr_sector_universe_is_deterministic_and_research_only():
    universe = build_sector_universe()

    assert list_sector_etfs(universe) == [
        "XLB",
        "XLC",
        "XLE",
        "XLF",
        "XLI",
        "XLK",
        "XLP",
        "XLRE",
        "XLU",
        "XLV",
        "XLY",
    ]
    assert get_sector_definition(universe, "technology").etf_symbol == "XLK"
    assert get_sector_definition(universe, "xlv").sector_group == "defensive"
    assert universe.to_dict()["metadata"]["universe_caveat"] == (
        "research_sector_context_only_not_allocation_or_execution_support"
    )


def test_create_sector_definition_normalizes_symbols_and_preserves_metadata():
    definition = create_sector_definition(
        sector_name=" Technology ",
        etf_symbol=" xlk ",
        sector_group="growth",
        benchmark_symbol=" spy ",
        metadata={"source": "unit-test"},
    )

    assert definition == SectorDefinition(
        sector_name="Technology",
        etf_symbol="XLK",
        sector_group="growth",
        market="US",
        session="regular_and_extended",
        timezone="America/New_York",
        benchmark_symbol="SPY",
        notes="",
        metadata={"source": "unit-test"},
    )


def test_sector_universe_rejects_duplicate_names_and_symbols():
    technology = create_sector_definition(
        sector_name="Technology",
        etf_symbol="XLK",
        sector_group="growth",
    )
    duplicate_symbol = create_sector_definition(
        sector_name="Duplicate Tech",
        etf_symbol="xlk",
        sector_group="growth",
    )
    duplicate_name = create_sector_definition(
        sector_name=" technology ",
        etf_symbol="VGT",
        sector_group="growth",
    )

    with pytest.raises(ValueError, match="Duplicate sector ETF symbols"):
        build_sector_universe([technology, duplicate_symbol])

    with pytest.raises(ValueError, match="Duplicate sector names"):
        build_sector_universe([technology, duplicate_name])


def test_filter_sector_universe_and_missing_definition_errors():
    universe = default_spdr_sector_universe()

    defensive = filter_sector_universe(universe, sector_group="defensive")
    assert [sector.etf_symbol for sector in defensive] == ["XLP", "XLRE", "XLU", "XLV"]

    spy_benchmarked = filter_sector_universe(universe, benchmark_symbol="spy")
    assert len(spy_benchmarked) == 11

    with pytest.raises(KeyError, match="Sector definition not found"):
        get_sector_definition(universe, "Semiconductors")


def test_sector_universe_round_trips_json(tmp_path):
    universe = build_sector_universe(metadata={"run_id": "test"})
    output_path = tmp_path / "sector_universe.json"

    write_sector_universe(universe, output_path)
    loaded = read_sector_universe(output_path)

    assert loaded == validate_sector_universe(json.loads(output_path.read_text()))
    assert loaded.metadata["run_id"] == "test"

    with pytest.raises(FileExistsError):
        write_sector_universe(universe, output_path)
