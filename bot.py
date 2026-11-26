
import json
import os
import requests
import pandas as pd
import numpy as np

from datetime import datetime, timezone, date


# ==========================================
# 1. PROJECT SETTINGS
# ==========================================

SYMBOL = "DOGEUSDT"

BASE_URL = (
    "https://data-api.binance.vision/api/v3/klines"
)

START_BALANCE = 100.0

RISK_FRACTION = 0.005
DAILY_LOSS_LIMIT = 0.02
FEE_RATE = 0.001

MAX_POSITION_FRACTION = 0.25

DATA_DIR = os.path.join(
    os.path.dirname(__file__),
    "data"
)

STATE_FILE = os.path.join(
    DATA_DIR,
    "paper_state.json"
)

SIGNAL_FILE = os.path.join(
    DATA_DIR,
    "signal_history.json"
)


# ==========================================
# 2. BINANCE MARKET DATA
# ==========================================

def fetch_market(interval="1m", limit=300):

    params = {
        "symbol": SYMBOL,
        "interval": interval,
        "limit": limit
    }

    response = requests.get(
        BASE_URL,
        params=params,
        timeout=20,
        headers={"User-Agent": "DOGE-AI-SCALPER-PRO"}
    )

    response.raise_for_status()

    raw = response.json()

    if not isinstance(raw, list) or not raw:
        raise ValueError("Binance returned invalid market data.")

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
        "ignore"
    ]

    df = pd.DataFrame(raw, columns=columns)

    for col in [
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    df["close_time"] = pd.to_numeric(
        df["close_time"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["open", "high", "low", "close", "volume"]
    )

    if len(df) < 30:
        raise ValueError("Insufficient Binance candles.")

    return add_indicators(df)


# ==========================================
# 3. TECHNICAL INDICATORS
# ==========================================

def add_indicators(df):

    df = df.copy()

    # EMA 9 and EMA 21
    df["ema9"] = df["close"].ewm(
        span=9,
        adjust=False
    ).mean()

    df["ema21"] = df["close"].ewm(
        span=21,
        adjust=False
    ).mean()

    # RSI 14
    delta = df["close"].diff()

    gain = delta.clip(
        lower=0
    ).ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    loss = (-delta.clip(
        upper=0
    )).ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    rs = gain / loss.replace(0, np.nan)

    df["rsi"] = (
        100 - (100 / (1 + rs))
    ).fillna(50)

    # MACD
    fast = df["close"].ewm(
        span=12,
        adjust=False
    ).mean()

    slow = df["close"].ewm(
        span=26,
        adjust=False
    ).mean()

    macd = fast - slow

    signal_line = macd.ewm(
        span=9,
        adjust=False
    ).mean()

    df["macd_hist"] = macd - signal_line

    # Volume average
    df["vol_avg"] = df["volume"].rolling(
        window=20
    ).mean()

    # ATR 14
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - df["close"].shift()).abs(),
            (df["low"] - df["close"].shift()).abs()
        ],
        axis=1
    ).max(axis=1)

    df["atr"] = tr.rolling(
        window=14
    ).mean()

    return df


# ==========================================
# 4. MARKET SNAPSHOT AND SIGNAL SCORING
# ==========================================

def build_snapshot(df1, df5):

    if len(df1) < 30 or len(df5) < 30:
        raise ValueError("Not enough candles for analysis.")

    # Ignore unfinished candles
    a = df1.iloc[-2]
    b = df5.iloc[-2]

    price = float(a["close"])

    if b["ema9"] > b["ema21"]:
        trend = "صاعد"
    elif b["ema9"] < b["ema21"]:
        trend = "هابط"
    else:
        trend = "عرضي"

    checks = {
        "اتجاه 5 دقائق صاعد": trend == "صاعد",

        "EMA 9 أعلى من EMA 21":
            a["ema9"] > a["ema21"],

        "RSI مناسب":
            45 <= a["rsi"] <= 68,

        "MACD إيجابي":
            a["macd_hist"] > 0,

        "حجم التداول مناسب": (
            pd.notna(a["vol_avg"])
            and a["volume"] > a["vol_avg"] * 0.8
        )
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

    # Conservative entry rule
    signal = "BUY" if score == 5 else "HOLD"

    passed = [
        name for name, ok in checks.items()
        if ok
    ]

    failed = [
        name for name, ok in checks.items()
        if not ok
    ]

    reason = (
        "الشروط المكتملة: " + "، ".join(passed)
        if passed else "لم يكتمل أي شرط"
    )

    if failed:
        reason += (
            " | الشروط الناقصة: "
            + "، ".join(failed)
        )

    atr = (
        float(a["atr"])
        if pd.notna(a["atr"]) and a["atr"] > 0
        else price * 0.003
    )

    return {
        "price": price,
        "rsi": float(a["rsi"]),
        "ema9": float(a["ema9"]),
        "ema21": float(a["ema21"]),
        "trend_5m": trend,
        "signal": signal,
        "reason": reason,
        "atr": atr,
        "candle_time": int(a["close_time"]),
        "score": int(score),
        "quality": quality,
        "checks": checks
    }


# ==========================================
# 5. PAPER PORTFOLIO MANAGEMENT
# ==========================================

def default_state():

    return {
        "balance": START_BALANCE,
        "realized_pnl": 0.0,
        "daily_realized_pnl": 0.0,
        "position": None,
        "trades": [],
        "day": str(date.today()),
        "day_start_balance": START_BALANCE
    }


def load_state():

    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(STATE_FILE):
        return default_state()

    try:
        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            state = json.load(f)

    except (json.JSONDecodeError, OSError):
        raise RuntimeError(
            "تعذر قراءة ملف المحفظة التجريبية. "
            "لا تحذف الملف قبل فحصه."
        )

    defaults = default_state()

    for key, value in defaults.items():
        state.setdefault(key, value)

    return state


def save_state(state):

    os.makedirs(DATA_DIR, exist_ok=True)

    with open(
        STATE_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            state,
            f,
            ensure_ascii=False,
            indent=2
        )


def reset_state():

    state = default_state()
    save_state(state)


# ==========================================
# 6. SIGNAL HISTORY
# ==========================================

def load_signal_history():

    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(SIGNAL_FILE):
        return []

    try:
        with open(
            SIGNAL_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            history = json.load(f)

        return history if isinstance(history, list) else []

    except (json.JSONDecodeError, OSError):
        return []


def save_signal_history(history):

    os.makedirs(DATA_DIR, exist_ok=True)

    with open(
        SIGNAL_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            history,
            f,
            ensure_ascii=False,
            indent=2
        )


def record_signal(snapshot):

    history = load_signal_history()

    candle_time = int(snapshot["candle_time"])

    # Avoid duplicate signals for the same candle
    for item in history:

        if int(item["candle_time"]) == candle_time:
            return

    history.append({

        "candle_time": candle_time,

        "recorded_at": datetime.now(
            timezone.utc
        ).isoformat(timespec="seconds"),

        "signal": snapshot.get("signal", "HOLD"),

        "price": float(snapshot["price"]),

        "score": int(snapshot.get("score", 0)),

        "quality": snapshot.get(
            "quality",
            "غير متاح"
        ),

        "checks": snapshot.get("checks", {}),

        "evaluated": False,

        "outcome": None,

        "future_price": None,

        "return_pct": None

    })

    save_signal_history(history)


# ==========================================
# 7. EVALUATE SIGNALS AFTER FIVE MINUTES
# ==========================================

def update_signal_outcomes(df1):

    if df1 is None or len(df1) == 0:
        return

    required = {"close_time", "close"}

    if not required.issubset(df1.columns):
        return

    market = df1.copy()

    market["_close_time"] = pd.to_numeric(
        market["close_time"],
        errors="coerce"
    )

    market["_close"] = pd.to_numeric(
        market["close"],
        errors="coerce"
    )

    market = market.dropna(
        subset=["_close_time", "_close"]
    ).sort_values("_close_time")

    if market.empty:
        return

    history = load_signal_history()
    changed = False

    for item in history:

        if item.get("evaluated", False):
            continue

        entry_price = float(item["price"])

        # Five minutes after the signal candle
        target_time = (
            int(item["candle_time"])
            + 5 * 60 * 1000
        )

        future_rows = market[
            market["_close_time"] >= target_time
        ]

        if future_rows.empty:
            continue

        future_price = float(
            future_rows.iloc[0]["_close"]
        )

        return_pct = (
            (future_price - entry_price)
            / entry_price
        ) * 100

        signal = item.get("signal", "HOLD")

        if signal == "BUY":

            if return_pct > 0:
                outcome = "نجاح"
            elif return_pct < 0:
                outcome = "خسارة"
            else:
                outcome = "تعادل"

        else:

            if return_pct < 0:
                outcome = "تجنب خسارة"
            elif return_pct > 0:
                outcome = "فرصة فائتة"
            else:
                outcome = "تعادل"

        item["evaluated"] = True
        item["future_price"] = future_price
        item["return_pct"] = round(return_pct, 5)
        item["outcome"] = outcome

        item["evaluated_at"] = datetime.now(
            timezone.utc
        ).isoformat(timespec="seconds")

        changed = True

    if changed:
        save_signal_history(history)


# ==========================================
# 8. PAPER TRADING ENGINE
# ==========================================

def run_paper_cycle(snapshot, df1=None):

    # Save every new signal
    record_signal(snapshot)

    # Evaluate older signals when market data is supplied
    if df1 is not None:
        update_signal_outcomes(df1)

    state = load_state()

    today = str(date.today())

    # Reset daily tracking on a new day
    if state["day"] != today:

        state["day"] = today

        state["day_start_balance"] = state["balance"]

        state["daily_realized_pnl"] = 0.0

    # Daily loss protection
    daily_limit = (
        state["day_start_balance"]
        * DAILY_LOSS_LIMIT
    )

    if state["daily_realized_pnl"] <= -daily_limit:

        save_state(state)

        return {
            "message": "توقف حماية: تم بلوغ حد الخسارة اليومي."
        }

    position = state["position"]

    price = float(snapshot["price"])

    # --------------------------------------
    # Manage existing position
    # --------------------------------------

    if position:

        exit_reason = None

        if price <= position["stop"]:
            exit_reason = "وقف الخسارة"

        elif price >= position["target"]:
            exit_reason = "جني الأرباح"

        elif (
            snapshot["signal"] == "HOLD"
            and snapshot["trend_5m"] == "هابط"
        ):
            exit_reason = "انعكاس الاتجاه"

        if exit_reason:

            qty = position["qty"]
            entry = position["entry"]

            gross = (price - entry) * qty

            fees = (
                entry * qty + price * qty
            ) * FEE_RATE

            pnl = gross - fees

            # Return sale proceeds to virtual balance
            state["balance"] += (
                qty * price
                - qty * price * FEE_RATE
            )

            state["realized_pnl"] += pnl

            state["daily_realized_pnl"] += pnl

            state["trades"].append({

                "وقت الإغلاق": datetime.now(
                    timezone.utc
                ).isoformat(timespec="seconds"),

                "الدخول": round(entry, 7),

                "الخروج": round(price, 7),

                "الكمية": round(qty, 2),

                "النتيجة USDT": round(pnl, 5),

                "سبب الإغلاق": exit_reason

            })

            state["position"] = None

            save_state(state)

            return {
                "message": (
                    f"إغلاق افتراضي — {exit_reason} "
                    f"— النتيجة {pnl:.5f} USDT"
                )
            }

        save_state(state)

        return {
            "message": (
                "الاحتفاظ بالصفقة الافتراضية؛ "
                "لم يتحقق شرط الخروج."
            )
        }

    # --------------------------------------
    # Check entry signal
    # --------------------------------------

    if snapshot["signal"] != "BUY":

        save_state(state)

        return {
            "message": "لا دخول: الإشارة الحالية HOLD."
        }

    # --------------------------------------
    # Calculate conservative position size
    # --------------------------------------

    stop_distance = max(
        snapshot["atr"] * 1.2,
        price * 0.0015
    )

    risk_cash = (
        state["balance"] * RISK_FRACTION
    )

    qty = risk_cash / stop_distance

    max_position_value = (
        state["balance"] * MAX_POSITION_FRACTION
    )

    max_qty = (
        max_position_value
        / (price * (1 + FEE_RATE))
    )

    qty = min(qty, max_qty)

    cost = qty * price

    fee = cost * FEE_RATE

    if (
        qty <= 0
        or cost + fee > state["balance"]
    ):

        save_state(state)

        return {
            "message": (
                "لم يتم الدخول: حجم الصفقة غير مناسب للرصيد."
            )
        }

    target = price + stop_distance * 1.2

    # Deduct virtual purchase cost and fee
    state["balance"] -= cost + fee

    state["position"] = {

        "entry": price,

        "qty": qty,

        "stop": price - stop_distance,

        "target": target,

        "entry_fee": fee

    }

    save_state(state)

    return {
        "message": (
            f"شراء افتراضي {qty:.2f} DOGE؛ "
            f"وقف {price - stop_distance:.7f} "
            f"وهدف {target:.7f}."
        )
    }

