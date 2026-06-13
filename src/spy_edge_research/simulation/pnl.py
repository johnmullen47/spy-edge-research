"""P&L aggregation, equity curve, and drawdown for the simulation layer (MOD 14).

Turns a list of closed ``SimTrade`` records into descriptive tables: a per-trade
ledger, a realized equity curve (P&L booked at each trade's exit bar), and a
summary with win rate, gross/net mean returns, total P&L, and max drawdown.
These are simulation outputs, not performance claims or trade authorizations.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from spy_edge_research.simulation.contracts import EquityPoint, SimTrade

TRADE_LEDGER_COLUMNS: tuple[str, ...] = (
    "position_id",
    "candidate_id",
    "side",
    "entry_bar",
    "exit_bar",
    "entry_price",
    "exit_price",
    "holding_bars",
    "gross_return_bps",
    "cost_bps",
    "net_return_bps",
    "pnl_points",
    "exit_reason",
)

EQUITY_CURVE_COLUMNS: tuple[str, ...] = (
    "bar_index",
    "timestamp",
    "cumulative_pnl_points",
    "cumulative_net_return_bps",
    "open_position_count",
)


def build_trade_ledger(trades: Sequence[SimTrade]) -> pd.DataFrame:
    """Build a deterministic per-trade ledger DataFrame."""
    rows = [
        {column: getattr(trade, column) for column in TRADE_LEDGER_COLUMNS}
        for trade in trades
    ]
    ledger = pd.DataFrame(rows, columns=list(TRADE_LEDGER_COLUMNS))
    if ledger.empty:
        return ledger
    return ledger.sort_values(["exit_bar", "position_id"], kind="mergesort").reset_index(
        drop=True
    )


def build_equity_curve(
    trades: Sequence[SimTrade], timestamps: pd.Series | None = None
) -> pd.DataFrame:
    """Build a realized equity curve, booking each trade's P&L at its exit bar.

    ``open_position_count`` at an exit bar counts positions whose holding window
    spans it. ``timestamps`` (optional, indexed by bar) labels each exit bar.
    """
    if not trades:
        return pd.DataFrame(columns=list(EQUITY_CURVE_COLUMNS))

    ordered = sorted(trades, key=lambda t: (t.exit_bar, t.position_id))
    cumulative_pnl = 0.0
    cumulative_bps = 0.0
    rows: list[dict] = []
    for trade in ordered:
        cumulative_pnl += trade.pnl_points
        cumulative_bps += trade.net_return_bps
        open_count = sum(
            1 for other in trades if other.entry_bar <= trade.exit_bar < other.exit_bar
        )
        timestamp = (
            timestamps.iloc[trade.exit_bar]
            if timestamps is not None and trade.exit_bar < len(timestamps)
            else None
        )
        rows.append(
            vars(
                EquityPoint(
                    bar_index=trade.exit_bar,
                    timestamp=timestamp,
                    cumulative_pnl_points=cumulative_pnl,
                    cumulative_net_return_bps=cumulative_bps,
                    open_position_count=open_count,
                )
            )
        )
    return pd.DataFrame(rows, columns=list(EQUITY_CURVE_COLUMNS))


def max_drawdown_points(equity_curve: pd.DataFrame) -> float:
    """Maximum peak-to-trough drawdown of cumulative P&L (>= 0)."""
    if equity_curve.empty:
        return 0.0
    cumulative = equity_curve["cumulative_pnl_points"].to_numpy(dtype=float)
    running_peak = -float("inf")
    worst = 0.0
    for value in cumulative:
        running_peak = max(running_peak, value)
        worst = min(worst, value - running_peak)
    return abs(float(worst))


def summarize_simulation(
    trades: Sequence[SimTrade], equity_curve: pd.DataFrame
) -> pd.DataFrame:
    """One-row descriptive summary of the simulated trades."""
    count = len(trades)
    if count == 0:
        row = {
            "trade_count": 0,
            "win_rate": float("nan"),
            "mean_gross_return_bps": float("nan"),
            "mean_net_return_bps": float("nan"),
            "total_pnl_points": 0.0,
            "max_drawdown_points": 0.0,
        }
        return pd.DataFrame([row])

    wins = sum(1 for trade in trades if trade.net_return_bps > 0)
    row = {
        "trade_count": int(count),
        "win_rate": wins / count,
        "mean_gross_return_bps": sum(t.gross_return_bps for t in trades) / count,
        "mean_net_return_bps": sum(t.net_return_bps for t in trades) / count,
        "total_pnl_points": sum(t.pnl_points for t in trades),
        "max_drawdown_points": max_drawdown_points(equity_curve),
    }
    return pd.DataFrame([row])
