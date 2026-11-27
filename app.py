

import streamlit as st
import pandas as pd
import json
from datetime import datetime

from bot import (
    fetch_market,
    build_snapshot,
    run_paper_cycle,
    load_state,
    reset_state,
    load_signal_history,
    START_BALANCE,
)

st.set_page_config(
    page_title="DOGE AI SCALPER PRO",
    page_icon="🐕",
    layout="wide",
)

st.title("🐕 DOGE AI SCALPER PRO")
st.caption(
    "نسخة تجريبية — Paper Trading فقط | Binance Spot | DOGE/USDT"
)

st.warning(
    "هذه النسخة للمحاكاة والتحليل فقط. "
    "لا تنفذ أوامر شراء أو بيع حقيقية."
)

# -----------------------------
# أدوات التحكم
# -----------------------------

col1, col2 = st.columns(2)

with col1:
    update_button = st.button(
        "🔄 تحديث السوق والتحليل",
        use_container_width=True,
    )

with col2:
    reset_button = st.button(
        "♻️ إعادة ضبط المحفظة التجريبية",
        use_container_width=True,
    )

if reset_button:
    reset_state()
    st.success("تمت إعادة ضبط المحفظة التجريبية.")
    st.rerun()

st.divider()
st.subheader("💾 حفظ نسخة احتياطية من المحاكاة")
st.caption(
    "نزّل ملفات المحفظة وسجل الإشارات قبل نقل التشغيل. "
    "هذه الخطوة لا تغيّر الرصيد أو الصفقات."
)

backup_state = load_state()
backup_history = load_signal_history()

st.download_button(
    "⬇️ تنزيل نسخة المحفظة والصفقات",
    data=json.dumps(backup_state, ensure_ascii=False, indent=2),
    file_name="doge_paper_state.json",
    mime="application/json",
    use_container_width=True,
)

st.download_button(
    "⬇️ تنزيل سجل الإشارات",
    data=json.dumps(backup_history, ensure_ascii=False, indent=2),
    file_name="doge_signal_history.json",
    mime="application/json",
    use_container_width=True,
)

# -----------------------------
# جلب بيانات السوق
# -----------------------------

if update_button:
    st.cache_data.clear()

try:
    with st.spinner("جاري جلب بيانات Binance وتحليل السوق..."):
        df1 = fetch_market(interval="1m", limit=300)
        df5 = fetch_market(interval="5m", limit=200)

        snapshot = build_snapshot(df1, df5)

        # تسجيل الإشارة وتحديث نتائج الإشارات السابقة
        result = run_paper_cycle(snapshot, df1)

except Exception as e:
    st.error("تعذر جلب البيانات أو تحليل السوق.")
    st.code(str(e))
    st.info(
        "تحقق من اتصال الإنترنت ومن ملف bot.py "
        "ومن عنوان Binance العام المستخدم لجلب البيانات."
    )
    st.stop()

# -----------------------------
# المحفظة التجريبية
# -----------------------------

state = load_state()

balance = float(state.get("balance", START_BALANCE))
realized_pnl = float(state.get("realized_pnl", 0))
closed_trades = state.get("closed_trades", [])

st.divider()
st.subheader("💰 المحفظة التجريبية")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "الرصيد الحالي",
    f"{balance:.2f} USDT",
)

c2.metric(
    "الربح / الخسارة المحققة",
    f"{realized_pnl:.4f} USDT",
)

c3.metric(
    "الصفقات المغلقة",
    len(closed_trades),
)

c4.metric(
    "وضع التشغيل",
    "محاكاة فقط",
)

# -----------------------------
# تحليل السوق
# -----------------------------

st.divider()
st.subheader("📊 تحليل DOGE/USDT")

price = snapshot.get("price", 0)
rsi = snapshot.get("rsi", 0)
ema9 = snapshot.get("ema9", 0)
ema21 = snapshot.get("ema21", 0)
trend = snapshot.get("trend_5m", "غير محدد")
signal = snapshot.get("signal", "HOLD")
score = snapshot.get("score", 0)
quality = snapshot.get("quality", "غير محددة")
reason = snapshot.get("reason", "")

c1, c2, c3 = st.columns(3)

c1.metric(
    "السعر الحالي",
    f"{float(price):.6f} USDT",
)

c2.metric(
    "RSI 14",
    f"{float(rsi):.2f}",
)

c3.metric(
    "قوة الإشارة",
    f"{score}/5",
)

c4, c5, c6 = st.columns(3)

c4.metric("EMA 9", f"{float(ema9):.6f}")
c5.metric("EMA 21", f"{float(ema21):.6f}")
c6.metric("اتجاه 5 دقائق", str(trend))

if signal == "BUY":
    st.success(f"إشارة السوق: {signal} — جودة الإشارة: {quality}")
else:
    st.info(f"إشارة السوق: {signal} — جودة الإشارة: {quality}")

st.write("**سبب الإشارة:**", reason)

# -----------------------------
# شروط الاستراتيجية
# -----------------------------

st.divider()
st.subheader("🧠 فحص شروط الاستراتيجية")

checks = snapshot.get("checks", {})

if checks:
    for name, passed in checks.items():
        if passed:
            st.success(f"✅ {name}")
        else:
            st.warning(f"⏳ {name}")
else:
    st.info("لا توجد تفاصيل للشروط في بيانات التحليل.")

# -----------------------------
# نتيجة دورة المحاكاة
# -----------------------------

st.divider()
st.subheader("⚙️ نتيجة دورة التداول التجريبية")

if isinstance(result, dict):
    for key, value in result.items():
        st.write(f"**{key}:** {value}")
else:
    st.write(result)

# -----------------------------
# حالة الصفقة المفتوحة
# -----------------------------

st.divider()
st.subheader("📌 حالة الصفقة")

position = state.get("position")

if position:
    st.write("**الحالة:** توجد صفقة تجريبية مفتوحة")

    for key, value in position.items():
        st.write(f"**{key}:** {value}")
else:
    st.info("لا توجد صفقة تجريبية مفتوحة حالياً.")

# -----------------------------
# سجل الصفقات
# -----------------------------

st.divider()
st.subheader("📜 سجل الصفقات التجريبية")

state = load_state()
closed_trades = state.get("closed_trades", [])

if closed_trades:
    trades_df = pd.DataFrame(closed_trades)
    st.dataframe(
        trades_df.iloc[::-1],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("لم يتم إغلاق أي صفقة تجريبية حتى الآن.")

# -----------------------------
# سجل الإشارات والتقييم
# -----------------------------

st.divider()
st.subheader("🧠 سجل الإشارات ونتائجها")

try:
    history = load_signal_history()
except Exception as e:
    history = []
    st.warning(f"تعذر تحميل سجل الإشارات: {e}")

if history:
    evaluated = [
        item for item in history
        if item.get("evaluated")
    ]

    pending = [
        item for item in history
        if not item.get("evaluated")
    ]

    buy_evaluated = [
        item for item in evaluated
        if item.get("signal") == "BUY"
    ]

    buy_wins = [
        item for item in buy_evaluated
        if item.get("outcome") == "نجاح"
    ]

    win_rate = (
        len(buy_wins) / len(buy_evaluated) * 100
        if buy_evaluated else 0
    )

    a, b, c, d = st.columns(4)

    a.metric("إجمالي الإشارات", len(history))
    b.metric("الإشارات التي تم تقييمها", len(evaluated))
    c.metric("إشارات قيد الانتظار", len(pending))
    d.metric(
        "نسبة نجاح BUY",
        f"{win_rate:.1f}%" if buy_evaluated else "لا توجد بيانات",
    )

    st.caption(
        "نسبة النجاح محسوبة من إشارات BUY التي اكتمل تقييمها فقط، "
        "وليست نسبة ربح المحفظة."
    )

    display_rows = []

    for item in reversed(history):
        display_rows.append({
            "وقت التسجيل": item.get("recorded_at", ""),
            "الإشارة": item.get("signal", ""),
            "السعر وقت الإشارة": item.get("price", ""),
            "النتيجة بعد 5 دقائق": item.get("future_price", ""),
            "التغير %": item.get("return_pct", ""),
            "التقييم": item.get("outcome", "قيد الانتظار"),
            "تم التقييم": item.get("evaluated", False),
        })

    history_df = pd.DataFrame(display_rows)

    st.dataframe(
        history_df,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "يقيس هذا السجل حركة السعر بعد الإشارة بخمس دقائق. "
        "إنه سجل تقييم وتحليل، وليس تعلماً آلياً ذاتياً أو دليلاً "
        "على تنفيذ صفقة حقيقية."
    )

else:
    st.info(
        "لم تُسجل إشارات بعد. سيبدأ السجل بالظهور "
        "بعد تحديث السوق وتشغيل دورات المحاكاة."
    )

# -----------------------------
# معلومات النظام
# -----------------------------

st.divider()
st.subheader("⚙️ إعدادات النظام")

settings_col1, settings_col2 = st.columns(2)

with settings_col1:
    st.write("**المنصة:** Binance Spot")
    st.write("**الزوج:** DOGE/USDT")
    st.write("**الإطار الأساسي:** 1 دقيقة")
    st.write("**تأكيد الاتجاه:** 5 دقائق")

with settings_col2:
    st.write("**رأس المال الابتدائي:** 100 USDT")
    st.write("**المخاطرة:** محافظة")
    st.write("**الاستراتيجية:** EMA + RSI + MACD + ATR")
    st.write("**نوع التداول:** Paper Trading فقط")

st.caption(
    f"آخر تحديث للواجهة: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)
