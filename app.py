
import streamlit as st
import pandas as pd
import json

from datetime import datetime, timezone

from storage import (
    load_state,
    load_signal_history,
)

from bot import (
    fetch_market,
    build_snapshot,
)

st.set_page_config(
    page_title="DOGE AI SCALPER PRO",
    page_icon="🐕",
    layout="wide",
)

st.title("🐕 DOGE AI SCALPER PRO")

st.caption(
    "Cloud Dashboard | Binance Spot | DOGE/USDT"
)

st.warning(
    "محاكاة فقط — لا توجد أوامر تداول حقيقية."
)

st.info(
    "المحرك في مرحلة التطوير. "
    "هذه الواجهة للمراقبة والقراءة فقط."
)

st.button(
    "🔄 تحديث البيانات",
    use_container_width=True,
)

# CLOUD STORAGE

try:
    state = load_state()
    history = load_signal_history()

    required = {
        "balance",
        "realized_pnl",
        "position",
        "closed_trades",
    }

    if not required.issubset(state):
        raise RuntimeError("Incomplete wallet")

    st.success("🟢 Supabase متصل")

except Exception:
    st.error("تعذر تحميل البيانات السحابية.")
    st.stop()

# WALLET

st.divider()
st.subheader("💰 المحفظة التجريبية")

balance = float(state["balance"])
pnl = float(state["realized_pnl"])
trades = state["closed_trades"]
position = state["position"]

a, b = st.columns(2)

a.metric(
    "الرصيد النقدي المتاح",
    f"{balance:.2f} USDT",
)

b.metric(
    "الأرباح المحققة",
    f"{pnl:.4f} USDT",
)

c, d = st.columns(2)

c.metric("الصفقات المغلقة", len(trades))
d.metric("وضع التشغيل", "محاكاة")

# MARKET ANALYSIS

st.divider()
st.subheader("📊 تحليل السوق")

snapshot = None

try:
    with st.spinner("جاري تحليل السوق..."):
        df1 = fetch_market(
            interval="1m",
            limit=300,
        )

        df5 = fetch_market(
            interval="5m",
            limit=300,
        )

        snapshot = build_snapshot(df1, df5)

except Exception:
    st.warning("بيانات السوق غير متاحة مؤقتاً.")

if snapshot:

    price = float(snapshot["price"])
    score = int(snapshot.get("score", 0))
    signal = snapshot.get("signal", "HOLD")

    a, b = st.columns(2)

    a.metric(
        "سعر آخر شمعة مغلقة",
        f"{price:.6f}",
    )

    b.metric(
        "RSI 14",
        f'{float(snapshot.get("rsi", 0)):.2f}',
    )

    c, d = st.columns(2)

    c.metric(
        "EMA 9",
        f'{float(snapshot.get("ema9", 0)):.6f}',
    )

    d.metric(
        "EMA 21",
        f'{float(snapshot.get("ema21", 0)):.6f}',
    )

    st.write(
        "اتجاه 5 دقائق:",
        snapshot.get("trend_5m", ""),
    )

    st.write(
        "جودة الإشارة:",
        snapshot.get("quality", ""),
    )

    st.progress(
        max(0.0, min(1.0, score / 5))
    )

    st.write(f"قوة الإشارة: {score}/5")

    if signal == "BUY":
        st.success("إشارة تحليلية: BUY")
    else:
        st.info(f"إشارة تحليلية: {signal}")

    st.caption(
        "الإشارة للعرض فقط ولا تنفذ صفقة."
    )

    st.write(snapshot.get("reason", ""))

    st.subheader("🧠 شروط الاستراتيجية")

    for name, passed in snapshot.get(
        "checks", {}
    ).items():

        if passed:
            st.success(f"✅ {name}")
        else:
            st.warning(f"⏳ {name}")

# OPEN POSITION

st.divider()
st.subheader("📌 الصفقة المفتوحة")

if position:

    st.warning(
        "صفقة تجريبية محفوظة من التشغيل السابق."
        " إدارتها متوقفة مؤقتاً."
    )

    for key, value in position.items():
        st.write(f"**{key}:** {value}")

    if snapshot:
        price = float(snapshot["price"])
        qty = float(position["qty"])
        entry = float(position["entry"])

        estimated_pnl = (
            (price - entry) * qty
            - float(position.get("entry_fee", 0))
            - price * qty * 0.001
        )

        st.metric(
            "الربح غير المحقق التقديري",
            f"{estimated_pnl:.4f} USDT",
        )

        st.caption(
            "تقدير بسعر آخر شمعة مغلقة "
            "ورسوم خروج افتراضية 0.1%."
        )

else:
    st.info("لا توجد صفقة مفتوحة.")

# TRADE HISTORY

st.divider()
st.subheader("📜 سجل الصفقات")

if trades:
    st.dataframe(
        pd.DataFrame(trades).iloc[::-1],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("لا توجد صفقات مغلقة.")

# SIGNAL ANALYTICS

st.divider()
st.subheader("🧠 تحليل أداء الإشارات")

evaluated = [
    x for x in history
    if x.get("evaluated")
]

buy_evaluated = [
    x for x in evaluated
    if x.get("signal") == "BUY"
]

wins = [
    x for x in buy_evaluated
    if x.get("outcome") == "نجاح"
]

a, b = st.columns(2)

a.metric("إجمالي الإشارات", len(history))
b.metric("الإشارات المقيمة", len(evaluated))

c, d = st.columns(2)

c.metric(
    "قيد الانتظار",
    len(history) - len(evaluated),
)

rate = (
    f"{len(wins) / len(buy_evaluated) * 100:.1f}%"
    if buy_evaluated
    else "لا توجد بيانات"
)

d.metric("نجاح إشارات BUY", rate)

st.caption(
    "هذه إحصائيات الإشارات المحفوظة، "
    "وليست نسبة نجاح الصفقات أو تعلماً ذاتياً."
)

if history:

    rows = []

    for item in reversed(history):
        rows.append({
            "وقت التسجيل": item.get("recorded_at"),
            "الإشارة": item.get("signal"),
            "السعر": item.get("price"),
            "القوة": item.get("score"),
            "السعر اللاحق": item.get("future_price"),
            "التغير %": item.get("return_pct"),
            "التقييم": (
                item.get("outcome")
                or "قيد الانتظار"
            ),
        })

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )

# BACKUPS

st.divider()

with st.expander("💾 النسخ الاحتياطية"):

    st.download_button(
        "تنزيل المحفظة",
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2,
        ),
        "doge_paper_state.json",
        "application/json",
    )

    st.download_button(
        "تنزيل سجل الإشارات",
        json.dumps(
            history,
            ensure_ascii=False,
            indent=2,
        ),
        "doge_signal_history.json",
        "application/json",
    )

# SYSTEM STATUS

st.divider()
st.subheader("⚙️ حالة النظام")

st.write("**المنصة:** Binance Spot")
st.write("**الزوج:** DOGE/USDT")
st.write("**رأس المال الابتدائي:** 100 USDT")
st.write("**المخاطرة:** محافظة")
st.write("**التخزين:** Supabase")
st.write("**الواجهة:** قراءة فقط")
st.write("**التداول التلقائي:** متوقف")
st.write("**التعلم الذاتي:** غير مفعل")
st.write("**إعادة ضبط المحفظة:** معطلة")

st.caption(
    "آخر تحديث للواجهة UTC: "
    + datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
)
