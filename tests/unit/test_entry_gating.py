"""
Phase item4b-i：進場 gating（跨交易回饋 + can_enter）

驗證引擎的 on_trade_closed 回饋與 can_enter gating hook：策略在平倉後封鎖進場，
gated 版只進場一次、ungated 版會反覆進場。（scalping 用它接 EquityCurveGuardian 連虧冷卻。）
"""

import pandas as pd
from datetime import datetime, timedelta

from src.execution.backtest_engine import BacktestEngine
from src.execution.strategy import Strategy
from src.models.config import StrategyConfig, RiskManagement, ExitConditions
from src.models.trading import Signal
from src.models.market_data import MarketData


class _GatedStrat(Strategy):
    """一直想做多、SL -2%/TP +2%；平倉後（若 gate）封鎖後續進場。"""
    def __init__(self, config, gate=True):
        super().__init__(config)
        self._gate = gate
        self._blocked = False
        self.closed = 0

    def generate_signal(self, md: MarketData) -> Signal:
        return Signal(self.config.strategy_id, md.timestamp, self.config.symbol,
                      'BUY', 'long', 0.0, 0.0, 0.0, 0.0, 1.0)

    def calculate_position_size(self, capital, price):
        return (capital * self.config.risk_management.position_size) / price

    def calculate_stop_loss(self, entry, direction, atr):
        return entry * 0.98

    def calculate_take_profit(self, entry, direction, atr):
        return entry * 1.02

    def should_exit(self, position, md):
        return False

    def on_trade_closed(self, trade, bar_index):
        self.closed += 1
        if self._gate:
            self._blocked = True

    def can_enter(self, bar_index):
        return not self._blocked


def _config():
    return StrategyConfig(
        strategy_id="gate-test", strategy_name="Gate", version="1.0.0", enabled=True,
        symbol="BTCUSDT", timeframes=["1h"], parameters={},
        risk_management=RiskManagement(position_size=0.3, leverage=1, max_trades_per_day=999,
            max_consecutive_losses=999, daily_loss_limit=0.99, stop_loss_atr=1.5, take_profit_atr=3.0),
        entry_conditions=[], exit_conditions=ExitConditions(stop_loss="", take_profit=""))


def _downtrend(n=20, start=100.0, pct=-0.01):
    rows = []
    t0 = datetime(2024, 1, 1)
    price = start
    for k in range(n):
        nxt = price * (1 + pct)
        o, c = price, nxt
        rows.append({'timestamp': t0 + timedelta(hours=k),
                     'open': o, 'high': max(o, c) * 1.001, 'low': min(o, c) * 0.999,
                     'close': c, 'volume': 1000.0})
        price = nxt
    return {"1h": pd.DataFrame(rows)}


def _engine():
    return BacktestEngine(10000, commission=0.0, slippage=0.0, fill_timing='next_open')


def test_gating_blocks_reentry_after_close():
    gated = _GatedStrat(_config(), gate=True)
    r_gated = _engine().run_single_strategy(gated, _downtrend())
    ungated = _GatedStrat(_config(), gate=False)
    r_ungated = _engine().run_single_strategy(ungated, _downtrend())

    # on_trade_closed 有被呼叫
    assert gated.closed >= 1
    # gated 平倉後封鎖 → 只進場一次
    assert len(r_gated.trades) == 1
    # ungated 反覆進場 → 多筆
    assert len(r_ungated.trades) > 1
