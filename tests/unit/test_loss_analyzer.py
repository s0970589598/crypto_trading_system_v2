"""
LossAnalyzer 的單元測試
"""

import pytest
from datetime import datetime, timedelta
import pandas as pd

from src.analysis.loss_analyzer import LossAnalyzer, LossAnalysis, LossPattern
from src.models.trading import Trade


def create_trade(trade_id, direction, entry_price, exit_price, exit_reason,
                 entry_hours_ago=2, stop_loss=None, take_profit=None, **kwargs):
    """Helper function to create a trade with metadata"""
    metadata = {}
    if stop_loss is not None:
        metadata['stop_loss'] = stop_loss
    if take_profit is not None:
        metadata['take_profit'] = take_profit
    
    trade = Trade(
        trade_id=trade_id,
        strategy_id=kwargs.get('strategy_id', 'test-strategy'),
        symbol=kwargs.get('symbol', 'BTCUSDT'),
        direction=direction,
        entry_time=datetime.now() - timedelta(hours=entry_hours_ago),
        exit_time=kwargs.get('exit_time', datetime.now()),
        entry_price=entry_price,
        exit_price=exit_price,
        size=kwargs.get('size', 0.1),
        leverage=kwargs.get('leverage', 5),
        exit_reason=exit_reason,
        metadata=metadata
    )
    trade.calculate_pnl()
    return trade


@pytest.fixture
def analyzer():
    """創建 LossAnalyzer 實例"""
    return LossAnalyzer()


@pytest.fixture
def sample_losing_trade():
    """創建示例虧損交易"""
    return create_trade(
        trade_id="test-001",
        direction="long",
        entry_price=50000.0,
        exit_price=49000.0,
        exit_reason="止損",
        stop_loss=49500.0,
        take_profit=52000.0
    )


def test_analyzer_initialization():
    """測試分析器初始化"""
    analyzer = LossAnalyzer()
    
    assert analyzer.custom_rules == {}
    assert analyzer.loss_history == []
    assert len(LossAnalyzer.LOSS_REASONS) > 0


def test_analyze_losing_trade(analyzer, sample_losing_trade):
    """測試分析虧損交易"""
    analysis = analyzer.analyze_trade(sample_losing_trade)
    
    assert isinstance(analysis, LossAnalysis)
    assert analysis.trade_id == sample_losing_trade.trade_id
    assert analysis.loss_reason in LossAnalyzer.LOSS_REASONS
    assert 0.0 <= analysis.confidence <= 1.0
    assert len(analysis.recommendations) > 0


def test_analyze_winning_trade_raises_error(analyzer):
    """測試分析獲利交易應該拋出錯誤"""
    winning_trade = create_trade(
        trade_id="test-002",
        direction="long",
        entry_price=50000.0,
        exit_price=52000.0,  # 獲利
        exit_reason="獲利",
        stop_loss=49500.0,
        take_profit=52000.0
    )
    
    with pytest.raises(ValueError, match="不是虧損交易"):
        analyzer.analyze_trade(winning_trade)


def test_classify_stop_loss_too_tight(analyzer):
    """測試分類：止損太緊"""
    trade = create_trade(
        trade_id="test-003",
        direction="long",
        entry_price=50000.0,
        exit_price=49600.0,  # 虧損 0.8%
        exit_reason="止損",
        entry_hours_ago=1,
        stop_loss=49600.0,  # 止損距離 0.8%（很緊）
        take_profit=52000.0
    )
    
    loss_reason, confidence = analyzer.classify_loss_reason(trade)
    
    assert loss_reason == 'STOP_LOSS_TOO_TIGHT'
    assert confidence >= 0.8


def test_classify_premature_entry(analyzer):
    """測試分類：過早進場"""
    trade = create_trade(
        trade_id="test-004",
        direction="long",
        entry_price=50000.0,
        exit_price=49000.0,
        exit_reason="止損",
        entry_hours_ago=0.5,  # 30 minutes
        stop_loss=49000.0,  # 止損距離 2%
        take_profit=52000.0
    )
    
    loss_reason, confidence = analyzer.classify_loss_reason(trade)
    
    # 持倉時間很短（< 1小時），應該分類為過早進場
    assert loss_reason == 'PREMATURE_ENTRY'


def test_classify_trend_misjudgment(analyzer):
    """測試分類：趨勢判斷錯誤"""
    trade = create_trade(
        trade_id="test-005",
        direction="long",
        entry_price=50000.0,
        exit_price=49000.0,  # 虧損 2%
        exit_reason="止損",
        entry_hours_ago=3,
        stop_loss=49000.0,  # 止損距離 2%
        take_profit=52000.0
    )
    
    loss_reason, confidence = analyzer.classify_loss_reason(trade)
    
    # 虧損百分比接近止損距離，應該分類為趨勢判斷錯誤
    assert loss_reason == 'TREND_MISJUDGMENT'


def test_classify_holding_too_long(analyzer):
    """測試分類：持倉時間過長"""
    trade = create_trade(
        trade_id="test-006",
        direction="long",
        entry_price=50000.0,
        exit_price=49000.0,
        exit_reason="手動平倉",
        entry_hours_ago=30,
        stop_loss=48000.0,
        take_profit=52000.0
    )
    
    loss_reason, confidence = analyzer.classify_loss_reason(trade)
    
    assert loss_reason == 'HOLDING_TOO_LONG'


def test_find_common_patterns(analyzer):
    """測試找出共同虧損模式"""
    trades = []
    
    # 創建 3 筆止損太緊的交易
    for i in range(3):
        trade = create_trade(
            trade_id=f"tight-{i}",
            direction="long",
            entry_price=50000.0,
            exit_price=49600.0,
            exit_reason="止損",
            stop_loss=49600.0,  # 止損太緊
            take_profit=52000.0
        )
        trades.append(trade)
    
    # 創建 2 筆趨勢判斷錯誤的交易
    for i in range(2):
        trade = create_trade(
            trade_id=f"trend-{i}",
            direction="long",
            entry_price=50000.0,
            exit_price=49000.0,
            exit_reason="止損",
            entry_hours_ago=3,
            stop_loss=49000.0,
            take_profit=52000.0
        )
        trades.append(trade)
    
    patterns = analyzer.find_common_patterns(trades)
    
    assert len(patterns) >= 2
    assert all(isinstance(p, LossPattern) for p in patterns)
    
    # 驗證模式按虧損金額排序
    for i in range(len(patterns) - 1):
        assert patterns[i].total_loss >= patterns[i + 1].total_loss


def test_calculate_loss_distribution(analyzer):
    """測試計算虧損分布"""
    trades = []
    
    # 創建不同類型的虧損交易
    for i in range(5):
        trade = create_trade(
            trade_id=f"test-{i}",
            direction="long",
            entry_price=50000.0,
            exit_price=49000.0,
            exit_reason="止損",
            stop_loss=49000.0,
            take_profit=52000.0
        )
        trades.append(trade)
    
    distribution = analyzer.calculate_loss_distribution(trades)
    
    assert isinstance(distribution, dict)
    assert len(distribution) > 0
    
    # 驗證佔比總和為 100%
    total = sum(distribution.values())
    assert abs(total - 100.0) < 0.01


def test_generate_recommendations_stop_loss_too_tight(analyzer):
    """測試生成建議：止損太緊"""
    trade = create_trade(
        trade_id="test-007",
        direction="long",
        entry_price=50000.0,
        exit_price=49600.0,
        exit_reason="止損",
        entry_hours_ago=1,
        stop_loss=49600.0,
        take_profit=52000.0
    )
    
    recommendations = analyzer.generate_recommendations('STOP_LOSS_TOO_TIGHT', trade)
    
    assert len(recommendations) > 0
    assert any('止損' in rec for rec in recommendations)


def test_generate_recommendations_trend_misjudgment(analyzer):
    """測試生成建議：趨勢判斷錯誤"""
    trade = create_trade(
        trade_id="test-008",
        direction="long",
        entry_price=50000.0,
        exit_price=49000.0,
        exit_reason="止損",
        stop_loss=49000.0,
        take_profit=52000.0
    )
    
    recommendations = analyzer.generate_recommendations('TREND_MISJUDGMENT', trade)
    
    assert len(recommendations) > 0
    assert any('趨勢' in rec for rec in recommendations)


def test_loss_history_recording(analyzer, sample_losing_trade):
    """測試虧損歷史記錄"""
    assert len(analyzer.loss_history) == 0
    
    analyzer.analyze_trade(sample_losing_trade)
    
    assert len(analyzer.loss_history) == 1
    assert analyzer.loss_history[0].trade_id == sample_losing_trade.trade_id


def test_track_improvement_trend(analyzer):
    """測試追蹤改善趨勢"""
    trades = []
    
    # 創建 30 筆交易（混合獲利和虧損）
    for i in range(30):
        is_winning = i % 3 != 0  # 2/3 獲利，1/3 虧損
        
        if is_winning:
            exit_price = 50000.0 * 1.02
        else:
            exit_price = 50000.0 * 0.98
        
        trade = create_trade(
            trade_id=f"test-{i}",
            direction="long",
            entry_price=50000.0,
            exit_price=exit_price,
            exit_reason="止損" if not is_winning else "獲利",
            entry_hours_ago=30 - i,
            exit_time=datetime.now() - timedelta(hours=30 - i - 1),
            stop_loss=49000.0,
            take_profit=52000.0
        )
        trades.append(trade)
    
    trend_df = analyzer.track_improvement_trend(trades, window_size=10)
    
    assert isinstance(trend_df, pd.DataFrame)
    assert len(trend_df) > 0
    assert 'loss_rate' in trend_df.columns
    assert 'avg_loss' in trend_df.columns


def test_generate_report(analyzer):
    """測試生成報告"""
    trades = []
    
    # 創建一些虧損交易
    for i in range(5):
        trade = create_trade(
            trade_id=f"test-{i}",
            direction="long",
            entry_price=50000.0,
            exit_price=49000.0,
            exit_reason="止損",
            stop_loss=49000.0,
            take_profit=52000.0
        )
        trades.append(trade)
    
    report = analyzer.generate_report(trades)
    
    assert isinstance(report, str)
    assert len(report) > 0
    assert "虧損分析報告" in report
    assert "總交易數" in report


def test_custom_rules_initialization():
    """測試自定義規則初始化"""
    custom_rules = {
        'rule1': 'value1',
        'rule2': 'value2',
    }
    
    analyzer = LossAnalyzer(custom_rules=custom_rules)
    
    assert analyzer.custom_rules == custom_rules


def test_loss_pattern_structure():
    """測試虧損模式數據結構"""
    pattern = LossPattern(
        pattern_name="TEST_PATTERN",
        description="測試模式",
        occurrence_count=5,
        total_loss=100.0,
        percentage=50.0,
        examples=["trade-1", "trade-2"],
    )
    
    assert pattern.pattern_name == "TEST_PATTERN"
    assert pattern.description == "測試模式"
    assert pattern.occurrence_count == 5
    assert pattern.total_loss == 100.0
    assert pattern.percentage == 50.0
    assert len(pattern.examples) == 2


def test_loss_analysis_structure():
    """測試虧損分析數據結構"""
    analysis = LossAnalysis(
        trade_id="test-001",
        loss_reason="STOP_LOSS_TOO_TIGHT",
        confidence=0.9,
        contributing_factors=["高槓桿", "波動率大"],
        recommendations=["放寬止損", "降低槓桿"],
        metadata={"key": "value"},
    )
    
    assert analysis.trade_id == "test-001"
    assert analysis.loss_reason == "STOP_LOSS_TOO_TIGHT"
    assert analysis.confidence == 0.9
    assert len(analysis.contributing_factors) == 2
    assert len(analysis.recommendations) == 2
    assert analysis.metadata["key"] == "value"


def test_no_losses_edge_case(analyzer):
    """測試邊緣情況：沒有虧損交易"""
    trades = []
    
    # 創建只有獲利交易的列表
    for i in range(5):
        trade = create_trade(
            trade_id=f"winning-{i}",
            direction="long",
            entry_price=50000.0,
            exit_price=52000.0,  # 獲利
            exit_reason="獲利",
            stop_loss=49000.0,
            take_profit=52000.0
        )
        trades.append(trade)
    
    # 測試 find_common_patterns
    patterns = analyzer.find_common_patterns(trades)
    assert len(patterns) == 0
    
    # 測試 calculate_loss_distribution
    distribution = analyzer.calculate_loss_distribution(trades)
    assert len(distribution) == 0
    
    # 測試 generate_report
    report = analyzer.generate_report(trades)
    assert "沒有虧損交易需要分析" in report


def test_single_loss_edge_case(analyzer):
    """測試邊緣情況：只有一筆虧損交易"""
    trade = create_trade(
        trade_id="single-loss",
        direction="long",
        entry_price=50000.0,
        exit_price=49000.0,
        exit_reason="止損",
        stop_loss=49000.0,
        take_profit=52000.0
    )
    
    trades = [trade]
    
    # 測試 find_common_patterns
    patterns = analyzer.find_common_patterns(trades)
    assert len(patterns) == 1
    assert patterns[0].occurrence_count == 1
    assert patterns[0].percentage == 100.0
    
    # 測試 calculate_loss_distribution
    distribution = analyzer.calculate_loss_distribution(trades)
    assert len(distribution) == 1
    total_percentage = sum(distribution.values())
    assert abs(total_percentage - 100.0) < 0.01
    
    # 測試 analyze_trade
    analysis = analyzer.analyze_trade(trade)
    assert analysis.trade_id == trade.trade_id
    assert analysis.loss_reason in LossAnalyzer.LOSS_REASONS


def test_specific_pattern_stop_loss_too_tight(analyzer):
    """測試特定虧損模式識別：止損太緊"""
    trades = []
    
    # 創建 5 筆止損太緊的交易
    for i in range(5):
        trade = create_trade(
            trade_id=f"tight-{i}",
            direction="long",
            entry_price=50000.0,
            exit_price=49700.0,  # 虧損 0.6%
            exit_reason="止損",
            entry_hours_ago=1,
            stop_loss=49700.0,  # 止損距離 0.6%（很緊）
            take_profit=52000.0
        )
        trades.append(trade)
    
    patterns = analyzer.find_common_patterns(trades)
    
    # 應該只有一個模式
    assert len(patterns) == 1
    assert patterns[0].pattern_name == 'STOP_LOSS_TOO_TIGHT'
    assert patterns[0].occurrence_count == 5
    assert patterns[0].percentage == 100.0


def test_specific_pattern_trend_misjudgment(analyzer):
    """測試特定虧損模式識別：趨勢判斷錯誤"""
    trades = []
    
    # 創建 3 筆趨勢判斷錯誤的交易
    for i in range(3):
        trade = create_trade(
            trade_id=f"trend-{i}",
            direction="long",
            entry_price=50000.0,
            exit_price=49000.0,  # 虧損 2%
            exit_reason="止損",
            entry_hours_ago=3,
            stop_loss=49000.0,  # 止損距離 2%
            take_profit=52000.0
        )
        trades.append(trade)
    
    patterns = analyzer.find_common_patterns(trades)
    
    assert len(patterns) == 1
    assert patterns[0].pattern_name == 'TREND_MISJUDGMENT'
    assert patterns[0].occurrence_count == 3


def test_specific_pattern_premature_entry(analyzer):
    """測試特定虧損模式識別：過早進場"""
    trades = []
    
    # 創建 4 筆過早進場的交易
    for i in range(4):
        trade = create_trade(
            trade_id=f"premature-{i}",
            direction="long",
            entry_price=50000.0,
            exit_price=49000.0,
            exit_reason="止損",
            entry_hours_ago=0.3,  # 18 minutes
            stop_loss=49000.0,
            take_profit=52000.0
        )
        trades.append(trade)
    
    patterns = analyzer.find_common_patterns(trades)
    
    assert len(patterns) == 1
    assert patterns[0].pattern_name == 'PREMATURE_ENTRY'
    assert patterns[0].occurrence_count == 4


def test_specific_pattern_holding_too_long(analyzer):
    """測試特定虧損模式識別：持倉時間過長"""
    trades = []
    
    # 創建 2 筆持倉時間過長的交易
    for i in range(2):
        trade = create_trade(
            trade_id=f"long-hold-{i}",
            direction="long",
            entry_price=50000.0,
            exit_price=49000.0,
            exit_reason="手動平倉",
            entry_hours_ago=30,  # 30 hours
            stop_loss=48000.0,
            take_profit=52000.0
        )
        trades.append(trade)
    
    patterns = analyzer.find_common_patterns(trades)
    
    assert len(patterns) == 1
    assert patterns[0].pattern_name == 'HOLDING_TOO_LONG'
    assert patterns[0].occurrence_count == 2


def test_multiple_patterns_percentage_calculation(analyzer):
    """測試多種模式的佔比計算"""
    trades = []
    
    # 創建 3 筆止損太緊的交易（每筆虧損 100 USDT）
    # 止損距離 0.4%（很緊）
    for i in range(3):
        trade = create_trade(
            trade_id=f"tight-{i}",
            direction="long",
            entry_price=50000.0,
            exit_price=49800.0,
            exit_reason="止損",
            entry_hours_ago=1,
            stop_loss=49800.0,  # 止損距離 0.4%（< 1%，會被分類為止損太緊）
            take_profit=52000.0,
            size=0.5  # 0.5 BTC * 200 = 100 USDT loss
        )
        trades.append(trade)
    
    # 創建 2 筆趨勢判斷錯誤的交易（每筆虧損 200 USDT）
    # 止損距離 2%（正常），虧損接近止損距離
    for i in range(2):
        trade = create_trade(
            trade_id=f"trend-{i}",
            direction="long",
            entry_price=50000.0,
            exit_price=49000.0,  # 虧損 2%
            exit_reason="止損",
            entry_hours_ago=3,
            stop_loss=49000.0,  # 止損距離 2%（正常）
            take_profit=52000.0,
            size=0.5  # 0.5 BTC * 1000 = 500 USDT loss (實際會更少因為槓桿)
        )
        trades.append(trade)
    
    distribution = analyzer.calculate_loss_distribution(trades)
    
    # 驗證佔比總和為 100%
    total_percentage = sum(distribution.values())
    assert abs(total_percentage - 100.0) < 0.01
    
    # 驗證至少有一個模式
    assert len(distribution) >= 1
    
    # 如果有多個模式，驗證它們的佔比
    if len(distribution) > 1:
        # 所有佔比應該是正數
        for percentage in distribution.values():
            assert percentage > 0
            assert percentage <= 100


def test_percentage_calculation_with_mixed_trades(analyzer):
    """測試混合交易（獲利+虧損）的佔比計算"""
    trades = []
    
    # 創建 3 筆獲利交易
    for i in range(3):
        trade = create_trade(
            trade_id=f"winning-{i}",
            direction="long",
            entry_price=50000.0,
            exit_price=52000.0,
            exit_reason="獲利",
            stop_loss=49000.0,
            take_profit=52000.0
        )
        trades.append(trade)
    
    # 創建 2 筆虧損交易
    for i in range(2):
        trade = create_trade(
            trade_id=f"losing-{i}",
            direction="long",
            entry_price=50000.0,
            exit_price=49000.0,
            exit_reason="止損",
            stop_loss=49000.0,
            take_profit=52000.0
        )
        trades.append(trade)
    
    distribution = analyzer.calculate_loss_distribution(trades)
    
    # 應該只計算虧損交易
    total_percentage = sum(distribution.values())
    assert abs(total_percentage - 100.0) < 0.01
    
    # 獲利交易不應該出現在分布中
    patterns = analyzer.find_common_patterns(trades)
    total_losing_trades = sum(p.occurrence_count for p in patterns)
    assert total_losing_trades == 2


def test_empty_trades_list(analyzer):
    """測試空交易列表"""
    trades = []
    
    patterns = analyzer.find_common_patterns(trades)
    assert len(patterns) == 0
    
    distribution = analyzer.calculate_loss_distribution(trades)
    assert len(distribution) == 0
    
    report = analyzer.generate_report(trades)
    assert "沒有虧損交易需要分析" in report


def test_pattern_sorting_by_loss_amount(analyzer):
    """測試模式按虧損金額排序"""
    trades = []
    
    # 創建 1 筆大額虧損（趨勢判斷錯誤）
    trade1 = create_trade(
        trade_id="big-loss",
        direction="long",
        entry_price=50000.0,
        exit_price=48000.0,  # 虧損 2000 USDT
        exit_reason="止損",
        entry_hours_ago=3,
        stop_loss=48000.0,
        take_profit=52000.0,
        size=1.0
    )
    trades.append(trade1)
    
    # 創建 5 筆小額虧損（止損太緊）
    for i in range(5):
        trade = create_trade(
            trade_id=f"small-loss-{i}",
            direction="long",
            entry_price=50000.0,
            exit_price=49800.0,  # 虧損 100 USDT
            exit_reason="止損",
            entry_hours_ago=1,
            stop_loss=49800.0,
            take_profit=52000.0,
            size=0.5
        )
        trades.append(trade)
    
    patterns = analyzer.find_common_patterns(trades)
    
    # 應該有 2 個模式
    assert len(patterns) == 2
    
    # 第一個模式應該是虧損金額最大的（趨勢判斷錯誤）
    assert patterns[0].pattern_name == 'TREND_MISJUDGMENT'
    assert patterns[0].total_loss > patterns[1].total_loss
    
    # 第二個模式應該是止損太緊
    assert patterns[1].pattern_name == 'STOP_LOSS_TOO_TIGHT'


def test_percentage_precision(analyzer):
    """測試佔比計算的精確度"""
    trades = []
    
    # 創建 3 筆相同虧損的交易
    for i in range(3):
        trade = create_trade(
            trade_id=f"equal-loss-{i}",
            direction="long",
            entry_price=50000.0,
            exit_price=49000.0,
            exit_reason="止損",
            stop_loss=49000.0,
            take_profit=52000.0,
            size=0.1
        )
        trades.append(trade)
    
    distribution = analyzer.calculate_loss_distribution(trades)
    
    # 所有交易虧損相同，應該都歸為同一類
    assert len(distribution) == 1
    
    # 佔比應該正好是 100%
    total_percentage = sum(distribution.values())
    assert abs(total_percentage - 100.0) < 0.0001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
