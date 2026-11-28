
"""
DOGE AI SCALPER PRO
Cloud Engine - Phase 2
PAPER TRADING ONLY
SAFE TEST MODE
"""

from storage import (
    load_state,
    load_signal_history,
    load_last_engine_candle,
    commit_engine_cycle,
)


def main():

    print("DOGE AI SCALPER PRO")
    print("MODE: SAFE TEST")

    state = load_state()
    history = load_signal_history()
    last_candle = load_last_engine_candle()

    print("Supabase connection: OK")
    print("Wallet loaded: OK")
    print("Signals:", len(history))
    print("Closed trades:", len(state["closed_trades"]))
    print("Open position:", bool(state["position"]))
    print("Last engine candle:", last_candle)

    try:

        commit_engine_cycle(
            candle_time=1,
            expected_state=state,
            new_state=state,
            signals=[],
            enable_write=False,
        )

    except RuntimeError as error:

        if str(error) != "Engine writes are disabled.":
            raise

        print("Write protection: OK")

    else:
        raise RuntimeError(
            "Write protection failed."
        )

    print("Writes enabled: False")
    print("Cloud engine phase 2: SUCCESS")


if __name__ == "__main__":
    main()
