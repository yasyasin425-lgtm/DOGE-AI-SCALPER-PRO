
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

# --------------------------------
# Page configuration
# --------------------------------

st.set_page_config(
    page_title="DOGE AI SCALPER PRO",
    page_icon="🐕",
    layout="wide",
)

st.title("🐕 DOGE AI SCALPER PRO")
st.caption("Binance Spot | DOGE/USDT | Paper Trading فقط")

st.warning(
    "هذه نسخة تجريبية فقط. لا تنفذ صفقات حقيقية. "
    "بيانات السوق العامة من Binance ولا تحتاج إلى API Key."
)

# --------------------------------
# Portfolio overview
# --------------------------------

try:
    state = load_state()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "الرصيد الافتراضي",
        f'{state["balance"]:.2f} USDT'
    )

    col2.metric(
        "الأرباح والخسائر",
        f'{state["realized_pnl"]:.4f} USDT'
    )

    col3.metric(
        "الصفقات المغلقة",
        str(len(state["trades"]))
    )

    col4.metric("الوضع", "محاكاة فقط")

except Exception as exc:
    st.error(f"خطأ في قراءة المحفظة: {exc}")
    st.stop()

st.divider()

# --------------------------------
# Main controls
# --------------------------------

left, right = st.columns(2)

with left:
    update_clicked = st.button(
        "تحديث البيانات وتحليل السوق",
        type="primary",
        use_container_width=True
    )

with right:
    reset_clicked = st.button(
        "إعادة ضبط المحفظة التجريبية",
        use_container_width=True
    )

if reset_clicked:
    reset_state()
    st.session_state.pop("last_snapshot", None)
    st.session_state.pop("last_result", None)
    st.success("تمت إعادة ضبط المحفظة التجريبية.")
    st.rerun()

# --------------------------------
# Fetch Binance market data
# --------------------------------

if update_clicked:

    with st.spinner("جاري تحليل DOGE/USDT من Binance..."):

        try:
            df1 = fetch_market("1m", 300)
            df5 = fetch_market("5m", 200)

            if df1 is None or df5 is None:
                st.error("لم تصل بيانات السوق.")
            
            elif len(df1) < 30 or len(df5) < 30:
                st.error("بيانات Binance غير كافية للتحليل.")

            else:
                snapshot = build_snapshot(df1, df5)

                result = run_paper_cycle(snapshot)

                st.session_state["last_snapshot"] = snapshot
                st.session_state["last_result"] = result

                st.success("اكتمل تحليل السوق بنجاح.")

        except Exception as exc:

            error_message = str(exc)

            if "451" in error_message:
                st.error(
                    "Binance رفضت الاتصال بالخطأ 451. "
                    "المشكلة في الوصول إلى الخدمة وليست في API Key."
                )

            elif "429" in error_message:
                st.error(
                    "طلبات كثيرة إلى Binance. انتظر قليلاً ثم أعد المحاولة."
                )

            else:
                st.error(
                    f"حدث خطأ: {type(exc).__name__}: {error_message}"
                )

# --------------------------------
# Market analysis
# --------------------------------

if "last_snapshot" in st.session_state:

    s = st.session_state["last_snapshot"]

    st.divider()
    st.subheader("📊 تحليل السوق")

    a, b, c, d = st.columns(4)

    a.metric(
        "السعر الحالي",
        f'{s["price"]:.7f} USDT'
    )

    b.metric(
        "RSI - دقيقة",
        f'{s["rsi"]:.2f}'
    )

    c.metric(
        "EMA 9",
        f'{s["ema9"]:.7f}'
    )

    d.metric(
        "EMA 21",
        f'{s["ema21"]:.7f}'
    )

    st.write(
        "**اتجاه 5 دقائق:**",
        s.get("trend_5m", "غير متاح")
    )

    st.divider()

    # Signal quality
    st.subheader("🎯 تقييم الإشارة")

    signal = s.get("signal", "HOLD")
    score = int(s.get("score", 0))
    score = max(0, min(score, 5))

    quality = s.get("quality", "غير متاح")

    x, y, z = st.columns(3)

    x.metric("الإشارة", signal)
    y.metric("قوة الإشارة", f"{score}/5")
    z.metric("جودة الإشارة", quality)

    st.progress(score / 5)

    # Signal conditions
    st.write("**تفاصيل الشروط الفنية:**")

    checks = s.get("checks", {})

    if checks:

        for name, passed in checks.items():

            if passed:
                st.success(f"✅ {name}")

            else:
                st.warning(f"❌ {name}")

    else:

        st.info(
            "تفاصيل تقييم الشروط غير متاحة. "
            "تحقق من تحديث build_snapshot في bot.py."
        )

    st.write("**سبب الإشارة:**")
    st.write(s.get("reason", "لا يوجد تفسير متاح."))

    # Paper trading decision
    st.divider()
    st.subheader("🤖 قرار المحاكاة")

    result = st.session_state.get("last_result", {})

    st.info(
        result.get("message", "لم يصدر قرار تجريبي بعد.")
    )

# --------------------------------
# Paper portfolio
# --------------------------------

st.divider()
st.subheader("💰 المحفظة التجريبية")

try:
    state = load_state()

    position = state.get("position")

    if position:

        st.info(
            f'صفقة مفتوحة افتراضياً: '
            f'{position["qty"]:.2f} DOGE '
            f'| سعر الدخول: {position["entry"]:.7f} USDT '
            f'| وقف الخسارة: {position["stop"]:.7f} '
            f'| الهدف: {position["target"]:.7f}'
        )

    else:

        st.write("لا توجد صفقة مفتوحة حالياً.")

except Exception as exc:

    st.error(f"تعذر تحميل المحفظة: {exc}")

# --------------------------------
# Trade history
# --------------------------------

st.divider()
st.subheader("📜 سجل الصفقات")

try:

    state = load_state()
    trades = state.get("trades", [])

    if trades:

        history = pd.DataFrame(trades)

        st.dataframe(
            history.iloc[::-1],
            use_container_width=True,
            hide_index=True
        )

    else:

        st.write("لم تُسجل صفقات مغلقة حتى الآن.")

except Exception as exc:

    st.error(f"تعذر عرض سجل الصفقات: {exc}")

# --------------------------------
# Settings
# --------------------------------

st.divider()

with st.expander("⚙️ إعدادات النسخة التجريبية"):

    st.write(f"رأس المال الابتدائي: {START_BALANCE:.2f} USDT")
    st.write("المخاطرة لكل صفقة: 0.5%")
    st.write("حد الخسارة اليومي: 2%")
    st.write("رسوم المحاكاة: 0.1% لكل جهة")
    st.write("إطار الدخول: دقيقة واحدة")
    st.write("تأكيد الاتجاه: 5 دقائق")
    st.write("التداول الحقيقي: غير مفعل")
    st.write("التعلم الآلي: غير مفعل حالياً")

st.caption(
    "DOGE AI SCALPER PRO | "
    + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
)
