"""
Phase 站5 測試：StrategySelector（選最佳 + 成功門檻把關）

驗證：
1. 買入持有基準（贏過 BTC 用）在 OOS 區段計算正確。
2. OOS 累計報酬複利、最差回撤聚合正確。
3. 寬鬆門檻下候選通過、winner 被選出。
4. 嚴格門檻（OOS Sharpe 不可能達到）下候選被擋、失敗原因列出、winner 為 None。
5. 多候選依 OOS Sharpe 排序。
"""

import pandas as pd
from datetime import datetime, timedelta

from src.analysis.strategy_selector import (
    StrategySelector, SuccessCriteria, CandidateResult, SelectionResult,
)
from src.analysis.optimizer import WalkForwardResult
from src.execution.strategy import Strategy
from src.models.trading import Signal
from src.models.market_data import MarketData


# --- 最小可控策略（與 walk-forward 測試同型）---
class _LongScalp(Strategy):
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
        'strategy_id': 'sel-test', 'strategy_name': 'Sel Test', 'version': '1.0.0',
        'enabled': True, 'symbol': 'BTCUSDT', 'timeframes': ['1h'], 'parameters': {},
        'risk_management': {
            'position_size': 0.3, 'leverage': 1, 'max_trades_per_day': 9999,
            'max_consecutive_losses': 9999, 'daily_loss_limit': 0.99,
            'stop_loss_atr': 1.5, 'take_profit_atr': 3.0,
        },
        'entry_conditions': [], 'exit_conditions': {'stop_loss': '', 'take_profit': ''},
    }


def _trend_df(n=120, start=100.0, pct=0.015):
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
    return pd.DataFrame(rows)


def _wf(window_results, mean_oos=0.5, total_trades=120):
    return WalkForwardResult(
        n_windows=len(window_results), optimization_metric='sharpe_ratio',
        window_results=window_results, mean_is_score=1.0, mean_oos_score=mean_oos,
        oos_score_std=0.0, pct_windows_oos_positive=0.5, overfit_gap=0.5,
        total_oos_trades=total_trades,
    )


# ---------------------------------------------------------------------------
# 1. 買入持有基準
# ---------------------------------------------------------------------------

def test_benchmark_return_on_oos_segment():
    df = _trend_df(n=100, start=100.0, pct=0.01)  # 每根 +1%
    selector = StrategySelector({'1h': df})
    # initial_train_ratio=0.5 → OOS 是後半（index 50..99）
    bench = selector._benchmark_return_pct(0.5)
    oos = df.iloc[50:]
    expected = (oos.iloc[-1]['close'] / oos.iloc[0]['close'] - 1) * 100
    assert abs(bench - expected) < 1e-6
    assert bench > 0  # 上漲段基準為正


# ---------------------------------------------------------------------------
# 2. 聚合 helper
# ---------------------------------------------------------------------------

def test_compound_and_worst_drawdown_aggregation():
    wf = _wf([
        {'oos_pnl_pct': 10.0, 'oos_max_drawdown_pct': 5.0},
        {'oos_pnl_pct': -5.0, 'oos_max_drawdown_pct': 12.0},
    ])
    # 複利：1.10 * 0.95 - 1 = 0.045 = 4.5%
    assert abs(StrategySelector._compound_oos_return_pct(wf) - 4.5) < 1e-9
    # 最差回撤 = 12
    assert StrategySelector._worst_drawdown_pct(wf) == 12.0


# ---------------------------------------------------------------------------
# 3. 寬鬆門檻 → 通過、選出 winner
# ---------------------------------------------------------------------------

def test_lenient_criteria_passes_and_selects_winner():
    df = _trend_df()
    lenient = SuccessCriteria(min_oos_sharpe=-1e9, min_oos_trades=0,
                              max_drawdown_pct=1e9, must_beat_benchmark=False)
    selector = StrategySelector({'1h': df}, criteria=lenient, slippage=0.0)
    candidates = [{'name': 'long', 'strategy_class': _LongScalp, 'base_config': _base_config()}]
    res = selector.evaluate(candidates, {'risk_management.leverage': [1, 2]},
                            n_windows=2, initial_train_ratio=0.5)
    assert isinstance(res, SelectionResult)
    assert len(res.results) == 1
    assert res.results[0].passed is True
    assert res.winner is not None
    assert res.winner.name == 'long'


# ---------------------------------------------------------------------------
# 4. 嚴格門檻 → 擋下、列原因、無 winner
# ---------------------------------------------------------------------------

def test_strict_sharpe_blocks_and_reports_reason():
    df = _trend_df()
    strict = SuccessCriteria(min_oos_sharpe=1e9, min_oos_trades=0,
                             max_drawdown_pct=1e9, must_beat_benchmark=False)
    selector = StrategySelector({'1h': df}, criteria=strict, slippage=0.0)
    candidates = [{'name': 'long', 'strategy_class': _LongScalp, 'base_config': _base_config()}]
    res = selector.evaluate(candidates, {'risk_management.leverage': [1]},
                            n_windows=2, initial_train_ratio=0.5)
    assert res.results[0].passed is False
    assert any('OOS Sharpe' in f for f in res.results[0].failures)
    assert res.winner is None


# ---------------------------------------------------------------------------
# 5. 多候選依 OOS Sharpe 排序
# ---------------------------------------------------------------------------

def test_candidates_ranked_by_oos_sharpe():
    df = _trend_df()
    selector = StrategySelector({'1h': df}, slippage=0.0)
    candidates = [
        {'name': 'a', 'strategy_class': _LongScalp, 'base_config': _base_config()},
        {'name': 'b', 'strategy_class': _LongScalp, 'base_config': _base_config()},
    ]
    res = selector.evaluate(candidates, {'risk_management.leverage': [1]},
                            n_windows=2, initial_train_ratio=0.5)
    assert len(res.results) == 2
    # 已依 OOS Sharpe 由高到低排序
    scores = [r.walk_forward.mean_oos_score for r in res.results]
    assert scores == sorted(scores, reverse=True)
