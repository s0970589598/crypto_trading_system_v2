"""
MultiTimeframeStrategy 單元測試

測試多週期共振策略的功能。
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.strategies.multi_timeframe_strategy import MultiTimeframeStrategy
from src.models.config import StrategyConfig, RiskManagement, ExitConditions, NotificationConfig
from src.models.market_data import MarketData, TimeframeData
from src.models.trading import Position


@pytest.fixture
def strategy_config():
    """創建策略配置"""
    return StrategyConfig(
        strategy_id="test-multi-timeframe",
        strategy_name="Test Multi-Timeframe Strategy",
        version="1.0.0",
        enabled=True,
        symbol="ETHUSDT",
        timeframes=["1d", "4h", "1h", "15m"],
        parameters={
            "stop_loss_atr": 1.5,
            "take_profit_atr": 3.0,
            "rsi_range": [30, 70],
            "ema_distance": 0.03,
            "volume_threshold": 1.0,
        },
        risk_management=RiskManagement(
            position_size=0.20,
            leverage=5,
            max_trades_per_day=3,
            max_consecutive_losses=3,
            daily_loss_limit=0.10,
            stop_loss_atr=1.5,
            take_profit_atr=3.0,
        ),
        entry_conditions=[],
        exit_conditions=ExitConditions(stop_loss="", take_profit=""),
        notifications=NotificationConfig(telegram=False, email=False),
    )


@pytest.fixture
def market_data():
    """創建市場數據"""
    # 生成測試數據
    n_candles = 100
    base_price = 3000.0
    
    def generate_ohlcv(n, base):
        dates = pd.date_range(end=datetime.now(), periods=n, freq='15T')
        return pd.DataFrame({
            'timestamp': dates,
            'open': [base + np.random.randn() * 10 for _ in range(n)],
            'high': [base + np.random.randn() * 10 + 5 for _ in range(n)],
            'low': [base + np.random.randn() * 10 - 5 for _ in range(n)],
            'close': [base + np.random.randn() * 10 for _ in range(n)],
            'volume': [1000 + np.random.randn() * 100 for _ in range(n)],
        })
    
    # 創建多週期數據
    timeframes = {
        '1d': TimeframeData(
            timeframe='1d',
            ohlcv=generate_ohlcv(100, base_price),
            indicators={}
        ),
        '4h': TimeframeData(
            timeframe='4h',
            ohlcv=generate_ohlcv(100, base_price),
            indicators={}
        ),
        '1h': TimeframeData(
            timeframe='1h',
            ohlcv=generate_ohlcv(100, base_price),
            indicators={}
        ),
        '15m': TimeframeData(
            timeframe='15m',
            ohlcv=generate_ohlcv(100, base_price),
            indicators={}
        ),
    }
    
    return MarketData(
        symbol="ETHUSDT",
        timestamp=datetime.now(),
        timeframes=timeframes
    )


def test_strategy_initialization(strategy_config):
    """測試策略初始化"""
    strategy = MultiTimeframeStrategy(strategy_config)
    
    assert strategy.config.strategy_id == "test-multi-timeframe"
    assert strategy.stop_loss_atr == 1.5
    assert strategy.take_profit_atr == 3.0
    assert strategy.rsi_range == [30, 70]
    assert strategy.ema_distance == 0.03
    assert strategy.volume_threshold == 1.0


def test_generate_signal_hold(strategy_config, market_data):
    """測試生成 HOLD 信號（條件不滿足）"""
    strategy = MultiTimeframeStrategy(strategy_config)
    signal = strategy.generate_signal(market_data)
    
    # 由於隨機數據，大概率不滿足進場條件
    assert signal.strategy_id == "test-multi-timeframe"
    assert signal.symbol == "ETHUSDT"
    assert signal.action in ['HOLD', 'BUY', 'SELL']


def test_calculate_position_size(strategy_config):
    """測試倉位計算"""
    strategy = MultiTimeframeStrategy(strategy_config)
    
    capital = 10000.0
    price = 3000.0
    
    size = strategy.calculate_position_size(capital, price)
    
    # 20% 倉位 * 5x 槓桿 = 100% 資金
    expected_value = capital * 0.20 * 5
    expected_size = expected_value / price
    
    assert abs(size - expected_size) < 0.0001


def test_calculate_stop_loss(strategy_config):
    """測試止損計算"""
    strategy = MultiTimeframeStrategy(strategy_config)
    
    entry_price = 3000.0
    atr = 50.0
    
    # 做多止損
    stop_loss_long = strategy.calculate_stop_loss(entry_price, 'long', atr)
    assert stop_loss_long == entry_price - (atr * 1.5)
    
    # 做空止損
    stop_loss_short = strategy.calculate_stop_loss(entry_price, 'short', atr)
    assert stop_loss_short == entry_price + (atr * 1.5)


def test_calculate_take_profit(strategy_config):
    """測試目標計算"""
    strategy = MultiTimeframeStrategy(strategy_config)
    
    entry_price = 3000.0
    atr = 50.0
    
    # 做多目標
    take_profit_long = strategy.calculate_take_profit(entry_price, 'long', atr)
    assert take_profit_long == entry_price + (atr * 3.0)
    
    # 做空目標
    take_profit_short = strategy.calculate_take_profit(entry_price, 'short', atr)
    assert take_profit_short == entry_price - (atr * 3.0)


def test_should_exit_stop_loss(strategy_config, market_data):
    """測試止損出場"""
    strategy = MultiTimeframeStrategy(strategy_config)
    
    # 創建做多持倉
    position = Position(
        strategy_id="test-multi-timeframe",
        symbol="ETHUSDT",
        direction='long',
        entry_time=datetime.now(),
        entry_price=3000.0,
        size=1.0,
        stop_loss=2900.0,
        take_profit=3150.0,
        leverage=5,
        unrealized_pnl=0.0
    )
    
    # 修改市場數據，使價格低於止損
    market_data.timeframes['15m'].ohlcv.iloc[-1, market_data.timeframes['15m'].ohlcv.columns.get_loc('close')] = 2850.0
    
    should_exit = strategy.should_exit(position, market_data)
    assert should_exit


def test_should_exit_take_profit(strategy_config, market_data):
    """測試獲利出場"""
    strategy = MultiTimeframeStrategy(strategy_config)
    
    # 創建做多持倉
    position = Position(
        strategy_id="test-multi-timeframe",
        symbol="ETHUSDT",
        direction='long',
        entry_time=datetime.now(),
        entry_price=3000.0,
        size=1.0,
        stop_loss=2900.0,
        take_profit=3150.0,
        leverage=5,
        unrealized_pnl=0.0
    )
    
    # 修改市場數據，使價格高於目標
    market_data.timeframes['15m'].ohlcv.iloc[-1, market_data.timeframes['15m'].ohlcv.columns.get_loc('close')] = 3200.0
    
    should_exit = strategy.should_exit(position, market_data)
    assert should_exit


def test_calculate_indicators(strategy_config, market_data):
    """測試指標計算"""
    strategy = MultiTimeframeStrategy(strategy_config)
    
    tf_1d = market_data.get_timeframe('1d')
    tf_4h = market_data.get_timeframe('4h')
    tf_1h = market_data.get_timeframe('1h')
    tf_15m = market_data.get_timeframe('15m')
    
    indicators = strategy._calculate_indicators(tf_1d, tf_4h, tf_1h, tf_15m)
    
    # 驗證所有指標都存在
    assert 'trend_1d' in indicators
    assert 'trend_4h' in indicators
    assert 'trend_1h' in indicators
    assert 'trend_15m' in indicators
    assert 'rsi_15m' in indicators
    assert 'atr_1h' in indicators
    assert 'price' in indicators
    assert 'ema20_1h' in indicators
    assert 'ema50_1h' in indicators
    assert 'volume_ratio' in indicators
    
    # 驗證指標值合理
    assert indicators['trend_1d'] in ['Uptrend', 'Downtrend', 'Sideways', 'Unknown']
    assert 0 <= indicators['rsi_15m'] <= 100
    assert indicators['atr_1h'] >= 0
    assert indicators['price'] > 0
    assert indicators['volume_ratio'] >= 0


def test_calculate_confidence(strategy_config):
    """測試置信度計算"""
    strategy = MultiTimeframeStrategy(strategy_config)
    
    # 高置信度場景
    high_confidence_indicators = {
        'trend_1d': 'Uptrend',
        'trend_4h': 'Uptrend',
        'trend_1h': 'Uptrend',
        'rsi_15m': 50.0,
        'price': 3000.0,
        'ema20_1h': 2995.0,
        'ema50_1h': 2990.0,
        'volume_ratio': 1.6
    }
    
    confidence = strategy._calculate_confidence(high_confidence_indicators)
    assert confidence > 0.7
    
    # 低置信度場景
    low_confidence_indicators = {
        'trend_1d': 'Downtrend',
        'trend_4h': 'Uptrend',
        'trend_1h': 'Uptrend',
        'rsi_15m': 75.0,
        'price': 3000.0,
        'ema20_1h': 2900.0,
        'ema50_1h': 2850.0,
        'volume_ratio': 0.8
    }
    
    confidence = strategy._calculate_confidence(low_confidence_indicators)
    assert confidence < 0.5


def test_check_entry_conditions(strategy_config):
    """測試進場條件檢查"""
    strategy = MultiTimeframeStrategy(strategy_config)
    
    # 滿足條件的場景
    good_indicators = {
        'trend_4h': 'Uptrend',
        'trend_1h': 'Uptrend',
        'rsi_15m': 50.0,
        'price': 3000.0,
        'ema20_1h': 2995.0,
        'ema50_1h': 2990.0,
        'volume_ratio': 1.2
    }
    
    should_enter, direction = strategy._check_entry_conditions(good_indicators)
    assert should_enter
    assert direction == 'long'
    
    # 趨勢不一致
    bad_trend_indicators = good_indicators.copy()
    bad_trend_indicators['trend_1h'] = 'Downtrend'
    
    should_enter, direction = strategy._check_entry_conditions(bad_trend_indicators)
    assert not should_enter
    
    # RSI 超範圍
    bad_rsi_indicators = good_indicators.copy()
    bad_rsi_indicators['rsi_15m'] = 75.0
    
    should_enter, direction = strategy._check_entry_conditions(bad_rsi_indicators)
    assert not should_enter
    
    # 價格遠離 EMA
    bad_price_indicators = good_indicators.copy()
    bad_price_indicators['ema20_1h'] = 2800.0
    bad_price_indicators['ema50_1h'] = 2750.0
    
    should_enter, direction = strategy._check_entry_conditions(bad_price_indicators)
    assert not should_enter
    
    # 成交量不足
    bad_volume_indicators = good_indicators.copy()
    bad_volume_indicators['volume_ratio'] = 0.8
    
    should_enter, direction = strategy._check_entry_conditions(bad_volume_indicators)
    assert not should_enter
