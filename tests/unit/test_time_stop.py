"""
Phase item4：時間停損（bars_held 在 [start,end] 且仍在成本區 ±cost_zone_pct% → 平倉）

1. 持倉一直在成本區 → 到觸發窗即時間停損平倉。
2. 已離開成本區（有明顯浮盈/虧）→ 不觸發。
3. 未設定（get_time_stop=None）→ 不觸發（向後相容）。
"""

import pandas as pd
from datetime import datetime, timedelta

from src.execution.backtest_engine import BacktestEngine
from src.execution.strategy import Strategy
from src.models.config import StrategyConfig, RiskManagement, ExitConditions
from src.models.trading import Signal
from src.models.market_data import MarketData


class _TimeStopStrat(Strategy):
    """做多一次；SL/TP 設很寬不干擾；時間停損窗 [3,5]、成本區 ±0.5%。"""
    def __init__(self, config, enabled=True):
        super().__init__(config)
        self._fired = False
        self._enabled = enabled

    def generate_signal(self, md: MarketData) -> Signal:
        if not self._fired:
            self._fired = True
            return Signal(self.config.strategy_id, md.timestamp, self.config.symbol,
                          'BUY', 'long', 0.0, 0.0, 0.0, 0.0, 1.0)
        return Signal.hold(self.config.strategy_id, md.timestamp, self.config.symbol)

    def calculate_position_size(self, capital, price):
        return (capital * self.config.risk_management.position_size) / price

    def calculate_stop_loss(self, entry, direction, atr):
        return entry * 0.90

    def calculate_take_profit(self, entry, direction, atr):
        return entry * 1.20

    def get_time_stop(self, entry, direction, atr):
        return {'start': 3, 'end': 5, 'cost_zone_pct': 0.5} if self._enabled else None

    def should_exit(self, position, md):
        return False


def _config():
    return StrategyConfig(
        strategy_id="ts-test", strategy_name="TS", version="1.0.0", enabled=True,
        symbol="BTCUSDT", timeframes=["1h"], parameters={},
        risk_management=RiskManagement(position_size=0.5, leverage=1, max_trades_per_day=99,
            max_consecutive_losses=99, daily_loss_limit=0.99, stop_loss_atr=1.5, take_profit_atr=3.0),
        entry_conditions=[], exit_conditions=ExitConditions(stop_loss="", take_profit=""))


def _data(overrides, n=8, entry_open=100.0):
    rows = []
    t0 = datetime(2024, 1, 1)
    for k in range(n):
        if k in overrides:
            o, h, l, c = overrides[k]
        elif k == 1:
            o, h, l, c = entry_open, 100.5, 99.5, 100.0
        else:
            o, h, l, c = 100.0, 100.5, 99.5, 100.0
        rows.append({'timestamp': t0 + timedelta(hours=k),
                     'open': o, 'high': h, 'low': l, 'close': c, 'volume': 1000.0})
    return {"1h": pd.DataFrame(rows)}


def _engine():
    return BacktestEngine(10000, commission=0.0, slippage=0.0, fill_timing='next_open')


def _reasons(res):
    return [t.exit_reason for t in res.trades]


def test_time_stop_triggers_when_flat_in_window():
    # 全程在成本區（~100）；bars_held=3 落在窗 [3,5] → 第 4 根時間停損
    res = _engine().run_single_strategy(_TimeStopStrat(_config()), _data({}))
    assert len(res.trades) == 1
    assert res.trades[0].exit_reason == "時間停損"
    assert res.trades[0].exit_time == datetime(2024, 1, 1) + timedelta(hours=4)


def test_no_time_stop_when_not_in_cost_zone():
    # 進場後價格拉到 ~102（+2% > 成本區 0.5%）→ 不觸發時間停損
    moved = {k: (102.0, 102.5, 101.5, 102.0) for k in range(2, 8)}
    res = _engine().run_single_strategy(_TimeStopStrat(_config()), _data(moved))
    assert "時間停損" not in _reasons(res)


def test_no_time_stop_when_disabled():
    res = _engine().run_single_strategy(_TimeStopStrat(_config(), enabled=False), _data({}))
    assert "時間停損" not in _reasons(res)
