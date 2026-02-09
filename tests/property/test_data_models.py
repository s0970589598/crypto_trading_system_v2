"""
數據模型的屬性測試

Feature: multi-strategy-system
Property 10: 回測結果持久化往返
Property 19: 覆盤數據導出往返
Property 31: 數據導出往返
"""

import pytest
from hypothesis import given, strategies as st
from datetime import datetime, timedelta
import tempfile
import os

from src.models import BacktestResult, Trade, StrategyConfig


# ============================================================================
# Hypothesis 策略（生成器）
# ============================================================================

@st.composite
def trade_strategy(draw):
    """生成隨機交易記錄"""
    direction = draw(st.sampled_from(['long', 'short']))
    entry_price = draw(st.floats(min_value=100, max_value=100000))
    
    # 出場價格根據方向生成（確保有合理的損益）
    if direction == 'long':
        exit_price = draw(st.floats(min_value=entry_price * 0.8, max_value=entry_price * 1.5))
    else:
        exit_price = draw(st.floats(min_value=entry_price * 0.8, max_value=entry_price * 1.2))
    
    entry_time = datetime.now() - timedelta(hours=draw(st.integers(min_value=1, max_value=100)))
    exit_time = entry_time + timedelta(hours=draw(st.integers(min_value=1, max_value=24)))
    
    trade = Trade(
        strategy_id=draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        symbol=draw(st.sampled_from(['BTCUSDT', 'ETHUSDT', 'BNBUSDT'])),
        direction=direction,
        entry_time=entry_time,
        exit_time=exit_time,
        entry_price=entry_price,
        exit_price=exit_price,
        size=draw(st.floats(min_value=0.01, max_value=10.0)),
        leverage=draw(st.integers(min_value=1, max_value=20)),
        exit_reason=draw(st.sampled_from(['止損', '獲利', '手動平倉'])),
    )
    
    # 計算損益
    trade.calculate_pnl()
    
    return trade


@st.composite
def backtest_result_strategy(draw):
    """生成隨機回測結果"""
    initial_capital = draw(st.floats(min_value=100, max_value=10000))
    trades = draw(st.lists(trade_strategy(), min_size=1, max_size=50))
    
    # 計算最終資金
    final_capital = initial_capital + sum(t.pnl for t in trades)
    
    start_date = datetime.now() - timedelta(days=draw(st.integers(min_value=30, max_value=365)))
    end_date = start_date + timedelta(days=draw(st.integers(min_value=7, max_value=90)))
    
    result = BacktestResult(
        strategy_id=draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        final_capital=final_capital,
        trades=trades,
    )
    
    # 計算指標
    result.calculate_metrics()
    
    return result


# ============================================================================
# Property 10: 回測結果持久化往返
# ============================================================================

# Feature: multi-strategy-system, Property 10: 回測結果持久化往返
@given(backtest_result_strategy())
def test_backtest_result_save_load_roundtrip(result):
    """
    對於任何回測結果，將結果保存到文件後再載入，應該得到等價的結果對象（所有關鍵字段相同）
    
    Validates: Requirements 4.7
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, 'test_result.json')
        
        # 保存
        result.save(filepath)
        
        # 載入
        loaded_result = BacktestResult.load(filepath)
        
        # 驗證關鍵字段相同
        assert loaded_result.strategy_id == result.strategy_id
        assert loaded_result.initial_capital == result.initial_capital
        assert loaded_result.final_capital == result.final_capital
        assert loaded_result.total_trades == result.total_trades
        assert loaded_result.winning_trades == result.winning_trades
        assert loaded_result.losing_trades == result.losing_trades
        assert abs(loaded_result.win_rate - result.win_rate) < 0.01
        assert abs(loaded_result.total_pnl - result.total_pnl) < 0.01
        assert abs(loaded_result.profit_factor - result.profit_factor) < 0.01
        
        # 驗證交易數量相同
        assert len(loaded_result.trades) == len(result.trades)
        
        # 驗證每筆交易的關鍵字段
        for original_trade, loaded_trade in zip(result.trades, loaded_result.trades):
            assert loaded_trade.trade_id == original_trade.trade_id
            assert loaded_trade.strategy_id == original_trade.strategy_id
            assert loaded_trade.symbol == original_trade.symbol
            assert loaded_trade.direction == original_trade.direction
            assert abs(loaded_trade.entry_price - original_trade.entry_price) < 0.01
            assert abs(loaded_trade.exit_price - original_trade.exit_price) < 0.01
            assert abs(loaded_trade.pnl - original_trade.pnl) < 0.01


# ============================================================================
# Property 31: 數據導出往返
# ============================================================================

# Feature: multi-strategy-system, Property 31: 數據導出往返
@given(trade_strategy())
def test_trade_to_dict_roundtrip(trade):
    """
    對於任何交易數據，導出到字典後再重建，應該得到等價的數據（所有字段相同）
    
    Validates: Requirements 10.7
    """
    # 導出為字典
    trade_dict = trade.to_dict()
    
    # 從字典重建
    reconstructed_trade = Trade(
        trade_id=trade_dict['trade_id'],
        strategy_id=trade_dict['strategy_id'],
        symbol=trade_dict['symbol'],
        direction=trade_dict['direction'],
        entry_time=datetime.fromisoformat(trade_dict['entry_time']),
        exit_time=datetime.fromisoformat(trade_dict['exit_time']),
        entry_price=trade_dict['entry_price'],
        exit_price=trade_dict['exit_price'],
        size=trade_dict['size'],
        leverage=trade_dict['leverage'],
        pnl=trade_dict['pnl'],
        pnl_pct=trade_dict['pnl_pct'],
        commission=trade_dict['commission'],
        exit_reason=trade_dict['exit_reason'],
        metadata=trade_dict['metadata'],
    )
    
    # 驗證所有字段相同
    assert reconstructed_trade.trade_id == trade.trade_id
    assert reconstructed_trade.strategy_id == trade.strategy_id
    assert reconstructed_trade.symbol == trade.symbol
    assert reconstructed_trade.direction == trade.direction
    assert reconstructed_trade.entry_price == trade.entry_price
    assert reconstructed_trade.exit_price == trade.exit_price
    assert reconstructed_trade.size == trade.size
    assert reconstructed_trade.leverage == trade.leverage
    assert abs(reconstructed_trade.pnl - trade.pnl) < 0.01
    assert abs(reconstructed_trade.pnl_pct - trade.pnl_pct) < 0.01
    assert abs(reconstructed_trade.commission - trade.commission) < 0.01
    assert reconstructed_trade.exit_reason == trade.exit_reason


# Feature: multi-strategy-system, Property 31: 數據導出往返
@given(backtest_result_strategy())
def test_backtest_result_to_dict_roundtrip(result):
    """
    對於任何回測結果，導出到字典後應該包含所有關鍵信息
    
    Validates: Requirements 10.7
    """
    # 導出為字典
    result_dict = result.to_dict()
    
    # 驗證字典包含所有必需字段
    assert 'strategy_id' in result_dict
    assert 'start_date' in result_dict
    assert 'end_date' in result_dict
    assert 'initial_capital' in result_dict
    assert 'final_capital' in result_dict
    assert 'total_trades' in result_dict
    assert 'winning_trades' in result_dict
    assert 'losing_trades' in result_dict
    assert 'win_rate' in result_dict
    assert 'total_pnl' in result_dict
    assert 'profit_factor' in result_dict
    assert 'trades' in result_dict
    
    # 驗證值正確
    assert result_dict['strategy_id'] == result.strategy_id
    assert result_dict['initial_capital'] == result.initial_capital
    assert result_dict['final_capital'] == result.final_capital
    assert result_dict['total_trades'] == result.total_trades
    assert len(result_dict['trades']) == len(result.trades)


# ============================================================================
# 額外的單元測試（驗證數據模型的基本功能）
# ============================================================================

def test_trade_calculate_pnl_long():
    """測試做多交易的損益計算"""
    trade = Trade(
        strategy_id='test',
        symbol='BTCUSDT',
        direction='long',
        entry_price=100.0,
        exit_price=110.0,
        size=1.0,
        leverage=1,
    )
    
    trade.calculate_pnl(commission_rate=0.001)
    
    # 原始損益：(110 - 100) * 1 = 10
    # 手續費：(100 + 110) * 1 * 0.001 = 0.21
    # 淨損益：10 - 0.21 = 9.79
    assert abs(trade.pnl - 9.79) < 0.01
    assert abs(trade.pnl_pct - 10.0) < 0.01


def test_trade_calculate_pnl_short():
    """測試做空交易的損益計算"""
    trade = Trade(
        strategy_id='test',
        symbol='BTCUSDT',
        direction='short',
        entry_price=110.0,
        exit_price=100.0,
        size=1.0,
        leverage=1,
    )
    
    trade.calculate_pnl(commission_rate=0.001)
    
    # 原始損益：(110 - 100) * 1 = 10
    # 手續費：(110 + 100) * 1 * 0.001 = 0.21
    # 淨損益：10 - 0.21 = 9.79
    assert abs(trade.pnl - 9.79) < 0.01
    assert abs(trade.pnl_pct - 10.0) < 0.01


def test_backtest_result_calculate_metrics():
    """測試回測結果指標計算"""
    # 創建測試交易
    trades = [
        Trade(strategy_id='test', symbol='BTCUSDT', direction='long',
              entry_time=datetime.now(), exit_time=datetime.now(),
              entry_price=100, exit_price=110, size=1, pnl=10, pnl_pct=10),
        Trade(strategy_id='test', symbol='BTCUSDT', direction='long',
              entry_time=datetime.now(), exit_time=datetime.now(),
              entry_price=100, exit_price=95, size=1, pnl=-5, pnl_pct=-5),
        Trade(strategy_id='test', symbol='BTCUSDT', direction='long',
              entry_time=datetime.now(), exit_time=datetime.now(),
              entry_price=100, exit_price=105, size=1, pnl=5, pnl_pct=5),
    ]
    
    result = BacktestResult(
        strategy_id='test',
        start_date=datetime.now(),
        end_date=datetime.now(),
        initial_capital=1000,
        final_capital=1010,
        trades=trades,
    )
    
    result.calculate_metrics()
    
    # 驗證統計
    assert result.total_trades == 3
    assert result.winning_trades == 2
    assert result.losing_trades == 1
    assert abs(result.win_rate - 66.67) < 0.1
    assert result.total_pnl == 10
    assert result.avg_win == 7.5  # (10 + 5) / 2
    assert result.avg_loss == -5
