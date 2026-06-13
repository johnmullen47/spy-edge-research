"""Deterministic research instrument registry helpers.

The registry describes instruments available for research context only. It is
not a tradability, routing, broker, or execution registry.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


INSTRUMENT_REGISTRY_CAVEAT = "research_registry_only_not_tradability_or_execution_support"
DEFAULT_INSTRUMENT_ROLES = {
    "primary",
    "index_confirmation",
    "sector_context",
    "macro_context",
    "factor_context",
}


@dataclass(frozen=True)
class InstrumentDefinition:
    """Typed metadata for one research instrument."""

    symbol: str
    name: str
    asset_class: str
    role: str
    market: str
    session: str
    timezone: str
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InstrumentRegistry:
    """A deterministic collection of research instrument definitions."""

    instruments: tuple[InstrumentDefinition, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable registry dictionary."""
        return {
            "metadata": {
                "registry_caveat": INSTRUMENT_REGISTRY_CAVEAT,
                **dict(self.metadata),
            },
            "instruments": [asdict(instrument) for instrument in self.instruments],
        }


def create_instrument_definition(
    *,
    symbol: str,
    name: str,
    asset_class: str,
    role: str,
    market: str = "US",
    session: str = "regular_and_extended",
    timezone: str = "America/New_York",
    notes: str = "",
    metadata: Mapping[str, Any] | None = None,
) -> InstrumentDefinition:
    """Create and validate one instrument definition."""
    normalized = InstrumentDefinition(
        symbol=_normalize_symbol(symbol),
        name=_require_non_empty_string(name, "name"),
        asset_class=_require_non_empty_string(asset_class, "asset_class"),
        role=_require_non_empty_string(role, "role"),
        market=_require_non_empty_string(market, "market"),
        session=_require_non_empty_string(session, "session"),
        timezone=_require_non_empty_string(timezone, "timezone"),
        notes=notes,
        metadata=dict(metadata or {}),
    )
    _validate_definition(normalized)
    return normalized


def build_instrument_registry(
    instruments: Iterable[InstrumentDefinition | Mapping[str, Any]] | None = None,
    *,
    metadata: Mapping[str, Any] | None = None,
) -> InstrumentRegistry:
    """Build a deterministic registry, using default index ETFs when omitted."""
    source = _default_instruments() if instruments is None else instruments
    normalized = [_coerce_definition(item) for item in source]
    normalized = sorted(normalized, key=lambda item: item.symbol)
    registry = InstrumentRegistry(tuple(normalized), dict(metadata or {}))
    return validate_instrument_registry(registry)


def validate_instrument_registry(registry: InstrumentRegistry | Mapping[str, Any]) -> InstrumentRegistry:
    """Validate registry structure and reject duplicate symbols."""
    if isinstance(registry, InstrumentRegistry):
        normalized = [_coerce_definition(item) for item in registry.instruments]
        metadata = dict(registry.metadata)
    elif isinstance(registry, Mapping):
        if "instruments" not in registry:
            raise KeyError("registry is missing instruments")
        if not isinstance(registry.get("metadata", {}), Mapping):
            raise TypeError("registry metadata must be a mapping")
        normalized = [_coerce_definition(item) for item in registry["instruments"]]
        metadata = dict(registry.get("metadata", {}))
    else:
        raise TypeError("registry must be an InstrumentRegistry or mapping")

    symbols = [instrument.symbol for instrument in normalized]
    duplicates = sorted({symbol for symbol in symbols if symbols.count(symbol) > 1})
    if duplicates:
        raise ValueError(f"Duplicate instrument symbols: {duplicates}")
    return InstrumentRegistry(tuple(sorted(normalized, key=lambda item: item.symbol)), metadata)


def get_instrument_definition(
    registry: InstrumentRegistry | Mapping[str, Any],
    symbol: str,
) -> InstrumentDefinition:
    """Return one instrument by symbol."""
    normalized = validate_instrument_registry(registry)
    target = _normalize_symbol(symbol)
    for instrument in normalized.instruments:
        if instrument.symbol == target:
            return instrument
    raise KeyError(f"Instrument symbol not found: {target}")


def list_instruments(registry: InstrumentRegistry | Mapping[str, Any]) -> list[InstrumentDefinition]:
    """List instrument definitions in deterministic symbol order."""
    return list(validate_instrument_registry(registry).instruments)


def filter_instruments_by_role(
    registry: InstrumentRegistry | Mapping[str, Any],
    role: str,
) -> list[InstrumentDefinition]:
    """List instruments whose role matches ``role``."""
    target = _require_non_empty_string(role, "role")
    return [item for item in list_instruments(registry) if item.role == target]


def write_instrument_registry(
    registry: InstrumentRegistry | Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Write registry JSON with stable key ordering."""
    normalized = validate_instrument_registry(registry)
    target = Path(output_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(normalized.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def read_instrument_registry(path: str | Path) -> InstrumentRegistry:
    """Read and validate a registry JSON file."""
    return validate_instrument_registry(json.loads(Path(path).read_text(encoding="utf-8")))


def _default_instruments() -> list[InstrumentDefinition]:
    return [
        create_instrument_definition(
            symbol="SPY",
            name="SPDR S&P 500 ETF Trust",
            asset_class="ETF",
            role="primary",
            notes="Default primary instrument for SPY directional edge research.",
        ),
        create_instrument_definition(
            symbol="QQQ",
            name="Invesco QQQ Trust",
            asset_class="ETF",
            role="index_confirmation",
            notes="Nasdaq-100 ETF used as index confirmation context.",
        ),
        create_instrument_definition(
            symbol="DIA",
            name="SPDR Dow Jones Industrial Average ETF Trust",
            asset_class="ETF",
            role="index_confirmation",
            notes="Dow Jones ETF used as index confirmation context.",
        ),
        create_instrument_definition(
            symbol="IWM",
            name="iShares Russell 2000 ETF",
            asset_class="ETF",
            role="index_confirmation",
            notes="Small-cap ETF used as index confirmation context.",
        ),
    ]


def _coerce_definition(item: InstrumentDefinition | Mapping[str, Any]) -> InstrumentDefinition:
    if isinstance(item, InstrumentDefinition):
        _validate_definition(item)
        return item
    if not isinstance(item, Mapping):
        raise TypeError("instrument definitions must be dataclasses or mappings")
    return create_instrument_definition(**dict(item))


def _validate_definition(definition: InstrumentDefinition) -> None:
    for field_name in (
        "symbol",
        "name",
        "asset_class",
        "role",
        "market",
        "session",
        "timezone",
    ):
        _require_non_empty_string(getattr(definition, field_name), field_name)
    if not isinstance(definition.metadata, dict):
        raise TypeError("metadata must be a dict")


def _normalize_symbol(symbol: str) -> str:
    return _require_non_empty_string(symbol, "symbol").upper()


def _require_non_empty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()
