
"""
DOGE AI SCALPER PRO
Integrated Execution Safety Tests
PAPER TRADING ONLY
"""

import unittest
import pandas as pd

from copy import deepcopy
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import patch

from execution import validate_entry

from exit_monitor import evaluate_exit

from paper_engine_v3 import (
    run_cycle,
    run_exit_cycle,
)

from engine import prepare_execution


D = Decimal


class TestExecution(unittest.TestCase):

    def setUp(self):

        self.now = 1800000000000

        self.state = {
            "balance": D("100"),
            "realized_pnl": D("0"),
            "position": None,
            "closed_trades": [],
            "trades": [],
            "day": datetime.fromtimestamp(
                self.now / 1000,
                timezone.utc,
            ).date().isoformat(),
            "day_start_balance": D("100"),
            "daily_realized_pnl": D("0"),
        }

        self.snapshot = {
            "price": D("0.06"),
            "atr": D("0.0001"),
            "signal": "BUY",
            "score": 5,
            "quality": "Strong",
            "checks": {},
            "candle_time": self.now - 1000,
            "strategy_version": "1.0",
        }

        self.quote = {
            "symbol": "DOGEUSDT",
            "bid": D("0.05999"),
            "ask": D("0.06001"),
            "spread": D("0.000333333333"),
            "timestamp": self.now,
        }

    def validate(self, snapshot=None, quote=None):

        with patch(
            "execution.time.time",
            return_value=self.now / 1000,
        ):

            return validate_entry(
                snapshot or self.snapshot,
                quote or self.quote,
            )

    def open_position(self):

        snapshot = deepcopy(self.snapshot)

        snapshot["execution"] = self.validate()

        with patch(
            "paper_engine_v3.time.time",
            return_value=self.now / 1000,
        ):

            result = run_cycle(
                self.state,
                snapshot,
                pd.DataFrame(),
            )

        self.assertEqual(
            result["decision"]["action"],
            "BUY",
        )

        return result["state"]

    # =================================
    # ENTRY PROTECTION
    # =================================

    def test_01_valid_entry(self):

        result = self.validate()

        self.assertTrue(
            result["allowed"]
        )

        self.assertEqual(
            result["entry_price"],
            self.quote["ask"],
        )

    def test_02_wide_spread(self):

        quote = deepcopy(self.quote)

        quote["spread"] = D("0.005")

        result = self.validate(quote=quote)

        self.assertFalse(
            result["allowed"]
        )

    def test_03_price_deviation(self):

        quote = deepcopy(self.quote)

        quote["ask"] = D("0.065")

        result = self.validate(quote=quote)

        self.assertFalse(
            result["allowed"]
        )

    def test_04_stale_signal(self):

        snapshot = deepcopy(self.snapshot)

        snapshot["candle_time"] -= 600000

        result = self.validate(
            snapshot=snapshot
        )

        self.assertFalse(
            result["allowed"]
        )

    def test_05_stale_quote(self):

        quote = deepcopy(self.quote)

        quote["timestamp"] -= 10000

        result = self.validate(quote=quote)

        self.assertFalse(
            result["allowed"]
        )

    def test_06_hold_signal(self):

        snapshot = deepcopy(self.snapshot)

        snapshot["signal"] = "HOLD"

        result = self.validate(
            snapshot=snapshot
        )

        self.assertFalse(
            result["allowed"]
        )

    def test_07_market_entry_price(self):

        state = self.open_position()

        self.assertEqual(
            state["position"]["entry"],
            self.quote["ask"],
        )

        self.assertEqual(
            state["position"]["execution_timestamp"],
            self.now,
        )

    def test_08_unvalidated_entry(self):

        with patch(
            "paper_engine_v3.time.time",
            return_value=self.now / 1000,
        ):

            result = run_cycle(
                self.state,
                self.snapshot,
                pd.DataFrame(),
            )

        self.assertEqual(
            result["decision"]["action"],
            "HOLD",
        )

        self.assertIsNone(
            result["state"]["position"]
        )

    # =================================
    # EXIT PROTECTION
    # =================================

    def test_09_stop_loss(self):

        state = self.open_position()

        position = state["position"]

        quote = deepcopy(self.quote)

        quote["bid"] = position["stop"]

        result = evaluate_exit(
            position,
            quote,
            now_ms=self.now,
        )

        self.assertEqual(
            result["action"],
            "SELL",
        )

        self.assertEqual(
            result["reason"],
            "وقف الخسارة",
        )

    def test_10_take_profit(self):

        state = self.open_position()

        position = state["position"]

        quote = deepcopy(self.quote)

        quote["bid"] = position["target"]

        quote["ask"] = (
            quote["bid"] + D("0.00001")
        )

        result = evaluate_exit(
            position,
            quote,
            now_ms=self.now,
        )

        self.assertEqual(
            result["action"],
            "SELL",
        )

        self.assertEqual(
            result["reason"],
            "جني الأرباح",
        )

    def test_11_time_exit(self):

        state = self.open_position()

        position = state["position"]

        quote = deepcopy(self.quote)

        quote["timestamp"] += 300000

        result = evaluate_exit(
            position,
            quote,
            now_ms=self.now + 300000,
        )

        self.assertEqual(
            result["action"],
            "SELL",
        )

        self.assertEqual(
            result["reason"],
            "انتهاء مدة الصفقة",
        )

    def test_12_expired_exit_quote(self):

        state = self.open_position()

        result = evaluate_exit(
            state["position"],
            self.quote,
            now_ms=self.now + 10000,
        )

        self.assertEqual(
            result["action"],
            "HOLD",
        )

    def test_13_independent_exit(self):

        state = self.open_position()

        original = deepcopy(state)

        position = state["position"]

        decision = {
            "action": "SELL",
            "reason": "جني الأرباح",
            "exit_price": position["target"],
            "execution_timestamp":
                self.now + 30000,
        }

        with patch(
            "paper_engine_v3.monitor_position",
            return_value=decision,
        ):

            result = run_exit_cycle(state)

        self.assertEqual(
            result["decision"]["action"],
            "SELL",
        )

        self.assertIsNone(
            result["state"]["position"]
        )

        self.assertGreater(
            result["state"]["realized_pnl"],
            D("0"),
        )

        self.assertEqual(
            state,
            original,
        )

    def test_14_original_wallet_protection(self):

        original = deepcopy(self.state)

        self.open_position()

        self.assertEqual(
            self.state,
            original,
        )

    def test_15_quote_connection_failure(self):

        with patch(
            "engine.fetch_execution_price",
            side_effect=RuntimeError(
                "Connection unavailable"
            ),
        ):

            result = prepare_execution(
                self.state,
                self.snapshot,
            )

        self.assertFalse(
            result["execution"]["allowed"]
        )

    def test_16_no_open_position(self):

        result = run_exit_cycle(
            self.state
        )

        self.assertEqual(
            result["decision"]["action"],
            "HOLD",
        )

        self.assertEqual(
            result["state"],
            self.state,
        )

    def test_17_exact_wallet_accounting(self):

        state = self.open_position()

        decision = {
            "action": "SELL",
            "reason": "جني الأرباح",
            "exit_price":
                state["position"]["target"],
            "execution_timestamp":
                self.now + 60000,
        }

        with patch(
            "paper_engine_v3.monitor_position",
            return_value=decision,
        ):

            result = run_exit_cycle(state)

        final_state = result["state"]

        self.assertEqual(
            final_state["balance"],
            D("100")
            + final_state["realized_pnl"],
        )


if __name__ == "__main__":

    unittest.main(verbosity=2)
