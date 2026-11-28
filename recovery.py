

"""
DOGE AI SCALPER PRO
Historical Recovery V2
PAPER TRADING ONLY
READ ONLY MODE
"""

import requests

from datetime import datetime, timezone

from storage import (
    load_state,
    load_signal_history,
)

URL = "https://data-api.binance.vision/api/v3/klines"

SYMBOL = "DOGEUSDT"

FEE_RATE = 0.001

MINUTE = 60000


def fetch_candles(start, limit):

    response = requests.get(
        URL,
        params={
            "symbol": SYMBOL,
            "interval": "1m",
            "startTime": start,
            "limit": limit,
        },
        timeout=30,
    )

    response.raise_for_status()

    candles = response.json()

    if not isinstance(candles, list) or not candles:
        raise RuntimeError(
            "Historical data unavailable."
        )

    return candles


def main():

    print("DOGE AI SCALPER PRO")
    print("Historical Recovery V2")
    print("MODE: READ ONLY")

    state = load_state()

    position = state.get("position")

    if not position:
        raise RuntimeError("No open position.")

    history = load_signal_history()

    entry = float(position["entry"])
    stop = float(position["stop"])
    target = float(position["target"])
    qty = float(position["qty"])

    entry_fee = float(
        position.get(
            "entry_fee",
            entry * qty * FEE_RATE
        )
    )

    if not 0 < stop < entry < target or qty <= 0:
        raise RuntimeError("Invalid position.")

    matches = [
        item for item in history
        if item.get("signal") == "BUY"
        and abs(
            float(item["price"]) - entry
        ) < 0.000000001
    ]

    if len(matches) != 1:
        raise RuntimeError(
            "Entry time is uncertain."
        )

    recorded = datetime.fromisoformat(
        matches[0]["recorded_at"]
    )

    recorded_ms = int(
        recorded.timestamp() * 1000
    )

    entry_minute = (
        recorded_ms // MINUTE
    ) * MINUTE

    now = int(
        datetime.now(timezone.utc).timestamp()
        * 1000
    )

    print("Entry signal:", recorded.isoformat())

    # =====================================
    # VERIFY ENTRY CANDLE
    # =====================================

    rows = fetch_candles(entry_minute, 1)

    candle = rows[0]

    if int(candle[0]) != entry_minute:
        raise RuntimeError(
            "Entry candle unavailable."
        )

    if int(candle[6]) >= now:
        raise RuntimeError(
            "Entry candle is not closed."
        )

    entry_high = float(candle[2])
    entry_low = float(candle[3])

    print("Entry candle high:", entry_high)
    print("Entry candle low:", entry_low)

    if entry_low <= stop or entry_high >= target:

        print("Entry candle: UNCERTAIN")
        print("Detailed review required.")
        print("Wallet writes: DISABLED")

        return

    print("Entry candle: SAFE")

    # =====================================
    # HISTORICAL REPLAY
    # =====================================

    start = entry_minute + MINUTE

    expected = start

    checked = 0

    exit_price = None
    exit_reason = None
    exit_time = None

    while expected + MINUTE <= now:

        candles = fetch_candles(
            expected,
            1000
        )

        for candle in candles:

            candle_open_time = int(candle[0])
            candle_close_time = int(candle[6])

            if candle_open_time != expected:
                raise RuntimeError(
                    "Historical data gap."
                )

            if candle_close_time >= now:
                break

            expected += MINUTE

            checked += 1

            opening = float(candle[1])
            high = float(candle[2])
            low = float(candle[3])

            if opening <= stop:

                exit_reason = "STOP LOSS"
                exit_price = opening

            elif opening >= target:

                exit_reason = "TAKE PROFIT"
                exit_price = target

            elif low <= stop:

                exit_reason = "STOP LOSS"
                exit_price = stop

                if high >= target:
                    print(
                        "Both levels touched: "
                        "conservative stop applied."
                    )

            elif high >= target:

                exit_reason = "TAKE PROFIT"
                exit_price = target

            else:
                continue

            exit_time = datetime.fromtimestamp(
                candle_open_time / 1000,
                timezone.utc,
            ).isoformat()

            break

        if exit_price is not None:
            break

        if len(candles) < 1000:
            break

    print("Candles checked:", checked)

    if exit_price is None:

        print("No historical exit found.")
        print("Wallet writes: DISABLED")

        return

    # =====================================
    # FINANCIAL PREVIEW
    # =====================================

    gross_pnl = (
        exit_price - entry
    ) * qty

    exit_fee = (
        exit_price * qty * FEE_RATE
    )

    net_pnl = (
        gross_pnl
        - entry_fee
        - exit_fee
    )

    projected_balance = (
        float(state["balance"])
        + exit_price * qty
        - exit_fee
    )

    projected_realized_pnl = (
        float(state["realized_pnl"])
        + net_pnl
    )

    print("Historical exit:", exit_reason)
    print("Exit candle UTC:", exit_time)
    print("Estimated exit price:", exit_price)

    print(
        "Gross PNL:",
        round(gross_pnl, 8)
    )

    print(
        "Entry fee:",
        round(entry_fee, 8)
    )

    print(
        "Exit fee:",
        round(exit_fee, 8)
    )

    print(
        "Net PNL:",
        round(net_pnl, 8)
    )

    print(
        "Projected balance:",
        round(projected_balance, 8)
    )

    print(
        "Projected realized PNL:",
        round(projected_realized_pnl, 8)
    )

    print("Entry time inferred from signal.")
    print("Wallet writes: DISABLED")
    print("Historical Recovery V2: SUCCESS")


if __name__ == "__main__":
    main()
