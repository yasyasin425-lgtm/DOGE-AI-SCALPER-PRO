
"""
DOGE AI SCALPER PRO
Paper Engine Safety Tests
"""

import unittest
import time
import pandas as pd

from copy import deepcopy
from datetime import datetime, timezone

from paper_engine import run_cycle

from risk import (
    calculate_position,
    calculate_exit,
)


class TestPaperEngine(unittest.TestCase):

    def setUp(self):

        self.timestamp = (
            int(time.time() // 60)
            * 60000 - 1
        )

        self.state = {
            "balance": 100.0,
            "realized_pnl": 0.0,
            "position": None,
            "closed_trades": [],
            "trades": [],
            "day": datetime.fromtimestamp(
                self.timestamp / 1000,
                timezone.utc,
            ).date().isoformat(),
            "day_start_balance": 100.0,
            "daily_realized_pnl": 0.0,
        }

        self.snapshot = {
            "price": 0.06,
            "atr": 0.0001,
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
            self.state, 0.06, 0.0001
        )

        self.assertIsNotNone(position)

        self.assertLessEqual(
            position["total_cost"],
            25.0 + 1e-9,
        )

        self.assertLessEqual(
            position["risk_cash"],
            0.5 + 1e-9,
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
            target * 1.001,
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
            0,
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
            stop * 0.999,
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
            0,
        )

    def test_06_daily_loss_limit(self):

        state = deepcopy(self.state)

        state["daily_realized_pnl"] = -2.0

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
                state, 0.06, 0.0001
            )
        )

    def test_08_trading_fees(self):

        position = calculate_position(
            self.state, 0.06, 0.0001
        )

        result = calculate_exit(
            position,
            position["entry"],
        )

        self.assertLess(
            result["net_pnl"], 0
        )

        self.assertGreater(
            result["entry_fee"], 0
        )

        self.assertGreater(
            result["exit_fee"], 0
        )

    def test_09_stop_priority(self):

        state = self.open_position()

        position = state["position"]

        candles = self.make_candle(
            self.timestamp,
            position["entry"],
            position["target"] * 1.001,
            position["stop"] * 0.999,
            position["entry"],
        )

        result = run_cycle(
            state,
            self.snapshot,
            candles,
        )

        self.assertLess(
            result["state"]["realized_pnl"],
            0,
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


if __name__ == "__main__":

    unittest.main(verbosity=2)
