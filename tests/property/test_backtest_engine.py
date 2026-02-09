"""
BacktestEngine 屬性測試

測試回測引擎的正確性屬性。
"""

import pytest
import pandas as pd
from hypothesis import given, strategies as st, assume, settings
from datetime import datetime, timedelta
from typing import Dict

from src.execution.backtest_engine import BacktestEngine
from src.execution.strategy import Strategy
from src.models.config import StrategyConfig, RiskManagement, ExitConditions, NotificationConfig
from src.models.trading import Trade
from src.models.market_data import MarketData


# ============================================================================
# 測試數據生成策略
# ============================================================================

@st.composite
def market_data_strategy(draw, n_candles=100):
    """生成市場數據"""
    base_price = draw(st.floats(min_value=1000, max_value=100000))
    
    data = []
    current_time = datetime(2024, 1, 1)
    
    for i in range(n_candles):
        low = base_price * draw(st.floats(min_value=0.98, max_value=1.0))
        high = low * draw(st.floats(min_value=1.0, max_value=1.02))
        open_price = draw(st.floats(min_value=low, max_value=high))
        close_price = draw(st.floats(min_value=low, max_value=high))
        volume = draw(st.floats(min_value=100, max_value=10000))
        
        data.append({
            'timestamp': current_time + timedelta(hours=i),
            'open': open_price,
            'high': high,
            'low': low,
            'close': close_price,
            'volume': volume,
        })
        
        base_price = close_price
    
    return pd.DataFrame(data)


class SimpleStrategy(Strategy):
    """簡單測試策略"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.signal_count = 0
    
    def generate_signal(self, market_data: MarketData):
        """生成信號：每 10 次生成一個買入信號"""
        from src.models.trading import Signal
        
        self.signal_count += 1
        
        if self.signal_count % 10 == 0:
            timeframe = list(market_data.timeframes.keys())[0]
            latest = market_data.timeframes[timeframe].get_latest()
            
            return Signal(
                strategy_id=self.config.strategy_id,
                timestamp=market_data.timestamp,
                symbol=self.config.symbol,
                action='BUY',
                direction='long',
                entry_price=latest['close'],
                stop_loss=latest['close'] * 0.98,
                take_profit=latest['close'] * 1.04,
                position_size=0.01,
                confidence=0.8,
            )
        
        return Signal(
            strategy_id=self.config.strategy_id,
            timestamp=market_data.timestamp,
            symbol=self.config.symbol,
            action='HOLD',
            direction=None,
            entry_price=0.0,
            stop_loss=0.0,
            take_profit=0.0,
            position_size=0.0,
            confidence=0.0,
        )
    
    def calculate_position_size(self, capital: float, price: float) -> float:
        """計算倉位大小"""
        return (capital * self.config.risk_management.position_size) / price
    
    def calculate_stop_loss(self, entry_price: float, direction: str, atr: float) -> float:
        """計算止損"""
        if direction == 'long':
            return entry_price - (atr * self.config.risk_management.stop_loss_atr)
        else:
            return entry_price + (atr * self.config.risk_management.stop_loss_atr)
    
    def calculate_take_profit(self, entry_price: float, direction: str, atr: float) -> float:
        """計算目標"""
        if direction == 'long':
            return entry_price + (atr * self.config.risk_management.take_profit_atr)
        else:
            return entry_price - (atr * self.config.risk_management.take_profit_atr)
    
    def should_exit(self, position, market_data: MarketData) -> bool:
        """判斷是否出場"""
        return False


def create_test_strategy(strategy_id: str = "test-strategy") -> Strategy:
    """創建測試策略"""
    config = StrategyConfig(
        strategy_id=strategy_id,
        strategy_name="Test Strategy",
        version="1.0.0",
        enabled=True,
        symbol="BTCUSDT",
        timeframes=["1h"],
        parameters={},
        risk_management=RiskManagement(
            position_size=0.1,
            leverage=1,
            max_trades_per_day=10,
            max_consecutive_losses=3,
            daily_loss_limit=0.1,
            stop_loss_atr=1.5,
            take_profit_atr=3.0,
        ),
        entry_conditions=[],
        exit_conditions=ExitConditions(
            stop_loss="",
            take_profit="",
        ),
    )
    
    return SimpleStrategy(config)


# ============================================================================
# Property 9: 回測數據一致性
# ============================================================================

# Feature: multi-strategy-system, Property 9: 回測數據一致性
@settings(deadline=1000)  # 增加超時限制到 1000ms
@given(
    market_data=market_data_strategy(n_candles=50),
    initial_capital=st.floats(min_value=1000, max_value=10000),
    commission=st.floats(min_value=0.0001, max_value=0.001),
)
def test_backtest_data_consistency(market_data, initial_capital, commission):
    """
    對於任何在同一時間範圍內對多個策略執行的回測，
    所有策略應該使用相同的市場數據、手續費率和滑點設置。
    """
    # 創建多個策略
    strategy1 = create_test_strategy("strategy-1")
    strategy2 = create_test_strategy("strategy-2")
    
    # 創建回測引擎
    engine = BacktestEngine(initial_capital, commission)
    
    # 準備市場數據
    market_data_dict = {"1h": market_data}
    
    # 回測兩個策略
    result1 = engine.run_single_strategy(strategy1, market_data_dict)
    result2 = engine.run_single_strategy(strategy2, market_data_dict)
    
    # 驗證：兩個策略使用相同的初始資金
    assert result1.initial_capital == result2.initial_capital == initial_capital
    
    # 驗證：兩個策略使用相同的時間範圍
    assert result1.start_date == result2.start_date
    assert result1.end_date == result2.end_date
    
    # 驗證：如果策略邏輯相同，交易數量應該相同
    # （因為我們使用相同的策略類）
    assert result1.total_trades == result2.total_trades


# ============================================================================
# Property 11: 績效指標計算正確性
# ============================================================================

# Feature: multi-strategy-system, Property 11: 績效指標計算正確性
@given(
    num_trades=st.integers(min_value=5, max_value=50),
    win_rate_target=st.floats(min_value=0.3, max_value=0.7),
)
def test_performance_metrics_correctness(num_trades, win_rate_target):
    """
    對於任何交易列表，計算的勝率應該等於（獲利交易數 / 總交易數），
    且獲利因子應該等於（總獲利 / 總虧損的絕對值）。
    """
    # 生成交易列表
    trades = []
    num_wins = int(num_trades * win_rate_target)
    num_losses = num_trades - num_wins
    
    total_win = 0.0
    total_loss = 0.0
    
    for i in range(num_wins):
        trade = Trade(
            strategy_id="test",
            symbol="BTCUSDT",
            direction="long",
            entry_price=50000.0,
            exit_price=51000.0,
            size=0.1,
            leverage=1,
        )
        trade.pnl = 100.0  # 獲利
        total_win += trade.pnl
        trades.append(trade)
    
    for i in range(num_losses):
        trade = Trade(
            strategy_id="test",
            symbol="BTCUSDT",
            direction="long",
            entry_price=50000.0,
            exit_price=49000.0,
            size=0.1,
            leverage=1,
        )
        trade.pnl = -100.0  # 虧損
        total_loss += abs(trade.pnl)
        trades.append(trade)
    
    # 計算指標
    engine = BacktestEngine(10000.0)
    metrics = engine.calculate_metrics(trades)
    
    # 驗證：勝率計算正確
    expected_win_rate = num_wins / num_trades
    assert abs(metrics['win_rate'] - expected_win_rate) < 0.01, \
        f"勝率應該是 {expected_win_rate:.2%}，實際是 {metrics['win_rate']:.2%}"
    
    # 驗證：獲利交易數正確
    assert metrics['winning_trades'] == num_wins
    
    # 驗證：虧損交易數正確
    assert metrics['losing_trades'] == num_losses
    
    # 驗證：總交易數正確
    assert metrics['total_trades'] == num_trades
    
    # 驗證：獲利因子計算正確
    if total_loss > 0:
        expected_profit_factor = total_win / total_loss
        assert abs(metrics['profit_factor'] - expected_profit_factor) < 0.01, \
            f"獲利因子應該是 {expected_profit_factor:.2f}，實際是 {metrics['profit_factor']:.2f}"


# ============================================================================
# 單元測試
# ============================================================================

def test_backtest_engine_initialization():
    """測試回測引擎初始化"""
    engine = BacktestEngine(10000.0, 0.0005)
    
    assert engine.initial_capital == 10000.0
    assert engine.commission == 0.0005


def test_single_strategy_backtest():
    """測試單策略回測"""
    # 創建簡單的市場數據
    data = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='1H'),
        'open': [50000.0] * 100,
        'high': [51000.0] * 100,
        'low': [49000.0] * 100,
        'close': [50500.0] * 100,
        'volume': [1000.0] * 100,
    })
    
    # 創建策略
    strategy = create_test_strategy()
    
    # 創建回測引擎
    engine = BacktestEngine(10000.0)
    
    # 運行回測
    result = engine.run_single_strategy(strategy, {"1h": data})
    
    # 驗證結果
    assert result.initial_capital == 10000.0
    assert result.strategy_id == "test-strategy"
    assert result.total_trades >= 0
    assert result.start_date is not None
    assert result.end_date is not None


def test_multi_strategy_backtest():
    """測試多策略回測"""
    # 創建市場數據
    data = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='1H'),
        'open': [50000.0] * 100,
        'high': [51000.0] * 100,
        'low': [49000.0] * 100,
        'close': [50500.0] * 100,
        'volume': [1000.0] * 100,
    })
    
    # 創建多個策略
    strategy1 = create_test_strategy("strategy-1")
    strategy2 = create_test_strategy("strategy-2")
    
    # 創建回測引擎
    engine = BacktestEngine(10000.0)
    
    # 運行多策略回測
    results = engine.run_multi_strategy(
        [strategy1, strategy2],
        {"1h": data},
        {"strategy-1": 0.6, "strategy-2": 0.4}
    )
    
    # 驗證結果
    assert len(results) == 2
    assert "strategy-1" in results
    assert "strategy-2" in results
    
    # 驗證資金分配
    assert results["strategy-1"].initial_capital == 6000.0  # 60%
    assert results["strategy-2"].initial_capital == 4000.0  # 40%


def test_calculate_metrics_empty_trades():
    """測試空交易列表的指標計算"""
    engine = BacktestEngine(10000.0)
    metrics = engine.calculate_metrics([])
    
    assert metrics['total_trades'] == 0
    assert metrics['win_rate'] == 0.0
    assert metrics['profit_factor'] == 0.0


def test_calculate_metrics_all_wins():
    """測試全部獲利的指標計算"""
    trades = []
    for i in range(10):
        trade = Trade(
            strategy_id="test",
            symbol="BTCUSDT",
            direction="long",
            entry_price=50000.0,
            exit_price=51000.0,
            size=0.1,
            leverage=1,
        )
        trade.pnl = 100.0
        trades.append(trade)
    
    engine = BacktestEngine(10000.0)
    metrics = engine.calculate_metrics(trades)
    
    assert metrics['total_trades'] == 10
    assert metrics['winning_trades'] == 10
    assert metrics['losing_trades'] == 0
    assert metrics['win_rate'] == 1.0
    assert metrics['total_pnl'] == 1000.0


def test_calculate_metrics_all_losses():
    """測試全部虧損的指標計算"""
    trades = []
    for i in range(10):
        trade = Trade(
            strategy_id="test",
            symbol="BTCUSDT",
            direction="long",
            entry_price=50000.0,
            exit_price=49000.0,
            size=0.1,
            leverage=1,
        )
        trade.pnl = -100.0
        trades.append(trade)
    
    engine = BacktestEngine(10000.0)
    metrics = engine.calculate_metrics(trades)
    
    assert metrics['total_trades'] == 10
    assert metrics['winning_trades'] == 0
    assert metrics['losing_trades'] == 10
    assert metrics['win_rate'] == 0.0
    assert metrics['total_pnl'] == -1000.0
    assert metrics['profit_factor'] == 0.0


def test_backtest_with_date_range():
    """測試指定日期範圍的回測"""
    # 創建市場數據
    data = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='1H'),
        'open': [50000.0] * 100,
        'high': [51000.0] * 100,
        'low': [49000.0] * 100,
        'close': [50500.0] * 100,
        'volume': [1000.0] * 100,
    })
    
    # 創建策略
    strategy = create_test_strategy()
    
    # 創建回測引擎
    engine = BacktestEngine(10000.0)
    
    # 運行回測（指定日期範圍）
    start_date = datetime(2024, 1, 10)
    end_date = datetime(2024, 1, 20)
    
    result = engine.run_single_strategy(
        strategy,
        {"1h": data},
        start_date=start_date,
        end_date=end_date
    )
    
    # 驗證日期範圍
    assert result.start_date >= start_date
    assert result.end_date <= end_date
