


import json
import os
import math
import requests
import pandas as pd
import numpy as np

from datetime import datetime, timezone, date


# ==========================================
# 1. PROJECT SETTINGS
# ==========================================

SYMBOL = "DOGEUSDT"

BASE_URL = "https://data-api.binance.vision/api/v3/klines"

START_BALANCE = 100.0

RISK_FRACTION = 0.005
DAILY_LOSS_LIMIT = 0.02
FEE_RATE = 0.001

MAX_POSITION_FRACTION = 0.25

REWARD_RISK_RATIO = 1.5

MIN_STOP_FRACTION = 0.0015

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
# 2. JSON SAFE CONVERSION
# ==========================================

def json_safe(value):

    if isinstance(value, np.generic):
        return json_safe(value.item())

    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())

    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            json_safe(item)
            for item in value
        ]

    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()

    if value is pd.NA:
        return None

    if isinstance(value, float) and not math.isfinite(value):
        return None

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return str(value)


def save_json(path, data):

    os.makedirs(DATA_DIR, exist_ok=True)

    safe_data = json_safe(data)

    temp_path = path + ".tmp"

    with open(
        temp_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            safe_data,
            f,
            ensure_ascii=False,
            indent=2,
            allow_nan=False
        )

    os.replace(temp_path, path)


# ==========================================
# 3. BINANCE MARKET DATA
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
        headers={
            "User-Agent": "DOGE-AI-SCALPER-PRO"
        }
    )

    response.raise_for_status()

    raw = response.json()

    if not isinstance(raw, list) or not raw:
        raise ValueError(
            "Binance returned invalid market data."
        )

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

    df = pd.DataFrame(
        raw,
        columns=columns
    )

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
        subset=[
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time"
        ]
    )

    if len(df) < 30:
        raise ValueError(
            "Insufficient Binance candles."
        )

    return add_indicators(df)


# ==========================================
# 4. TECHNICAL INDICATORS
# ==========================================

def add_indicators(df):

    df = df.copy()

    # EMA 9
    df["ema9"] = df["close"].ewm(
        span=9,
        adjust=False
    ).mean()

    # EMA 21
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

    rs = gain / loss.replace(
        0,
        np.nan
    )

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

    df["macd_hist"] = (
        macd - signal_line
    )

    # Volume average
    df["vol_avg"] = df["volume"].rolling(
        window=20
    ).mean()

    # ATR 14
    tr = pd.concat(
        [
            df["high"] - df["low"],

            (
                df["high"] - df["close"].shift()
            ).abs(),

            (
                df["low"] - df["close"].shift()
            ).abs()
        ],
        axis=1
    ).max(axis=1)

    df["atr"] = tr.rolling(
        window=14
    ).mean()

    return df


# ==========================================
# 5. MARKET SNAPSHOT
# ==========================================

def build_snapshot(df1, df5):

    if len(df1) < 30 or len(df5) < 30:
        raise ValueError(
            "Not enough candles for analysis."
        )

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

        "اتجاه 5 دقائق صاعد":
            bool(trend == "صاعد"),

        "EMA 9 أعلى من EMA 21":
            bool(a["ema9"] > a["ema21"]),

        "RSI مناسب":
            bool(45 <= a["rsi"] <= 68),

        "MACD إيجابي":
            bool(a["macd_hist"] > 0),

        "حجم التداول مناسب":
            bool(
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

    signal = (
        "BUY"
        if score == 5
        else "HOLD"
    )

    passed = [
        name
        for name, ok in checks.items()
        if ok
    ]

    failed = [
        name
        for name, ok in checks.items()
        if not ok
    ]

    reason = (
        "الشروط المكتملة: " + "، ".join(passed)
        if passed
        else "لم يكتمل أي شرط"
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
# 6. POSITION TARGET CALCULATION
# ==========================================

def calculate_position_levels(
    entry,
    atr,
    reward_risk=REWARD_RISK_RATIO
):

    stop_distance = max(
        float(atr) * 1.2,
        float(entry) * MIN_STOP_FRACTION
    )

    stop = float(entry) - stop_distance

    # Estimated loss per DOGE including entry and exit fees
    risk_per_unit = (
        stop_distance
        + FEE_RATE * (float(entry) + stop)
    )

    # Target price that covers both fees and desired net reward
    target = (
        float(entry) * (1 + FEE_RATE)
        + reward_risk * risk_per_unit
    ) / (1 - FEE_RATE)

    return {
        "stop_distance": stop_distance,
        "stop": stop,
        "target": target,
        "risk_per_unit": risk_per_unit
    }


# ==========================================
# 7. PAPER PORTFOLIO
# ==========================================

def default_state():

    return {

        "balance": START_BALANCE,

        "realized_pnl": 0.0,

        "daily_realized_pnl": 0.0,

        "position": None,

        "trades": [],

        "closed_trades": [],

        "day": str(date.today()),

        "day_start_balance": START_BALANCE
    }


def load_state():

    os.makedirs(
        DATA_DIR,
        exist_ok=True
    )

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
            "تعذر قراءة ملف المحفظة التجريبية."
        )

    defaults = default_state()

    for key, value in defaults.items():
        state.setdefault(key, value)

    # Compatibility with older app.py and bot.py versions
    if not state["closed_trades"] and state["trades"]:

        state["closed_trades"] = state["trades"]

    if not state["trades"] and state["closed_trades"]:

        state["trades"] = state["closed_trades"]

    # Ensure old open positions have fee and updated target
    position = state.get("position")

    if position:

        entry = float(position["entry"])

        qty = float(position["qty"])

        position.setdefault(
            "entry_fee",
            entry * qty * FEE_RATE
        )

        levels = calculate_position_levels(
            entry,
            max(
                entry * MIN_STOP_FRACTION / 1.2,
                0.00000001
            )
        )

        # Preserve an existing stop when available
        if "stop" in position:

            position["stop"] = float(
                position["stop"]
            )

            stop_distance = (
                entry - position["stop"]
            )

            risk_per_unit = (
                stop_distance
                + FEE_RATE * (
                    entry + position["stop"]
                )
            )

            position["target"] = (
                entry * (1 + FEE_RATE)
                + REWARD_RISK_RATIO * risk_per_unit
            ) / (1 - FEE_RATE)

        else:

            position["stop"] = levels["stop"]

            position["target"] = levels["target"]

    return state


def save_state(state):

    # Keep both names synchronized for compatibility
    state["trades"] = state.get(
        "closed_trades",
        state.get("trades", [])
    )

    state["closed_trades"] = state["trades"]

    save_json(
        STATE_FILE,
        state
    )


def reset_state():

    state = default_state()

    save_state(state)


# ==========================================
# 8. SIGNAL HISTORY
# ==========================================

def load_signal_history():

    os.makedirs(
        DATA_DIR,
        exist_ok=True
    )

    if not os.path.exists(SIGNAL_FILE):
        return []

    try:

        with open(
            SIGNAL_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            history = json.load(f)

        return (
            history
            if isinstance(history, list)
            else []
        )

    except (json.JSONDecodeError, OSError):

        return []


def save_signal_history(history):

    save_json(
        SIGNAL_FILE,
        history
    )


def record_signal(snapshot):

    history = load_signal_history()

    candle_time = int(
        snapshot["candle_time"]
    )

    for item in history:

        if int(item["candle_time"]) == candle_time:
            return

    history.append({

        "candle_time": candle_time,

        "recorded_at": datetime.now(
            timezone.utc
        ).isoformat(timespec="seconds"),

        "signal": snapshot.get(
            "signal",
            "HOLD"
        ),

        "price": float(snapshot["price"]),

        "score": int(snapshot.get("score", 0)),

        "quality": snapshot.get(
            "quality",
            "غير متاح"
        ),

        "checks": json_safe(
            snapshot.get("checks", {})
        ),

        "evaluated": False,

        "outcome": None,

        "future_price": None,

        "return_pct": None
    })

    save_signal_history(history)


# ==========================================
# 9. SIGNAL EVALUATION
# ==========================================

def update_signal_outcomes(df1):

    if df1 is None or len(df1) == 0:
        return

    required = {
        "close_time",
        "close"
    }

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
        subset=[
            "_close_time",
            "_close"
        ]
    ).sort_values("_close_time")

    if market.empty:
        return

    history = load_signal_history()

    changed = False

    for item in history:

        if item.get("evaluated", False):
            continue

        entry_price = float(
            item["price"]
        )

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

        signal = item.get(
            "signal",
            "HOLD"
        )

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

        item["return_pct"] = round(
            return_pct,
            5
        )

        item["outcome"] = outcome

        item["evaluated_at"] = datetime.now(
            timezone.utc
        ).isoformat(timespec="seconds")

        changed = True

    if changed:
        save_signal_history(history)


# ==========================================
# 10. PAPER TRADING ENGINE
# ==========================================

def run_paper_cycle(snapshot, df1=None):

    record_signal(snapshot)

    if df1 is not None:
        update_signal_outcomes(df1)

    state = load_state()

    today = str(date.today())

    if state["day"] != today:

        state["day"] = today

        state["day_start_balance"] = state["balance"]

        state["daily_realized_pnl"] = 0.0

    daily_limit = (
        state["day_start_balance"]
        * DAILY_LOSS_LIMIT
    )

    if state["daily_realized_pnl"] <= -daily_limit:

        save_state(state)

        return {
            "message": (
                "توقف حماية: تم بلوغ حد الخسارة اليومي."
            )
        }

    position = state.get("position")

    price = float(
        snapshot["price"]
    )

    # --------------------------------------
    # MANAGE OPEN POSITION
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

            qty = float(
                position["qty"]
            )

            entry = float(
                position["entry"]
            )

            entry_fee = float(
                position.get(
                    "entry_fee",
                    entry * qty * FEE_RATE
                )
            )

            gross = (
                price - entry
            ) * qty

            exit_fee = (
                price * qty * FEE_RATE
            )

            pnl = (
                gross
                - entry_fee
                - exit_fee
            )

            # Return sale proceeds after exit fee
            state["balance"] += (
                price * qty - exit_fee
            )

            state["realized_pnl"] += pnl

            state["daily_realized_pnl"] += pnl

            trade = {

                "وقت الإغلاق": datetime.now(
                    timezone.utc
                ).isoformat(timespec="seconds"),

                "الدخول": round(
                    entry,
                    8
                ),

                "الخروج": round(
                    price,
                    8
                ),

                "الكمية": round(
                    qty,
                    4
                ),

                "رسوم الدخول": round(
                    entry_fee,
                    6
                ),

                "رسوم الخروج": round(
                    exit_fee,
                    6
                ),

                "النتيجة USDT": round(
                    pnl,
                    6
                ),

                "سبب الإغلاق": exit_reason
            }

            state["closed_trades"].append(
                trade
            )

            state["trades"] = state["closed_trades"]

            state["position"] = None

            save_state(state)

            return {
                "message": (
                    f"إغلاق افتراضي — {exit_reason} "
                    f"— صافي النتيجة {pnl:.6f} USDT"
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
    # CHECK ENTRY SIGNAL
    # --------------------------------------

    if snapshot["signal"] != "BUY":

        save_state(state)

        return {
            "message": (
                "لا دخول: الإشارة الحالية HOLD."
            )
        }

    # --------------------------------------
    # POSITION SIZING
    # --------------------------------------

    levels = calculate_position_levels(
        price,
        snapshot["atr"]
    )

    stop_distance = levels["stop_distance"]

    stop = levels["stop"]

    target = levels["target"]

    # Risk includes estimated entry and exit fees
    risk_cash = (
        state["balance"]
        * RISK_FRACTION
    )

    risk_per_unit = (
        stop_distance
        + FEE_RATE * (price + stop)
    )

    qty_by_risk = (
        risk_cash / risk_per_unit
    )

    max_position_value = (
        state["balance"]
        * MAX_POSITION_FRACTION
    )

    max_qty = (
        max_position_value
        / (price * (1 + FEE_RATE))
    )

    qty = min(
        qty_by_risk,
        max_qty
    )

    cost = qty * price

    entry_fee = cost * FEE_RATE

    if (
        qty <= 0
        or cost + entry_fee > state["balance"]
    ):

        save_state(state)

        return {
            "message": (
                "لم يتم الدخول: حجم الصفقة غير مناسب للرصيد."
            )
        }

    # --------------------------------------
    # OPEN PAPER POSITION
    # --------------------------------------

    state["balance"] -= (
        cost + entry_fee
    )

    state["position"] = {

        "entry": price,

        "qty": qty,

        "stop": stop,

        "target": target,

        "entry_fee": entry_fee,

        "reward_risk": REWARD_RISK_RATIO,

        "risk_cash": risk_cash

    }

    save_state(state)

    return {

        "message": (
            f"شراء افتراضي {qty:.4f} DOGE "
            f"بسعر {price:.8f}. "
            f"وقف الخسارة {stop:.8f}. "
            f"هدف الربح {target:.8f}. "
            f"العائد إلى المخاطرة {REWARD_RISK_RATIO}:1."
        )
    }

# ==========================================
# TEMPORARY MIGRATION PROTECTION
# ==========================================

def run_paper_cycle(snapshot, df1=None):
    return {
        "message": "التداول متوقف مؤقتاً أثناء نقل البيانات."
    }


def reset_state():
    raise RuntimeError(
        "إعادة ضبط المحفظة معطلة أثناء نقل البيانات."
    )
