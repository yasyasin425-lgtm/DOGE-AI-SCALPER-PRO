
"""
DOGE AI SCALPER PRO
Cloud Engine V6
Integrated Execution Engine
DRY RUN - PAPER TRADING ONLY
"""

import simplejson

from copy import deepcopy
from decimal import Decimal

from config import (
    PAPER_TRADING,
    LIVE_TRADING,
    ENGINE_ENABLED,
    ENABLE_DATABASE_WRITES,
)

from storage import (
    load_state_exact,
    load_signal_history,
    load_last_engine_candle,
)

from strategy import analyze_market

from execution import (
    fetch_execution_price,
    validate_entry,
)

from paper_engine_v3 import (
    run_cycle,
    run_exit_cycle,
)

from learning import (
    evaluate_signals,
    learning_report,
)


# =====================================
# SAFETY CONFIGURATION
# =====================================

def validate_safety():

    if not PAPER_TRADING or LIVE_TRADING:

        raise RuntimeError(
            "Unsafe trading configuration."
        )

    if ENGINE_ENABLED or ENABLE_DATABASE_WRITES:

        raise RuntimeError(
            "Dry run requires disabled writes."
        )


# =====================================
# WALLET VALIDATION
# =====================================

def validate_wallet(state):

    required = {
        "balance",
        "realized_pnl",
        "position",
        "closed_trades",
        "day_start_balance",
        "daily_realized_pnl",
    }

    if not required.issubset(state):

        raise RuntimeError(
            "Incomplete wallet data."
        )

    balance = state["balance"]

    if not isinstance(
        balance, (Decimal, int)
    ) or isinstance(balance, bool):

        raise RuntimeError(
            "Exact balance required."
        )

    if not Decimal(balance).is_finite():

        raise RuntimeError(
            "Invalid wallet balance."
        )

    if balance < 0:

        raise RuntimeError(
            "Negative wallet balance."
        )

    if not isinstance(
        state["closed_trades"], list
    ):

        raise RuntimeError(
            "Invalid trade history."
        )


def validate_precision(state):

    encoded = simplejson.dumps(
        state,
        use_decimal=True,
        allow_nan=False,
    )

    decoded = simplejson.loads(
        encoded,
        use_decimal=True,
    )

    if decoded != state:

        raise RuntimeError(
            "Financial precision lost."
        )


# =====================================
# ENTRY EXECUTION
# =====================================

def prepare_execution(state, snapshot):

    prepared = deepcopy(snapshot)

    prepared["execution"] = {
        "allowed": False,
        "reason": "Entry not required",
    }

    if state.get("position") is not None:

        return prepared

    if snapshot["signal"] != "BUY":

        return prepared

    try:

        quote = fetch_execution_price()

        execution = validate_entry(
            snapshot,
            quote,
        )

    except Exception as error:

        execution = {
            "allowed": False,
            "reason": "Market quote unavailable",
        }

        print(
            "Execution protection:",
            type(error).__name__,
        )

    prepared["execution"] = execution

    if execution["allowed"]:

        print("Market quote: OK")
        print("Entry validation: PASSED")

    else:

        print(
            "Entry blocked:",
            execution["reason"],
        )

    return prepared


# =====================================
# SIGNAL EVALUATION
# =====================================

def process_learning(
    state,
    history,
    signals,
    candles,
):

    combined = {
        int(item["candle_time"]):
            deepcopy(item)
        for item in history
    }

    for item in signals:

        key = int(item["candle_time"])

        if key not in combined:

            combined[key] = deepcopy(item)

    eligible = [
        item
        for item in combined.values()
        if item.get("strategy_version") == "1.0"
    ]

    updated = evaluate_signals(
        eligible,
        candles,
    )

    for item in updated:

        combined[
            int(item["candle_time"])
        ] = item

    report = learning_report(
        state,
        list(combined.values()),
    )

    print("Signal evaluation: OK")
    print("Learning module: OK")

    print(
        "Learning status:",
        report["status"],
    )


# =====================================
# CLOUD DATA PROTECTION
# =====================================

def verify_cloud(
    original_state,
    original_history,
    checkpoint,
):

    if load_state_exact() != original_state:

        raise RuntimeError(
            "Cloud wallet changed."
        )

    if (
        load_signal_history(exact=True)
        != original_history
    ):

        raise RuntimeError(
            "Cloud history changed."
        )

    if load_last_engine_candle() != checkpoint:

        raise RuntimeError(
            "Cloud checkpoint changed."
        )

    print("Cloud wallet unchanged: OK")
    print("Cloud history unchanged: OK")
    print("Cloud checkpoint unchanged: OK")


# =====================================
# MAIN ENGINE
# =====================================

def main():

    print("DOGE AI SCALPER PRO")
    print("Cloud Engine V6")
    print("MODE: DRY RUN")
    print("PRECISION: DECIMAL")

    validate_safety()

    print("Safety configuration: OK")

    state = load_state_exact()

    history = load_signal_history(
        exact=True
    )

    checkpoint = load_last_engine_candle()

    validate_wallet(state)

    validate_precision(state)

    original_state = deepcopy(state)

    original_history = deepcopy(history)

    print("Supabase connection: OK")
    print("Exact wallet loaded: OK")

    # Existing positions have priority.
    # Exit monitoring does not require
    # a new market candle.

    if state.get("position") is not None:

        print("Position monitoring: ACTIVE")

        result = run_exit_cycle(
            state
        )

        simulated_state = result["state"]

        decision = result["decision"]

        print("Independent exit cycle: OK")

    else:

        snapshot, candles = analyze_market()

        candle_time = int(
            snapshot["candle_time"]
        )

        print("Binance market data: OK")
        print("Technical indicators: OK")

        print("Signal:", snapshot["signal"])

        print(
            "Score:",
            snapshot["score"],
            "/ 5",
        )

        if (
            checkpoint is not None
            and candle_time <= checkpoint
        ):

            simulated_state = deepcopy(state)

            decision = {
                "action": "HOLD",
                "reason": "Candle already processed",
            }

        else:

            prepared = prepare_execution(
                state,
                snapshot,
            )

            result = run_cycle(
                state,
                prepared,
                candles,
            )

            simulated_state = result["state"]

            decision = result["decision"]

            process_learning(
                simulated_state,
                history,
                result["signals"],
                candles,
            )

    validate_wallet(simulated_state)

    validate_precision(simulated_state)

    print("Risk management: OK")
    print("Financial precision: OK")
    print("Paper Engine V3.1: OK")

    print(
        "Simulated action:",
        decision["action"],
    )

    print(
        "Decision reason:",
        decision["reason"],
    )

    if state != original_state:

        raise RuntimeError(
            "Original wallet modified."
        )

    if history != original_history:

        raise RuntimeError(
            "Original history modified."
        )

    verify_cloud(
        original_state,
        original_history,
        checkpoint,
    )

    print("Database writes: DISABLED")
    print("Live trading: DISABLED")
    print("Cloud Engine V6: SUCCESS")


if __name__ == "__main__":

    main()
