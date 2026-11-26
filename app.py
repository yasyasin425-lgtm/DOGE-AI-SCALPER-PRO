import streamlit as st
import pandas as pd
from datetime import datetime, timezone

from bot import (
    fetch_market,
    build_snapshot,
    run_paper_cycle,
    load_state,
    reset_state,
    START_BALANCE,
)

st.set_page_config(page_title="DOGE AI SCALPER PRO", page_icon="🐕", layout="wide")
st.title("🐕 DOGE AI SCALPER PRO")
st.caption("Binance Spot | DOGE/USDT | Paper Trading فقط")

st.warning(
    "هذه نسخة تجريبية لا تنفذ تداولاً حقيقياً. "
    "تجلب بيانات السوق العامة من Binance ولا تحتاج إلى API Key لجلب الشموع."
)

state = load_state()
a, b, c, d = st.columns(4)
a.metric("الرصيد الافتراضي", f'{state["balance"]:.2f} USDT')
b.metric("الأرباح/الخسائر المحققة", f'{state["realized_pnl"]:.4f} USDT')
c.metric("الصفقات المغلقة", str(len(state["trades"])))
d.metric("الوضع", "محاكاة فقط")

left, right = st.columns(2)

with left:
    if st.button("تحديث البيانات وتحليل السوق", type="primary", use_container_width=True):
        with st.spinner("جاري جلب بيانات DOGE/USDT من Binance..."):
            try:
                df1 = fetch_market("1m", 300)
                df5 = fetch_market("5m", 200)
                if df1 is None or df5 is None or len(df1) < 30 or len(df5) < 30:
                    st.error("وصلت بيانات غير كافية من Binance لإجراء التحليل.")
                else:
                    snap = build_snapshot(df1, df5)
                    result = run_paper_cycle(snap)
                    st.session_state["last_snapshot"] = snap
                    st.session_state["last_result"] = result
                    st.success("اكتمل تحليل السوق وتحديث المحاكاة.")
            except Exception as exc:
                message = str(exc)
                if "451" in message:
                    st.error(
                        "Binance أعادت الخطأ 451. هذا رفض وصول من جهة الخدمة/الخادم، "
                        "وليس بسبب عدم وجود API Key. لم يتم تنفيذ أي تداول."
                    )
                    st.info(
                        "أبقينا Binance كما طلبت. تغيير app.py وحده لا يزيل قيد 451؛ "
                        "سنفحص عنوان واجهة بيانات Binance واتصال خادم Streamlit في الخطوة التالية."
                    )
                else:
                    st.error(f"تعذر جلب البيانات أو تحليلها: {type(exc).__name__}: {message}")

with right:
    if st.button("إعادة ضبط المحفظة التجريبية", use_container_width=True):
        reset_state()
        st.session_state.pop("last_snapshot", None)
        st.session_state.pop("last_result", None)
        st.rerun()

if "last_snapshot" in st.session_state:
    s = st.session_state["last_snapshot"]
    st.subheader("قراءة السوق")
    x1, x2, x3, x4 = st.columns(4)
    x1.metric("السعر", f'{s["price"]:.7f} USDT')
    x2.metric("RSI (1m)", f'{s["rsi"]:.1f}')
    x3.metric("EMA 9 / EMA 21", f'{s["ema9"]:.7f} / {s["ema21"]:.7f}')
    x4.metric("اتجاه 5 دقائق", s["trend_5m"])
    st.write("**الإشارة:**", s["signal"], "—", s["reason"])
    st.write("**القرار التجريبي:**", st.session_state.get("last_result", {}).get("message", "—"))

state = load_state()
st.subheader("المحفظة التجريبية")
if state["position"]:
    p = state["position"]
    st.info(
        f'صفقة مفتوحة افتراضياً: {p["qty"]:.2f} DOGE عند {p["entry"]:.7f} USDT '
        f'| وقف: {p["stop"]:.7f} | هدف: {p["target"]:.7f}'
    )
else:
    st.write("لا توجد صفقة مفتوحة حالياً.")

st.subheader("سجل الصفقات")
if state["trades"]:
    st.dataframe(pd.DataFrame(state["trades"]).iloc[::-1], use_container_width=True, hide_index=True)
else:
    st.write("لم تُسجل صفقات بعد. اضغط زر تحديث البيانات لبدء المحاكاة.")

st.caption(f'آخر فتح للوحة: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}')

with st.expander("إعدادات النسخة التجريبية"):
    st.write(f"- رأس المال الابتدائي: {START_BALANCE:.2f} USDT")
    st.write("- مخاطرة الصفقة: 0.5% من الرصيد")
    st.write("- حد الخسارة اليومي: 2% من رصيد بداية اليوم")
    st.write("- رسوم المحاكاة: 0.1% لكل جهة (قابلة للتعديل في bot.py)")
    st.write("- الإطار: دقيقة للدخول و5 دقائق لتأكيد الاتجاه")
    st.write("- لا يوجد تعلم آلي ذاتي أو تداول حقيقي في هذه النسخة.")
