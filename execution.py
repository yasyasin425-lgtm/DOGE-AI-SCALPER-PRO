
"""
DOGE AI SCALPER PRO
Execution Engine V1
Market Price Validation
PAPER TRADING ONLY
"""

import requests
import time

from decimal import Decimal
from datetime import datetime, timezone

from config import (
    SYMBOL,
    PAPER_TRADING,
    LIVE_TRADING,
    MAX_SIGNAL_AGE_SECONDS,
)

from money import decimal_value


TICKER_URL = (
    "https://data-api.binance.vision"
    "/api/v3/ticker/bookTicker"
)

MAX_REQUEST_SECONDS = 5

MAX_SPREAD_FRACTION = Decimal("0.001")

MAX_PRICE_DEVIATION = Decimal("0.002")


def fetch_execution_price():

    if not PAPER_TRADING or LIVE_TRADING:

        raise RuntimeError(
            "Unsafe execution mode."
        )

    started = time.monotonic()

    response = requests.get(
        TICKER_URL,
        params={"symbol": SYMBOL},
        timeout=MAX_REQUEST_SECONDS,
    )

    response.raise_for_status()

    elapsed = time.monotonic() - started

    if elapsed > MAX_REQUEST_SECONDS:

        raise RuntimeError(
            "Market response too slow."
        )

    data = response.json()

    if data.get("symbol") != SYMBOL:

        raise RuntimeError(
            "Unexpected market symbol."
        )

    bid = decimal_value(data["bidPrice"])

    ask = decimal_value(data["askPrice"])

    if bid <= 0 or ask <= 0 or ask < bid:

        raise RuntimeError(
            "Invalid market prices."
        )

    midpoint = (bid + ask) / 2

    spread = (ask - bid) / midpoint

    return {
        "symbol": SYMBOL,
        "bid": bid,
        "ask": ask,
        "midpoint": midpoint,
        "spread": spread,
        "observed_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "timestamp": int(time.time() * 1000),
        "response_seconds": elapsed,
    }


def validate_entry(snapshot, quote):

    if snapshot["signal"] != "BUY":

        return {
            "allowed": False,
            "reason": "No buy signal",
        }

    age = (
        int(time.time() * 1000)
        - int(snapshot["candle_time"])
    ) / 1000

    if age < 0 or age > MAX_SIGNAL_AGE_SECONDS:

        return {
            "allowed": False,
            "reason": "Stale signal",
        }

    quote_age = (
        int(time.time() * 1000)
        - int(quote["timestamp"])
    ) / 1000

    if quote_age < 0 or quote_age > 5:

        return {
            "allowed": False,
            "reason": "Stale market quote",
        }

    if quote["spread"] > MAX_SPREAD_FRACTION:

        return {
            "allowed": False,
            "reason": "Spread too wide",
        }

    signal_price = decimal_value(
        snapshot["price"]
    )

    if signal_price <= 0:

        raise RuntimeError(
            "Invalid signal price."
        )

    execution_price = quote["ask"]

    deviation = abs(
        execution_price - signal_price
    ) / signal_price

    if deviation > MAX_PRICE_DEVIATION:

        return {
            "allowed": False,
            "reason": "Price moved too far",
        }

    return {
        "allowed": True,
        "reason": "Execution validated",
        "entry_price": execution_price,
        "spread": quote["spread"],
        "deviation": deviation,
        "execution_timestamp": quote["timestamp"],
        "estimated_execution": True,
        "paper_trading": True,
    }
