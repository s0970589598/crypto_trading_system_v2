"""
Phase B1 測試：分批止盈（tp1 部分平倉 + tp2 全平剩餘）

驗證：
1. 觸及 tp1（未達 tp2/SL）→ 部分平倉、記一筆 partial trade、剩餘部位續抱。
2. 後續觸及 tp2 → 全平剩餘（共兩筆交易、各半）。
3. 同一根同時觸及 tp1 與 tp2 → tp1 分批 + tp2 全平（兩筆、同根）。
4. 不利方向（止損）與 tp1 同根觸及 → 止損優先、不分批（保守）。
5. 無分批策略（get_partial_take_profit 回 None）→ 行為與單一 TP 相同（向後相容）。
"""

import pandas as pd
from datetime import datetime, timedelta

from src.execution.backtest_engine import BacktestEngine
from src.execution.strategy import Strategy
from src.models.config import StrategyConfig, RiskManagement, ExitConditions
from src.models.trading import Signal
from src.models.market_data import MarketData


class _PartialStrat(Strategy):
    """做多一次：SL=entry*0.90、tp2=entry*1.04；可選分批 tp1=entry*1.02 平 50%。"""
    def __init__(self, config, partial=True, tp1_pct=0.5):
        super().__init__(config)
        self._fired = False
        self._partial = partial
        self._tp1_pct = tp1_pct

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
        return entry * 1.04

    def get_partial_take_profit(self, entry, direction, atr):
        if not self._partial:
            return None
        return {'tp1': entry * 1.02, 'tp1_close_pct': self._tp1_pct}

    def should_exit(self, position, md):
        return False


def _config():
    return StrategyConfig(
        strategy_id="b1-test", strategy_name="B1", version="1.0.0", enabled=True,
        symbol="BTCUSDT", timeframes=["1h"], parameters={},
        risk_management=RiskManagement(position_size=0.5, leverage=1, max_trades_per_day=99,
            max_consecutive_losses=99, daily_loss_limit=0.99, stop_loss_atr=1.5, take_profit_atr=3.0),
        entry_conditions=[], exit_conditions=ExitConditions(stop_loss="", take_profit=""))


def _data(overrides, n=8, entry_open=100.0):
    """中性 K 線（範圍 [99.5,100.5]，不觸及 tp1=102/tp2=104/SL=90）；bar1 open=進場價。"""
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


# ---------------------------------------------------------------------------

def test_tp1_partial_then_tp2_full():
    # bar3 觸 tp1(102) 不觸 tp2/SL → 分批；bar4 觸 tp2(104) → 全平剩餘
    res = _engine().run_single_strategy(
        _PartialStrat(_config()),
        _data({3: (100.0, 102.5, 100.0, 101.0), 4: (101.0, 104.5, 101.0, 103.0)}))
    assert len(res.trades) == 2
    tp1_trade, tp2_trade = res.trades[0], res.trades[1]
    assert tp1_trade.exit_reason == "止盈tp1"
    assert abs(tp1_trade.exit_price - 102.0) < 1e-9
    assert tp2_trade.exit_reason == "獲利"
    assert abs(tp2_trade.exit_price - 104.0) < 1e-9
    # 各平一半 → 兩筆 size 相同
    assert abs(tp1_trade.size - tp2_trade.size) < 1e-9


def test_same_bar_tp1_and_tp2():
    # bar3 同根觸 tp1(102) 與 tp2(104) → 兩筆、同根
    res = _engine().run_single_strategy(
        _PartialStrat(_config()),
        _data({3: (100.0, 105.0, 100.0, 103.0)}))
    assert len(res.trades) == 2
    assert res.trades[0].exit_reason == "止盈tp1"
    assert res.trades[1].exit_reason == "獲利"
    bar3_time = datetime(2024, 1, 1) + timedelta(hours=3)
    assert res.trades[0].exit_time == bar3_time
    assert res.trades[1].exit_time == bar3_time


def test_stop_loss_takes_priority_over_tp1():
    # bar3 同根觸 tp1(102) 與 SL(90) → 止損優先、不分批
    res = _engine().run_single_strategy(
        _PartialStrat(_config()),
        _data({3: (100.0, 102.5, 89.0, 95.0)}))
    assert len(res.trades) == 1
    assert res.trades[0].exit_reason == "止損"
    assert abs(res.trades[0].exit_price - 90.0) < 1e-9


def test_no_partial_is_backward_compatible():
    # 無分批（get_partial_take_profit 回 None）→ 單一 TP、一筆全平
    res = _engine().run_single_strategy(
        _PartialStrat(_config(), partial=False),
        _data({3: (100.0, 104.5, 100.0, 103.0)}))
    assert len(res.trades) == 1
    assert res.trades[0].exit_reason == "獲利"
    assert abs(res.trades[0].exit_price - 104.0) < 1e-9
