"""
Phase B2 測試：MFE 利潤回吐保護

浮盈曾達 mfe_trigger_pct%、但當前收盤回落至 mfe_protection_floor_pct% 以下 → 強制平倉。
驗證：
1. 達觸發門檻後回吐到底線以下 → MFE 平倉。
2. 從未達觸發門檻 → 不平（撐到回測結束強平）。
3. 達門檻但仍在底線之上 → 不平。
4. 無 MFE 設定（get_mfe_protection 回 None）→ 不平（向後相容）。
"""

import pandas as pd
from datetime import datetime, timedelta

from src.execution.backtest_engine import BacktestEngine
from src.execution.strategy import Strategy
from src.models.config import StrategyConfig, RiskManagement, ExitConditions
from src.models.trading import Signal
from src.models.market_data import MarketData


class _MfeStrat(Strategy):
    """做多一次：SL=entry*0.90、tp2=entry*1.20（不干擾）；MFE 觸發 5%、底線 2%。"""
    def __init__(self, config, mfe=True):
        super().__init__(config)
        self._fired = False
        self._mfe = mfe

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

    def get_mfe_protection(self, entry, direction, atr):
        if not self._mfe:
            return None
        return {'mfe_trigger_pct': 5.0, 'mfe_protection_floor_pct': 2.0}

    def should_exit(self, position, md):
        return False


def _config():
    return StrategyConfig(
        strategy_id="b2-test", strategy_name="B2", version="1.0.0", enabled=True,
        symbol="BTCUSDT", timeframes=["1h"], parameters={},
        risk_management=RiskManagement(position_size=0.5, leverage=1, max_trades_per_day=99,
            max_consecutive_losses=99, daily_loss_limit=0.99, stop_loss_atr=1.5, take_profit_atr=3.0),
        entry_conditions=[], exit_conditions=ExitConditions(stop_loss="", take_profit=""))


def _data(overrides, n=8, entry_open=100.0):
    """中性 K 線（[99.5,100.5] 圍繞 100）；bar1 open=進場價 100。"""
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


# ---------------------------------------------------------------------------

def test_mfe_triggers_after_giveback():
    # bar3 浮盈到 +6%(max_fav 106)、收盤 +4% 未觸；bar4 收盤回吐到 +1.5% ≤ 底線 2% → MFE 平倉
    res = _engine().run_single_strategy(
        _MfeStrat(_config()),
        _data({3: (100.0, 106.0, 100.0, 104.0), 4: (104.0, 104.0, 100.0, 101.5)}))
    assert len(res.trades) == 1
    assert res.trades[0].exit_reason == "MFE保護"
    assert abs(res.trades[0].exit_price - 101.5) < 1e-9


def test_no_mfe_when_trigger_never_reached():
    # 最高僅 +3%(< 5% 觸發門檻)→ 即使收盤回到成本也不觸發
    res = _engine().run_single_strategy(
        _MfeStrat(_config()),
        _data({3: (100.0, 103.0, 100.0, 100.0)}))
    assert "MFE保護" not in _reasons(res)


def test_no_mfe_when_still_above_floor():
    # 浮盈達 +6%，但之後收盤都維持在 +3%(> 底線 2%)→ 不觸發
    res = _engine().run_single_strategy(
        _MfeStrat(_config()),
        _data({3: (100.0, 106.0, 103.0, 105.0),
               4: (104.0, 104.0, 103.0, 103.5),
               5: (103.5, 104.0, 103.0, 103.5)}, n=6))
    assert "MFE保護" not in _reasons(res)


def test_no_mfe_when_disabled_backward_compatible():
    # 無 MFE 設定 → 同 test1 的回吐情境也不觸發
    res = _engine().run_single_strategy(
        _MfeStrat(_config(), mfe=False),
        _data({3: (100.0, 106.0, 100.0, 104.0), 4: (104.0, 104.0, 100.0, 101.5)}))
    assert "MFE保護" not in _reasons(res)
