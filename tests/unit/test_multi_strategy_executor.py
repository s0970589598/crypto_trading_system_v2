"""
MultiStrategyExecutor 單元測試

測試多策略執行引擎的功能。
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.execution.multi_strategy_executor import MultiStrategyExecutor
from src.execution.strategy import Strategy
from src.managers.strategy_manager import StrategyManager
from src.managers.risk_manager import RiskManager
from src.models.config import StrategyConfig, RiskManagement, ExitConditions, NotificationConfig
from src.models.risk import RiskConfig
from src.models.market_data import MarketData, TimeframeData
from src.models.trading import Signal, Position


class SimpleTestStrategy(Strategy):
    """簡單測試策略"""
    
    def __init__(self, config: StrategyConfig, signal_action: str = 'HOLD'):
        super().__init__(config)
        self.signal_action = signal_action
        self.call_count = 0
    
    def generate_signal(self, market_data: MarketData) -> Signal:
        self.call_count += 1
        
        if self.signal_action == 'HOLD':
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
        
        # 獲取當前價格
        tf = market_data.get_timeframe(self.config.timeframes[0])
        price = tf.get_latest()['close']
        
        return Signal(
            strategy_id=self.config.strategy_id,
            timestamp=market_data.timestamp,
            symbol=self.config.symbol,
            action=self.signal_action,
            direction='long' if self.signal_action == 'BUY' else 'short',
            entry_price=price,
            stop_loss=price * 0.98,
            take_profit=price * 1.04,
            position_size=self.config.risk_management.position_size,  # 使用配置的倉位比例
            confidence=0.8,
        )
    
    def calculate_position_size(self, capital: float, price: float) -> float:
        return (capital * self.config.risk_management.position_size) / price
    
    def calculate_stop_loss(self, entry_price: float, direction: str, atr: float) -> float:
        if direction == 'long':
            return entry_price - (atr * 1.5)
        else:
            return entry_price + (atr * 1.5)
    
    def calculate_take_profit(self, entry_price: float, direction: str, atr: float) -> float:
        if direction == 'long':
            return entry_price + (atr * 3.0)
        else:
            return entry_price - (atr * 3.0)
    
    def should_exit(self, position: Position, market_data: MarketData) -> bool:
        # 獲取當前價格
        tf = market_data.get_timeframe(self.config.timeframes[0])
        current_price = tf.get_latest()['close']
        
        # 檢查止損和獲利
        if position.direction == 'long':
            if current_price <= position.stop_loss or current_price >= position.take_profit:
                return True
        else:
            if current_price >= position.stop_loss or current_price <= position.take_profit:
                return True
        
        return False


@pytest.fixture
def risk_manager():
    """創建風險管理器"""
    config = RiskConfig(
        global_max_drawdown=0.5,  # 50%
        daily_loss_limit=0.5,  # 50%
        global_max_position=0.9,  # 90%
        strategy_max_position=0.5,  # 50%（允許單策略使用 50% 資金）
    )
    return RiskManager(config, 10000.0)


@pytest.fixture
def strategy_manager(tmp_path):
    """創建策略管理器"""
    return StrategyManager(str(tmp_path))


@pytest.fixture
def executor(strategy_manager, risk_manager):
    """創建多策略執行引擎"""
    return MultiStrategyExecutor(strategy_manager, risk_manager)


@pytest.fixture
def test_strategy():
    """創建測試策略"""
    config = StrategyConfig(
        strategy_id="test-strategy-1",
        strategy_name="Test Strategy 1",
        version="1.0.0",
        enabled=True,
        symbol="BTCUSDT",
        timeframes=["1h"],
        parameters={},
        risk_management=RiskManagement(
            position_size=0.1,  # 10% 倉位
            leverage=1,  # 1 倍槓桿
            max_trades_per_day=10,
            max_consecutive_losses=3,
            daily_loss_limit=0.1,
            stop_loss_atr=1.5,
            take_profit_atr=3.0,
        ),
        entry_conditions=[],
        exit_conditions=ExitConditions(stop_loss="", take_profit=""),
        notifications=NotificationConfig(telegram=False, email=False),
    )
    return SimpleTestStrategy(config)


@pytest.fixture
def market_data():
    """創建市場數據"""
    n_candles = 100
    base_price = 50000.0
    
    dates = pd.date_range(end=datetime.now(), periods=n_candles, freq='1h')
    df = pd.DataFrame({
        'timestamp': dates,
        'open': [base_price] * n_candles,
        'high': [base_price * 1.01] * n_candles,
        'low': [base_price * 0.99] * n_candles,
        'close': [base_price] * n_candles,
        'volume': [1000.0] * n_candles,
    })
    
    return MarketData(
        symbol="BTCUSDT",
        timestamp=datetime.now(),
        timeframes={
            '1h': TimeframeData(timeframe='1h', ohlcv=df, indicators={})
        }
    )


def test_executor_initialization(executor):
    """測試執行引擎初始化"""
    assert executor.strategy_manager is not None
    assert executor.risk_manager is not None
    assert len(executor.strategies) == 0
    assert len(executor.strategy_states) == 0


def test_add_strategy(executor, test_strategy):
    """測試添加策略"""
    executor.add_strategy(test_strategy, priority=1)
    
    assert "test-strategy-1" in executor.strategies
    assert "test-strategy-1" in executor.strategy_states
    assert "test-strategy-1" in executor.positions
    assert "test-strategy-1" in executor.trade_history
    assert executor.signal_priority["test-strategy-1"] == 1


def test_remove_strategy(executor, test_strategy):
    """測試移除策略"""
    executor.add_strategy(test_strategy)
    
    # 移除策略
    result = executor.remove_strategy("test-strategy-1")
    assert result
    assert "test-strategy-1" not in executor.strategies


def test_remove_strategy_with_position(executor, test_strategy, market_data):
    """測試移除有持倉的策略（應該失敗）"""
    test_strategy.signal_action = 'BUY'
    executor.add_strategy(test_strategy)
    
    # 生成並執行信號
    signals = executor.generate_signals(market_data)
    filtered = executor.filter_signals(signals)
    if filtered:
        executor.execute_signal(filtered[0], market_data)
    
    # 嘗試移除（應該失敗）
    result = executor.remove_strategy("test-strategy-1")
    assert not result
    assert "test-strategy-1" in executor.strategies


def test_get_strategy_capital_equal_allocation(executor, test_strategy):
    """測試資金分配（平均分配）"""
    executor.add_strategy(test_strategy)
    
    # 添加第二個策略
    config2 = test_strategy.config
    config2.strategy_id = "test-strategy-2"
    strategy2 = SimpleTestStrategy(config2)
    executor.add_strategy(strategy2)
    
    # 每個策略應該獲得 50% 的資金
    capital1 = executor.get_strategy_capital("test-strategy-1")
    capital2 = executor.get_strategy_capital("test-strategy-2")
    
    assert capital1 == 5000.0  # 10000 * 0.5
    assert capital2 == 5000.0


def test_get_strategy_capital_custom_allocation(strategy_manager, risk_manager):
    """測試資金分配（自定義分配）"""
    allocation = {
        "test-strategy-1": 0.6,
        "test-strategy-2": 0.4,
    }
    executor = MultiStrategyExecutor(strategy_manager, risk_manager, allocation)
    
    config = StrategyConfig(
        strategy_id="test-strategy-1",
        strategy_name="Test Strategy 1",
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
        exit_conditions=ExitConditions(stop_loss="", take_profit=""),
        notifications=NotificationConfig(telegram=False, email=False),
    )
    
    strategy1 = SimpleTestStrategy(config)
    executor.add_strategy(strategy1)
    
    config2 = config
    config2.strategy_id = "test-strategy-2"
    strategy2 = SimpleTestStrategy(config2)
    executor.add_strategy(strategy2)
    
    capital1 = executor.get_strategy_capital("test-strategy-1")
    capital2 = executor.get_strategy_capital("test-strategy-2")
    
    assert capital1 == 6000.0  # 10000 * 0.6
    assert capital2 == 4000.0  # 10000 * 0.4


def test_generate_signals_hold(executor, test_strategy, market_data):
    """測試生成 HOLD 信號"""
    test_strategy.signal_action = 'HOLD'
    executor.add_strategy(test_strategy)
    
    signals = executor.generate_signals(market_data)
    
    # HOLD 信號不應該被添加到列表
    assert len(signals) == 0


def test_generate_signals_buy(executor, test_strategy, market_data):
    """測試生成 BUY 信號"""
    test_strategy.signal_action = 'BUY'
    executor.add_strategy(test_strategy)
    
    signals = executor.generate_signals(market_data)
    
    assert len(signals) == 1
    assert signals[0].action == 'BUY'
    assert signals[0].strategy_id == "test-strategy-1"


def test_generate_signals_disabled_strategy(executor, test_strategy, market_data):
    """測試禁用策略不生成信號"""
    test_strategy.signal_action = 'BUY'
    executor.add_strategy(test_strategy)
    
    # 禁用策略
    executor.strategy_states["test-strategy-1"].enabled = False
    
    signals = executor.generate_signals(market_data)
    
    assert len(signals) == 0


def test_filter_signals_priority(executor, market_data):
    """測試信號優先級過濾"""
    # 創建兩個策略
    config1 = StrategyConfig(
        strategy_id="high-priority",
        strategy_name="High Priority",
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
        exit_conditions=ExitConditions(stop_loss="", take_profit=""),
        notifications=NotificationConfig(telegram=False, email=False),
    )
    
    strategy1 = SimpleTestStrategy(config1, 'BUY')
    executor.add_strategy(strategy1, priority=1)
    
    config2 = StrategyConfig(
        strategy_id="low-priority",
        strategy_name="Low Priority",
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
        exit_conditions=ExitConditions(stop_loss="", take_profit=""),
        notifications=NotificationConfig(telegram=False, email=False),
    )
    strategy2 = SimpleTestStrategy(config2, 'BUY')
    executor.add_strategy(strategy2, priority=10)
    
    signals = executor.generate_signals(market_data)
    filtered = executor.filter_signals(signals)
    
    # 高優先級信號應該排在前面
    assert filtered[0].strategy_id == "high-priority"
    assert filtered[1].strategy_id == "low-priority"


def test_execute_signal(executor, test_strategy, market_data):
    """測試執行信號"""
    test_strategy.signal_action = 'BUY'
    executor.add_strategy(test_strategy)
    
    signals = executor.generate_signals(market_data)
    filtered = executor.filter_signals(signals)
    
    position = executor.execute_signal(filtered[0], market_data)
    
    assert position is not None
    assert position.strategy_id == "test-strategy-1"
    assert position.direction == 'long'
    assert executor.positions["test-strategy-1"] is not None


def test_execute_signal_with_existing_position(executor, test_strategy, market_data):
    """測試執行信號時已有持倉（應該失敗）"""
    test_strategy.signal_action = 'BUY'
    executor.add_strategy(test_strategy)
    
    signals = executor.generate_signals(market_data)
    filtered = executor.filter_signals(signals)
    
    # 第一次執行
    executor.execute_signal(filtered[0], market_data)
    
    # 第二次執行（應該失敗）
    position2 = executor.execute_signal(filtered[0], market_data)
    assert position2 is None


def test_check_exits_no_exit(executor, test_strategy, market_data):
    """測試檢查出場（不出場）"""
    test_strategy.signal_action = 'BUY'
    executor.add_strategy(test_strategy)
    
    signals = executor.generate_signals(market_data)
    filtered = executor.filter_signals(signals)
    executor.execute_signal(filtered[0], market_data)
    
    # 價格沒有變化，不應該出場
    trades = executor.check_exits(market_data)
    assert len(trades) == 0


def test_check_exits_stop_loss(executor, test_strategy, market_data):
    """測試檢查出場（止損）"""
    test_strategy.signal_action = 'BUY'
    executor.add_strategy(test_strategy)
    
    signals = executor.generate_signals(market_data)
    filtered = executor.filter_signals(signals)
    executor.execute_signal(filtered[0], market_data)
    
    # 修改價格觸發止損
    position = executor.positions["test-strategy-1"]
    market_data.timeframes['1h'].ohlcv.iloc[-1, market_data.timeframes['1h'].ohlcv.columns.get_loc('close')] = position.stop_loss - 100
    
    trades = executor.check_exits(market_data)
    assert len(trades) == 1
    assert trades[0].exit_reason == "策略出場"


def test_get_strategy_state(executor, test_strategy):
    """測試獲取策略狀態"""
    executor.add_strategy(test_strategy)
    
    state = executor.get_strategy_state("test-strategy-1")
    assert state is not None
    assert state.strategy_id == "test-strategy-1"
    assert state.enabled


def test_get_all_states(executor, test_strategy):
    """測試獲取所有策略狀態"""
    executor.add_strategy(test_strategy)
    
    config2 = test_strategy.config
    config2.strategy_id = "test-strategy-2"
    strategy2 = SimpleTestStrategy(config2)
    executor.add_strategy(strategy2)
    
    states = executor.get_all_states()
    assert len(states) == 2
    assert "test-strategy-1" in states
    assert "test-strategy-2" in states


def test_get_trade_history_single_strategy(executor, test_strategy, market_data):
    """測試獲取單個策略的交易歷史"""
    test_strategy.signal_action = 'BUY'
    executor.add_strategy(test_strategy)
    
    # 執行交易
    signals = executor.generate_signals(market_data)
    filtered = executor.filter_signals(signals)
    executor.execute_signal(filtered[0], market_data)
    
    # 觸發出場
    position = executor.positions["test-strategy-1"]
    market_data.timeframes['1h'].ohlcv.iloc[-1, market_data.timeframes['1h'].ohlcv.columns.get_loc('close')] = position.take_profit + 100
    executor.check_exits(market_data)
    
    history = executor.get_trade_history("test-strategy-1")
    assert len(history) == 1
    assert history[0].strategy_id == "test-strategy-1"


def test_get_trade_history_all_strategies(executor, market_data):
    """測試獲取所有策略的交易歷史"""
    # 創建兩個策略
    config1 = StrategyConfig(
        strategy_id="strategy-1",
        strategy_name="Strategy 1",
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
        exit_conditions=ExitConditions(stop_loss="", take_profit=""),
        notifications=NotificationConfig(telegram=False, email=False),
    )
    
    strategy1 = SimpleTestStrategy(config1, 'BUY')
    executor.add_strategy(strategy1)
    
    config2 = StrategyConfig(
        strategy_id="strategy-2",
        strategy_name="Strategy 2",
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
        exit_conditions=ExitConditions(stop_loss="", take_profit=""),
        notifications=NotificationConfig(telegram=False, email=False),
    )
    strategy2 = SimpleTestStrategy(config2, 'BUY')
    executor.add_strategy(strategy2)
    
    # 執行第一個策略的交易
    signals = executor.generate_signals(market_data)
    filtered = [s for s in executor.filter_signals(signals) if s.strategy_id == "strategy-1"]
    if filtered:
        executor.execute_signal(filtered[0], market_data)
        position = executor.positions["strategy-1"]
        if position:
            market_data.timeframes['1h'].ohlcv.iloc[-1, market_data.timeframes['1h'].ohlcv.columns.get_loc('close')] = position.take_profit + 100
            executor.check_exits(market_data)
    
    # 執行第二個策略的交易
    signals = executor.generate_signals(market_data)
    filtered = [s for s in executor.filter_signals(signals) if s.strategy_id == "strategy-2"]
    if filtered:
        executor.execute_signal(filtered[0], market_data)
        position = executor.positions["strategy-2"]
        if position:
            market_data.timeframes['1h'].ohlcv.iloc[-1, market_data.timeframes['1h'].ohlcv.columns.get_loc('close')] = position.take_profit + 100
            executor.check_exits(market_data)
    
    # 獲取所有交易
    all_history = executor.get_trade_history()
    assert len(all_history) >= 1  # 至少有一個交易


def test_reset_daily_stats(executor, test_strategy):
    """測試重置每日統計"""
    executor.add_strategy(test_strategy)
    
    # 修改統計
    state = executor.strategy_states["test-strategy-1"]
    state.trades_today = 5
    state.pnl_today = 100.0
    
    # 重置
    executor.reset_daily_stats()
    
    assert state.trades_today == 0
    assert state.pnl_today == 0.0
