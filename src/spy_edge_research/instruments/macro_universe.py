"""Deterministic macro research instrument universe helpers.

The universe describes macro, rates, credit, commodity, volatility, currency,
and risk-proxy metadata for research context only. It is not a tradability,
allocation, broker, portfolio-construction, or execution registry.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


MACRO_UNIVERSE_CAVEAT = "research_macro_context_only_not_allocation_or_execution_support"


@dataclass(frozen=True)
class MacroInstrumentDefinition:
    """Typed metadata for one macro research proxy definition."""

    symbol: str
    name: str
    macro_group: str
    role: str
    market: str
    session: str
    timezone: str
    benchmark_symbol: str = ""
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MacroInstrumentUniverse:
    """A deterministic collection of macro research proxy definitions."""

    instruments: tuple[MacroInstrumentDefinition, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable universe dictionary."""
        return {
            "metadata": {
                "universe_caveat": MACRO_UNIVERSE_CAVEAT,
                **dict(self.metadata),
            },
            "instruments": [asdict(instrument) for instrument in self.instruments],
        }


def create_macro_instrument_definition(
    *,
    symbol: str,
    name: str,
    macro_group: str,
    role: str,
    market: str = "US",
    session: str = "regular_and_extended",
    timezone: str = "America/New_York",
    benchmark_symbol: str = "SPY",
    notes: str = "",
    metadata: Mapping[str, Any] | None = None,
) -> MacroInstrumentDefinition:
    """Create and validate one macro research proxy definition."""
    definition = MacroInstrumentDefinition(
        symbol=_normalize_symbol(symbol, "symbol"),
        name=_require_non_empty_string(name, "name"),
        macro_group=_require_non_empty_string(macro_group, "macro_group"),
        role=_require_non_empty_string(role, "role"),
        market=_require_non_empty_string(market, "market"),
        session=_require_non_empty_string(session, "session"),
        timezone=_require_non_empty_string(timezone, "timezone"),
        benchmark_symbol=_normalize_optional_symbol(benchmark_symbol, "benchmark_symbol"),
        notes=notes,
        metadata=dict(metadata or {}),
    )
    _validate_definition(definition)
    return definition


def build_macro_instrument_universe(
    instruments: Iterable[MacroInstrumentDefinition | Mapping[str, Any]] | None = None,
    *,
    metadata: Mapping[str, Any] | None = None,
) -> MacroInstrumentUniverse:
    """Build a deterministic macro universe, using common proxies when omitted."""
    source = default_macro_instrument_universe().instruments if instruments is None else instruments
    normalized = [_coerce_definition(item) for item in source]
    universe = MacroInstrumentUniverse(
        tuple(sorted(normalized, key=lambda item: item.symbol)),
        dict(metadata or {}),
    )
    return validate_macro_instrument_universe(universe)


def default_macro_instrument_universe() -> MacroInstrumentUniverse:
    """Return common macro research proxies as deterministic metadata."""
    rows = [
        ("TLT", "iShares 20+ Year Treasury Bond ETF", "rates", "duration_proxy"),
        ("IEF", "iShares 7-10 Year Treasury Bond ETF", "rates", "intermediate_duration_proxy"),
        ("HYG", "iShares iBoxx High Yield Corporate Bond ETF", "credit", "credit_risk_proxy"),
        ("LQD", "iShares iBoxx Investment Grade Corporate Bond ETF", "credit", "investment_grade_credit_proxy"),
        ("GLD", "SPDR Gold Shares", "commodity", "inflation_proxy"),
        ("USO", "United States Oil Fund", "commodity", "energy_inflation_proxy"),
        ("UUP", "Invesco DB US Dollar Index Bullish Fund", "currency", "dollar_proxy"),
        ("VIXY", "ProShares VIX Short-Term Futures ETF", "volatility", "volatility_stress_proxy"),
        ("VXX", "iPath Series B S&P 500 VIX Short-Term Futures ETN", "volatility", "volatility_stress_proxy"),
    ]
    return MacroInstrumentUniverse(
        tuple(
            create_macro_instrument_definition(
                symbol=symbol,
                name=name,
                macro_group=group,
                role=role,
                notes="Common listed proxy included for descriptive macro-regime research.",
            )
            for symbol, name, group, role in rows
        ),
        {"source": "deterministic_common_macro_research_proxies"},
    )


def validate_macro_instrument_universe(
    universe: MacroInstrumentUniverse | Mapping[str, Any],
) -> MacroInstrumentUniverse:
    """Validate universe structure and reject duplicate symbols."""
    if isinstance(universe, MacroInstrumentUniverse):
        normalized = [_coerce_definition(item) for item in universe.instruments]
        metadata = dict(universe.metadata)
    elif isinstance(universe, Mapping):
        if "instruments" not in universe:
            raise KeyError("universe is missing instruments")
        if not isinstance(universe.get("metadata", {}), Mapping):
            raise TypeError("universe metadata must be a mapping")
        normalized = [_coerce_definition(item) for item in universe["instruments"]]
        metadata = dict(universe.get("metadata", {}))
    else:
        raise TypeError("universe must be a MacroInstrumentUniverse or mapping")

    symbols = [instrument.symbol for instrument in normalized]
    duplicate_symbols = sorted({symbol for symbol in symbols if symbols.count(symbol) > 1})
    if duplicate_symbols:
        raise ValueError(f"Duplicate macro instrument symbols: {duplicate_symbols}")
    return MacroInstrumentUniverse(tuple(sorted(normalized, key=lambda item: item.symbol)), metadata)


def get_macro_instrument_definition(
    universe: MacroInstrumentUniverse | Mapping[str, Any],
    symbol: str,
) -> MacroInstrumentDefinition:
    """Return one macro instrument definition by symbol."""
    normalized = validate_macro_instrument_universe(universe)
    target = _normalize_symbol(symbol, "symbol")
    for instrument in normalized.instruments:
        if instrument.symbol == target:
            return instrument
    raise KeyError(f"Macro instrument definition not found: {symbol}")


def list_macro_instruments(universe: MacroInstrumentUniverse | Mapping[str, Any]) -> list[str]:
    """List macro instrument symbols in deterministic order."""
    return [instrument.symbol for instrument in validate_macro_instrument_universe(universe).instruments]


def filter_macro_instruments(
    universe: MacroInstrumentUniverse | Mapping[str, Any],
    *,
    macro_group: str | None = None,
    role: str | None = None,
    benchmark_symbol: str | None = None,
) -> list[MacroInstrumentDefinition]:
    """List macro instruments matching optional metadata filters."""
    normalized = validate_macro_instrument_universe(universe)
    group = _require_non_empty_string(macro_group, "macro_group") if macro_group is not None else None
    normalized_role = _require_non_empty_string(role, "role") if role is not None else None
    benchmark = (
        _normalize_optional_symbol(benchmark_symbol, "benchmark_symbol")
        if benchmark_symbol is not None
        else None
    )
    return [
        instrument
        for instrument in normalized.instruments
        if (group is None or instrument.macro_group == group)
        and (normalized_role is None or instrument.role == normalized_role)
        and (benchmark is None or instrument.benchmark_symbol == benchmark)
    ]


def write_macro_instrument_universe(
    universe: MacroInstrumentUniverse | Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Write macro instrument universe JSON with stable key ordering."""
    normalized = validate_macro_instrument_universe(universe)
    target = Path(output_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(normalized.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def read_macro_instrument_universe(path: str | Path) -> MacroInstrumentUniverse:
    """Read and validate a macro instrument universe JSON file."""
    return validate_macro_instrument_universe(json.loads(Path(path).read_text(encoding="utf-8")))


def _coerce_definition(
    item: MacroInstrumentDefinition | Mapping[str, Any],
) -> MacroInstrumentDefinition:
    if isinstance(item, MacroInstrumentDefinition):
        _validate_definition(item)
        return item
    if not isinstance(item, Mapping):
        raise TypeError("macro instrument definitions must be dataclasses or mappings")
    return create_macro_instrument_definition(**dict(item))


def _validate_definition(definition: MacroInstrumentDefinition) -> None:
    _normalize_symbol(definition.symbol, "symbol")
    _require_non_empty_string(definition.name, "name")
    _require_non_empty_string(definition.macro_group, "macro_group")
    _require_non_empty_string(definition.role, "role")
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
