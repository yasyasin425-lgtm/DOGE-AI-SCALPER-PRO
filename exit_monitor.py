
"""
DOGE AI SCALPER PRO
Exit Monitor V1
Market Exit Validation
PAPER TRADING ONLY
"""

import time

from config import (
    PAPER_TRADING,
    LIVE_TRADING,
    MAX_TRADE_MINUTES,
)

from money import (
    ZERO,
    decimal_value,
)

from execution import fetch_execution_price


MAX_QUOTE_AGE_MS = 5000


# =====================================
# SAFETY VALIDATION
# =====================================

def validate_mode():

    if not PAPER_TRADING or LIVE_TRADING:

        raise RuntimeError(
            "Unsafe exit monitoring mode."
        )


# =====================================
# EXIT DECISION
# =====================================

def evaluate_exit(
    position,
    quote,
    now_ms=None,
):

    validate_mode()

    if position is None:

        return {
            "action": "HOLD",
            "reason": "No open position",
        }

    if now_ms is None:

        now_ms = int(time.time() * 1000)

    quote_time = int(
        quote["timestamp"]
    )

    quote_age = now_ms - quote_time

    if (
        quote_age < 0
        or quote_age > MAX_QUOTE_AGE_MS
    ):

        return {
            "action": "HOLD",
            "reason": "Expired exit quote",
        }

    entry_time = position.get(
        "execution_timestamp"
    )

    if entry_time is None:

        raise RuntimeError(
            "Missing execution timestamp."
        )

    entry_time = int(entry_time)

    if quote_time < entry_time:

        raise RuntimeError(
            "Quote predates position."
        )

    bid = decimal_value(
        quote["bid"]
    )

    ask = decimal_value(
        quote["ask"]
    )

    stop = decimal_value(
        position["stop"]
    )

    target = decimal_value(
        position["target"]
    )

    entry = decimal_value(
        position["entry"]
    )

    if (
        bid <= ZERO
        or ask < bid
        or stop <= ZERO
        or stop >= entry
        or target <= entry
    ):

        raise RuntimeError(
            "Invalid exit prices."
        )

    elapsed_ms = (
        quote_time - entry_time
    )

    reason = None

    # Stop loss has priority

    if bid <= stop:

        reason = "وقف الخسارة"

    elif bid >= target:

        reason = "جني الأرباح"

    elif (
        elapsed_ms
        >= MAX_TRADE_MINUTES * 60000
    ):

        reason = "انتهاء مدة الصفقة"

    if reason is None:

        return {
            "action": "HOLD",
            "reason": "Position monitored",
            "current_bid": bid,
            "elapsed_ms": elapsed_ms,
        }

    return {
        "action": "SELL",
        "reason": reason,
        "exit_price": bid,
        "execution_timestamp": quote_time,
        "elapsed_ms": elapsed_ms,
        "estimated_execution": True,
        "paper_trading": True,
        "execution_version": "3.0",
    }


# =====================================
# LIVE MARKET MONITOR
# =====================================

def monitor_position(position):

    validate_mode()

    if position is None:

        return {
            "action": "HOLD",
            "reason": "No open position",
        }

    try:

        quote = fetch_execution_price()

    except Exception:

        return {
            "action": "HOLD",
            "reason": "Exit quote unavailable",
            "retry_required": True,
        }

    return evaluate_exit(
        position,
        quote,
    )
