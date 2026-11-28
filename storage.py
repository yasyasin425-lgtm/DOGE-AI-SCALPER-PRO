

"""
DOGE AI SCALPER PRO
Cloud Storage V3
Decimal Precision Protection
"""

import os
import requests
import simplejson

from decimal import Decimal


# =====================================
# CONFIGURATION
# =====================================

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

    key = get_secret(
        "SUPABASE_SERVICE_ROLE_KEY"
    )

    if not url or not key:

        raise RuntimeError(
            "Supabase configuration is missing."
        )

    return (
        url.strip().rstrip("/"),
        key.strip(),
    )


# =====================================
# DATABASE CONNECTION
# =====================================

def request_db(
    method,
    table,
    params=None,
    payload=None,
    prefer=None,
    exact=False,
):

    url, key = get_config()

    headers = {
        "apikey": key,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Accept-Profile": "public",
    }

    if not key.startswith("sb_secret_"):

        headers["Authorization"] = (
            f"Bearer {key}"
        )

    if prefer:

        headers["Prefer"] = prefer

    body = None

    if payload is not None:

        body = simplejson.dumps(
            payload,
            use_decimal=True,
            allow_nan=False,
        )

    response = requests.request(
        method=method,
        url=f"{url}/rest/v1/{table}",
        headers=headers,
        params=params,
        data=body,
        timeout=20,
    )

    if not response.ok:

        try:

            error = response.json()

            code = str(
                error.get("code", "UNKNOWN")
            )

            if not code.isalnum():
                code = "UNKNOWN"

        except Exception:

            code = "UNKNOWN"

        raise RuntimeError(
            f"Supabase HTTP {response.status_code}"
            f" | Error code: {code}"
        )

    if response.content:

        return simplejson.loads(
            response.text,
            use_decimal=exact,
        )

    return None


# =====================================
# WALLET STORAGE
# =====================================

def load_state(exact=False):

    rows = request_db(
        "GET",
        "bot_state",
        params={
            "id": "eq.1",
            "select": "state",
        },
        exact=exact,
    )

    if not rows:

        raise RuntimeError(
            "Saved wallet not found. Reset blocked."
        )

    state = rows[0]["state"]

    if not isinstance(state, dict):

        raise RuntimeError(
            "Invalid wallet data."
        )

    return state


def load_state_exact():

    return load_state(exact=True)


def save_state(state):

    raise RuntimeError(
        "Direct wallet writes are disabled."
    )


def reset_state():

    raise RuntimeError(
        "Wallet reset is disabled."
    )


# =====================================
# SIGNAL HISTORY
# =====================================

def load_signal_history(exact=False):

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
                "offset": offset,
            },
            exact=exact,
        )

        if not rows:
            break

        history.extend(
            row["payload"] for row in rows
        )

        offset += len(rows)

    return history


def save_signal_history(history):

    raise RuntimeError(
        "Direct signal writes are disabled."
    )


# =====================================
# ENGINE CHECKPOINT
# =====================================

def load_last_engine_candle():

    rows = request_db(
        "GET",
        "engine_cycles",
        params={
            "select": "candle_time",
            "order": "candle_time.desc",
            "limit": 1,
        },
    )

    if not rows:

        return None

    return int(
        rows[0]["candle_time"]
    )


# =====================================
# ATOMIC DATABASE COMMIT
# =====================================

def commit_engine_cycle(
    candle_time,
    expected_state,
    new_state,
    signals,
    *,
    enable_write=False,
):

    from config import (
        PAPER_TRADING,
        LIVE_TRADING,
        ENGINE_ENABLED,
        ENABLE_DATABASE_WRITES,
    )

    if (
        not PAPER_TRADING
        or LIVE_TRADING
        or not ENGINE_ENABLED
        or not ENABLE_DATABASE_WRITES
        or enable_write is not True
    ):

        raise RuntimeError(
            "Engine writes are disabled."
        )

    if not isinstance(expected_state, dict):

        raise RuntimeError(
            "Invalid expected wallet."
        )

    if not isinstance(new_state, dict):

        raise RuntimeError(
            "Invalid updated wallet."
        )

    if not isinstance(signals, list):

        raise RuntimeError(
            "Invalid signal history."
        )

    balance = Decimal(
        str(new_state["balance"])
    )

    if not balance.is_finite() or balance < 0:

        raise RuntimeError(
            "Invalid wallet balance."
        )

    payload = {
        "p_candle_time": int(candle_time),
        "p_expected_state": expected_state,
        "p_state": new_state,
        "p_signals": signals,
    }

    result = request_db(
        method="POST",
        table="rpc/commit_engine_cycle",
        payload=payload,
        exact=True,
    )

    if result is True:
        return True

    if result is False:
        return False

    raise RuntimeError(
        "Unexpected database response."
    )


# =====================================
# CONNECTION TEST
# =====================================

def test_connection():

    state = load_state()

    signals = load_signal_history()

    return {
        "connected": True,
        "balance": state.get("balance"),
        "realized_pnl": state.get(
            "realized_pnl"
        ),
        "closed_trades": len(
            state.get("closed_trades", [])
        ),
        "open_position": bool(
            state.get("position")
        ),
        "signals_count": len(signals),
        "mode": "PAPER_TRADING",
        "writes_enabled": False,
    }
