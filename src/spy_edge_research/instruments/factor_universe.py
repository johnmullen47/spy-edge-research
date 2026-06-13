"""Deterministic research factor ETF universe helpers.

The universe describes factor ETF metadata (momentum, value, quality, size,
low-volatility, ...) for research context only. It is not a tradability,
allocation, broker, portfolio-construction, or execution registry.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


FACTOR_UNIVERSE_CAVEAT = "research_factor_context_only_not_allocation_or_execution_support"


@dataclass(frozen=True)
class FactorDefinition:
    """Typed metadata for one factor ETF research definition."""

    factor_name: str
    etf_symbol: str
    factor_style: str
    market: str
    session: str
    timezone: str
    benchmark_symbol: str = ""
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FactorUniverse:
    """A deterministic collection of factor ETF definitions."""

    factors: tuple[FactorDefinition, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable universe dictionary."""
        return {
            "metadata": {
                "universe_caveat": FACTOR_UNIVERSE_CAVEAT,
                **dict(self.metadata),
            },
            "factors": [asdict(factor) for factor in self.factors],
        }


def create_factor_definition(
    *,
    factor_name: str,
    etf_symbol: str,
    factor_style: str,
    market: str = "US",
    session: str = "regular_and_extended",
    timezone: str = "America/New_York",
    benchmark_symbol: str = "SPY",
    notes: str = "",
    metadata: Mapping[str, Any] | None = None,
) -> FactorDefinition:
    """Create and validate one factor ETF definition."""
    definition = FactorDefinition(
        factor_name=_require_non_empty_string(factor_name, "factor_name"),
        etf_symbol=_normalize_symbol(etf_symbol, "etf_symbol"),
        factor_style=_require_non_empty_string(factor_style, "factor_style"),
        market=_require_non_empty_string(market, "market"),
        session=_require_non_empty_string(session, "session"),
        timezone=_require_non_empty_string(timezone, "timezone"),
        benchmark_symbol=_normalize_optional_symbol(benchmark_symbol, "benchmark_symbol"),
        notes=notes,
        metadata=dict(metadata or {}),
    )
    _validate_definition(definition)
    return definition


def build_factor_universe(
    factors: Iterable[FactorDefinition | Mapping[str, Any]] | None = None,
    *,
    metadata: Mapping[str, Any] | None = None,
) -> FactorUniverse:
    """Build a deterministic factor universe, using common factor ETFs when omitted."""
    source = default_factor_etf_universe().factors if factors is None else factors
    normalized = [_coerce_definition(item) for item in source]
    universe = FactorUniverse(tuple(sorted(normalized, key=lambda item: item.etf_symbol)), dict(metadata or {}))
    return validate_factor_universe(universe)


def default_factor_etf_universe() -> FactorUniverse:
    """Return common single-factor ETFs as research metadata."""
    rows = [
        ("Momentum", "MTUM", "momentum"),
        ("Value", "VLUE", "value"),
        ("Quality", "QUAL", "quality"),
        ("Size", "SIZE", "size"),
        ("Minimum Volatility", "USMV", "low_volatility"),
        ("High Dividend Yield", "HDV", "yield"),
    ]
    return FactorUniverse(
        tuple(
            create_factor_definition(
                factor_name=name,
                etf_symbol=symbol,
                factor_style=style,
                notes="Common single-factor ETF included for descriptive factor-context research.",
            )
            for name, symbol, style in rows
        ),
        {"source": "deterministic_common_factor_etfs"},
    )


def validate_factor_universe(universe: FactorUniverse | Mapping[str, Any]) -> FactorUniverse:
    """Validate universe structure and reject duplicate names or symbols."""
    if isinstance(universe, FactorUniverse):
        normalized = [_coerce_definition(item) for item in universe.factors]
        metadata = dict(universe.metadata)
    elif isinstance(universe, Mapping):
        if "factors" not in universe:
            raise KeyError("universe is missing factors")
        if not isinstance(universe.get("metadata", {}), Mapping):
            raise TypeError("universe metadata must be a mapping")
        normalized = [_coerce_definition(item) for item in universe["factors"]]
        metadata = dict(universe.get("metadata", {}))
    else:
        raise TypeError("universe must be a FactorUniverse or mapping")

    names = [_normalize_key(factor.factor_name) for factor in normalized]
    symbols = [factor.etf_symbol for factor in normalized]
    duplicate_names = sorted({name for name in names if names.count(name) > 1})
    duplicate_symbols = sorted({symbol for symbol in symbols if symbols.count(symbol) > 1})
    if duplicate_names:
        raise ValueError(f"Duplicate factor names: {duplicate_names}")
    if duplicate_symbols:
        raise ValueError(f"Duplicate factor ETF symbols: {duplicate_symbols}")
    return FactorUniverse(tuple(sorted(normalized, key=lambda item: item.etf_symbol)), metadata)


def get_factor_definition(
    universe: FactorUniverse | Mapping[str, Any],
    factor_or_symbol: str,
) -> FactorDefinition:
    """Return one factor definition by factor name or ETF symbol."""
    normalized = validate_factor_universe(universe)
    target_name = _normalize_key(factor_or_symbol)
    target_symbol = _normalize_symbol(factor_or_symbol, "factor_or_symbol")
    for factor in normalized.factors:
        if _normalize_key(factor.factor_name) == target_name or factor.etf_symbol == target_symbol:
            return factor
    raise KeyError(f"Factor definition not found: {factor_or_symbol}")


def list_factor_etfs(universe: FactorUniverse | Mapping[str, Any]) -> list[str]:
    """List factor ETF symbols in deterministic order."""
    return [factor.etf_symbol for factor in validate_factor_universe(universe).factors]


def filter_factor_universe(
    universe: FactorUniverse | Mapping[str, Any],
    *,
    factor_style: str | None = None,
    benchmark_symbol: str | None = None,
) -> list[FactorDefinition]:
    """List factors matching optional style and benchmark filters."""
    normalized = validate_factor_universe(universe)
    style = _require_non_empty_string(factor_style, "factor_style") if factor_style is not None else None
    benchmark = (
        _normalize_optional_symbol(benchmark_symbol, "benchmark_symbol")
        if benchmark_symbol is not None
        else None
    )
    return [
        factor
        for factor in normalized.factors
        if (style is None or factor.factor_style == style)
        and (benchmark is None or factor.benchmark_symbol == benchmark)
    ]


def write_factor_universe(
    universe: FactorUniverse | Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Write factor universe JSON with stable key ordering."""
    normalized = validate_factor_universe(universe)
    target = Path(output_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(normalized.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def read_factor_universe(path: str | Path) -> FactorUniverse:
    """Read and validate a factor universe JSON file."""
    return validate_factor_universe(json.loads(Path(path).read_text(encoding="utf-8")))


def _coerce_definition(item: FactorDefinition | Mapping[str, Any]) -> FactorDefinition:
    if isinstance(item, FactorDefinition):
        _validate_definition(item)
        return item
    if not isinstance(item, Mapping):
        raise TypeError("factor definitions must be dataclasses or mappings")
    return create_factor_definition(**dict(item))


def _validate_definition(definition: FactorDefinition) -> None:
    _require_non_empty_string(definition.factor_name, "factor_name")
    _normalize_symbol(definition.etf_symbol, "etf_symbol")
    _require_non_empty_string(definition.factor_style, "factor_style")
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
