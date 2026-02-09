"""
PerformanceMonitor 屬性測試
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from datetime import datetime, timedelta
import statistics

from src.analysis.performance_monitor import (
    PerformanceMonitor,
    PerformanceMetrics,
    AlertConfig
)
from src.models.trading import Trade
from src.models.backtest import BacktestResult


# 策略生成器
@st.composite
def strategy_id_strategy(draw):
    """生成策略 ID"""
    return draw(st.text(min_size=1, max_size=20, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        min_codepoint=ord('a'),
        max_codepoint=ord('z')
    )))


# 交易生成器
@st.composite
def trade_strategy(draw, strategy_id: str):
    """生成交易記錄"""
    entry_price = draw(st.floats(min_value=100, max_value=100000))
    direction = draw(st.sampled_from(['long', 'short']))
    
    # 生成出場價格（可能獲利或虧損）
    price_change_pct = draw(st.floats(min_value=-0.1, max_value=0.1))
    exit_price = entry_price * (1 + price_change_pct)
    
    size = draw(st.floats(min_value=0.001, max_value=10.0))
    
    entry_time = datetime.now() - timedelta(hours=draw(st.integers(min_value=1, max_value=100)))
    exit_time = entry_time + timedelta(hours=draw(st.integers(min_value=1, max_value=24)))
    
    trade = Trade(
        strategy_id=strategy_id,
        symbol="BTCUSDT",
        direction=direction,
        entry_time=entry_time,
        exit_time=exit_time,
        entry_price=entry_price,
        exit_price=exit_price,
        size=size,
        leverage=draw(st.integers(min_value=1, max_value=10)),
    )
    
    trade.calculate_pnl()
    
    return trade


# 交易列表生成器
@st.composite
def trades_list_strategy(draw, strategy_id: str, min_size: int = 1, max_size: int = 50):
    """生成交易列表"""
    return draw(st.lists(
        trade_strategy(strategy_id),
        min_size=min_size,
        max_size=max_size
    ))


# Feature: multi-strategy-system, Property 20: 實時收益率計算正確性
@settings(max_examples=100, deadline=None)
@given(
    strategy_id=strategy_id_strategy(),
    initial_capital=st.floats(min_value=100, max_value=100000),
    trades=st.data()
)
def test_return_rate_calculation_correctness(strategy_id, initial_capital, trades):
    """
    Property 20: 實時收益率計算正確性
    
    對於任何策略，實時收益率應該等於（當前資金 - 初始資金）/ 初始資金
    
    Validates: Requirements 8.2
    """
    # 生成交易列表
    trade_list = trades.draw(trades_list_strategy(strategy_id, min_size=1, max_size=20))
    
    # 創建監控器
    monitor = PerformanceMonitor()
    monitor.set_initial_capital(strategy_id, initial_capital)
    
    # 更新所有交易
    for trade in trade_list:
        monitor.update_metrics(strategy_id, trade)
    
    # 獲取最新指標
    metrics = monitor.get_latest_metrics(strategy_id)
    assert metrics is not None
    
    # 計算預期收益率
    total_pnl = sum(t.pnl for t in trade_list)
    current_capital = initial_capital + total_pnl
    expected_return_rate = ((current_capital - initial_capital) / initial_capital) * 100
    
    # 驗證收益率計算正確
    actual_return_rate = metrics.calculate_return_rate()
    
    # 允許小的浮點誤差
    assert abs(actual_return_rate - expected_return_rate) < 0.01, (
        f"收益率計算錯誤: 預期 {expected_return_rate:.2f}%, 實際 {actual_return_rate:.2f}%"
    )
    
    # 驗證 total_pnl_pct 也正確
    assert abs(metrics.total_pnl_pct - expected_return_rate) < 0.01


# Feature: multi-strategy-system, Property 21: 異常警報觸發
@settings(max_examples=100, deadline=None)
@given(
    strategy_id=strategy_id_strategy(),
    initial_capital=st.floats(min_value=1000, max_value=10000),
    consecutive_losses=st.integers(min_value=5, max_value=10)
)
def test_anomaly_alert_trigger(strategy_id, initial_capital, consecutive_losses):
    """
    Property 21: 異常警報觸發
    
    對於任何策略，當其性能指標超出預定義的異常閾值時，系統應該發送警報
    
    Validates: Requirements 8.3
    """
    # 創建監控器，設置較低的閾值
    alert_config = AlertConfig(
        consecutive_loss_threshold=5,
        drawdown_threshold=10.0
    )
    monitor = PerformanceMonitor(alert_config=alert_config)
    monitor.set_initial_capital(strategy_id, initial_capital)
    
    # 生成連續虧損的交易
    for i in range(consecutive_losses):
        trade = Trade(
            strategy_id=strategy_id,
            symbol="BTCUSDT",
            direction="long",
            entry_time=datetime.now() - timedelta(hours=i+1),
            exit_time=datetime.now() - timedelta(hours=i),
            entry_price=1000.0,
            exit_price=950.0,  # 虧損 5%
            size=0.1,
            leverage=1,
        )
        trade.calculate_pnl()
        monitor.update_metrics(strategy_id, trade)
    
    # 檢測異常
    is_anomaly, anomaly_msg = monitor.check_anomaly(strategy_id)
    
    # 應該檢測到異常（連續虧損超過閾值）
    assert is_anomaly, f"應該檢測到異常，但沒有檢測到。連續虧損: {consecutive_losses}"
    assert "連續虧損" in anomaly_msg


# Feature: multi-strategy-system, Property 22: 策略退化檢測
@settings(max_examples=100, deadline=None)
@given(
    strategy_id=strategy_id_strategy(),
    initial_capital=st.floats(min_value=1000, max_value=10000),
    historical_win_rate=st.floats(min_value=60, max_value=80),
    recent_win_rate=st.floats(min_value=20, max_value=40)
)
def test_strategy_degradation_detection(
    strategy_id,
    initial_capital,
    historical_win_rate,
    recent_win_rate
):
    """
    Property 22: 策略退化檢測
    
    對於任何策略，當其最近 N 筆交易的勝率顯著低於歷史平均勝率時，
    系統應該檢測到性能退化
    
    Validates: Requirements 8.5
    """
    assume(historical_win_rate - recent_win_rate >= 15.0)  # 確保有顯著差異
    
    # 創建監控器
    alert_config = AlertConfig(
        degradation_window=20,
        degradation_threshold=15.0
    )
    monitor = PerformanceMonitor(alert_config=alert_config)
    monitor.set_initial_capital(strategy_id, initial_capital)
    
    # 生成歷史交易（高勝率）
    historical_trades_count = 30
    historical_wins = int(historical_trades_count * historical_win_rate / 100)
    
    for i in range(historical_trades_count):
        is_win = i < historical_wins
        trade = Trade(
            strategy_id=strategy_id,
            symbol="BTCUSDT",
            direction="long",
            entry_time=datetime.now() - timedelta(hours=100-i),
            exit_time=datetime.now() - timedelta(hours=99-i),
            entry_price=1000.0,
            exit_price=1050.0 if is_win else 950.0,
            size=0.1,
            leverage=1,
        )
        trade.calculate_pnl()
        monitor.update_metrics(strategy_id, trade)
    
    # 生成最近交易（低勝率）
    recent_trades_count = 20
    recent_wins = int(recent_trades_count * recent_win_rate / 100)
    
    for i in range(recent_trades_count):
        is_win = i < recent_wins
        trade = Trade(
            strategy_id=strategy_id,
            symbol="BTCUSDT",
            direction="long",
            entry_time=datetime.now() - timedelta(hours=20-i),
            exit_time=datetime.now() - timedelta(hours=19-i),
            entry_price=1000.0,
            exit_price=1050.0 if is_win else 950.0,
            size=0.1,
            leverage=1,
        )
        trade.calculate_pnl()
        monitor.update_metrics(strategy_id, trade)
    
    # 檢測退化
    is_degraded, degradation_score = monitor.detect_degradation(strategy_id)
    
    # 應該檢測到退化
    assert is_degraded, (
        f"應該檢測到退化。歷史勝率: {historical_win_rate:.1f}%, "
        f"近期勝率: {recent_win_rate:.1f}%, 差異: {historical_win_rate - recent_win_rate:.1f}%"
    )
    assert degradation_score > 0


# Feature: multi-strategy-system, Property 23: 連續虧損自動暫停
@settings(max_examples=100, deadline=None)
@given(
    strategy_id=strategy_id_strategy(),
    initial_capital=st.floats(min_value=1000, max_value=10000),
    consecutive_losses=st.integers(min_value=5, max_value=10)
)
def test_consecutive_loss_auto_halt(strategy_id, initial_capital, consecutive_losses):
    """
    Property 23: 連續虧損自動暫停
    
    對於任何策略，當連續虧損次數達到配置的閾值時，系統應該自動暫停該策略
    
    Validates: Requirements 8.6
    """
    # 創建監控器
    alert_config = AlertConfig(
        auto_halt_consecutive_losses=5
    )
    monitor = PerformanceMonitor(alert_config=alert_config)
    monitor.set_initial_capital(strategy_id, initial_capital)
    
    # 生成連續虧損的交易
    for i in range(consecutive_losses):
        trade = Trade(
            strategy_id=strategy_id,
            symbol="BTCUSDT",
            direction="long",
            entry_time=datetime.now() - timedelta(hours=i+1),
            exit_time=datetime.now() - timedelta(hours=i),
            entry_price=1000.0,
            exit_price=950.0,  # 虧損
            size=0.1,
            leverage=1,
        )
        trade.calculate_pnl()
        monitor.update_metrics(strategy_id, trade)
    
    # 檢查是否應該暫停
    should_halt, halt_reason = monitor.should_auto_halt(strategy_id)
    
    # 應該自動暫停
    assert should_halt, (
        f"應該自動暫停策略。連續虧損: {consecutive_losses}, "
        f"閾值: {alert_config.auto_halt_consecutive_losses}"
    )
    assert "連續虧損" in halt_reason
    
    # 驗證策略已被標記為暫停
    assert monitor.strategy_halted.get(strategy_id, False)


# 額外測試：指標歷史記錄
@settings(max_examples=100, deadline=None)
@given(
    strategy_id=strategy_id_strategy(),
    initial_capital=st.floats(min_value=1000, max_value=10000),
    trades=st.data()
)
def test_metrics_history_tracking(strategy_id, initial_capital, trades):
    """
    測試指標歷史記錄功能
    
    驗證每次更新都會保存到歷史記錄中
    """
    trade_list = trades.draw(trades_list_strategy(strategy_id, min_size=5, max_size=20))
    
    monitor = PerformanceMonitor()
    monitor.set_initial_capital(strategy_id, initial_capital)
    
    # 更新所有交易
    for trade in trade_list:
        monitor.update_metrics(strategy_id, trade)
    
    # 獲取歷史記錄
    history = monitor.get_metrics_history(strategy_id)
    
    # 歷史記錄數量應該等於交易數量
    assert len(history) == len(trade_list)
    
    # 每個歷史記錄都應該有正確的策略 ID
    for metrics in history:
        assert metrics.strategy_id == strategy_id


# 額外測試：回測基準比較
@settings(max_examples=100, deadline=None)
@given(
    strategy_id=strategy_id_strategy(),
    initial_capital=st.floats(min_value=1000, max_value=10000),
    backtest_win_rate=st.floats(min_value=50, max_value=80),
    actual_win_rate=st.floats(min_value=30, max_value=70)
)
def test_backtest_comparison(strategy_id, initial_capital, backtest_win_rate, actual_win_rate):
    """
    測試與回測基準的比較功能
    """
    # 創建回測基準
    backtest_result = BacktestResult(
        strategy_id=strategy_id,
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now(),
        initial_capital=initial_capital,
        final_capital=initial_capital * 1.2,
        win_rate=backtest_win_rate,
        total_pnl_pct=20.0,
        max_drawdown_pct=10.0,
        sharpe_ratio=1.5
    )
    
    # 創建監控器並設置基準
    monitor = PerformanceMonitor()
    monitor.set_initial_capital(strategy_id, initial_capital)
    monitor.set_backtest_baseline(strategy_id, backtest_result)
    
    # 生成實際交易
    trades_count = 20
    wins = int(trades_count * actual_win_rate / 100)
    
    for i in range(trades_count):
        is_win = i < wins
        trade = Trade(
            strategy_id=strategy_id,
            symbol="BTCUSDT",
            direction="long",
            entry_time=datetime.now() - timedelta(hours=i+1),
            exit_time=datetime.now() - timedelta(hours=i),
            entry_price=1000.0,
            exit_price=1050.0 if is_win else 950.0,
            size=0.1,
            leverage=1,
        )
        trade.calculate_pnl()
        monitor.update_metrics(strategy_id, trade)
    
    # 比較與回測
    comparison = monitor.compare_with_backtest(strategy_id)
    
    assert comparison['available']
    assert 'backtest' in comparison
    assert 'actual' in comparison
    assert 'difference' in comparison
    assert 'performance_grade' in comparison
    
    # 驗證回測數據
    assert comparison['backtest']['win_rate'] == backtest_win_rate
    
    # 驗證差異計算
    win_rate_diff = comparison['difference']['win_rate']
    expected_diff = comparison['actual']['win_rate'] - backtest_win_rate
    assert abs(win_rate_diff - expected_diff) < 0.01
