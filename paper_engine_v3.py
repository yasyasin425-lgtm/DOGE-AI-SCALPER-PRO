
"""
DOGE AI SCALPER PRO
Paper Engine V3.1
Integrated Entry and Exit Monitoring
PAPER TRADING ONLY
"""

import time

from copy import deepcopy
from datetime import datetime, timezone

from config import (
    MAX_SIGNAL_AGE_SECONDS,
)

from money import (
    ZERO,
    decimal_value,
    debit_balance,
)

from risk import calculate_position

from exit_monitor import monitor_position

from paper_engine import (
    validate_mode,
    normalize_state,
    update_daily_state,
    build_signal,
    close_position,
)


# =====================================
# OPEN POSITION
# =====================================

def open_position(state, snapshot, now):

    execution = snapshot.get(
        "execution", {}
    )

    if execution.get("allowed") is not True:

        return {
            "action": "HOLD",
            "reason": execution.get(
                "reason",
                "Execution not validated",
            ),
        }

    entry_price = decimal_value(
        execution["entry_price"]
    )

    execution_time = int(
        execution["execution_timestamp"]
    )

    candle_time = int(
        snapshot["candle_time"]
    )

    quote_age = now - execution_time

    if (
        quote_age < 0
        or quote_age > 5000
        or execution_time <= candle_time
    ):

        return {
            "action": "HOLD",
            "reason": "Expired entry quote",
        }

    update_daily_state(
        state,
        execution_time,
        entry_price,
    )

    position = calculate_position(
        state,
        entry_price,
        snapshot["atr"],
    )

    if position is None:

        return {
            "action": "HOLD",
            "reason": "Risk protection",
        }

    state["balance"] = debit_balance(
        state["balance"],
        position["total_cost"],
    )

    entry_candle_end = (
        (execution_time // 60000 + 1)
        * 60000 - 1
    )

    position.update({

        "entry_candle_time":
            entry_candle_end,

        "last_checked_candle":
            entry_candle_end,

        "signal_candle_time":
            candle_time,

        "execution_timestamp":
            execution_time,

        "opened_at":
            datetime.fromtimestamp(
                execution_time / 1000,
                timezone.utc,
            ).isoformat(),

        "strategy_version":
            snapshot.get(
                "strategy_version", "1.0"
            ),

        "execution_version": "3.1",

        "estimated_execution": True,

        "entry_spread":
            decimal_value(
                execution["spread"]
            ),

        "entry_deviation":
            decimal_value(
                execution["deviation"]
            ),
    })

    state["position"] = position

    return {
        "action": "BUY",
        "reason": "Validated market entry",
    }


# =====================================
# MONITOR EXISTING POSITION
# =====================================

def manage_open_position(state):

    position = state["position"]

    if "execution_timestamp" not in position:

        return {
            "action": "HOLD",
            "reason": "Legacy position requires review",
        }

    decision = monitor_position(
        position
    )

    if decision["action"] != "SELL":

        return decision

    exit_price = decimal_value(
        decision["exit_price"]
    )

    exit_time = int(
        decision["execution_timestamp"]
    )

    entry_time = int(
        position["execution_timestamp"]
    )

    if exit_time < entry_time:

        raise RuntimeError(
            "Invalid exit timestamp."
        )

    update_daily_state(
        state,
        exit_time,
        exit_price,
    )

    result = close_position(
        state,
        exit_price,
        decision["reason"],
        exit_time,
    )

    trade = state["closed_trades"][-1]

    trade.update({

        "entry_execution_timestamp":
            entry_time,

        "exit_execution_timestamp":
            exit_time,

        "holding_seconds":
            decimal_value(
                exit_time - entry_time
            ) / 1000,

        "execution_version": "3.1",

        "execution_source":
            "Observed Binance Bid",

        "estimated_execution": True,

        "paper_trading": True,
    })

    trade.pop("exit_candle_time", None)

    state["trades"] = deepcopy(
        state["closed_trades"]
    )

    return result


# =====================================
# MAIN TRADING CYCLE
# =====================================

def run_cycle(
    original_state,
    snapshot,
    candles,
):

    validate_mode()

    state = normalize_state(
        original_state
    )

    now = int(time.time() * 1000)

    candle_time = int(
        snapshot["candle_time"]
    )

    price = decimal_value(
        snapshot["price"]
    )

    if price <= ZERO:

        raise RuntimeError(
            "Invalid market price."
        )

    signal = build_signal(
        snapshot
    )

    signal["execution"] = deepcopy(
        snapshot.get("execution", {})
    )

    # Existing positions have priority

    if state.get("position") is not None:

        decision = manage_open_position(
            state
        )

    else:

        age = (
            now - candle_time
        ) / 1000

        if (
            age < 0
            or age > MAX_SIGNAL_AGE_SECONDS
        ):

            raise RuntimeError(
                "Stale trading snapshot."
            )

        update_daily_state(
            state,
            now,
            price,
        )

        decision = {
            "action": "HOLD",
            "reason": "No entry signal",
        }

        if snapshot["signal"] == "BUY":

            decision = open_position(
                state,
                snapshot,
                now,
            )

    if decimal_value(state["balance"]) < ZERO:

        raise RuntimeError(
            "Negative wallet balance."
        )

    signal["decision"] = deepcopy(
        decision
    )

    return {
        "state": state,
        "signals": [signal],
        "decision": decision,
        "candle_time": candle_time,
    }


# =====================================
# INDEPENDENT EXIT CYCLE
# =====================================

def run_exit_cycle(original_state):

    validate_mode()

    state = normalize_state(
        original_state
    )

    if state.get("position") is None:

        return {
            "state": state,
            "decision": {
                "action": "HOLD",
                "reason": "No open position",
            },
        }

    decision = manage_open_position(
        state
    )

    if decimal_value(state["balance"]) < ZERO:

        raise RuntimeError(
            "Negative wallet balance."
        )

    return {
        "state": state,
        "decision": decision,
    }
