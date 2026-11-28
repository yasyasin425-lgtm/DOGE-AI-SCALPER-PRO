
"""
DOGE AI SCALPER PRO
Paper Engine V2 Safety Tests
DECIMAL PRECISION
"""

import unittest
import time
import pandas as pd
import simplejson

from copy import deepcopy
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import patch

from paper_engine import run_cycle

from risk import (
    calculate_position,
    calculate_exit,
)

from money import (
    decimal_value,
    debit_balance,
    credit_balance,
)


D = Decimal


class TestPaperEngine(unittest.TestCase):

    def setUp(self):

        self.timestamp = (
            int(time.time() // 60)
            * 60000 - 1
        )

        self.state = {
            "balance": D("100"),
            "realized_pnl": D("0"),
            "position": None,
            "closed_trades": [],
            "trades": [],
            "day": datetime.fromtimestamp(
                self.timestamp / 1000,
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
            "quality": "قوية جداً",
            "checks": {},
            "candle_time": self.timestamp,
            "strategy_version": "1.0",
        }

    def make_candle(
        self, timestamp, opening,
        high, low, close
    ):

        return pd.DataFrame([{
            "close_time": timestamp,
            "open": opening,
            "high": high,
            "low": low,
            "close": close,
        }])

    def open_position(self):

        snapshot = deepcopy(self.snapshot)

        snapshot["candle_time"] -= 60000

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

    def test_01_position_size(self):

        position = calculate_position(
            self.state,
            D("0.06"),
            D("0.0001"),
        )

        self.assertIsNotNone(position)

        self.assertLessEqual(
            position["total_cost"],
            D("25"),
        )

        self.assertLessEqual(
            position["risk_cash"],
            D("0.5"),
        )

    def test_02_buy(self):

        original = deepcopy(self.state)

        result = run_cycle(
            self.state,
            self.snapshot,
            pd.DataFrame(),
        )

        self.assertEqual(
            result["decision"]["action"],
            "BUY",
        )

        self.assertIsNotNone(
            result["state"]["position"]
        )

        self.assertEqual(
            self.state, original
        )

    def test_03_hold(self):

        snapshot = deepcopy(self.snapshot)

        snapshot["signal"] = "HOLD"

        result = run_cycle(
            self.state,
            snapshot,
            pd.DataFrame(),
        )

        self.assertEqual(
            result["decision"]["action"],
            "HOLD",
        )

        self.assertIsNone(
            result["state"]["position"]
        )

    def test_04_take_profit(self):

        state = self.open_position()

        position = state["position"]

        target = position["target"]

        candles = self.make_candle(
            self.timestamp,
            position["entry"],
            target * D("1.001"),
            position["entry"],
            target,
        )

        result = run_cycle(
            state,
            self.snapshot,
            candles,
        )

        self.assertEqual(
            result["decision"]["action"],
            "SELL",
        )

        self.assertGreater(
            result["state"]["realized_pnl"],
            D("0"),
        )

        self.assertIsNone(
            result["state"]["position"]
        )

    def test_05_stop_loss(self):

        state = self.open_position()

        position = state["position"]

        stop = position["stop"]

        candles = self.make_candle(
            self.timestamp,
            position["entry"],
            position["entry"],
            stop * D("0.999"),
            stop,
        )

        result = run_cycle(
            state,
            self.snapshot,
            candles,
        )

        self.assertEqual(
            result["decision"]["action"],
            "SELL",
        )

        self.assertLess(
            result["state"]["realized_pnl"],
            D("0"),
        )

    def test_06_daily_loss_limit(self):

        state = deepcopy(self.state)

        state["daily_realized_pnl"] = D("-2")

        result = run_cycle(
            state,
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

    def test_07_single_position(self):

        state = self.open_position()

        self.assertIsNone(
            calculate_position(
                state,
                D("0.06"),
                D("0.0001"),
            )
        )

    def test_08_trading_fees(self):

        position = calculate_position(
            self.state,
            D("0.06"),
            D("0.0001"),
        )

        result = calculate_exit(
            position,
            position["entry"],
        )

        self.assertLess(
            result["net_pnl"],
            D("0"),
        )

        self.assertGreater(
            result["entry_fee"],
            D("0"),
        )

        self.assertGreater(
            result["exit_fee"],
            D("0"),
        )

    def test_09_stop_priority(self):

        state = self.open_position()

        position = state["position"]

        candles = self.make_candle(
            self.timestamp,
            position["entry"],
            position["target"] * D("1.001"),
            position["stop"] * D("0.999"),
            position["entry"],
        )

        result = run_cycle(
            state,
            self.snapshot,
            candles,
        )

        self.assertLess(
            result["state"]["realized_pnl"],
            D("0"),
        )

    def test_10_stale_signal(self):

        snapshot = deepcopy(self.snapshot)

        snapshot["candle_time"] -= 600000

        with self.assertRaises(RuntimeError):

            run_cycle(
                self.state,
                snapshot,
                pd.DataFrame(),
            )

    def test_11_decimal_balance(self):

        state = self.open_position()

        self.assertIsInstance(
            state["balance"],
            Decimal,
        )

        self.assertIsInstance(
            state["position"]["qty"],
            Decimal,
        )

    def test_12_exact_balance_roundtrip(self):

        balance = D(
            "100.12345678901234567890123456"
        )

        amount = D("25.123456789012")

        remaining = debit_balance(
            balance,
            amount,
        )

        restored = credit_balance(
            remaining,
            amount,
        )

        self.assertEqual(
            restored,
            balance,
        )

    def test_13_json_precision(self):

        state = self.open_position()

        encoded = simplejson.dumps(
            state,
            use_decimal=True,
            allow_nan=False,
        )

        decoded = simplejson.loads(
            encoded,
            use_decimal=True,
        )

        self.assertEqual(
            decoded,
            state,
        )

    def test_14_invalid_numbers(self):

        for value in [
            "NaN",
            "Infinity",
            "-Infinity",
        ]:

            with self.assertRaises(ValueError):

                decimal_value(value)

    def test_15_insufficient_balance(self):

        with self.assertRaises(RuntimeError):

            debit_balance(
                D("10"),
                D("11"),
            )

    def test_16_wallet_accounting(self):

        state = self.open_position()

        position = state["position"]

        target = position["target"]

        candles = self.make_candle(
            self.timestamp,
            position["entry"],
            target * D("1.001"),
            position["entry"],
            target,
        )

        result = run_cycle(
            state,
            self.snapshot,
            candles,
        )

        final_state = result["state"]

        expected = (
            self.state["balance"]
            + final_state["realized_pnl"]
        )

        self.assertEqual(
            final_state["balance"],
            expected,
        )

    def test_17_time_exit(self):

        state = self.open_position()

        position = state["position"]

        entry = position["entry"]

        rows = []

        for i in range(1, 6):

            rows.append({
                "close_time":
                    position["entry_candle_time"]
                    + i * 60000,
                "open": entry,
                "high": entry,
                "low": entry,
                "close": entry,
            })

        candles = pd.DataFrame(rows)

        snapshot = deepcopy(self.snapshot)

        snapshot["candle_time"] = rows[-1][
            "close_time"
        ]

        with patch(
            "paper_engine.MAX_SIGNAL_AGE_SECONDS",
            120,
        ), patch(
            "paper_engine.datetime"
        ) as clock:

            clock.now.return_value = (
                datetime.fromtimestamp(
                    snapshot["candle_time"] / 1000
                    + 1,
                    timezone.utc,
                )
            )

            clock.fromtimestamp.side_effect = (
                datetime.fromtimestamp
            )

            result = run_cycle(
                state,
                snapshot,
                candles,
            )

        self.assertEqual(
            result["decision"]["action"],
            "SELL",
        )

        self.assertEqual(
            result["decision"]["reason"],
            "انتهاء مدة الصفقة",
        )


if __name__ == "__main__":

    unittest.main(verbosity=2)
