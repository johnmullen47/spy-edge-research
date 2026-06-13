"""Deterministic research sector ETF universe helpers.

The universe describes sector ETF metadata for research context only. It is
not a tradability, allocation, broker, portfolio-construction, or execution
registry.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


SECTOR_UNIVERSE_CAVEAT = "research_sector_context_only_not_allocation_or_execution_support"


@dataclass(frozen=True)
class SectorDefinition:
    """Typed metadata for one sector ETF research definition."""

    sector_name: str
    etf_symbol: str
    sector_group: str
    market: str
    session: str
    timezone: str
    benchmark_symbol: str = ""
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SectorUniverse:
    """A deterministic collection of sector ETF definitions."""

    sectors: tuple[SectorDefinition, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable universe dictionary."""
        return {
            "metadata": {
                "universe_caveat": SECTOR_UNIVERSE_CAVEAT,
                **dict(self.metadata),
            },
            "sectors": [asdict(sector) for sector in self.sectors],
        }


def create_sector_definition(
    *,
    sector_name: str,
    etf_symbol: str,
    sector_group: str,
    market: str = "US",
    session: str = "regular_and_extended",
    timezone: str = "America/New_York",
    benchmark_symbol: str = "SPY",
    notes: str = "",
    metadata: Mapping[str, Any] | None = None,
) -> SectorDefinition:
    """Create and validate one sector ETF definition."""
    definition = SectorDefinition(
        sector_name=_require_non_empty_string(sector_name, "sector_name"),
        etf_symbol=_normalize_symbol(etf_symbol, "etf_symbol"),
        sector_group=_require_non_empty_string(sector_group, "sector_group"),
        market=_require_non_empty_string(market, "market"),
        session=_require_non_empty_string(session, "session"),
        timezone=_require_non_empty_string(timezone, "timezone"),
        benchmark_symbol=_normalize_optional_symbol(benchmark_symbol, "benchmark_symbol"),
        notes=notes,
        metadata=dict(metadata or {}),
    )
    _validate_definition(definition)
    return definition


def build_sector_universe(
    sectors: Iterable[SectorDefinition | Mapping[str, Any]] | None = None,
    *,
    metadata: Mapping[str, Any] | None = None,
) -> SectorUniverse:
    """Build a deterministic sector universe, using SPDR sectors when omitted."""
    source = default_spdr_sector_universe().sectors if sectors is None else sectors
    normalized = [_coerce_definition(item) for item in source]
    universe = SectorUniverse(tuple(sorted(normalized, key=lambda item: item.etf_symbol)), dict(metadata or {}))
    return validate_sector_universe(universe)


def default_spdr_sector_universe() -> SectorUniverse:
    """Return common SPDR sector ETFs as research metadata."""
    rows = [
        ("Communication Services", "XLC", "cyclical"),
        ("Consumer Discretionary", "XLY", "cyclical"),
        ("Consumer Staples", "XLP", "defensive"),
        ("Energy", "XLE", "cyclical"),
        ("Financials", "XLF", "cyclical"),
        ("Health Care", "XLV", "defensive"),
        ("Industrials", "XLI", "cyclical"),
        ("Materials", "XLB", "cyclical"),
        ("Real Estate", "XLRE", "defensive"),
        ("Technology", "XLK", "growth"),
        ("Utilities", "XLU", "defensive"),
    ]
    return SectorUniverse(
        tuple(
            create_sector_definition(
                sector_name=name,
                etf_symbol=symbol,
                sector_group=group,
                notes="Common SPDR sector ETF included for descriptive sector-context research.",
            )
            for name, symbol, group in rows
        ),
        {"source": "deterministic_common_spdr_sector_etfs"},
    )


def validate_sector_universe(universe: SectorUniverse | Mapping[str, Any]) -> SectorUniverse:
    """Validate universe structure and reject duplicate names or symbols."""
    if isinstance(universe, SectorUniverse):
        normalized = [_coerce_definition(item) for item in universe.sectors]
        metadata = dict(universe.metadata)
    elif isinstance(universe, Mapping):
        if "sectors" not in universe:
            raise KeyError("universe is missing sectors")
        if not isinstance(universe.get("metadata", {}), Mapping):
            raise TypeError("universe metadata must be a mapping")
        normalized = [_coerce_definition(item) for item in universe["sectors"]]
        metadata = dict(universe.get("metadata", {}))
    else:
        raise TypeError("universe must be a SectorUniverse or mapping")

    names = [_normalize_key(sector.sector_name) for sector in normalized]
    symbols = [sector.etf_symbol for sector in normalized]
    duplicate_names = sorted({name for name in names if names.count(name) > 1})
    duplicate_symbols = sorted({symbol for symbol in symbols if symbols.count(symbol) > 1})
    if duplicate_names:
        raise ValueError(f"Duplicate sector names: {duplicate_names}")
    if duplicate_symbols:
        raise ValueError(f"Duplicate sector ETF symbols: {duplicate_symbols}")
    return SectorUniverse(tuple(sorted(normalized, key=lambda item: item.etf_symbol)), metadata)


def get_sector_definition(
    universe: SectorUniverse | Mapping[str, Any],
    sector_or_symbol: str,
) -> SectorDefinition:
    """Return one sector definition by sector name or ETF symbol."""
    normalized = validate_sector_universe(universe)
    target_name = _normalize_key(sector_or_symbol)
    target_symbol = _normalize_symbol(sector_or_symbol, "sector_or_symbol")
    for sector in normalized.sectors:
        if _normalize_key(sector.sector_name) == target_name or sector.etf_symbol == target_symbol:
            return sector
    raise KeyError(f"Sector definition not found: {sector_or_symbol}")


def list_sector_etfs(universe: SectorUniverse | Mapping[str, Any]) -> list[str]:
    """List sector ETF symbols in deterministic order."""
    return [sector.etf_symbol for sector in validate_sector_universe(universe).sectors]


def filter_sector_universe(
    universe: SectorUniverse | Mapping[str, Any],
    *,
    sector_group: str | None = None,
    benchmark_symbol: str | None = None,
) -> list[SectorDefinition]:
    """List sectors matching optional group and benchmark filters."""
    normalized = validate_sector_universe(universe)
    group = _require_non_empty_string(sector_group, "sector_group") if sector_group is not None else None
    benchmark = (
        _normalize_optional_symbol(benchmark_symbol, "benchmark_symbol")
        if benchmark_symbol is not None
        else None
    )
    return [
        sector
        for sector in normalized.sectors
        if (group is None or sector.sector_group == group)
        and (benchmark is None or sector.benchmark_symbol == benchmark)
    ]


def write_sector_universe(
    universe: SectorUniverse | Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Write sector universe JSON with stable key ordering."""
    normalized = validate_sector_universe(universe)
    target = Path(output_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(normalized.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def read_sector_universe(path: str | Path) -> SectorUniverse:
    """Read and validate a sector universe JSON file."""
    return validate_sector_universe(json.loads(Path(path).read_text(encoding="utf-8")))


def _coerce_definition(item: SectorDefinition | Mapping[str, Any]) -> SectorDefinition:
    if isinstance(item, SectorDefinition):
        _validate_definition(item)
        return item
    if not isinstance(item, Mapping):
        raise TypeError("sector definitions must be dataclasses or mappings")
    return create_sector_definition(**dict(item))


def _validate_definition(definition: SectorDefinition) -> None:
    _require_non_empty_string(definition.sector_name, "sector_name")
    _normalize_symbol(definition.etf_symbol, "etf_symbol")
    _require_non_empty_string(definition.sector_group, "sector_group")
    _require_non_empty_string(definition.market, "market")
    _require_non_empty_string(definition.session, "session")
    _require_non_empty_string(definition.timezone, "timezone")
    _normalize_optional_symbol(definition.benchmark_symbol, "benchmark_symbol")
    if not isinstance(definition.metadata, dict):
        raise TypeError("metadata must be a dictionary")


def _require_non_empty_string(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _normalize_symbol(value: str, name: str) -> str:
    return _require_non_empty_string(value, name).upper()


def _normalize_optional_symbol(value: str, name: str) -> str:
    if value == "":
        return ""
    return _normalize_symbol(value, name)


def _normalize_key(value: str) -> str:
    return _require_non_empty_string(value, "key").strip().casefold()
