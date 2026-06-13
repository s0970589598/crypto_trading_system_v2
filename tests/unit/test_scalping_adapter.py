"""
Phase B3 測試：ScalpingAdapter（把向量化 scalping 接進逐根閉環）

用一個模擬 v11 介面的 fake 向量化策略（generate_signals + get_exit_levels）驗證：
1. 出場/部位 hook 把 get_exit_levels 的 SL/tp2/tp1/MFE 正確轉成 Strategy 介面。
2. 端到端跑進 BacktestEngine：prepare 預算訊號 → 逐根映射 BUY → 分批止盈(B1) +
   走完出場，證明 scalping 的出場機制透過 adapter 接進閉環。
3. 無訊號 → 無交易。
"""

import pandas as pd
from datetime import datetime, timedelta

from src.strategies.scalping_adapter import ScalpingAdapter
from src.execution.backtest_engine import BacktestEngine
from src.models.config import StrategyConfig, RiskManagement, ExitConditions


class _FakeVectorized:
    """模擬 v11 介面：在指定 bar 發 long_signal；出場用固定比例（SL-10%/tp1+2%/tp2+4%）。"""
    def __init__(self, long_signal_bars=()):
        self._bars = set(long_signal_bars)

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['long_signal'] = False
        df['short_signal'] = False
        df['regime'] = 'mid'
        df['atr'] = 1.0
        df['position_scale'] = 1.0
        loc = df.columns.get_loc('long_signal')
        for i in self._bars:
            df.iloc[i, loc] = True
        return df

    def get_exit_levels(self, entry_price, direction, atr, regime):
        if direction == 'long':
            return {'stop_loss': entry_price * 0.90, 'tp1': entry_price * 1.02,
                    'tp2': entry_price * 1.04, 'tp1_close_pct': 0.5,
                    'use_mfe_protection': True, 'mfe_trigger_pct': 5.0,
                    'mfe_protection_floor_pct': 2.0}
        return {'stop_loss': entry_price * 1.10, 'tp1': entry_price * 0.98,
                'tp2': entry_price * 0.96, 'tp1_close_pct': 0.5,
                'use_mfe_protection': True, 'mfe_trigger_pct': 5.0,
                'mfe_protection_floor_pct': 2.0}


def _config():
    return StrategyConfig(
        strategy_id="b3-test", strategy_name="B3", version="1.0.0", enabled=True,
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


# ---------------------------------------------------------------------------

def test_exit_hooks_translate_vectorized_levels():
    adapter = ScalpingAdapter(_config(), _FakeVectorized())
    assert adapter.calculate_stop_loss(100.0, 'long', 1.0) == 90.0
    assert adapter.calculate_take_profit(100.0, 'long', 1.0) == 104.0
    assert adapter.get_partial_take_profit(100.0, 'long', 1.0) == {'tp1': 102.0, 'tp1_close_pct': 0.5}
    mfe = adapter.get_mfe_protection(100.0, 'long', 1.0)
    assert mfe == {'mfe_trigger_pct': 5.0, 'mfe_protection_floor_pct': 2.0}


def test_end_to_end_partial_then_tp2_via_adapter():
    # fake 在 bar0 發 BUY → bar1 成交；bar3 觸 tp1(102) 分批、bar4 觸 tp2(104) 全平
    adapter = ScalpingAdapter(_config(), _FakeVectorized(long_signal_bars=[0]))
    res = _engine().run_single_strategy(
        adapter, _data({3: (100.0, 102.5, 100.0, 101.0), 4: (101.0, 104.5, 101.0, 103.0)}))
    assert len(res.trades) == 2
    assert res.trades[0].exit_reason == "止盈tp1"
    assert abs(res.trades[0].exit_price - 102.0) < 1e-9
    assert res.trades[1].exit_reason == "獲利"
    assert abs(res.trades[1].exit_price - 104.0) < 1e-9


def test_no_signal_no_trade():
    adapter = ScalpingAdapter(_config(), _FakeVectorized(long_signal_bars=[]))
    res = _engine().run_single_strategy(adapter, _data({}))
    assert len(res.trades) == 0
