
"""
DOGE AI SCALPER PRO
Paper Engine V3
Execution Price Protection
PAPER TRADING ONLY
"""

import time

from copy import deepcopy
from datetime import datetime, timezone

from config import (
    MAX_SIGNAL_AGE_SECONDS,
    MAX_TRADE_MINUTES,
)

from money import (
    ZERO,
    decimal_value,
    debit_balance,
)

from risk import calculate_position

from paper_engine import (
    validate_mode,
    normalize_state,
    update_daily_state,
    build_signal,
    manage_position,
    close_position,
)


def run_cycle(
    original_state,
    snapshot,
    candles,
):

    validate_mode()

    state = normalize_state(
        original_state
    )

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

    now = int(time.time() * 1000)

    age = (now - candle_time) / 1000

    if age < 0 or age > MAX_SIGNAL_AGE_SECONDS:

        raise RuntimeError(
            "Stale trading snapshot."
        )

    execution = deepcopy(
        snapshot.get("execution", {})
    )

    signal = build_signal(snapshot)

    signal["execution"] = execution

    decision = {
        "action": "HOLD",
        "reason": "No entry signal",
    }

    # =================================
    # EXISTING POSITION
    # =================================

    if state.get("position") is not None:

        position = state["position"]

        opened_timestamp = position.get(
            "execution_timestamp"
        )

        if opened_timestamp is not None:

            opened_timestamp = int(
                opened_timestamp
            )

            last_checked = int(
                position["last_checked_candle"]
            )

            if candle_time > last_checked:

                decision = manage_position(
                    state,
                    candles,
                    candle_time,
                )

            else:

                decision = {
                    "action": "HOLD",
                    "reason": "Waiting for full candle",
                }

            # Maximum holding time

            if (
                state.get("position") is not None
                and now - opened_timestamp
                >= MAX_TRADE_MINUTES * 60000
            ):

                decision = {
                    "action": "HOLD",
                    "reason": "Fresh exit quote required",
                }

        else:

            decision = manage_position(
                state,
                candles,
                candle_time,
            )

    # =================================
    # NEW POSITION
    # =================================

    else:

        update_daily_state(
            state,
            now,
            price,
        )

        if snapshot["signal"] == "BUY":

            if execution.get("allowed") is not True:

                decision = {
                    "action": "HOLD",
                    "reason": execution.get(
                        "reason",
                        "Execution not validated",
                    ),
                }

            else:

                entry_price = decimal_value(
                    execution["entry_price"]
                )

                execution_time = int(
                    execution["execution_timestamp"]
                )

                quote_age = (
                    int(time.time() * 1000)
                    - execution_time
                )

                if (
                    quote_age < 0
                    or quote_age > 5000
                    or execution_time <= candle_time
                ):

                    decision = {
                        "action": "HOLD",
                        "reason": "Expired execution quote",
                    }

                else:

                    position = calculate_position(
                        state,
                        entry_price,
                        snapshot["atr"],
                    )

                    if position is None:

                        decision = {
                            "action": "HOLD",
                            "reason": "Risk protection",
                        }

                    else:

                        state["balance"] = debit_balance(
                            state["balance"],
                            position["total_cost"],
                        )

                        # Ignore the partial entry candle

                        entry_candle_end = (
                            (execution_time // 60000 + 1)
                            * 60000 - 1
                        )

                        position["entry_candle_time"] = (
                            entry_candle_end
                        )

                        position["last_checked_candle"] = (
                            entry_candle_end
                        )

                        position["signal_candle_time"] = (
                            candle_time
                        )

                        position["execution_timestamp"] = (
                            execution_time
                        )

                        position["opened_at"] = (
                            datetime.fromtimestamp(
                                execution_time / 1000,
                                timezone.utc,
                            ).isoformat()
                        )

                        position["strategy_version"] = (
                            snapshot.get(
                                "strategy_version",
                                "1.0",
                            )
                        )

                        position["execution_version"] = (
                            "3.0"
                        )

                        position["estimated_execution"] = (
                            True
                        )

                        position["entry_spread"] = (
                            decimal_value(
                                execution["spread"]
                            )
                        )

                        position["entry_deviation"] = (
                            decimal_value(
                                execution["deviation"]
                            )
                        )

                        state["position"] = position

                        decision = {
                            "action": "BUY",
                            "reason": "Validated market entry",
                        }

    update_daily_state(
        state,
        now,
        price,
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
