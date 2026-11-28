
"""
DOGE AI SCALPER PRO
Cloud Engine - Phase 4
PAPER TRADING ONLY
ATOMIC STORAGE TEST
"""

from storage import (
    load_state,
    load_signal_history,
    load_last_engine_candle,
    commit_engine_cycle,
)


def main():

    print("DOGE AI SCALPER PRO")
    print("MODE: ATOMIC STORAGE TEST")

    state = load_state()
    history = load_signal_history()

    if load_last_engine_candle() is not None:
        raise RuntimeError(
            "Existing engine cycle detected."
        )

    result = commit_engine_cycle(
        candle_time=1,
        expected_state=state,
        new_state=state,
        signals=[],
        enable_write=True,
    )

    if result is not True:
        raise RuntimeError("Save test failed.")

    print("API atomic save: OK")

    duplicate = commit_engine_cycle(
        candle_time=1,
        expected_state=state,
        new_state=state,
        signals=[],
        enable_write=True,
    )

    if duplicate is not False:
        raise RuntimeError(
            "Duplicate protection failed."
        )

    print("Duplicate protection: OK")

    if load_state() != state:
        raise RuntimeError("Wallet changed.")

    if load_signal_history() != history:
        raise RuntimeError("Signals changed.")

    if load_last_engine_candle() != 1:
        raise RuntimeError("Cycle verification failed.")

    print("Wallet unchanged: OK")
    print("Signals unchanged: OK")
    print("Engine cycle saved: OK")
    print("Cloud engine phase 4: SUCCESS")


if __name__ == "__main__":
    main()
