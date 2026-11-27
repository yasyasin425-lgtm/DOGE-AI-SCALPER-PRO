
"""
DOGE AI SCALPER PRO
Automated paper-trading engine.
PAPER TRADING ONLY — NO REAL ORDERS.
"""

import json
import shutil
from pathlib import Path

from bot import (
    fetch_market,
    build_snapshot,
    run_paper_cycle,
    load_state,
    load_signal_history,
    save_state,
    STATE_FILE,
    SIGNAL_FILE,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

BACKUP_STATE = BASE_DIR / "doge_paper_state.json"
BACKUP_HISTORY = BASE_DIR / "doge_signal_history.json"


def restore_backups():
    """Restore existing backups without creating a new wallet."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    state_path = Path(STATE_FILE)
    signal_path = Path(SIGNAL_FILE)

    if not state_path.exists():
        if not BACKUP_STATE.exists():
            raise RuntimeError(
                "STOP: Portfolio backup is missing. "
                "No new wallet will be created."
            )

        shutil.copy2(BACKUP_STATE, state_path)

    if not signal_path.exists():
        if not BACKUP_HISTORY.exists():
            raise RuntimeError(
                "STOP: Signal-history backup is missing."
            )

        shutil.copy2(BACKUP_HISTORY, signal_path)

    # Validate both files before processing.
    with open(state_path, "r", encoding="utf-8") as f:
        state_data = json.load(f)

    with open(signal_path, "r", encoding="utf-8") as f:
        history_data = json.load(f)

    if not isinstance(state_data, dict):
        raise RuntimeError("Invalid portfolio backup.")

    if not isinstance(history_data, list):
        raise RuntimeError("Invalid signal-history backup.")

    required = {
        "balance",
        "realized_pnl",
        "position",
        "closed_trades",
    }

    if not required.issubset(state_data):
        raise RuntimeError(
            "Portfolio backup is incomplete. Stopping safely."
        )


def main():
    print("DOGE AI SCALPER PRO")
    print("MODE: PAPER TRADING ONLY")

    restore_backups()

    state = load_state()
    history = load_signal_history()

    print("Existing balance:", state["balance"])
    print("Existing closed trades:", len(state["closed_trades"]))
    print("Existing signals:", len(history))

    # Fetch both timeframes required by build_snapshot.
    df1 = fetch_market(interval="1m", limit=300)
    df5 = fetch_market(interval="5m", limit=300)

    if df1 is None or df5 is None:
        raise RuntimeError("Market data unavailable.")

    if df1.empty or df5.empty:
        raise RuntimeError("Empty market data.")

    # build_snapshot requires 1-minute and 5-minute data.
    snapshot = build_snapshot(df1, df5)

    candle_time = int(snapshot["candle_time"])

    # Prevent processing the same closed 1-minute candle twice.
    last_candle = state.get("last_engine_candle")

    if last_candle is not None and int(last_candle) == candle_time:
        print("This candle was already processed. Skipping.")
        return

    print("Price:", snapshot["price"])
    print("Signal:", snapshot["signal"])
    print("Score:", snapshot["score"])

    # Correct function signature: snapshot first, df1 second.
    result = run_paper_cycle(snapshot, df1)

    # Save the processed candle marker after the paper cycle.
    updated_state = load_state()
    updated_state["last_engine_candle"] = candle_time
    save_state(updated_state)

    print(result.get("message", "Paper cycle completed."))
    print("Updated balance:", updated_state["balance"])
    print("Paper cycle completed successfully.")


if __name__ == "__main__":
    main()

