
"""
DOGE AI SCALPER PRO
Trading Strategy V1
PAPER TRADING ONLY
"""

import math
import time
import requests
import pandas as pd
import numpy as np

from config import (
    SYMBOL,
    MARKET_URL,
    ENTRY_INTERVAL,
    TREND_INTERVAL,
    CANDLE_LIMIT,
    EMA_FAST,
    EMA_SLOW,
    RSI_PERIOD,
    RSI_MIN,
    RSI_MAX,
    MACD_FAST,
    MACD_SLOW,
    MACD_SIGNAL,
    ATR_PERIOD,
    VOLUME_PERIOD,
    VOLUME_MULTIPLIER,
    MIN_SIGNAL_SCORE,
    MAX_SIGNAL_AGE_SECONDS,
)


# =====================================
# MARKET DATA
# =====================================

def fetch_candles(interval):

    response = requests.get(
        MARKET_URL,
        params={
            "symbol": SYMBOL,
            "interval": interval,
            "limit": CANDLE_LIMIT,
        },
        timeout=20,
    )

    response.raise_for_status()

    raw = response.json()

    if not isinstance(raw, list) or not raw:
        raise RuntimeError("Invalid market data.")

    columns = [
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_volume",
        "trades",
        "taker_base",
        "taker_quote",
        "ignore",
    ]

    df = pd.DataFrame(
        raw,
        columns=columns,
    )

    numeric_columns = [
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
    ]

    for column in numeric_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df = df.dropna(
        subset=numeric_columns
    )

    now = int(time.time() * 1000)

    df = df[
        df["close_time"] < now
    ]

    df = df.sort_values(
        "open_time"
    ).drop_duplicates(
        "open_time"
    ).reset_index(drop=True)

    if len(df) < 60:
        raise RuntimeError(
            "Insufficient closed candles."
        )

    intervals = {
        "1m": 60000,
        "5m": 300000,
    }

    expected = intervals[interval]

    if not df["open_time"].diff().dropna().eq(
        expected
    ).all():
        raise RuntimeError("Market data gap.")

    values = df[numeric_columns].to_numpy()

    if not np.isfinite(values).all():
        raise RuntimeError("Invalid candle values.")

    if (df["low"] <= 0).any():
        raise RuntimeError("Invalid candle price.")

    if (df["volume"] < 0).any():
        raise RuntimeError("Invalid volume.")

    return df


# =====================================
# TECHNICAL INDICATORS
# =====================================

def add_indicators(df):

    df = df.copy()

    close = df["close"]

    df["ema_fast"] = close.ewm(
        span=EMA_FAST,
        adjust=False,
    ).mean()

    df["ema_slow"] = close.ewm(
        span=EMA_SLOW,
        adjust=False,
    ).mean()

    delta = close.diff()

    gain = delta.clip(lower=0)

    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / RSI_PERIOD,
        adjust=False,
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / RSI_PERIOD,
        adjust=False,
    ).mean()

    rs = avg_gain / avg_loss.replace(
        0,
        np.nan,
    )

    rsi = 100 - 100 / (1 + rs)

    rsi = rsi.mask(
        (avg_loss == 0) & (avg_gain > 0),
        100,
    )

    rsi = rsi.mask(
        (avg_loss == 0) & (avg_gain == 0),
        50,
    )

    df["rsi"] = rsi

    macd = (
        close.ewm(
            span=MACD_FAST,
            adjust=False,
        ).mean()
        -
        close.ewm(
            span=MACD_SLOW,
            adjust=False,
        ).mean()
    )

    signal_line = macd.ewm(
        span=MACD_SIGNAL,
        adjust=False,
    ).mean()

    df["macd_hist"] = (
        macd - signal_line
    )

    previous_close = close.shift(1)

    true_range = pd.concat(
        [
            df["high"] - df["low"],

            (
                df["high"] - previous_close
            ).abs(),

            (
                df["low"] - previous_close
            ).abs(),
        ],
        axis=1,
    ).max(axis=1)

    df["atr"] = true_range.rolling(
        ATR_PERIOD
    ).mean()

    df["volume_avg"] = df["volume"].shift(
        1
    ).rolling(
        VOLUME_PERIOD
    ).mean()

    return df


# =====================================
# SIGNAL GENERATION
# =====================================

def analyze_market():

    df1 = add_indicators(
        fetch_candles(ENTRY_INTERVAL)
    )

    df5 = add_indicators(
        fetch_candles(TREND_INTERVAL)
    )

    a = df1.iloc[-1]

    candle_time = int(a["close_time"])

    # Avoid using future trend data

    available_trend = df5[
        df5["close_time"] <= candle_time
    ]

    if available_trend.empty:
        raise RuntimeError(
            "Trend data unavailable."
        )

    b = available_trend.iloc[-1]

    age = (
        time.time()
        - candle_time / 1000
    )

    if age < 0 or age > MAX_SIGNAL_AGE_SECONDS:
        raise RuntimeError("Stale market signal.")

    trend_age = (
        candle_time - int(b["close_time"])
    )

    if trend_age >= 300000:
        raise RuntimeError("Stale trend data.")

    price = float(a["close"])

    atr = float(a["atr"])

    rsi = float(a["rsi"])

    indicators = [
        price,
        atr,
        rsi,
        float(a["ema_fast"]),
        float(a["ema_slow"]),
        float(a["macd_hist"]),
        float(a["volume_avg"]),
        float(b["ema_fast"]),
        float(b["ema_slow"]),
    ]

    if not all(
        math.isfinite(v) for v in indicators
    ):
        raise RuntimeError("Invalid indicators.")

    if price <= 0 or atr <= 0:
        raise RuntimeError("Invalid price or ATR.")

    if b["ema_fast"] > b["ema_slow"]:
        trend = "صاعد"

    elif b["ema_fast"] < b["ema_slow"]:
        trend = "هابط"

    else:
        trend = "عرضي"

    checks = {

        "اتجاه 5 دقائق صاعد":
            bool(trend == "صاعد"),

        "EMA 9 أعلى من EMA 21":
            bool(
                a["ema_fast"] > a["ema_slow"]
            ),

        "RSI مناسب":
            bool(RSI_MIN <= rsi <= RSI_MAX),

        "MACD إيجابي":
            bool(a["macd_hist"] > 0),

        "حجم التداول مناسب":
            bool(
                a["volume_avg"] > 0
                and a["volume"] >
                a["volume_avg"] * VOLUME_MULTIPLIER
            ),
    }

    score = sum(checks.values())

    if score == 5:
        quality = "قوية جداً"

    elif score == 4:
        quality = "قوية"

    elif score == 3:
        quality = "متوسطة"

    else:
        quality = "ضعيفة"

    signal = (
        "BUY"
        if score >= MIN_SIGNAL_SCORE
        else "HOLD"
    )

    snapshot = {
        "symbol": SYMBOL,
        "price": price,
        "atr": atr,
        "rsi": rsi,
        "ema9": float(a["ema_fast"]),
        "ema21": float(a["ema_slow"]),
        "macd_hist": float(a["macd_hist"]),
        "trend_5m": trend,
        "signal": signal,
        "score": int(score),
        "quality": quality,
        "checks": checks,
        "candle_time": candle_time,
        "signal_age_seconds": round(age, 2),
        "strategy_version": "1.0",
    }

    return snapshot, df1


# =====================================
# READ ONLY TEST
# =====================================

def main():

    snapshot, candles = analyze_market()

    print("DOGE AI SCALPER PRO")
    print("Strategy V1")
    print("Market:", SYMBOL)
    print("Price:", snapshot["price"])
    print("RSI:", round(snapshot["rsi"], 2))
    print("Trend:", snapshot["trend_5m"])
    print("Signal:", snapshot["signal"])
    print("Score:", snapshot["score"], "/ 5")
    print("Closed candles:", len(candles))
    print("Database writes: DISABLED")
    print("Strategy V1: SUCCESS")


if __name__ == "__main__":
    main()
