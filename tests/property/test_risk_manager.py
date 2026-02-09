"""
RiskManager 屬性測試

測試風險管理器的正確性屬性。
"""

import pytest
from hypothesis import given, strategies as st, assume
from datetime import datetime

from src.managers.risk_manager import RiskManager
from src.models.risk import RiskConfig, GlobalRiskState
from src.models.trading import Signal, Trade
from src.models.state import StrategyState


# ============================================================================
# 測試數據生成策略
# ============================================================================

@st.composite
def risk_config_strategy(draw):
    """生成有效的風險配置"""
    global_max_position = draw(st.floats(min_value=0.5, max_value=1.0))
    strategy_max_position = draw(st.floats(min_value=0.1, max_value=global_max_position))
    
    return RiskConfig(
        global_max_drawdown=draw(st.floats(min_value=0.1, max_value=0.5)),
        daily_loss_limit=draw(st.floats(min_value=0.05, max_value=0.3)),
        global_max_position=global_max_position,
        strategy_max_position=strategy_max_position,
    )


@st.composite
def signal_strategy(draw, strategy_id="test-strategy"):
    """生成交易信號"""
    entry_price = draw(st.floats(min_value=100, max_value=100000))
    position_size = draw(st.floats(min_value=0.001, max_value=10.0))
    
    return Signal(
        strategy_id=strategy_id,
        timestamp=datetime.now(),
        symbol="BTCUSDT",
        action="BUY",
        direction="long",
        entry_price=entry_price,
        stop_loss=entry_price * 0.98,
        take_profit=entry_price * 1.06,
        position_size=position_size,
        confidence=0.8,
    )


@st.composite
def trade_strategy(draw, strategy_id="test-strategy"):
    """生成交易記錄"""
    entry_price = draw(st.floats(min_value=100, max_value=100000))
    exit_price = draw(st.floats(min_value=100, max_value=100000))
    size = draw(st.floats(min_value=0.001, max_value=10.0))
    
    trade = Trade(
        strategy_id=strategy_id,
        symbol="BTCUSDT",
        direction="long",
        entry_time=datetime.now(),
        exit_time=datetime.now(),
        entry_price=entry_price,
        exit_price=exit_price,
        size=size,
        leverage=5,
    )
    trade.calculate_pnl()
    
    return trade


# ============================================================================
# Property 6: 資金分配守恆
# ============================================================================

# Feature: multi-strategy-system, Property 6: 資金分配守恆
@given(
    initial_capital=st.floats(min_value=1000, max_value=100000),
    config=risk_config_strategy(),
)
def test_capital_conservation(initial_capital, config):
    """
    對於任何多策略系統，所有策略的已分配資金總和應該小於或等於總可用資金，
    且每個策略只能使用其分配的資金。
    """
    risk_manager = RiskManager(config, initial_capital)
    
    # 初始狀態：總倉位應該為 0
    assert risk_manager.global_state.total_position_value == 0.0
    
    # 添加多個策略的倉位
    strategies = ["strategy-1", "strategy-2", "strategy-3"]
    total_allocated = 0.0
    
    for strategy_id in strategies:
        # 計算最大可用倉位
        max_position = risk_manager.calculate_max_position_size(strategy_id, initial_capital)
        
        # 分配部分倉位（50%）
        allocated = max_position * 0.5
        risk_manager.add_position(strategy_id, allocated)
        total_allocated += allocated
    
    # 驗證：總倉位不超過初始資金
    assert risk_manager.global_state.total_position_value <= initial_capital
    
    # 驗證：總倉位等於所有策略倉位之和
    strategy_sum = sum(risk_manager.global_state.strategy_positions.values())
    assert abs(risk_manager.global_state.total_position_value - strategy_sum) < 0.01


# ============================================================================
# Property 24: 全局回撤限制觸發
# ============================================================================

# Feature: multi-strategy-system, Property 24: 全局回撤限制觸發
@given(
    initial_capital=st.floats(min_value=1000, max_value=100000),
    config=risk_config_strategy(),
    drawdown_pct=st.floats(min_value=0.0, max_value=0.6),
)
def test_global_drawdown_limit(initial_capital, config, drawdown_pct):
    """
    對於任何多策略系統，當總回撤超過全局限制時，系統應該暫停所有策略。
    """
    risk_manager = RiskManager(config, initial_capital)
    
    # 模擬資金變化導致回撤
    # 注意：這會同時影響回撤和每日虧損，因為 daily_start_capital == initial_capital
    new_capital = initial_capital * (1 - drawdown_pct)
    risk_manager.global_state.update_capital(new_capital)
    
    # 檢查全局風險
    passed, reason = risk_manager.check_global_risk()
    
    # 計算實際的回撤和每日虧損
    actual_drawdown = risk_manager.global_state.get_current_drawdown()
    actual_daily_loss = risk_manager.global_state.get_daily_loss_pct()
    
    # 驗證：當回撤或每日虧損超過限制時，應該觸發暫停
    should_halt = (actual_drawdown > config.global_max_drawdown or 
                   actual_daily_loss > config.daily_loss_limit)
    
    if should_halt:
        assert not passed, f"回撤 {actual_drawdown:.2%} 或每日虧損 {actual_daily_loss:.2%} 超過限制，應該觸發暫停"
        assert risk_manager.global_state.trading_halted, "交易應該被暫停"
        
        # 驗證：應該記錄風險事件
        events = risk_manager.get_risk_events()
        assert len(events) > 0, "應該記錄風險事件"
        assert events[-1].event_type in ['drawdown', 'daily_loss'], "最新事件應該是回撤或每日虧損事件"
    else:
        assert passed, f"回撤 {actual_drawdown:.2%} 和每日虧損 {actual_daily_loss:.2%} 都未超過限制，不應該觸發暫停"


# ============================================================================
# Property 25: 單策略倉位限制
# ============================================================================

# Feature: multi-strategy-system, Property 25: 單策略倉位限制
@given(
    initial_capital=st.floats(min_value=1000, max_value=100000),
    config=risk_config_strategy(),
    position_multiplier=st.floats(min_value=0.5, max_value=2.0),
)
def test_strategy_position_limit(initial_capital, config, position_multiplier):
    """
    對於任何策略的交易信號，如果執行該信號會導致倉位超過該策略的最大倉位限制，
    系統應該拒絕該信號。
    """
    risk_manager = RiskManager(config, initial_capital)
    strategy_id = "test-strategy"
    
    # 計算目標倉位（基於策略限制的倍數）
    target_position = initial_capital * config.strategy_max_position * position_multiplier
    
    # 創建信號
    signal = Signal(
        strategy_id=strategy_id,
        timestamp=datetime.now(),
        symbol="BTCUSDT",
        action="BUY",
        direction="long",
        entry_price=50000.0,
        stop_loss=49000.0,
        take_profit=53000.0,
        position_size=target_position / 50000.0,  # 轉換為幣數
        confidence=0.8,
    )
    
    # 創建策略狀態
    strategy_state = StrategyState(
        strategy_id=strategy_id,
        enabled=True,
    )
    
    # 檢查策略風險
    passed, reason = risk_manager.check_strategy_risk(strategy_id, signal, strategy_state)
    
    # 驗證：當倉位超過限制時，應該拒絕信號
    if position_multiplier > 1.0:
        assert not passed, f"倉位超過限制，應該拒絕信號"
        assert "倉位超限" in reason, f"原因應該包含'倉位超限'，實際：{reason}"
        
        # 驗證：應該記錄風險事件
        events = risk_manager.get_risk_events()
        assert len(events) > 0, "應該記錄風險事件"
        assert events[-1].event_type == 'position_limit', "最新事件應該是倉位限制事件"
    else:
        # 倉位在限制內，應該通過（除非全局倉位也超限）
        if not passed:
            # 可能是全局倉位超限
            assert "倉位超限" in reason


# ============================================================================
# Property 26: 全局倉位限制
# ============================================================================

# Feature: multi-strategy-system, Property 26: 全局倉位限制
@given(
    initial_capital=st.floats(min_value=1000, max_value=100000),
    config=risk_config_strategy(),
)
def test_global_position_limit(initial_capital, config):
    """
    對於任何多策略系統的交易信號，如果執行該信號會導致所有策略的總倉位超過全局限制，
    系統應該拒絕該信號。
    """
    risk_manager = RiskManager(config, initial_capital)
    
    # 先添加接近全局限制的倉位
    existing_position = initial_capital * config.global_max_position * 0.95
    risk_manager.add_position("strategy-1", existing_position)
    
    # 嘗試添加新倉位
    new_position_value = initial_capital * 0.1
    signal = Signal(
        strategy_id="strategy-2",
        timestamp=datetime.now(),
        symbol="BTCUSDT",
        action="BUY",
        direction="long",
        entry_price=50000.0,
        stop_loss=49000.0,
        take_profit=53000.0,
        position_size=new_position_value / 50000.0,
        confidence=0.8,
    )
    
    strategy_state = StrategyState(strategy_id="strategy-2", enabled=True)
    
    # 檢查策略風險
    passed, reason = risk_manager.check_strategy_risk("strategy-2", signal, strategy_state)
    
    # 計算新的總倉位使用率
    new_total = existing_position + new_position_value
    new_usage = new_total / initial_capital
    
    # 驗證：當總倉位超過全局限制時，應該拒絕信號
    if new_usage > config.global_max_position:
        assert not passed, f"總倉位 {new_usage:.2%} 超過全局限制 {config.global_max_position:.2%}，應該拒絕信號"
        assert "倉位超限" in reason, f"原因應該包含'倉位超限'，實際：{reason}"
        
        # 驗證：應該記錄風險事件
        events = risk_manager.get_risk_events()
        assert len(events) > 0, "應該記錄風險事件"
        assert events[-1].event_type == 'position_limit', "最新事件應該是倉位限制事件"


# ============================================================================
# Property 27: 風險事件記錄完整性
# ============================================================================

# Feature: multi-strategy-system, Property 27: 風險事件記錄完整性
@given(
    initial_capital=st.floats(min_value=1000, max_value=100000),
    config=risk_config_strategy(),
    num_violations=st.integers(min_value=1, max_value=5),
)
def test_risk_event_recording(initial_capital, config, num_violations):
    """
    對於任何觸發的風險限制（回撤、虧損、倉位），系統應該記錄該風險事件，
    包括時間、類型、觸發值和採取的行動。
    """
    risk_manager = RiskManager(config, initial_capital)
    
    # 觸發多次風險事件
    for i in range(num_violations):
        # 創建超過策略倉位限制的信號
        over_limit_position = initial_capital * config.strategy_max_position * 1.5
        signal = Signal(
            strategy_id=f"strategy-{i}",
            timestamp=datetime.now(),
            symbol="BTCUSDT",
            action="BUY",
            direction="long",
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=53000.0,
            position_size=over_limit_position / 50000.0,
            confidence=0.8,
        )
        
        strategy_state = StrategyState(strategy_id=f"strategy-{i}", enabled=True)
        
        # 檢查風險（應該觸發事件）
        risk_manager.check_strategy_risk(f"strategy-{i}", signal, strategy_state)
    
    # 驗證：應該記錄所有風險事件
    events = risk_manager.get_risk_events()
    assert len(events) == num_violations, f"應該記錄 {num_violations} 個風險事件，實際記錄 {len(events)} 個"
    
    # 驗證：每個事件都包含必需字段
    for event in events:
        assert event.timestamp is not None, "事件應該有時間戳"
        assert event.event_type != "", "事件應該有類型"
        assert event.trigger_value >= 0, "事件應該有觸發值"
        assert event.limit_value >= 0, "事件應該有限制值"
        assert event.action_taken != "", "事件應該記錄採取的行動"
        
        # 驗證：事件可以轉換為字典
        event_dict = event.to_dict()
        assert 'timestamp' in event_dict
        assert 'event_type' in event_dict
        assert 'trigger_value' in event_dict
        assert 'limit_value' in event_dict
        assert 'action_taken' in event_dict


# ============================================================================
# 單元測試
# ============================================================================

def test_risk_manager_initialization():
    """測試風險管理器初始化"""
    config = RiskConfig()
    initial_capital = 10000.0
    
    risk_manager = RiskManager(config, initial_capital)
    
    assert risk_manager.config == config
    assert risk_manager.global_state.initial_capital == initial_capital
    assert risk_manager.global_state.current_capital == initial_capital
    assert risk_manager.global_state.peak_capital == initial_capital
    assert risk_manager.global_state.total_position_value == 0.0
    assert not risk_manager.global_state.trading_halted


def test_calculate_max_position_size():
    """測試最大倉位計算"""
    config = RiskConfig(
        strategy_max_position=0.3,
        global_max_position=0.8,
    )
    initial_capital = 10000.0
    
    risk_manager = RiskManager(config, initial_capital)
    
    # 無現有倉位時
    max_position = risk_manager.calculate_max_position_size("strategy-1", initial_capital)
    assert max_position == 3000.0  # 30% of 10000
    
    # 添加現有倉位後
    risk_manager.add_position("strategy-1", 1000.0)
    max_position = risk_manager.calculate_max_position_size("strategy-1", initial_capital)
    assert max_position == 2000.0  # 3000 - 1000


def test_add_remove_position():
    """測試添加和移除倉位"""
    config = RiskConfig()
    initial_capital = 10000.0
    
    risk_manager = RiskManager(config, initial_capital)
    
    # 添加倉位
    risk_manager.add_position("strategy-1", 1000.0)
    assert risk_manager.global_state.total_position_value == 1000.0
    assert risk_manager.global_state.strategy_positions["strategy-1"] == 1000.0
    
    risk_manager.add_position("strategy-2", 2000.0)
    assert risk_manager.global_state.total_position_value == 3000.0
    
    # 移除倉位
    risk_manager.remove_position("strategy-1", 500.0)
    assert risk_manager.global_state.strategy_positions["strategy-1"] == 500.0
    assert risk_manager.global_state.total_position_value == 2500.0
    
    # 完全移除倉位
    risk_manager.remove_position("strategy-1", 500.0)
    assert "strategy-1" not in risk_manager.global_state.strategy_positions
    assert risk_manager.global_state.total_position_value == 2000.0


def test_update_risk_state():
    """測試更新風險狀態"""
    config = RiskConfig()
    initial_capital = 10000.0
    
    risk_manager = RiskManager(config, initial_capital)
    
    # 添加倉位
    risk_manager.add_position("strategy-1", 1000.0)
    
    # 創建獲利交易
    trade = Trade(
        strategy_id="strategy-1",
        symbol="BTCUSDT",
        direction="long",
        entry_price=50000.0,
        exit_price=51000.0,
        size=0.02,
        leverage=5,
    )
    trade.calculate_pnl()
    
    # 更新風險狀態
    risk_manager.update_risk_state(trade)
    
    # 驗證資金更新
    assert risk_manager.global_state.current_capital > initial_capital
    
    # 驗證倉位減少
    assert risk_manager.global_state.total_position_value == 0.0


def test_daily_loss_limit():
    """測試每日虧損限制"""
    config = RiskConfig(daily_loss_limit=0.1)  # 10%
    initial_capital = 10000.0
    
    risk_manager = RiskManager(config, initial_capital)
    
    # 模擬虧損 5%（未超限）
    risk_manager.global_state.update_capital(9500.0)
    passed, _ = risk_manager.check_global_risk()
    assert passed
    
    # 模擬虧損 15%（超限）
    risk_manager.global_state.update_capital(8500.0)
    passed, reason = risk_manager.check_global_risk()
    assert not passed
    assert "虧損" in reason
    assert risk_manager.global_state.trading_halted


def test_reset_daily_stats():
    """測試重置每日統計"""
    config = RiskConfig()
    initial_capital = 10000.0
    
    risk_manager = RiskManager(config, initial_capital)
    
    # 模擬虧損
    risk_manager.global_state.update_capital(9500.0)
    assert risk_manager.global_state.daily_pnl == -500.0
    
    # 重置每日統計
    risk_manager.reset_daily_stats()
    assert risk_manager.global_state.daily_pnl == 0.0
    assert risk_manager.global_state.daily_start_capital == 9500.0
