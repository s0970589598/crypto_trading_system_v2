"""
LossAnalyzer 的基於屬性的測試

驗證 Property 15 和 Property 16
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timedelta
import uuid

from src.analysis.loss_analyzer import LossAnalyzer, LossAnalysis, LossPattern
from src.models.trading import Trade


# 策略生成器
@st.composite
def losing_trade(draw):
    """生成虧損交易"""
    entry_price = draw(st.floats(min_value=100, max_value=100000))
    
    # 確保是虧損交易
    direction = draw(st.sampled_from(['long', 'short']))
    
    if direction == 'long':
        # 做多虧損：出場價 < 進場價
        exit_price = entry_price * draw(st.floats(min_value=0.90, max_value=0.99))
    else:
        # 做空虧損：出場價 > 進場價
        exit_price = entry_price * draw(st.floats(min_value=1.01, max_value=1.10))
    
    size = draw(st.floats(min_value=0.01, max_value=10.0))
    leverage = draw(st.integers(min_value=1, max_value=20))
    
    entry_time = datetime.now() - timedelta(hours=draw(st.integers(min_value=1, max_value=48)))
    exit_time = entry_time + timedelta(hours=draw(st.floats(min_value=0.1, max_value=24.0)))
    
    # 計算止損和目標價
    if direction == 'long':
        stop_loss = entry_price * draw(st.floats(min_value=0.95, max_value=0.99))
        take_profit = entry_price * draw(st.floats(min_value=1.02, max_value=1.10))
    else:
        stop_loss = entry_price * draw(st.floats(min_value=1.01, max_value=1.05))
        take_profit = entry_price * draw(st.floats(min_value=0.90, max_value=0.98))
    
    trade = Trade(
        trade_id=str(uuid.uuid4()),
        strategy_id=draw(st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz-')),
        symbol=draw(st.sampled_from(['BTCUSDT', 'ETHUSDT'])),
        direction=direction,
        entry_time=entry_time,
        exit_time=exit_time,
        entry_price=entry_price,
        exit_price=exit_price,
        size=size,
        leverage=leverage,
        exit_reason=draw(st.sampled_from(['止損', '獲利', '手動平倉'])),
        metadata={'stop_loss': stop_loss, 'take_profit': take_profit}
    )
    
    # 計算損益
    trade.calculate_pnl()
    
    # 確保是虧損交易
    assert not trade.is_winning(), f"生成的交易不是虧損交易: pnl={trade.pnl}"
    
    return trade


# Feature: multi-strategy-system, Property 15: 虧損分類完整性
# 對於任何虧損交易，系統應該自動分配至少一個虧損原因分類
@given(trade=losing_trade())
@settings(max_examples=100, deadline=None)
def test_loss_classification_completeness(trade):
    """
    Property 15: 虧損分類完整性
    
    驗證：對於任何虧損交易，系統應該自動分配至少一個虧損原因分類
    
    Validates: Requirements 6.1
    """
    analyzer = LossAnalyzer()
    
    # 分析虧損交易
    analysis = analyzer.analyze_trade(trade)
    
    # 驗證：必須有虧損原因分類
    assert analysis.loss_reason is not None, "虧損原因不能為 None"
    assert analysis.loss_reason != "", "虧損原因不能為空字符串"
    assert isinstance(analysis.loss_reason, str), "虧損原因必須是字符串"
    
    # 驗證：虧損原因應該是預定義的分類之一
    valid_reasons = set(LossAnalyzer.LOSS_REASONS.keys())
    assert analysis.loss_reason in valid_reasons, \
        f"虧損原因 '{analysis.loss_reason}' 不在預定義分類中"
    
    # 驗證：置信度應該在 0-1 之間
    assert 0.0 <= analysis.confidence <= 1.0, \
        f"置信度 {analysis.confidence} 不在 [0, 1] 範圍內"
    
    # 驗證：分析結果應該包含交易 ID
    assert analysis.trade_id == trade.trade_id, "分析結果的交易 ID 不匹配"
    
    # 驗證：應該有改進建議
    assert isinstance(analysis.recommendations, list), "改進建議必須是列表"
    assert len(analysis.recommendations) > 0, "應該至少有一條改進建議"


# Feature: multi-strategy-system, Property 16: 虧損佔比總和
# 對於任何虧損分析結果，所有虧損原因的佔比總和應該等於 100%
@given(trades=st.lists(losing_trade(), min_size=5, max_size=20))
@settings(max_examples=100, deadline=None)
def test_loss_distribution_sum(trades):
    """
    Property 16: 虧損佔比總和
    
    驗證：對於任何虧損分析結果，所有虧損原因的佔比總和應該等於 100%
    
    Validates: Requirements 6.4
    """
    analyzer = LossAnalyzer()
    
    # 計算虧損分布
    distribution = analyzer.calculate_loss_distribution(trades)
    
    # 驗證：分布不為空
    assert len(distribution) > 0, "虧損分布不應為空"
    
    # 驗證：所有佔比都是非負數
    for reason, percentage in distribution.items():
        assert percentage >= 0.0, f"虧損原因 '{reason}' 的佔比 {percentage} 不能為負數"
        assert percentage <= 100.0, f"虧損原因 '{reason}' 的佔比 {percentage} 不能超過 100%"
    
    # 驗證：所有佔比總和等於 100%（允許浮點誤差）
    total_percentage = sum(distribution.values())
    assert abs(total_percentage - 100.0) < 0.01, \
        f"虧損佔比總和 {total_percentage}% 不等於 100%"


# Feature: multi-strategy-system, Property 15 擴展: 虧損模式識別完整性
# 對於任何虧損交易列表，find_common_patterns 應該識別出所有虧損交易
@given(trades=st.lists(losing_trade(), min_size=3, max_size=15))
@settings(max_examples=100, deadline=None)
def test_loss_pattern_completeness(trades):
    """
    Property 15 擴展: 虧損模式識別完整性
    
    驗證：find_common_patterns 應該識別出所有虧損交易
    
    Validates: Requirements 6.2, 6.3
    """
    analyzer = LossAnalyzer()
    
    # 找出虧損模式
    patterns = analyzer.find_common_patterns(trades)
    
    # 驗證：應該有至少一個模式
    assert len(patterns) > 0, "應該至少識別出一個虧損模式"
    
    # 驗證：所有模式的出現次數總和應該等於虧損交易數
    total_occurrences = sum(p.occurrence_count for p in patterns)
    losing_count = len([t for t in trades if not t.is_winning()])
    assert total_occurrences == losing_count, \
        f"模式出現次數總和 {total_occurrences} 不等於虧損交易數 {losing_count}"
    
    # 驗證：所有模式的總虧損應該等於所有虧損交易的總虧損（允許浮點誤差）
    total_pattern_loss = sum(p.total_loss for p in patterns)
    total_trade_loss = sum(abs(t.pnl) for t in trades if not t.is_winning())
    assert abs(total_pattern_loss - total_trade_loss) < 0.01, \
        f"模式總虧損 {total_pattern_loss} 不等於交易總虧損 {total_trade_loss}"
    
    # 驗證：每個模式都有描述
    for pattern in patterns:
        assert pattern.pattern_name, "模式名稱不能為空"
        assert pattern.description, "模式描述不能為空"
        assert pattern.occurrence_count > 0, "模式出現次數必須大於 0"
        assert pattern.total_loss > 0, "模式總虧損必須大於 0"
        assert 0 <= pattern.percentage <= 100, "模式佔比必須在 0-100 之間"


# Feature: multi-strategy-system, Property 15 擴展: 改進建議生成
# 對於任何虧損原因，應該生成至少一條改進建議
@given(trade=losing_trade())
@settings(max_examples=100, deadline=None)
def test_recommendations_generation(trade):
    """
    Property 15 擴展: 改進建議生成
    
    驗證：對於任何虧損原因，應該生成至少一條改進建議
    
    Validates: Requirements 6.5
    """
    analyzer = LossAnalyzer()
    
    # 分類虧損原因
    loss_reason, confidence = analyzer.classify_loss_reason(trade)
    
    # 生成改進建議
    recommendations = analyzer.generate_recommendations(loss_reason, trade)
    
    # 驗證：應該有至少一條建議
    assert len(recommendations) > 0, f"虧損原因 '{loss_reason}' 應該有至少一條改進建議"
    
    # 驗證：所有建議都是非空字符串
    for rec in recommendations:
        assert isinstance(rec, str), "建議必須是字符串"
        assert len(rec) > 0, "建議不能為空字符串"


# Feature: multi-strategy-system, Property 15 擴展: 虧損歷史記錄
# 分析過的虧損交易應該被記錄到歷史中
@given(trades=st.lists(losing_trade(), min_size=1, max_size=10))
@settings(max_examples=100, deadline=None)
def test_loss_history_recording(trades):
    """
    Property 15 擴展: 虧損歷史記錄
    
    驗證：分析過的虧損交易應該被記錄到歷史中
    
    Validates: Requirements 6.1
    """
    analyzer = LossAnalyzer()
    
    # 初始歷史應該為空
    assert len(analyzer.loss_history) == 0, "初始歷史應該為空"
    
    # 分析所有交易
    for trade in trades:
        analyzer.analyze_trade(trade)
    
    # 驗證：歷史記錄數量應該等於交易數量
    assert len(analyzer.loss_history) == len(trades), \
        f"歷史記錄數量 {len(analyzer.loss_history)} 不等於交易數量 {len(trades)}"
    
    # 驗證：所有交易 ID 都在歷史中
    history_trade_ids = {a.trade_id for a in analyzer.loss_history}
    trade_ids = {t.trade_id for t in trades}
    assert history_trade_ids == trade_ids, "歷史記錄的交易 ID 與輸入交易不匹配"


# Feature: multi-strategy-system, Property 16 擴展: 虧損模式佔比一致性
# 虧損模式的佔比應該與 calculate_loss_distribution 的結果一致
@given(trades=st.lists(losing_trade(), min_size=5, max_size=15))
@settings(max_examples=100, deadline=None)
def test_pattern_distribution_consistency(trades):
    """
    Property 16 擴展: 虧損模式佔比一致性
    
    驗證：虧損模式的佔比應該與 calculate_loss_distribution 的結果一致
    
    Validates: Requirements 6.4
    """
    analyzer = LossAnalyzer()
    
    # 獲取虧損模式
    patterns = analyzer.find_common_patterns(trades)
    
    # 獲取虧損分布
    distribution = analyzer.calculate_loss_distribution(trades)
    
    # 驗證：模式數量應該等於分布中的原因數量
    assert len(patterns) == len(distribution), \
        f"模式數量 {len(patterns)} 不等於分布中的原因數量 {len(distribution)}"
    
    # 驗證：每個模式的佔比應該與分布中的佔比一致
    for pattern in patterns:
        assert pattern.pattern_name in distribution, \
            f"模式 '{pattern.pattern_name}' 不在分布中"
        
        dist_percentage = distribution[pattern.pattern_name]
        assert abs(pattern.percentage - dist_percentage) < 0.01, \
            f"模式 '{pattern.pattern_name}' 的佔比 {pattern.percentage}% " \
            f"與分布中的佔比 {dist_percentage}% 不一致"


# Feature: multi-strategy-system, 錯誤處理: 非虧損交易應該拋出異常
@given(trade=losing_trade())
@settings(max_examples=50, deadline=None)
def test_winning_trade_raises_error(trade):
    """
    錯誤處理: 非虧損交易應該拋出異常
    
    驗證：analyze_trade 對於獲利交易應該拋出 ValueError
    """
    analyzer = LossAnalyzer()
    
    # 將虧損交易改為獲利交易
    if trade.direction == 'long':
        trade.exit_price = trade.entry_price * 1.05
    else:
        trade.exit_price = trade.entry_price * 0.95
    
    trade.calculate_pnl()
    
    # 驗證：應該是獲利交易
    assert trade.is_winning(), "測試交易應該是獲利交易"
    
    # 驗證：應該拋出 ValueError
    with pytest.raises(ValueError, match="不是虧損交易"):
        analyzer.analyze_trade(trade)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
