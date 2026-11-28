
import requests
from datetime import datetime, timezone
from storage import load_state, load_signal_history

URL = "https://data-api.binance.vision/api/v3/klines"


def main():

    state = load_state()
    position = state.get("position")

    if not position:
        raise RuntimeError("No open position.")

    history = load_signal_history()

    entry = float(position["entry"])
    stop = float(position["stop"])
    target = float(position["target"])

    matches = [
        item for item in history
        if item.get("signal") == "BUY"
        and abs(float(item["price"]) - entry) < 0.000000001
    ]

    if len(matches) != 1:
        raise RuntimeError("Entry time is uncertain.")

    match = matches[0]

    recorded = datetime.fromisoformat(
        match["recorded_at"]
    )

    recorded_ms = int(recorded.timestamp() * 1000)

    entry_minute = (recorded_ms // 60000) * 60000

check = requests.get(
    URL,
    params={
        "symbol": "DOGEUSDT",
        "interval": "1m",
        "startTime": entry_minute,
        "limit": 1
    },
    timeout=30
)

check.raise_for_status()
rows = check.json()

if not rows or int(rows[0][0]) != entry_minute:
    raise RuntimeError("Entry candle unavailable.")

c = rows[0]

print("Entry candle high:", c[2])
print("Entry candle low:", c[3])

if float(c[3]) > stop and float(c[2]) < target:
    print("Entry candle: SAFE")
else:
    raise RuntimeError("Entry minute needs detailed review.")

start = entry_minute + 60000

    response = requests.get(
        URL,
        params={
            "symbol": "DOGEUSDT",
            "interval": "1m",
            "startTime": start,
            "limit": 1000
        },
        timeout=30
    )

    response.raise_for_status()
    candles = response.json()

    if not isinstance(candles, list) or not candles:
        raise RuntimeError("No historical data.")

    expected = start
    now = int(datetime.now(timezone.utc).timestamp() * 1000)

    print("Historical recovery preview")
    print("Entry signal:", recorded.isoformat())

    for candle in candles:

        if int(candle[0]) != expected:
            raise RuntimeError("Historical data gap.")

        if int(candle[6]) >= now:
            break

        expected += 60000

        opening = float(candle[1])
        high = float(candle[2])
        low = float(candle[3])

        if opening <= stop:
            reason = "STOP LOSS"
            price = opening

        elif opening >= target:
            reason = "TAKE PROFIT"
            price = target

        elif low <= stop:
            reason = "STOP LOSS"
            price = stop

        elif high >= target:
            reason = "TAKE PROFIT"
            price = target

        else:
            continue

        print("Historical exit candidate:", reason)
        print("Estimated exit price:", price)
        print("Candle time:", datetime.fromtimestamp(
            int(candle[0]) / 1000,
            timezone.utc
        ).isoformat())

        print("Entry minute not verified")
        print("Wallet writes: DISABLED")
        return

    print("No exit found in downloaded candles.")
    print("Wallet writes: DISABLED")


if __name__ == "__main__":
    main()
