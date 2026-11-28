
"""
DOGE AI SCALPER PRO
Cloud Storage Precision Test
READ ONLY
"""

import simplejson

from decimal import Decimal

from storage import (
    load_state,
    load_state_exact,
    load_signal_history,
    load_last_engine_candle,
    commit_engine_cycle,
)


def main():

    print("Cloud Storage V3")
    print("MODE: READ ONLY")

    state = load_state_exact()

    history = load_signal_history(
        exact=True
    )

    checkpoint = load_last_engine_candle()

    print("Supabase connection: OK")

    balance = state["balance"]

    if not isinstance(balance, Decimal):

        raise RuntimeError(
            "Decimal precision unavailable."
        )

    if not balance.is_finite() or balance < 0:

        raise RuntimeError(
            "Invalid wallet balance."
        )

    print("Decimal balance: OK")

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
            "Precision loss detected."
        )

    print("Wallet JSON round-trip: OK")

    encoded_history = simplejson.dumps(
        history,
        use_decimal=True,
        allow_nan=False,
    )

    decoded_history = simplejson.loads(
        encoded_history,
        use_decimal=True,
    )

    if decoded_history != history:

        raise RuntimeError(
            "Signal precision loss detected."
        )

    print("Signal history precision: OK")

    standard_state = load_state()

    if float(balance) != float(
        standard_state["balance"]
    ):

        raise RuntimeError(
            "Dashboard compatibility failed."
        )

    print("Dashboard balance compatibility: OK")

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

        print("Database write protection: OK")

    else:

        raise RuntimeError(
            "Write protection failed."
        )

    if load_state_exact() != state:

        raise RuntimeError(
            "Wallet changed unexpectedly."
        )

    if load_signal_history(exact=True) != history:

        raise RuntimeError(
            "Signal history changed."
        )

    if load_last_engine_candle() != checkpoint:

        raise RuntimeError(
            "Checkpoint changed."
        )

    print("Original wallet unchanged: OK")
    print("Signal history unchanged: OK")
    print("Engine checkpoint unchanged: OK")
    print("Cloud Storage V3: SUCCESS")


if __name__ == "__main__":

    main()
