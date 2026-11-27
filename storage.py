
import os
import requests

# ==========================================
# DOGE AI SCALPER PRO
# SUPABASE CLOUD STORAGE
# PAPER TRADING ONLY
# ==========================================


def get_secret(name):
    value = os.environ.get(name)

    if value:
        return value

    try:
        import streamlit as st
        return st.secrets.get(name)
    except Exception:
        return None


def get_config():
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise RuntimeError(
            "Supabase configuration is missing."
        )

    return url.rstrip("/"), key


def request_db(method, table, params=None,
               payload=None, prefer=None):

    url, key = get_config()

    headers = {
        "apikey": key,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    if not key.startswith("sb_secret_"):
        headers["Authorization"] = f"Bearer {key}"

    if prefer:
        headers["Prefer"] = prefer

    response = requests.request(
        method=method,
        url=f"{url}/rest/v1/{table}",
        headers=headers,
        params=params,
        json=payload,
        timeout=20
    )

    if not response.ok:
        raise RuntimeError(
            f"Supabase error: HTTP {response.status_code}"
        )

    if response.content:
        return response.json()

    return None


# ==========================================
# 1. LOAD WALLET
# ==========================================

def load_state():

    rows = request_db(
        "GET",
        "bot_state",
        params={
            "id": "eq.1",
            "select": "state"
        }
    )

    if not rows:
        raise RuntimeError(
            "Saved wallet not found. Reset blocked."
        )

    state = rows[0]["state"]

    if not isinstance(state, dict):
        raise RuntimeError("Invalid wallet data.")

    return state


# ==========================================
# 2. SAVE WALLET
# ==========================================

def save_state(state):

    raise RuntimeError(
        "Wallet writes disabled during migration."
    )


# ==========================================
# 3. LOAD SIGNAL HISTORY
# ==========================================

def load_signal_history():

    history = []
    offset = 0
    page_size = 500

    while True:

        rows = request_db(
            "GET",
            "signal_history",
            params={
                "select": "payload",
                "order": "candle_time.asc",
                "limit": page_size,
                "offset": offset
            }
        )

        if not rows:
            break

        history.extend(
            row["payload"] for row in rows
        )

        offset += len(rows)

    return history


# ==========================================
# 4. SAVE SIGNAL HISTORY
# ==========================================

def save_signal_history(history):

    raise RuntimeError(
        "Signal writes disabled during migration."
    )


# ==========================================
# 5. CONNECTION TEST
# ==========================================

def test_connection():

    state = load_state()
    signals = load_signal_history()

    return {
        "connected": True,
        "balance": state.get("balance"),
        "realized_pnl": state.get("realized_pnl"),
        "closed_trades": len(
            state.get("closed_trades", [])
        ),
        "open_position": bool(
            state.get("position")
        ),
        "signals_count": len(signals),
        "mode": "PAPER_TRADING",
        "writes_enabled": False
    }


# ==========================================
# 6. RESET PROTECTION
# ==========================================

def reset_state():

    raise RuntimeError(
        "Wallet reset is disabled."
    )
