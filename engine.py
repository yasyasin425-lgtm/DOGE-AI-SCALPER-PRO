
"""
DOGE AI SCALPER PRO
Cloud Engine V4
Decimal Precision
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

from paper_engine import run_cycle

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
    ):

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


# =====================================
# PRECISION VALIDATION
# =====================================

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
# MAIN ENGINE
# =====================================

def main():

    print("DOGE AI SCALPER PRO")
    print("Cloud Engine V4")
    print("MODE: DRY RUN")
    print("PRECISION: DECIMAL")

    validate_safety()

    print("Safety configuration: OK")

    # Load original cloud data

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
    print("Wallet precision: OK")

    # Analyze Binance market

    snapshot, candles = analyze_market()

    candle_time = int(
        snapshot["candle_time"]
    )

    if (
        checkpoint is not None
        and candle_time <= checkpoint
    ):

        print("Candle already processed.")
        print("Database writes: DISABLED")

        return

    print("Binance market data: OK")
    print("Technical indicators: OK")
    print("Signal:", snapshot["signal"])
    print("Score:", snapshot["score"], "/ 5")

    # Simulate trading cycle

    result = run_cycle(
        state,
        snapshot,
        candles,
    )

    simulated_state = result["state"]

    decision = result["decision"]

    validate_wallet(simulated_state)

    validate_precision(simulated_state)

    if not isinstance(
        simulated_state["balance"],
        Decimal,
    ):

        raise RuntimeError(
            "Decimal balance required."
        )

    print("Risk management V2: OK")
    print("Paper Engine V2: OK")
    print("Financial precision: OK")
    print(
        "Simulated action:",
        decision["action"],
    )

    # Evaluate signal history

    combined = {
        int(item["candle_time"]):
            deepcopy(item)
        for item in history
    }

    for item in result["signals"]:

        key = int(item["candle_time"])

        if key not in combined:

            combined[key] = deepcopy(item)

    updated = evaluate_signals(
        list(combined.values()),
        candles,
    )

    for item in updated:

        combined[
            int(item["candle_time"])
        ] = item

    simulated_history = list(
        combined.values()
    )

    report = learning_report(
        simulated_state,
        simulated_history,
    )

    print("Signal evaluation: OK")
    print("Learning module: OK")
    print(
        "Learning status:",
        report["status"],
    )

    # Verify original data protection

    if state != original_state:

        raise RuntimeError(
            "Original wallet modified."
        )

    if history != original_history:

        raise RuntimeError(
            "Original history modified."
        )

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

    print("Original wallet unchanged: OK")
    print("Cloud history unchanged: OK")
    print("Engine checkpoint unchanged: OK")
    print("Database writes: DISABLED")
    print("Live trading: DISABLED")
    print("Cloud Engine V4: SUCCESS")


if __name__ == "__main__":

    main()
