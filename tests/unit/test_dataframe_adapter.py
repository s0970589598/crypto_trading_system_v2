"""DataFrameSignalAdapter：從 generate_signals 產出的 df 欄位讀訊號 + 出場。"""
import pandas as pd
from datetime import datetime, timedelta

from src.strategies.scalping_adapter import DataFrameSignalAdapter
from src.execution.backtest_engine import BacktestEngine
from src.models.config import StrategyConfig, RiskManagement, ExitConditions


class _FakeDfStrat:
    """在指定 bar 設 long_signal + long_stop_loss(-2%)/long_take_profit(+2%)。"""
    def __init__(self, long_bars=()):
        self._b = set(long_bars)

    def generate_signals(self, df):
        df = df.copy()
        for col in ('long_signal', 'short_signal'):
            df[col] = False
        for col in ('long_stop_loss', 'long_take_profit', 'short_stop_loss', 'short_take_profit'):
            df[col] = float('nan')
        for i in self._b:
            c = df.iloc[i]['close']
            df.iloc[i, df.columns.get_loc('long_signal')] = True
            df.iloc[i, df.columns.get_loc('long_stop_loss')] = c * 0.98
            df.iloc[i, df.columns.get_loc('long_take_profit')] = c * 1.02
        return df


def _cfg():
    return StrategyConfig(strategy_id="df", strategy_name="df", version="1.0.0", enabled=True,
        symbol="BTCUSDT", timeframes=["1h"], parameters={},
        risk_management=RiskManagement(position_size=0.2, leverage=1, max_trades_per_day=99,
            max_consecutive_losses=99, daily_loss_limit=0.99, stop_loss_atr=1.5, take_profit_atr=3.0),
        entry_conditions=[], exit_conditions=ExitConditions(stop_loss="", take_profit=""))


def _data(overrides, n=8):
    rows = []
    t0 = datetime(2024, 1, 1)
    for k in range(n):
        if k in overrides:
            o, h, l, c = overrides[k]
        elif k == 1:
            o, h, l, c = 100.0, 100.5, 99.5, 100.0
        else:
            o, h, l, c = 100.0, 100.5, 99.5, 100.0
        rows.append({'timestamp': t0 + timedelta(hours=k),
                     'open': o, 'high': h, 'low': l, 'close': c, 'volume': 1000.0})
    return {"1h": pd.DataFrame(rows)}


def test_reads_signal_and_exits_from_df_columns():
    # bar0 訊號（close=100 → SL 98 / TP 102）；bar1 成交；bar3 高點觸 TP 102
    eng = BacktestEngine(10000, commission=0.0, slippage=0.0, fill_timing='next_open')
    strat = DataFrameSignalAdapter(_cfg(), _FakeDfStrat(long_bars=[0]))
    res = eng.run_single_strategy(strat, _data({3: (100.0, 102.5, 100.0, 101.0)}))
    assert len(res.trades) == 1
    assert res.trades[0].exit_reason == "獲利"
    assert abs(res.trades[0].exit_price - 102.0) < 1e-9  # TP 來自 df 欄位


def test_no_signal_no_trade():
    eng = BacktestEngine(10000, commission=0.0, slippage=0.0, fill_timing='next_open')
    strat = DataFrameSignalAdapter(_cfg(), _FakeDfStrat(long_bars=[]))
    res = eng.run_single_strategy(strat, _data({}))
    assert len(res.trades) == 0
