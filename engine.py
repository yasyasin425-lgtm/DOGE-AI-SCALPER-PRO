
"""
DOGE AI SCALPER PRO
Cloud Engine V3
Integrated Dry Run
PAPER TRADING ONLY
"""

from copy import deepcopy

from config import (
    PAPER_TRADING,
    LIVE_TRADING,
    ENGINE_ENABLED,
    ENABLE_DATABASE_WRITES,
)

from storage import (
    load_state,
    load_signal_history,
    load_last_engine_candle,
)

from strategy import analyze_market

from paper_engine import run_cycle

from learning import (
    evaluate_signals,
    learning_report,
)


def main():

    print("DOGE AI SCALPER PRO")
    print("Cloud Engine V3")
    print("MODE: DRY RUN")

    # =====================================
    # SAFETY CHECK
    # =====================================

    if not PAPER_TRADING or LIVE_TRADING:
        raise RuntimeError("Unsafe trading mode.")

    if ENGINE_ENABLED or ENABLE_DATABASE_WRITES:
        raise RuntimeError(
            "Dry run requires disabled writes."
        )

    print("Safety configuration: OK")

    # =====================================
    # LOAD CLOUD WALLET
    # =====================================

    state = load_state()

    history = load_signal_history()

    last_candle = load_last_engine_candle()

    original_state = deepcopy(state)

    original_history = deepcopy(history)

    print("Supabase connection: OK")
    print("Wallet loaded: OK")
    print("Signal history loaded: OK")

    # =====================================
    # MARKET ANALYSIS
    # =====================================

    snapshot, candles = analyze_market()

    candle_time = int(
        snapshot["candle_time"]
    )

    if (
        last_candle is not None
        and candle_time <= last_candle
    ):
        raise RuntimeError(
            "Candle already processed."
        )

    print("Binance market data: OK")
    print("Technical indicators: OK")
    print("Signal:", snapshot["signal"])
    print("Score:", snapshot["score"], "/ 5")

    # =====================================
    # SIMULATED TRADING CYCLE
    # =====================================

    result = run_cycle(
        state,
        snapshot,
        candles,
    )

    simulated_state = result["state"]

    decision = result["decision"]

    print("Risk management: OK")
    print("Paper engine: OK")
    print("Simulated action:", decision["action"])
    print("Decision reason:", decision["reason"])

    # =====================================
    # SIGNAL EVALUATION
    # =====================================

    combined = {
        int(item["candle_time"]): deepcopy(item)
        for item in history
    }

    for item in result["signals"]:

        key = int(item["candle_time"])

        if key not in combined:
            combined[key] = item

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
    print("Learning status:", report["status"])

    # =====================================
    # VERIFY NO CHANGES
    # =====================================

    if state != original_state:
        raise RuntimeError(
            "Original state modified."
        )

    if history != original_history:
        raise RuntimeError(
            "Original history modified."
        )

    if load_state() != original_state:
        raise RuntimeError(
            "Cloud wallet changed."
        )

    if load_signal_history() != original_history:
        raise RuntimeError(
            "Cloud history changed."
        )

    if load_last_engine_candle() != last_candle:
        raise RuntimeError(
            "Cloud checkpoint changed."
        )

    print("Original wallet unchanged: OK")
    print("Cloud history unchanged: OK")
    print("Engine checkpoint unchanged: OK")
    print("Database writes: DISABLED")
    print("Live trading: DISABLED")
    print("Cloud Engine V3: SUCCESS")


if __name__ == "__main__":
    main()
