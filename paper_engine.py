
"""
DOGE AI SCALPER PRO
Paper Trading Engine V1
SIMULATION ONLY
"""

import math

from copy import deepcopy
from datetime import datetime, timezone

from config import (
    PAPER_TRADING,
    LIVE_TRADING,
    MAX_TRADE_MINUTES,
    MAX_SIGNAL_AGE_SECONDS,
)

from risk import (
    calculate_equity,
    calculate_position,
    calculate_exit,
)


def utc_time(timestamp):

    return datetime.fromtimestamp(
        timestamp / 1000,
        timezone.utc,
    )


def validate_mode():

    if not PAPER_TRADING or LIVE_TRADING:

        raise RuntimeError(
            "Unsafe trading configuration."
        )


def update_daily_state(state, timestamp, price):

    today = utc_time(timestamp).date().isoformat()

    if state.get("day") != today:

        state["day"] = today

        state["day_start_balance"] = (
            calculate_equity(state, price)
        )

        state["daily_realized_pnl"] = 0.0


def build_signal(snapshot):

    return {
        "candle_time": int(snapshot["candle_time"]),

        "recorded_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "signal": snapshot["signal"],

        "price": float(snapshot["price"]),

        "score": int(snapshot["score"]),

        "quality": snapshot["quality"],

        "checks": snapshot["checks"],

        "strategy_version": snapshot.get(
            "strategy_version", "1.0"
        ),

        "evaluated": False,

        "outcome": None,

        "future_price": None,

        "return_pct": None,
    }


def close_position(
    state,
    exit_price,
    reason,
    candle_time,
):

    position = state["position"]

    result = calculate_exit(
        position,
        exit_price,
    )

    pnl = result["net_pnl"]

    state["balance"] += result["proceeds"]

    state["realized_pnl"] += pnl

    state["daily_realized_pnl"] += pnl

    trade = {
        "وقت الإغلاق": utc_time(
            candle_time
        ).isoformat(),

        "الدخول": float(position["entry"]),

        "الخروج": float(exit_price),

        "الكمية": round(
            float(position["qty"]), 4
        ),

        "رسوم الدخول": round(
            result["entry_fee"], 6
        ),

        "رسوم الخروج": round(
            result["exit_fee"], 6
        ),

        "النتيجة USDT": round(pnl, 6),

        "سبب الإغلاق": reason,

        "entry_candle_time": position[
            "entry_candle_time"
        ],

        "exit_candle_time": candle_time,

        "estimated_execution": True,

        "paper_trading": True,

        "strategy_version": position.get(
            "strategy_version", "1.0"
        ),
    }

    state["closed_trades"].append(trade)

    state["trades"] = deepcopy(
        state["closed_trades"]
    )

    state["position"] = None

    return {
        "action": "SELL",
        "reason": reason,
        "net_pnl": pnl,
    }


def manage_position(state, candles, candle_time):

    position = state["position"]

    entry_time = int(
        position["entry_candle_time"]
    )

    last_checked = int(
        position.get(
            "last_checked_candle",
            entry_time,
        )
    )

    if candle_time <= last_checked:

        return {
            "action": "HOLD",
            "reason": "Already checked",
        }

    rows = candles[
        (candles["close_time"] > last_checked)
        &
        (candles["close_time"] <= candle_time)
    ].sort_values("close_time")

    expected = last_checked + 60000

    stop = float(position["stop"])

    target = float(position["target"])

    for _, row in rows.iterrows():

        timestamp = int(row["close_time"])

        if timestamp != expected:

            raise RuntimeError(
                "Missing position history."
            )

        expected += 60000

        opening = float(row["open"])

        high = float(row["high"])

        low = float(row["low"])

        close = float(row["close"])

        update_daily_state(
            state,
            timestamp,
            opening,
        )

        if opening <= stop:

            return close_position(
                state,
                opening,
                "وقف الخسارة",
                timestamp,
            )

        if opening >= target:

            return close_position(
                state,
                target,
                "جني الأرباح",
                timestamp,
            )

        if low <= stop:

            return close_position(
                state,
                stop,
                "وقف الخسارة",
                timestamp,
            )

        if high >= target:

            return close_position(
                state,
                target,
                "جني الأرباح",
                timestamp,
            )

        elapsed = (
            timestamp - entry_time
        ) / 60000

        if elapsed >= MAX_TRADE_MINUTES:

            return close_position(
                state,
                close,
                "انتهاء مدة الصفقة",
                timestamp,
            )

        position["last_checked_candle"] = (
            timestamp
        )

    if expected != candle_time + 60000:

        raise RuntimeError(
            "Incomplete position history."
        )

    return {
        "action": "HOLD",
        "reason": "Position monitored",
    }


def run_cycle(
    original_state,
    snapshot,
    candles,
):

    validate_mode()

    state = deepcopy(original_state)

    candle_time = int(
        snapshot["candle_time"]
    )

    price = float(snapshot["price"])

    if not math.isfinite(price) or price <= 0:

        raise RuntimeError(
            "Invalid market price."
        )

    age = (
        datetime.now(timezone.utc).timestamp()
        - candle_time / 1000
    )

    if age < 0 or age > MAX_SIGNAL_AGE_SECONDS:

        raise RuntimeError(
            "Stale trading snapshot."
        )

    signal = build_signal(snapshot)

    if state.get("position") is not None:

        decision = manage_position(
            state,
            candles,
            candle_time,
        )

    else:

        update_daily_state(
            state,
            candle_time,
            price,
        )

        decision = {
            "action": "HOLD",
            "reason": "No entry signal",
        }

        if snapshot["signal"] == "BUY":

            position = calculate_position(
                state,
                price,
                snapshot["atr"],
            )

            if position is not None:

                state["balance"] -= position[
                    "total_cost"
                ]

                position["entry_candle_time"] = (
                    candle_time
                )

                position["last_checked_candle"] = (
                    candle_time
                )

                position["opened_at"] = utc_time(
                    candle_time
                ).isoformat()

                position["strategy_version"] = (
                    snapshot.get(
                        "strategy_version", "1.0"
                    )
                )

                state["position"] = position

                decision = {
                    "action": "BUY",
                    "reason": "Entry conditions met",
                }

            else:

                decision = {
                    "action": "HOLD",
                    "reason": "Risk protection",
                }

    update_daily_state(
        state,
        candle_time,
        price,
    )

    if not math.isfinite(state["balance"]):

        raise RuntimeError(
            "Invalid resulting balance."
        )

    if state["balance"] < 0:

        raise RuntimeError(
            "Negative wallet balance."
        )

    return {
        "state": state,
        "signals": [signal],
        "decision": decision,
        "candle_time": candle_time,
    }
