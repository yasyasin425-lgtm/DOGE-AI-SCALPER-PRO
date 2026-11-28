
"""
DOGE AI SCALPER PRO
Risk Management V1
PAPER TRADING ONLY
"""

import math

from config import (
    RISK_FRACTION,
    DAILY_LOSS_LIMIT,
    MAX_POSITION_FRACTION,
    FEE_RATE,
    REWARD_RISK_RATIO,
    MIN_STOP_FRACTION,
    ATR_MULTIPLIER,
)


def calculate_equity(state, price):

    balance = float(state["balance"])
    price = float(price)

    if not math.isfinite(balance) or balance < 0:
        raise ValueError("Invalid balance.")

    if not math.isfinite(price) or price <= 0:
        raise ValueError("Invalid market price.")

    position = state.get("position")

    if position:

        qty = float(position["qty"])

        if not math.isfinite(qty) or qty <= 0:
            raise ValueError("Invalid quantity.")

        value = qty * price

        balance += value * (1 - FEE_RATE)

    return balance


def daily_loss_reached(state):

    start = float(state["day_start_balance"])

    pnl = float(state["daily_realized_pnl"])

    if not math.isfinite(start) or start <= 0:
        raise ValueError("Invalid daily balance.")

    if not math.isfinite(pnl):
        raise ValueError("Invalid daily PNL.")

    limit = start * DAILY_LOSS_LIMIT

    return pnl <= -limit


def calculate_levels(entry, atr):

    entry = float(entry)
    atr = float(atr)

    if not math.isfinite(entry) or entry <= 0:
        raise ValueError("Invalid entry price.")

    if not math.isfinite(atr) or atr <= 0:
        raise ValueError("Invalid ATR.")

    distance = max(
        atr * ATR_MULTIPLIER,
        entry * MIN_STOP_FRACTION,
    )

    stop = entry - distance

    if stop <= 0:
        raise ValueError("Invalid stop loss.")

    risk_per_unit = (
        distance
        + FEE_RATE * (entry + stop)
    )

    target = (
        entry * (1 + FEE_RATE)
        + REWARD_RISK_RATIO * risk_per_unit
    ) / (1 - FEE_RATE)

    return {
        "stop": stop,
        "target": target,
        "stop_distance": distance,
        "risk_per_unit": risk_per_unit,
    }


def calculate_position(state, entry, atr):

    if state.get("position") is not None:
        return None

    if daily_loss_reached(state):
        return None

    entry = float(entry)

    balance = float(state["balance"])

    equity = calculate_equity(
        state,
        entry
    )

    if balance <= 0:
        return None

    levels = calculate_levels(
        entry,
        atr
    )

    daily_remaining = (
        float(state["day_start_balance"])
        * DAILY_LOSS_LIMIT
        + float(state["daily_realized_pnl"])
    )

    risk_cash = min(
        equity * RISK_FRACTION,
        daily_remaining,
    )

    if risk_cash <= 0:
        return None

    qty_by_risk = (
        risk_cash
        / levels["risk_per_unit"]
    )

    max_cost = min(
        balance,
        equity * MAX_POSITION_FRACTION,
    )

    qty_by_balance = (
        max_cost
        / (entry * (1 + FEE_RATE))
    )

    qty = min(
        qty_by_risk,
        qty_by_balance,
    )

    if not math.isfinite(qty) or qty <= 0:
        return None

    cost = qty * entry

    entry_fee = cost * FEE_RATE

    total_cost = cost + entry_fee

    if total_cost > balance:
        return None

    estimated_risk = (
        qty * levels["risk_per_unit"]
    )

    return {
        "entry": entry,
        "qty": qty,
        "stop": levels["stop"],
        "target": levels["target"],
        "entry_fee": entry_fee,
        "total_cost": total_cost,
        "risk_cash": estimated_risk,
        "reward_risk": REWARD_RISK_RATIO,
    }


def calculate_exit(position, exit_price):

    entry = float(position["entry"])

    qty = float(position["qty"])

    exit_price = float(exit_price)

    if not all(
        math.isfinite(v) and v > 0
        for v in (entry, qty, exit_price)
    ):
        raise ValueError("Invalid exit data.")

    entry_fee = float(
        position.get(
            "entry_fee",
            entry * qty * FEE_RATE,
        )
    )

    if not math.isfinite(entry_fee) or entry_fee < 0:
        raise ValueError("Invalid entry fee.")

    exit_fee = (
        exit_price * qty * FEE_RATE
    )

    gross_pnl = (
        exit_price - entry
    ) * qty

    net_pnl = (
        gross_pnl
        - entry_fee
        - exit_fee
    )

    proceeds = (
        exit_price * qty
        - exit_fee
    )

    return {
        "gross_pnl": gross_pnl,
        "net_pnl": net_pnl,
        "entry_fee": entry_fee,
        "exit_fee": exit_fee,
        "proceeds": proceeds,
    }
