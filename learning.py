
"""
DOGE AI SCALPER PRO
Learning System V1
PERFORMANCE ANALYSIS
PAPER TRADING ONLY
"""

import math

from copy import deepcopy
from datetime import datetime, timezone

from config import (
    FEE_RATE,
    LEARNING_ENABLED,
    AUTO_PARAMETER_UPDATES,
    MIN_LEARNING_TRADES,
    MIN_LEARNING_SIGNALS,
    SIGNAL_EVALUATION_MINUTES,
)


def evaluate_signals(history, candles):

    updated = []

    market = {}

    now = int(
        datetime.now(timezone.utc).timestamp()
        * 1000
    )

    for _, row in candles.iterrows():

        timestamp = int(row["close_time"])

        price = float(row["close"])

        if (
            timestamp < now
            and math.isfinite(price)
            and price > 0
        ):

            market[timestamp] = price

    for original in history:

        if original.get("evaluated", False):
            continue

        item = deepcopy(original)

        entry = float(item["price"])

        if not math.isfinite(entry) or entry <= 0:
            continue

        target_time = (
            int(item["candle_time"])
            + SIGNAL_EVALUATION_MINUTES * 60000
        )

        if target_time not in market:
            continue

        future_price = market[target_time]

        gross_return = (
            future_price - entry
        ) / entry

        net_return = (
            future_price * (1 - FEE_RATE)
            - entry * (1 + FEE_RATE)
        ) / (entry * (1 + FEE_RATE))

        if item["signal"] == "BUY":

            if net_return > 0:
                outcome = "نجاح"

            elif net_return < 0:
                outcome = "خسارة"

            else:
                outcome = "تعادل"

        elif item["signal"] == "HOLD":

            if net_return > 0:
                outcome = "فرصة فائتة"

            elif net_return < 0:
                outcome = "تجنب خسارة"

            else:
                outcome = "تعادل"

        else:
            continue

        item["evaluated"] = True

        item["future_price"] = future_price

        item["return_pct"] = round(
            gross_return * 100, 6
        )

        item["net_return_pct"] = round(
            net_return * 100, 6
        )

        item["outcome"] = outcome

        item["evaluation_version"] = "1.0"

        item["evaluated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        updated.append(item)

    return updated


# =====================================
# TRADE PERFORMANCE
# =====================================

def analyze_trades(state):

    trades = state.get("closed_trades", [])

    results = []

    for trade in trades:

        if "النتيجة USDT" not in trade:
            continue

        pnl = float(trade["النتيجة USDT"])

        if math.isfinite(pnl):
            results.append(pnl)

    wins = [p for p in results if p > 0]

    losses = [p for p in results if p < 0]

    total = len(results)

    gross_profit = sum(wins)

    gross_loss = abs(sum(losses))

    net_profit = sum(results)

    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else None
    )

    return {
        "total_trades": total,

        "winning_trades": len(wins),

        "losing_trades": len(losses),

        "breakeven_trades": (
            total - len(wins) - len(losses)
        ),

        "win_rate": (
            round(len(wins) / total * 100, 2)
            if total else 0.0
        ),

        "net_profit": round(net_profit, 8),

        "gross_profit": round(gross_profit, 8),

        "gross_loss": round(gross_loss, 8),

        "profit_factor": (
            round(profit_factor, 4)
            if profit_factor is not None
            else None
        ),

        "expectancy": (
            round(net_profit / total, 8)
            if total else 0.0
        ),
    }


# =====================================
# SIGNAL PERFORMANCE
# =====================================

def analyze_signals(history):

    evaluated = [
        item for item in history
        if item.get("evaluated") is True
        and item.get("evaluation_version") == "1.0"
    ]

    buys = [
        item for item in evaluated
        if item.get("signal") == "BUY"
    ]

    holds = [
        item for item in evaluated
        if item.get("signal") == "HOLD"
    ]

    successful = [
        item for item in buys
        if item.get("outcome") == "نجاح"
    ]

    missed = [
        item for item in holds
        if item.get("outcome") == "فرصة فائتة"
    ]

    avoided = [
        item for item in holds
        if item.get("outcome") == "تجنب خسارة"
    ]

    return {
        "total_signals": len(history),

        "evaluated_signals": len(evaluated),

        "buy_signals": len(buys),

        "hold_signals": len(holds),

        "successful_buy_signals": len(successful),

        "missed_opportunities": len(missed),

        "avoided_losses": len(avoided),

        "buy_success_rate": (
            round(
                len(successful) / len(buys) * 100,
                2
            )
            if buys else 0.0
        ),
    }


# =====================================
# INDICATOR ANALYSIS
# =====================================

def analyze_indicators(history):

    statistics = {}

    for item in history:

        if item.get("evaluated") is not True:
            continue

        if item.get("evaluation_version") != "1.0":
            continue

        net_return = item.get("net_return_pct")

        if net_return is None:
            continue

        net_return = float(net_return)

        if not math.isfinite(net_return):
            continue

        for name, passed in item.get(
            "checks", {}
        ).items():

            if name not in statistics:

                statistics[name] = {
                    "samples": 0,
                    "positive": 0,
                    "negative": 0,
                    "neutral": 0,
                }

            if passed is not True:
                continue

            data = statistics[name]

            data["samples"] += 1

            if net_return > 0:
                data["positive"] += 1

            elif net_return < 0:
                data["negative"] += 1

            else:
                data["neutral"] += 1

    for data in statistics.values():

        samples = data["samples"]

        data["success_rate"] = (
            round(
                data["positive"] / samples * 100,
                2
            )
            if samples else 0.0
        )

    return statistics


# =====================================
# LEARNING READINESS
# =====================================

def learning_report(state, history):

    trades = analyze_trades(state)

    signals = analyze_signals(history)

    indicators = analyze_indicators(history)

    eligible_trades = [
        trade
        for trade in state.get("closed_trades", [])
        if trade.get("strategy_version") == "1.0"
        and trade.get("paper_trading") is True
        and not trade.get("historical_recovery")
    ]

    trade_progress = min(
        len(eligible_trades)
        / MIN_LEARNING_TRADES,
        1.0,
    )

    signal_progress = min(
        signals["evaluated_signals"]
        / MIN_LEARNING_SIGNALS,
        1.0,
    )

    progress = min(
        trade_progress,
        signal_progress,
    )

    ready = (
        len(eligible_trades)
        >= MIN_LEARNING_TRADES
        and signals["evaluated_signals"]
        >= MIN_LEARNING_SIGNALS
    )

    if not ready:

        status = "COLLECTING_DATA"

    elif not LEARNING_ENABLED:

        status = "LEARNING_DISABLED"

    else:

        status = "READY_FOR_VALIDATION"

    return {
        "status": status,

        "learning_enabled": LEARNING_ENABLED,

        "auto_parameter_updates":
            AUTO_PARAMETER_UPDATES,

        "ready": ready,

        "progress_pct": round(
            progress * 100, 2
        ),

        "eligible_trades": len(eligible_trades),

        "required_trades": MIN_LEARNING_TRADES,

        "required_signals": MIN_LEARNING_SIGNALS,

        "trade_performance": trades,

        "signal_performance": signals,

        "indicator_statistics": indicators,

        "parameter_changes_applied": False,

        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }
