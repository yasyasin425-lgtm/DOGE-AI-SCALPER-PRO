import json, os, requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone, date

SYMBOL = "DOGEUSDT"
BASE_URL = "https://api.binance.com/api/v3/klines"
START_BALANCE = 100.0
RISK_FRACTION = 0.005       # 0.5% risk per trade
DAILY_LOSS_LIMIT = 0.02     # 2% daily stop
FEE_RATE = 0.001            # illustrative 0.1% per side; adjust to your actual fee tier
STATE_FILE = os.path.join(os.path.dirname(__file__), "data", "paper_state.json")

def fetch_market(interval="1m", limit=300):
    r = requests.get(BASE_URL, params={"symbol": SYMBOL, "interval": interval, "limit": limit}, timeout=15)
    r.raise_for_status()
    raw = r.json()
    cols = ["open_time","open","high","low","close","volume","close_time","quote_volume","trades","taker_base","taker_quote","ignore"]
    df = pd.DataFrame(raw, columns=cols)
    for col in ["open","high","low","close","volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return add_indicators(df)

def add_indicators(df):
    df = df.copy()
    df["ema9"] = df.close.ewm(span=9, adjust=False).mean()
    df["ema21"] = df.close.ewm(span=21, adjust=False).mean()
    delta = df.close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi"] = (100 - (100/(1+rs))).fillna(50)
    fast = df.close.ewm(span=12, adjust=False).mean()
    slow = df.close.ewm(span=26, adjust=False).mean()
    macd = fast - slow
    df["macd_hist"] = macd - macd.ewm(span=9, adjust=False).mean()
    df["vol_avg"] = df.volume.rolling(20).mean()
    tr = pd.concat([(df.high-df.low), (df.high-df.close.shift()).abs(), (df.low-df.close.shift()).abs()], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean()
    return df

def build_snapshot(df1, df5):
    # Ignore the still-forming candle to reduce unstable signals.
    a = df1.iloc[-2]
    b = df5.iloc[-2]
    price = float(a.close)
    trend = "صاعد" if b.ema9 > b.ema21 else ("هابط" if b.ema9 < b.ema21 else "عرضي")
    vol_ok = pd.notna(a.vol_avg) and a.volume > a.vol_avg * 0.8
    momentum_ok = a.macd_hist > 0
    if trend == "صاعد" and a.ema9 > a.ema21 and 45 <= a.rsi <= 68 and momentum_ok and vol_ok:
        signal, reason = "BUY", "اتجاه 5m صاعد وتوافق EMA/RSI/MACD والحجم"
    else:
        signal, reason = "HOLD", "شروط الدخول المحافظة غير مكتملة"
    atr = float(a.atr) if pd.notna(a.atr) and a.atr > 0 else price * 0.003
    return {"price":price, "rsi":float(a.rsi), "ema9":float(a.ema9), "ema21":float(a.ema21),
            "trend_5m":trend, "signal":signal, "reason":reason, "atr":atr,
            "candle_time":int(a.close_time)}

def load_state():
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    if not os.path.exists(STATE_FILE):
        return {"balance":START_BALANCE,"realized_pnl":0.0,"position":None,"trades":[],"day":str(date.today()),"day_start_balance":START_BALANCE}
    with open(STATE_FILE,"r",encoding="utf-8") as f:
        return json.load(f)

def save_state(s):
    with open(STATE_FILE,"w",encoding="utf-8") as f:
        json.dump(s,f,ensure_ascii=False,indent=2)

def reset_state():
    s={"balance":START_BALANCE,"realized_pnl":0.0,"position":None,"trades":[],"day":str(date.today()),"day_start_balance":START_BALANCE}
    save_state(s)

def run_paper_cycle(snap):
    s=load_state()
    today=str(date.today())
    if s["day"] != today:
        s["day"]=today
        s["day_start_balance"]=s["balance"]
    # Daily loss circuit breaker
    if s["realized_pnl"] <= -(s["day_start_balance"]*DAILY_LOSS_LIMIT):
        save_state(s)
        return {"message":"توقف حماية: تم بلوغ حد الخسارة اليومي."}
    p=s["position"]
    price=snap["price"]
    if p:
        exit_reason=None
        if price <= p["stop"]: exit_reason="وقف الخسارة"
        elif price >= p["target"]: exit_reason="جني الأرباح"
        elif (snap["signal"]=="HOLD" and snap["trend_5m"]=="هابط"): exit_reason="انعكاس الاتجاه"
        if exit_reason:
            gross=(price-p["entry"])*p["qty"]
            fees=(p["entry"]*p["qty"]+price*p["qty"])*FEE_RATE
            pnl=gross-fees
            s["balance"] += p["qty"]*price - (p["qty"]*price*FEE_RATE)
            s["realized_pnl"] += pnl
            s["trades"].append({"وقت الإغلاق":datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "الدخول":round(p["entry"],7),"الخروج":round(price,7),"الكمية":round(p["qty"],2),
                "النتيجة USDT":round(pnl,5),"سبب الإغلاق":exit_reason})
            s["position"]=None
            save_state(s)
            return {"message":f"إغلاق افتراضي — {exit_reason} — النتيجة {pnl:.5f} USDT"}
        save_state(s)
        return {"message":"الاحتفاظ بالصفقة الافتراضية؛ لم يتحقق شرط الخروج."}
    if snap["signal"]!="BUY":
        save_state(s)
        return {"message":"لا دخول: الإشارة الحالية HOLD."}
    stop=max(snap["atr"]*1.2, price*0.0015)
    risk_cash=s["balance"]*RISK_FRACTION
    qty=risk_cash/stop
    # Limit position notional to 25% of available cash in conservative mode.
    qty=min(qty, (s["balance"]*0.25)/(price*(1+FEE_RATE)))
    cost=qty*price
    fee=cost*FEE_RATE
    if qty<=0 or cost+fee>s["balance"]:
        save_state(s)
        return {"message":"لم يتم الدخول: حجم الصفقة غير مناسب للرصيد."}
    target=price+stop*1.2
    s["balance"]-=cost+fee
    s["position"]={"entry":price,"qty":qty,"stop":price-stop,"target":target,"entry_fee":fee}
    save_state(s)
    return {"message":f"شراء افتراضي {qty:.2f} DOGE؛ وقف {price-stop:.6f} وهدف {target:.6f}."}
