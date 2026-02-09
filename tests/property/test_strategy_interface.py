"""
策略接口屬性測試

驗證所有實現 Strategy 接口的策略類都正確實現了所有必需方法。
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime
import pandas as pd
import inspect

from src.execution.strategy import Strategy
from src.models.config import StrategyConfig, RiskManagement, ExitConditions, NotificationConfig
from src.models.market_data import MarketData, TimeframeData
from src.models.trading import Position


# ============================================================================
# 測試數據生成器
# ============================================================================

@st.composite
def strategy_config_strategy(draw):
    """生成有效的策略配置"""
    return StrategyConfig(
        strategy_id=draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='-_'))),
        strategy_name=draw(st.text(min_size=1, max_size=50)),
        version=draw(st.from_regex(r'\d+\.\d+\.\d+', fullmatch=True)),
        enabled=draw(st.booleans()),
        symbol=draw(st.sampled_from(['BTCUSDT', 'ETHUSDT', 'BNBUSDT'])),
        timeframes=draw(st.lists(
            st.sampled_from(['1m', '5m', '15m', '1h', '4h', '1d']),
            min_size=1, max_size=4, unique=True
        )),
        parameters=draw(st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.one_of(st.floats(min_value=0.1, max_value=10.0), st.integers(min_value=1, max_value=100)),
            min_size=0, max_size=5
        )),
        risk_management=RiskManagement(
            position_size=draw(st.floats(min_value=0.01, max_value=1.0)),
            leverage=draw(st.integers(min_value=1, max_value=20)),
            max_trades_per_day=draw(st.integers(min_value=1, max_value=10)),
            max_consecutive_losses=draw(st.integers(min_value=1, max_value=5)),
            daily_loss_limit=draw(st.floats(min_value=0.01, max_value=0.5)),
            stop_loss_atr=draw(st.floats(min_value=0.5, max_value=5.0)),
            take_profit_atr=draw(st.floats(min_value=1.0, max_value=10.0)),
        ),
        entry_conditions=draw(st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=5)),
        exit_conditions=ExitConditions(
            stop_loss='price - (atr * stop_loss_atr)',
            take_profit='price + (atr * take_profit_atr)',
        ),
        notifications=NotificationConfig(
            telegram=draw(st.booleans()),
            email=draw(st.booleans()),
        ),
    )


@st.composite
def market_data_strategy(draw):
    """生成有效的市場數據"""
    n_candles = draw(st.integers(min_value=50, max_value=200))
    base_price = draw(st.floats(min_value=1000, max_value=100000))
    
    # 生成 OHLCV 數據
    timestamps = [datetime.now() for _ in range(n_candles)]
    opens = [base_price * draw(st.floats(min_value=0.95, max_value=1.05)) for _ in range(n_candles)]
    highs = [o * draw(st.floats(min_value=1.0, max_value=1.02)) for o in opens]
    lows = [o * draw(st.floats(min_value=0.98, max_value=1.0)) for o in opens]
    closes = [draw(st.floats(min_value=l, max_value=h)) for l, h in zip(lows, highs)]
    volumes = [draw(st.floats(min_value=100, max_value=10000)) for _ in range(n_candles)]
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes,
    })
    
    # 生成指標
    indicators = {
        'RSI': pd.Series([draw(st.floats(min_value=0, max_value=100)) for _ in range(n_candles)]),
        'ATR': pd.Series([draw(st.floats(min_value=10, max_value=1000)) for _ in range(n_candles)]),
    }
    
    timeframe = draw(st.sampled_from(['1m', '5m', '15m', '1h', '4h', '1d']))
    
    tf_data = TimeframeData(
        timeframe=timeframe,
        ohlcv=df,
        indicators=indicators,
    )
    
    return MarketData(
        symbol=draw(st.sampled_from(['BTCUSDT', 'ETHUSDT'])),
        timestamp=datetime.now(),
        timeframes={timeframe: tf_data}
    )


# ============================================================================
# 測試策略實現（用於測試）
# ============================================================================

class TestStrategy(Strategy):
    """測試用的策略實現"""
    
    def generate_signal(self, market_data: MarketData):
        from src.models.trading import Signal
        return Signal(
            strategy_id=self.strategy_id,
            timestamp=datetime.now(),
            symbol=self.symbol,
            action='HOLD',
            direction=None,
            entry_price=market_data.get_latest_price(),
            stop_loss=0,
            take_profit=0,
            position_size=0,
            confidence=0.5,
            metadata={}
        )
    
    def calculate_position_size(self, capital: float, price: float) -> float:
        return (capital * self.risk_management.position_size) / price
    
    def calculate_stop_loss(self, entry_price: float, direction: str, atr: float) -> float:
        if direction == 'long':
            return entry_price - (atr * self.risk_management.stop_loss_atr)
        elif direction == 'short':
            return entry_price + (atr * self.risk_management.stop_loss_atr)
        return 0
    
    def calculate_take_profit(self, entry_price: float, direction: str, atr: float) -> float:
        if direction == 'long':
            return entry_price + (atr * self.risk_management.take_profit_atr)
        elif direction == 'short':
            return entry_price - (atr * self.risk_management.take_profit_atr)
        return 0
    
    def should_exit(self, position: Position, market_data: MarketData) -> tuple[bool, str]:
        current_price = market_data.get_latest_price()
        if position.should_stop_loss(current_price):
            return True, '止損'
        if position.should_take_profit(current_price):
            return True, '獲利'
        return False, ''


class IncompleteStrategy(Strategy):
    """不完整的策略實現（缺少方法）"""
    
    def generate_signal(self, market_data: MarketData):
        from src.models.trading import Signal
        return Signal(
            strategy_id=self.strategy_id,
            timestamp=datetime.now(),
            symbol=self.symbol,
            action='HOLD',
            direction=None,
            entry_price=0,
            stop_loss=0,
            take_profit=0,
            position_size=0,
            confidence=0.5,
            metadata={}
        )
    
    # 故意不實現其他方法


# ============================================================================
# 屬性測試
# ============================================================================

# Feature: multi-strategy-system, Property 8: 策略接口一致性
@given(config=strategy_config_strategy())
@settings(max_examples=100, deadline=None)
def test_strategy_interface_consistency(config):
    """
    Property 8: 策略接口一致性
    
    對於任何實現 Strategy 接口的策略類，該類必須實現所有必需的方法：
    - generate_signal
    - calculate_position_size
    - calculate_stop_loss
    - calculate_take_profit
    - should_exit
    
    Validates: Requirements 3.2
    """
    # 創建測試策略實例
    strategy = TestStrategy(config)
    
    # 驗證策略是 Strategy 的子類
    assert isinstance(strategy, Strategy), "策略必須繼承 Strategy 基類"
    
    # 驗證所有必需方法都存在且可調用
    required_methods = [
        'generate_signal',
        'calculate_position_size',
        'calculate_stop_loss',
        'calculate_take_profit',
        'should_exit',
    ]
    
    for method_name in required_methods:
        assert hasattr(strategy, method_name), f"策略必須實現 {method_name} 方法"
        method = getattr(strategy, method_name)
        assert callable(method), f"{method_name} 必須是可調用的方法"
    
    # 驗證方法簽名正確
    # generate_signal(market_data: MarketData) -> Signal
    sig = inspect.signature(strategy.generate_signal)
    assert len(sig.parameters) == 1, "generate_signal 必須接受 1 個參數（market_data）"
    
    # calculate_position_size(capital: float, price: float) -> float
    sig = inspect.signature(strategy.calculate_position_size)
    assert len(sig.parameters) == 2, "calculate_position_size 必須接受 2 個參數（capital, price）"
    
    # calculate_stop_loss(entry_price: float, direction: str, atr: float) -> float
    sig = inspect.signature(strategy.calculate_stop_loss)
    assert len(sig.parameters) == 3, "calculate_stop_loss 必須接受 3 個參數（entry_price, direction, atr）"
    
    # calculate_take_profit(entry_price: float, direction: str, atr: float) -> float
    sig = inspect.signature(strategy.calculate_take_profit)
    assert len(sig.parameters) == 3, "calculate_take_profit 必須接受 3 個參數（entry_price, direction, atr）"
    
    # should_exit(position: Position, market_data: MarketData) -> tuple[bool, str]
    sig = inspect.signature(strategy.should_exit)
    assert len(sig.parameters) == 2, "should_exit 必須接受 2 個參數（position, market_data）"


@given(config=strategy_config_strategy(), market_data=market_data_strategy())
@settings(max_examples=100, deadline=None)
def test_strategy_methods_callable(config, market_data):
    """
    驗證策略的所有方法都可以正常調用且返回正確類型
    
    Validates: Requirements 3.2
    """
    strategy = TestStrategy(config)
    
    # 測試 generate_signal
    signal = strategy.generate_signal(market_data)
    assert signal is not None, "generate_signal 必須返回 Signal 對象"
    assert hasattr(signal, 'action'), "Signal 必須有 action 屬性"
    assert signal.action in ['BUY', 'SELL', 'HOLD'], "action 必須是 BUY/SELL/HOLD"
    
    # 測試 calculate_position_size
    capital = 1000.0
    price = market_data.get_latest_price()
    position_size = strategy.calculate_position_size(capital, price)
    assert isinstance(position_size, (int, float)), "calculate_position_size 必須返回數值"
    assert position_size >= 0, "倉位大小不能為負數"
    
    # 測試 calculate_stop_loss
    entry_price = price
    atr = 100.0
    
    stop_loss_long = strategy.calculate_stop_loss(entry_price, 'long', atr)
    assert isinstance(stop_loss_long, (int, float)), "calculate_stop_loss 必須返回數值"
    assert stop_loss_long < entry_price, "做多止損必須低於進場價"
    
    stop_loss_short = strategy.calculate_stop_loss(entry_price, 'short', atr)
    assert isinstance(stop_loss_short, (int, float)), "calculate_stop_loss 必須返回數值"
    assert stop_loss_short > entry_price, "做空止損必須高於進場價"
    
    # 測試 calculate_take_profit
    take_profit_long = strategy.calculate_take_profit(entry_price, 'long', atr)
    assert isinstance(take_profit_long, (int, float)), "calculate_take_profit 必須返回數值"
    assert take_profit_long > entry_price, "做多目標必須高於進場價"
    
    take_profit_short = strategy.calculate_take_profit(entry_price, 'short', atr)
    assert isinstance(take_profit_short, (int, float)), "calculate_take_profit 必須返回數值"
    assert take_profit_short < entry_price, "做空目標必須低於進場價"
    
    # 測試 should_exit
    position = Position(
        strategy_id=strategy.strategy_id,
        symbol=strategy.symbol,
        direction='long',
        entry_time=datetime.now(),
        entry_price=entry_price,
        size=position_size,
        stop_loss=stop_loss_long,
        take_profit=take_profit_long,
        leverage=config.risk_management.leverage,
    )
    
    should_exit, reason = strategy.should_exit(position, market_data)
    assert isinstance(should_exit, bool), "should_exit 必須返回布爾值"
    assert isinstance(reason, str), "should_exit 必須返回字符串原因"


# ============================================================================
# 單元測試
# ============================================================================

def test_incomplete_strategy_cannot_instantiate():
    """
    測試不完整的策略類無法實例化
    
    Validates: Requirements 3.2
    """
    config = StrategyConfig(
        strategy_id='test',
        strategy_name='Test',
        version='1.0.0',
        enabled=True,
        symbol='BTCUSDT',
        timeframes=['1h'],
        parameters={},
        risk_management=RiskManagement(
            position_size=0.2,
            leverage=5,
            max_trades_per_day=3,
            max_consecutive_losses=3,
            daily_loss_limit=0.1,
            stop_loss_atr=1.5,
            take_profit_atr=3.0,
        ),
        entry_conditions=[],
        exit_conditions=ExitConditions(
            stop_loss='price - (atr * 1.5)',
            take_profit='price + (atr * 3.0)',
        ),
        notifications=NotificationConfig(telegram=False),
    )
    
    # 嘗試實例化不完整的策略應該失敗
    with pytest.raises(TypeError):
        IncompleteStrategy(config)


def test_strategy_initialization():
    """
    測試策略初始化正確設置所有屬性
    
    Validates: Requirements 3.2
    """
    config = StrategyConfig(
        strategy_id='test-strategy',
        strategy_name='測試策略',
        version='1.0.0',
        enabled=True,
        symbol='BTCUSDT',
        timeframes=['1h', '4h'],
        parameters={'custom_param': 100},
        risk_management=RiskManagement(
            position_size=0.2,
            leverage=5,
            max_trades_per_day=3,
            max_consecutive_losses=3,
            daily_loss_limit=0.1,
            stop_loss_atr=1.5,
            take_profit_atr=3.0,
        ),
        entry_conditions=['condition1', 'condition2'],
        exit_conditions=ExitConditions(
            stop_loss='price - (atr * 1.5)',
            take_profit='price + (atr * 3.0)',
        ),
        notifications=NotificationConfig(telegram=True),
    )
    
    strategy = TestStrategy(config)
    
    # 驗證所有屬性正確設置
    assert strategy.config == config
    assert strategy.strategy_id == 'test-strategy'
    assert strategy.strategy_name == '測試策略'
    assert strategy.symbol == 'BTCUSDT'
    assert strategy.timeframes == ['1h', '4h']
    assert strategy.parameters == {'custom_param': 100}
    assert strategy.risk_management == config.risk_management
    
    # 驗證輔助方法
    assert strategy.get_id() == 'test-strategy'
    assert strategy.get_name() == '測試策略'
    assert strategy.is_enabled() == True


def test_strategy_repr():
    """
    測試策略的字符串表示
    
    Validates: Requirements 3.2
    """
    config = StrategyConfig(
        strategy_id='test-id',
        strategy_name='Test Name',
        version='1.0.0',
        enabled=True,
        symbol='ETHUSDT',
        timeframes=['1h'],
        parameters={},
        risk_management=RiskManagement(
            position_size=0.2,
            leverage=5,
            max_trades_per_day=3,
            max_consecutive_losses=3,
            daily_loss_limit=0.1,
            stop_loss_atr=1.5,
            take_profit_atr=3.0,
        ),
        entry_conditions=[],
        exit_conditions=ExitConditions(
            stop_loss='price - (atr * 1.5)',
            take_profit='price + (atr * 3.0)',
        ),
        notifications=NotificationConfig(telegram=False),
    )
    
    strategy = TestStrategy(config)
    repr_str = repr(strategy)
    
    assert 'test-id' in repr_str
    assert 'Test Name' in repr_str
    assert 'ETHUSDT' in repr_str


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
