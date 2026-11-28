
"""
DOGE AI SCALPER PRO
Cloud Engine - Phase 3
PAPER TRADING ONLY
API PROTECTION TEST
"""

from storage import (
    load_state,
    load_signal_history,
    load_last_engine_candle,
    commit_engine_cycle,
)


def main():

    print("DOGE AI SCALPER PRO")
    print("MODE: API PROTECTION TEST")

    state = load_state()
    history = load_signal_history()
    last_candle = load_last_engine_candle()

    if last_candle is not None:
        raise RuntimeError(
            "Unexpected existing engine cycle."
        )

    print("Supabase connection: OK")
    print("Wallet loaded: OK")

    try:

        commit_engine_cycle(
            candle_time=1,
            expected_state={},
            new_state=state,
            signals=[],
            enable_write=True,
        )

    except RuntimeError as error:

        if "HTTP 400" not in str(error):
            raise

        if "P0001" not in str(error):
            raise

        print("API rejection: OK")

    else:
        raise RuntimeError(
            "Expected database rejection."
        )

    if load_state() != state:
        raise RuntimeError("Wallet changed.")

    if load_signal_history() != history:
        raise RuntimeError("Signals changed.")

    if load_last_engine_candle() != last_candle:
        raise RuntimeError("Engine cycle changed.")

    print("Wallet unchanged: OK")
    print("Signals unchanged: OK")
    print("Engine cycles unchanged: OK")
    print("Cloud engine phase 3: SUCCESS")


if __name__ == "__main__":
    main()
