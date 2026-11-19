import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from bot import fetch_market, build_snapshot, run_paper_cycle, load_state, reset_state, START_BALANCE

st.set_page_config(page_title="DOGE AI SCALPER PRO", page_icon="🐕", layout="wide")
st.title("🐕 DOGE AI SCALPER PRO")
st.caption("نسخة تجريبية — Paper Trading فقط | Binance Spot | DOGE/USDT")

state = load_state()
a,b,c,d = st.columns(4)
a.metric("الرصيد الافتراضي", f'{state["balance"]:.2f} USDT')
b.metric("الأرباح/الخسائر المحققة", f'{state["realized_pnl"]:.4f} USDT')
c.metric("الصفقات المغلقة", str(len(state["trades"])))
d.metric("الوضع", "محاكاة فقط")

st.warning("هذه النسخة لا تنفذ تداولاً حقيقياً. البيانات عامة، والنتائج الافتراضية لا تضمن أداءً مستقبلياً.")
left,right = st.columns([1,1])
with left:
    if st.button("تحديث البيانات وتحليل السوق", type="primary", use_container_width=True):
        with st.spinner("جاري جلب بيانات DOGE/USDT وتحليلها..."):
            try:
                df1 = fetch_market("1m", 300)
                df5 = fetch_market("5m", 200)
                snap = build_snapshot(df1, df5)
                result = run_paper_cycle(snap)
                st.session_state["last_snapshot"] = snap
                st.session_state["last_result"] = result
                st.success("اكتمل التحليل وتحديث المحاكاة.")
            except Exception as e:
                st.error(f"تعذر جلب البيانات: {e}")
with right:
    if st.button("إعادة ضبط المحفظة التجريبية", use_container_width=True):
        reset_state()
        st.session_state.pop("last_snapshot", None)
        st.session_state.pop("last_result", None)
        st.rerun()

if "last_snapshot" in st.session_state:
    s = st.session_state["last_snapshot"]
    st.subheader("قراءة السوق")
    x1,x2,x3,x4 = st.columns(4)
    x1.metric("السعر", f'{s["price"]:.6f} USDT')
    x2.metric("RSI (1m)", f'{s["rsi"]:.1f}')
    x3.metric("EMA 9 / EMA 21", f'{s["ema9"]:.6f} / {s["ema21"]:.6f}')
    x4.metric("اتجاه 5 دقائق", s["trend_5m"])
    st.write("**الإشارة:**", s["signal"], "—", s["reason"])
    st.write("**القرار التجريبي:**", st.session_state.get("last_result", {}).get("message","—"))

state = load_state()
st.subheader("المحفظة التجريبية")
if state["position"]:
    p = state["position"]
    st.info(f'صفقة مفتوحة افتراضياً: {p["qty"]:.2f} DOGE عند {p["entry"]:.6f} USDT | وقف: {p["stop"]:.6f} | هدف: {p["target"]:.6f}')
else:
    st.write("لا توجد صفقة مفتوحة حالياً.")

st.subheader("سجل الصفقات")
if state["trades"]:
    hist = pd.DataFrame(state["trades"])
    st.dataframe(hist.iloc[::-1], use_container_width=True, hide_index=True)
else:
    st.write("لم تُسجل صفقات بعد. اضغط زر تحديث البيانات لبدء المحاكاة.")
st.caption(f'آخر فتح للوحة: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}')

with st.expander("إعدادات النسخة التجريبية"):
    st.write("- رأس المال الابتدائي: 100 USDT")
    st.write("- مخاطرة الصفقة: 0.5% من الرصيد")
    st.write("- حد الخسارة اليومي: 2% من رصيد بداية اليوم")
    st.write("- رسوم محاكاة افتراضية: 0.1% لكل جهة (قابلة للتعديل في bot.py)")
    st.write("- الإطار: 1 دقيقة للدخول، و5 دقائق لتأكيد الاتجاه")
    st.write("- لا يوجد تعلم آلي ذاتي في هذه النسخة؛ سنجمع نتائج المحاكاة أولاً قبل إضافة نموذج مُدرّب.")
