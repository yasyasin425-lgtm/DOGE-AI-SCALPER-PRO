
"""
DOGE AI SCALPER PRO
Cloud Engine - Phase 1
PAPER TRADING ONLY
READ ONLY MODE
"""

from storage import (
    load_state,
    load_signal_history,
    test_connection,
)


def main():
    print("DOGE AI SCALPER PRO")
    print("MODE: PAPER TRADING ONLY")
    print("ENGINE: CLOUD READ ONLY")

    result = test_connection()

    if not result["connected"]:
        raise RuntimeError("Database unavailable")

    state = load_state()
    history = load_signal_history()

    required = {
        "balance",
        "realized_pnl",
        "position",
        "closed_trades",
    }

    if not required.issubset(state):
        raise RuntimeError("Invalid wallet data")

    print("Supabase connection: OK")
    print("Wallet loaded: OK")
    print("Signals:", len(history))
    print("Closed trades:", len(state["closed_trades"]))
    print("Open position:", bool(state["position"]))
    print("Writes enabled: False")
    print("Cloud engine test successful")


if __name__ == "__main__":
    main()
