
"""
DOGE AI SCALPER PRO
Financial Precision V1
PAPER TRADING ONLY
"""

from decimal import (
    Decimal,
    InvalidOperation,
    ROUND_HALF_EVEN,
    ROUND_DOWN,
    localcontext,
)

from config import FEE_RATE


ZERO = Decimal("0")

ONE = Decimal("1")

MONEY_PRECISION = Decimal("0.000000000001")

QTY_PRECISION = Decimal("0.00000001")


def decimal_value(value):

    if isinstance(value, bool):
        raise ValueError("Invalid financial value.")

    try:

        result = Decimal(str(value))

    except (InvalidOperation, ValueError):

        raise ValueError("Invalid decimal value.")

    if not result.is_finite():

        raise ValueError("Non-finite decimal value.")

    return result


def money(value):

    with localcontext() as ctx:

        ctx.prec = 40

        return decimal_value(value).quantize(
            MONEY_PRECISION,
            rounding=ROUND_HALF_EVEN,
        )


def quantity(value):

    with localcontext() as ctx:

        ctx.prec = 40

        result = decimal_value(value)

        if result < ZERO:
            raise ValueError("Negative quantity.")

        return result.quantize(
            QTY_PRECISION,
            rounding=ROUND_DOWN,
        )


def calculate_fee(amount):

    with localcontext() as ctx:

        ctx.prec = 40

        amount = decimal_value(amount)

        if amount < ZERO:
            raise ValueError("Negative amount.")

        return money(
            amount * decimal_value(FEE_RATE)
        )


def calculate_buy(entry, qty):

    with localcontext() as ctx:

        ctx.prec = 40

        entry = decimal_value(entry)

        qty = quantity(qty)

        if entry <= ZERO or qty <= ZERO:

            raise ValueError("Invalid buy values.")

        cost = money(entry * qty)

        fee = calculate_fee(cost)

        total_cost = money(cost + fee)

        return {
            "entry": entry,
            "qty": qty,
            "cost": cost,
            "entry_fee": fee,
            "total_cost": total_cost,
        }


def calculate_sell(position, exit_price):

    with localcontext() as ctx:

        ctx.prec = 40

        entry = decimal_value(
            position["entry"]
        )

        qty = decimal_value(
            position["qty"]
        )

        exit_price = decimal_value(
            exit_price
        )

        if min(entry, qty, exit_price) <= ZERO:

            raise ValueError("Invalid sell values.")

        entry_fee = decimal_value(
            position["entry_fee"]
        )

        if entry_fee < ZERO:

            raise ValueError("Invalid entry fee.")

        entry_cost = decimal_value(
            position.get(
                "total_cost",
                entry * qty + entry_fee,
            )
        )

        gross_value = money(
            exit_price * qty
        )

        exit_fee = calculate_fee(
            gross_value
        )

        proceeds = money(
            gross_value - exit_fee
        )

        gross_pnl = money(
            (exit_price - entry) * qty
        )

        net_pnl = money(
            proceeds - entry_cost
        )

        return {
            "gross_pnl": gross_pnl,
            "net_pnl": net_pnl,
            "entry_fee": entry_fee,
            "exit_fee": exit_fee,
            "proceeds": proceeds,
        }


def debit_balance(balance, amount):

    with localcontext() as ctx:

        ctx.prec = 50

        balance = decimal_value(balance)

        amount = decimal_value(amount)

        if balance < ZERO or amount < ZERO:

            raise ValueError("Invalid debit.")

        if amount > balance:

            raise RuntimeError(
                "Insufficient balance."
            )

        return balance - amount


def credit_balance(balance, amount):

    with localcontext() as ctx:

        ctx.prec = 50

        balance = decimal_value(balance)

        amount = decimal_value(amount)

        if balance < ZERO or amount < ZERO:

            raise ValueError("Invalid credit.")

        return balance + amount
