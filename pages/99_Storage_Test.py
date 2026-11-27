
import streamlit as st
import storage

st.title("DOGE AI - Storage Test")

st.info("Read-only connection test")

if st.button("Test Supabase"):
    try:
        result = storage.test_connection()

        st.success("Supabase connected successfully")

        st.write(
            "Wallet verified:",
            abs(result["balance"] - 75.24457009867103)
            < 0.000001
        )

        st.write("Signals:", result["signals_count"])
        st.write("Closed trades:", result["closed_trades"])
        st.write("Open position:", result["open_position"])
        st.write("Writes enabled:", result["writes_enabled"])

    except Exception:
        st.error("Supabase connection failed")
