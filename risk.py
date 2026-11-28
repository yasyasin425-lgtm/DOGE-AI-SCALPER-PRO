
"""
DOGE AI SCALPER PRO
Risk Management V2
Decimal Precision
PAPER TRADING ONLY
"""

from decimal import localcontext

from config import (
    RISK_FRACTION,
    DAILY_LOSS_LIMIT,
    MAX_POSITION_FRACTION,
    FEE_RATE,
    REWARD_RISK_RATIO,
    MIN_STOP_FRACTION,
    ATR_MULTIPLIER,
)

from money import (
    ZERO,
    ONE,
    decimal_value,
    quantity,
    calculate_buy,
    calculate_sell,
)


RISK = decimal_value(RISK_FRACTION)

DAILY_LIMIT = decimal_value(
    DAILY_LOSS_LIMIT
)

MAX_POSITION = decimal_value(
    MAX_POSITION_FRACTION
)

FEE = decimal_value(FEE_RATE)

REWARD_RISK = decimal_value(
    REWARD_RISK_RATIO
)

MIN_STOP = decimal_value(
    MIN_STOP_FRACTION
)

ATR_FACTOR = decimal_value(
    ATR_MULTIPLIER
)


# =====================================
# WALLET EQUITY
# =====================================

def calculate_equity(state, price):

    with localcontext() as ctx:

        ctx.prec = 50

        balance = decimal_value(
            state["balance"]
        )

        price = decimal_value(price)

        if balance < ZERO or price <= ZERO:

            raise ValueError(
                "Invalid wallet or price."
            )

        position = state.get("position")

        if position:

            qty = decimal_value(
                position["qty"]
            )

            if qty <= ZERO:

                raise ValueError(
                    "Invalid quantity."
                )

            balance += (
                qty * price * (ONE - FEE)
            )

        return balance


# =====================================
# DAILY LOSS PROTECTION
# =====================================

def daily_loss_reached(state):

    start = decimal_value(
        state["day_start_balance"]
    )

    pnl = decimal_value(
        state["daily_realized_pnl"]
    )

    if start <= ZERO:

        raise ValueError(
            "Invalid daily balance."
        )

    return pnl <= -(start * DAILY_LIMIT)


# =====================================
# STOP LOSS AND TAKE PROFIT
# =====================================

def calculate_levels(entry, atr):

    with localcontext() as ctx:

        ctx.prec = 40

        entry = decimal_value(entry)

        atr = decimal_value(atr)

        if entry <= ZERO or atr <= ZERO:

            raise ValueError(
                "Invalid entry or ATR."
            )

        distance = max(
            atr * ATR_FACTOR,
            entry * MIN_STOP,
        )

        stop = entry - distance

        if stop <= ZERO:

            raise ValueError(
                "Invalid stop loss."
            )

        risk_per_unit = (
            distance
            + FEE * (entry + stop)
        )

        target = (
            entry * (ONE + FEE)
            + REWARD_RISK * risk_per_unit
        ) / (ONE - FEE)

        return {
            "stop": stop,
            "target": target,
            "stop_distance": distance,
            "risk_per_unit": risk_per_unit,
        }


# =====================================
# POSITION SIZE
# =====================================

def calculate_position(state, entry, atr):

    with localcontext() as ctx:

        ctx.prec = 40

        if state.get("position") is not None:

            return None

        if daily_loss_reached(state):

            return None

        entry = decimal_value(entry)

        balance = decimal_value(
            state["balance"]
        )

        if balance <= ZERO:

            return None

        equity = calculate_equity(
            state,
            entry,
        )

        levels = calculate_levels(
            entry,
            atr,
        )

        daily_remaining = (
            decimal_value(
                state["day_start_balance"]
            ) * DAILY_LIMIT
            + decimal_value(
                state["daily_realized_pnl"]
            )
        )

        risk_cash = min(
            equity * RISK,
            daily_remaining,
        )

        if risk_cash <= ZERO:

            return None

        qty_by_risk = (
            risk_cash
            / levels["risk_per_unit"]
        )

        max_cost = min(
            balance,
            equity * MAX_POSITION,
        )

        qty_by_balance = (
            max_cost
            / (entry * (ONE + FEE))
        )

        qty = quantity(
            min(
                qty_by_risk,
                qty_by_balance,
            )
        )

        if qty <= ZERO:

            return None

        purchase = calculate_buy(
            entry,
            qty,
        )

        if purchase["total_cost"] > max_cost:

            return None

        estimated_risk = (
            qty * levels["risk_per_unit"]
        )

        if estimated_risk > risk_cash:

            return None

        return {
            **purchase,

            "stop": levels["stop"],

            "target": levels["target"],

            "risk_cash": estimated_risk,

            "reward_risk": REWARD_RISK,

            "precision_version": "2.0",
        }


# =====================================
# EXIT CALCULATIONS
# =====================================

def calculate_exit(position, exit_price):

    return calculate_sell(
        position,
        exit_price,
    )
