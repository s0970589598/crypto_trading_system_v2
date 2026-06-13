"""
Phase A3 測試：walk-forward / out-of-sample 驗證 + optimizer 滑點修補

驗證：
1. walk_forward 跑滿指定窗數，每窗都有 in-sample / out-of-sample 分數與聚合欄位。
2. 過擬合偵測：訓練段上漲、測試段下跌（regime 翻轉）時，OOS 表現顯著低於 IS，
   overfit_gap > 0、平均 OOS 為負——這正是「在單一歷史窗背答案」會踩的雷。
3. 穩健情境：全程上漲時 OOS 與 IS 同樣為正、落差小。
4. optimizer 現在會把滑點穿進回測引擎（修補 optimizer.py:155 原本漏帶 slippage 的洞）。
"""

import pandas as pd
from datetime import datetime, timedelta

from src.analysis.optimizer import Optimizer, WalkForwardResult
from src.execution.strategy import Strategy
from src.models.trading import Signal
from src.models.market_data import MarketData


class _LongScalp(Strategy):
    """長單：空手就進場，SL -2%、TP +2%。上漲段賺、下跌段賠。"""
    def generate_signal(self, md: MarketData) -> Signal:
        tf = list(md.timeframes.keys())[0]
        latest = md.timeframes[tf].get_latest()
        return Signal(self.config.strategy_id, md.timestamp, self.config.symbol,
                      'BUY', 'long', latest['close'], 0.0, 0.0, 0.0, 1.0)

    def calculate_position_size(self, capital, price):
        return (capital * self.config.risk_management.position_size) / price

    def calculate_stop_loss(self, entry, direction, atr):
        return entry * 0.98

    def calculate_take_profit(self, entry, direction, atr):
        return entry * 1.02

    def should_exit(self, position, md):
        return False


def _base_config():
    return {
        'strategy_id': 'wf-test', 'strategy_name': 'WF Test', 'version': '1.0.0',
        'enabled': True, 'symbol': 'BTCUSDT', 'timeframes': ['1h'], 'parameters': {},
        'risk_management': {
            'position_size': 0.3, 'leverage': 1, 'max_trades_per_day': 9999,
            'max_consecutive_losses': 9999, 'daily_loss_limit': 0.99,
            'stop_loss_atr': 1.5, 'take_profit_atr': 3.0,
        },
        'entry_conditions': [], 'exit_conditions': {'stop_loss': '', 'take_profit': ''},
    }


def _trend_df(n, start=100.0, pct_per_bar=0.015):
    """單向趨勢 K 線。pct>0 上漲、<0 下跌。"""
    rows = []
    t0 = datetime(2024, 1, 1)
    price = start
    for k in range(n):
        nxt = price * (1 + pct_per_bar)
        o, c = price, nxt
        h = max(o, c) * 1.001
        l = min(o, c) * 0.999
        rows.append({'timestamp': t0 + timedelta(hours=k),
                     'open': o, 'high': h, 'low': l, 'close': c, 'volume': 1000.0})
        price = nxt
    return pd.DataFrame(rows)


def _regime_flip_df(n, start=100.0):
    """前半上漲、後半下跌（regime 翻轉）。"""
    half = n // 2
    up = _trend_df(half, start=start, pct_per_bar=0.015)
    down_start = up.iloc[-1]['close']
    down = _trend_df(n - half, start=down_start, pct_per_bar=-0.015)
    # 修正 down 的時間戳接續 up
    down['timestamp'] = [up.iloc[-1]['timestamp'] + timedelta(hours=i + 1) for i in range(len(down))]
    return pd.concat([up, down], ignore_index=True)


def _make_optimizer(df, slippage=0.0, metric='total_pnl_pct'):
    return Optimizer(
        strategy_class=_LongScalp,
        base_config=_base_config(),
        market_data={'1h': df},
        initial_capital=10000.0,
        commission=0.0,
        optimization_metric=metric,
        slippage=slippage,
        fill_timing='next_open',
    )


# ---------------------------------------------------------------------------
# 1. walk_forward 結構
# ---------------------------------------------------------------------------

def test_walk_forward_runs_requested_windows():
    opt = _make_optimizer(_trend_df(240))
    res = opt.walk_forward({'risk_management.leverage': [1, 2]}, n_windows=3,
                           initial_train_ratio=0.5)
    assert isinstance(res, WalkForwardResult)
    assert res.n_windows == 3
    assert len(res.window_results) == 3
    for w in res.window_results:
        assert 'is_score' in w and 'oos_score' in w and 'best_params' in w
    # 聚合欄位存在且合理
    assert res.total_oos_trades > 0


# ---------------------------------------------------------------------------
# 2. 過擬合偵測（regime 翻轉）
# ---------------------------------------------------------------------------

def test_walk_forward_detects_overfit_on_regime_flip():
    # 訓練段上漲、測試段下跌 → IS 賺、OOS 賠
    opt = _make_optimizer(_regime_flip_df(240))
    res = opt.walk_forward({'risk_management.leverage': [1, 2]}, n_windows=2,
                           initial_train_ratio=0.5)
    # 平均 OOS 顯著低於平均 IS（過擬合落差為正）
    assert res.overfit_gap > 0
    assert res.mean_oos_score < res.mean_is_score
    # OOS 在下跌段為負
    assert res.mean_oos_score < 0
    # 未通過穩健門檻
    assert res.is_robust() is False


# ---------------------------------------------------------------------------
# 3. 穩健情境（全程上漲）
# ---------------------------------------------------------------------------

def test_walk_forward_robust_when_trend_persists():
    opt = _make_optimizer(_trend_df(240))
    res = opt.walk_forward({'risk_management.leverage': [1, 2]}, n_windows=3,
                           initial_train_ratio=0.5)
    # 趨勢延續 → OOS 也為正、與 IS 落差小
    assert res.mean_oos_score > 0
    assert res.overfit_gap < res.mean_is_score  # 落差不該大於 IS 本身


# ---------------------------------------------------------------------------
# 4. optimizer 滑點修補（原本 optimizer.py:155 漏帶 slippage）
# ---------------------------------------------------------------------------

def test_optimizer_threads_slippage_into_engine():
    df = _trend_df(120)
    params = {'risk_management.leverage': 1}
    # 同一段資料、同參數，有滑點的分數應低於無滑點
    score_no_slip, _ = _make_optimizer(df, slippage=0.0)._evaluate_params(params, {'1h': df})
    score_slip, _ = _make_optimizer(df, slippage=0.01)._evaluate_params(params, {'1h': df})
    assert score_slip < score_no_slip
