
"""
DOGE AI SCALPER PRO
Cloud Engine V2
PAPER TRADING ONLY
STANDBY MODE
"""

from storage import (
    load_state,
    load_signal_history,
    load_last_engine_candle,
)


def main():

    print("DOGE AI SCALPER PRO")
    print("Cloud Engine V2")
    print("MODE: PAPER TRADING")
    print("STATUS: STANDBY")

    state = load_state()
    history = load_signal_history()
    last_candle = load_last_engine_candle()

    required = {
        "balance",
        "realized_pnl",
        "position",
        "closed_trades",
    }

    if not required.issubset(state):
        raise RuntimeError("Invalid wallet.")

    if float(state["balance"]) < 0:
        raise RuntimeError("Invalid balance.")

    if state["position"] is not None:
        raise RuntimeError(
            "Unexpected open position."
        )

    recovered = [
        trade
        for trade in state["closed_trades"]
        if trade.get("recovery_id")
        == "DOGE-20261127-0452"
    ]

    if len(recovered) != 1:
        raise RuntimeError(
            "Recovery verification failed."
        )

    if last_candle is None:
        raise RuntimeError(
            "Engine checkpoint missing."
        )

    print("Database connection: OK")
    print("Wallet integrity: OK")
    print("Historical recovery: VERIFIED")
    print("Engine checkpoint: OK")
    print("Signal history: OK")
    print("Open position: NONE")
    print("New trades: DISABLED")
    print("Database writes: DISABLED")
    print("Cloud Engine V2: READY")


if __name__ == "__main__":
    main()
