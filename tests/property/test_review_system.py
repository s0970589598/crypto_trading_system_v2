"""
ReviewSystem 屬性測試

測試覆盤系統的正確性屬性。
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timedelta
import tempfile
import shutil
from pathlib import Path

from src.analysis.review_system import ReviewSystem, TradeNote
from src.models.trading import Trade


# ========== 測試數據生成器 ==========

@st.composite
def trade_strategy(draw):
    """生成隨機交易"""
    entry_time = draw(st.datetimes(
        min_value=datetime(2024, 1, 1),
        max_value=datetime(2024, 12, 31)
    ))
    
    direction = draw(st.sampled_from(['long', 'short']))
    entry_price = draw(st.floats(min_value=100, max_value=100000))
    
    # 生成出場價格（可能獲利或虧損）
    pnl_pct = draw(st.floats(min_value=-10, max_value=10))
    if direction == 'long':
        exit_price = entry_price * (1 + pnl_pct / 100)
    else:
        exit_price = entry_price * (1 - pnl_pct / 100)
    
    exit_time = entry_time + timedelta(hours=draw(st.integers(min_value=1, max_value=48)))
    
    trade = Trade(
        strategy_id=draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        symbol=draw(st.sampled_from(['BTCUSDT', 'ETHUSDT'])),
        direction=direction,
        entry_time=entry_time,
        exit_time=exit_time,
        entry_price=entry_price,
        exit_price=exit_price,
        size=draw(st.floats(min_value=0.01, max_value=10)),
        leverage=draw(st.integers(min_value=1, max_value=20)),
        exit_reason=draw(st.sampled_from(['止損', '獲利', '手動平倉'])),
        metadata={'stop_loss': entry_price * 0.95 if direction == 'long' else entry_price * 1.05},
    )
    
    # 計算損益
    trade.calculate_pnl()
    
    return trade


@st.composite
def trade_note_strategy(draw, trade_id: str):
    """生成隨機交易註記"""
    return TradeNote(
        trade_id=trade_id,
        timestamp=datetime.now(),
        note=draw(st.text(min_size=1, max_size=200)),
        tags=draw(st.lists(st.text(min_size=1, max_size=20), max_size=5)),
    )


# ========== 屬性測試 ==========

# Feature: multi-strategy-system, Property 17: 交易註記往返
@given(
    trade=trade_strategy(),
    note_text=st.text(min_size=1, max_size=200),
    tags=st.lists(st.text(min_size=1, max_size=20), max_size=5)
)
@settings(max_examples=100, deadline=None)
def test_trade_note_roundtrip(trade, note_text, tags):
    """
    對於任何交易，添加註記和標籤後，查詢該交易應該返回相同的註記和標籤。
    
    **Validates: Requirements 7.2**
    """
    # 創建臨時目錄
    with tempfile.TemporaryDirectory() as tmpdir:
        review_system = ReviewSystem(storage_dir=tmpdir)
        
        # 記錄交易
        review_system.record_trade(trade)
        
        # 添加註記
        review_system.add_note(trade.trade_id, note_text, tags)
        
        # 查詢註記
        notes = review_system.get_notes(trade.trade_id)
        
        # 驗證：應該有一條註記
        assert len(notes) == 1
        
        # 驗證：註記內容應該相同
        assert notes[0].trade_id == trade.trade_id
        assert notes[0].note == note_text
        assert notes[0].tags == tags


# Feature: multi-strategy-system, Property 17: 交易註記往返（持久化測試）
@given(
    trade=trade_strategy(),
    note_text=st.text(min_size=1, max_size=200),
    tags=st.lists(st.text(min_size=1, max_size=20), max_size=5)
)
@settings(max_examples=100, deadline=None)
def test_trade_note_persistence_roundtrip(trade, note_text, tags):
    """
    對於任何交易，添加註記後保存，重新載入系統應該返回相同的註記。
    
    **Validates: Requirements 7.2**
    """
    # 創建臨時目錄
    with tempfile.TemporaryDirectory() as tmpdir:
        # 第一次：記錄交易和註記
        review_system1 = ReviewSystem(storage_dir=tmpdir)
        review_system1.record_trade(trade)
        review_system1.add_note(trade.trade_id, note_text, tags)
        
        # 第二次：重新載入
        review_system2 = ReviewSystem(storage_dir=tmpdir)
        
        # 驗證：交易應該存在
        loaded_trade = review_system2.get_trade(trade.trade_id)
        assert loaded_trade is not None
        assert loaded_trade.trade_id == trade.trade_id
        
        # 驗證：註記應該存在且內容相同
        notes = review_system2.get_notes(trade.trade_id)
        assert len(notes) == 1
        assert notes[0].trade_id == trade.trade_id
        assert notes[0].note == note_text
        assert notes[0].tags == tags


# Feature: multi-strategy-system, Property 18: 覆盤報告時間範圍
@given(
    trades=st.lists(trade_strategy(), min_size=5, max_size=20),
    report_date=st.datetimes(
        min_value=datetime(2024, 1, 1),
        max_value=datetime(2024, 12, 31)
    )
)
@settings(max_examples=100, deadline=None)
def test_review_report_time_range(trades, report_date):
    """
    對於任何覆盤報告（每日/每週/每月），報告中包含的交易時間應該都在指定的時間範圍內。
    
    **Validates: Requirements 7.6**
    """
    # 創建臨時目錄
    with tempfile.TemporaryDirectory() as tmpdir:
        review_system = ReviewSystem(storage_dir=tmpdir)
        
        # 記錄所有交易
        for trade in trades:
            review_system.record_trade(trade)
        
        # 生成每日報告
        daily_report = review_system.generate_daily_report(report_date)
        
        # 驗證：報告中的所有交易都在指定日期內
        start_of_day = report_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        for trade in daily_report.trades:
            assert start_of_day <= trade.entry_time < end_of_day, \
                f"Trade entry time {trade.entry_time} not in range [{start_of_day}, {end_of_day})"


# Feature: multi-strategy-system, Property 18: 覆盤報告時間範圍（週報告）
@given(
    trades=st.lists(trade_strategy(), min_size=5, max_size=20),
    week_start=st.datetimes(
        min_value=datetime(2024, 1, 1),
        max_value=datetime(2024, 12, 24)
    )
)
@settings(max_examples=100, deadline=None)
def test_weekly_report_time_range(trades, week_start):
    """
    對於任何週報告，報告中包含的交易時間應該都在指定週內。
    
    **Validates: Requirements 7.6**
    """
    # 創建臨時目錄
    with tempfile.TemporaryDirectory() as tmpdir:
        review_system = ReviewSystem(storage_dir=tmpdir)
        
        # 記錄所有交易
        for trade in trades:
            review_system.record_trade(trade)
        
        # 生成每週報告
        weekly_report = review_system.generate_weekly_report(week_start)
        
        # 驗證：報告中的所有交易都在指定週內
        week_end = week_start + timedelta(days=7)
        
        for trade in weekly_report.trades:
            assert week_start <= trade.entry_time < week_end, \
                f"Trade entry time {trade.entry_time} not in range [{week_start}, {week_end})"


# Feature: multi-strategy-system, Property 18: 覆盤報告時間範圍（月報告）
@given(
    trades=st.lists(trade_strategy(), min_size=5, max_size=20),
    year=st.integers(min_value=2024, max_value=2024),
    month=st.integers(min_value=1, max_value=12)
)
@settings(max_examples=100, deadline=None)
def test_monthly_report_time_range(trades, year, month):
    """
    對於任何月報告，報告中包含的交易時間應該都在指定月份內。
    
    **Validates: Requirements 7.6**
    """
    # 創建臨時目錄
    with tempfile.TemporaryDirectory() as tmpdir:
        review_system = ReviewSystem(storage_dir=tmpdir)
        
        # 記錄所有交易
        for trade in trades:
            review_system.record_trade(trade)
        
        # 生成每月報告
        monthly_report = review_system.generate_monthly_report(year, month)
        
        # 驗證：報告中的所有交易都在指定月份內
        month_start = datetime(year, month, 1)
        if month == 12:
            month_end = datetime(year + 1, 1, 1)
        else:
            month_end = datetime(year, month + 1, 1)
        
        for trade in monthly_report.trades:
            assert month_start <= trade.entry_time < month_end, \
                f"Trade entry time {trade.entry_time} not in range [{month_start}, {month_end})"


# Feature: multi-strategy-system, Property 19: 覆盤數據導出往返
@given(
    trades=st.lists(trade_strategy(), min_size=1, max_size=10)
)
@settings(max_examples=100, deadline=None)
def test_review_data_export_import_roundtrip(trades):
    """
    對於任何覆盤數據，導出到文件後再導入，應該得到等價的數據（所有關鍵字段相同）。
    
    **Validates: Requirements 7.8**
    """
    # 創建臨時目錄
    with tempfile.TemporaryDirectory() as tmpdir:
        # 第一個系統：記錄交易
        review_system1 = ReviewSystem(storage_dir=tmpdir)
        
        for trade in trades:
            review_system1.record_trade(trade)
            # 添加一些註記
            review_system1.add_note(trade.trade_id, f"Note for {trade.trade_id}", ["tag1", "tag2"])
            # 計算質量評分
            review_system1.calculate_execution_quality(trade)
        
        # 導出數據
        export_file = Path(tmpdir) / "export.json"
        review_system1.export_data(str(export_file))
        
        # 第二個系統：導入數據
        tmpdir2 = tempfile.mkdtemp()
        try:
            review_system2 = ReviewSystem(storage_dir=tmpdir2)
            review_system2.import_data(str(export_file))
            
            # 驗證：所有交易都應該存在
            assert len(review_system2.trades) == len(trades)
            
            for original_trade in trades:
                # 驗證：交易存在
                imported_trade = review_system2.get_trade(original_trade.trade_id)
                assert imported_trade is not None
                
                # 驗證：關鍵字段相同
                assert imported_trade.trade_id == original_trade.trade_id
                assert imported_trade.strategy_id == original_trade.strategy_id
                assert imported_trade.symbol == original_trade.symbol
                assert imported_trade.direction == original_trade.direction
                assert imported_trade.entry_price == original_trade.entry_price
                assert imported_trade.exit_price == original_trade.exit_price
                assert imported_trade.size == original_trade.size
                assert imported_trade.pnl == original_trade.pnl
                
                # 驗證：註記存在
                notes = review_system2.get_notes(original_trade.trade_id)
                assert len(notes) == 1
                assert notes[0].note == f"Note for {original_trade.trade_id}"
                assert notes[0].tags == ["tag1", "tag2"]
                
                # 驗證：質量評分存在
                quality = review_system2.get_execution_quality(original_trade.trade_id)
                assert quality is not None
                assert quality.trade_id == original_trade.trade_id
        finally:
            shutil.rmtree(tmpdir2)


# Feature: multi-strategy-system, Property 19: 覆盤數據導出往返（部分數據）
@given(
    trades=st.lists(trade_strategy(), min_size=5, max_size=20),
    export_start_offset=st.integers(min_value=0, max_value=5),
    export_days=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=100, deadline=None)
def test_partial_review_data_export_import(trades, export_start_offset, export_days):
    """
    對於任何部分覆盤數據（指定時間範圍），導出後再導入應該只包含該時間範圍內的數據。
    
    **Validates: Requirements 7.8**
    """
    # 創建臨時目錄
    with tempfile.TemporaryDirectory() as tmpdir:
        # 第一個系統：記錄交易
        review_system1 = ReviewSystem(storage_dir=tmpdir)
        
        for trade in trades:
            review_system1.record_trade(trade)
        
        # 定義導出時間範圍
        base_date = datetime(2024, 6, 1)
        export_start = base_date + timedelta(days=export_start_offset)
        export_end = export_start + timedelta(days=export_days)
        
        # 導出指定時間範圍的數據
        export_file = Path(tmpdir) / "partial_export.json"
        review_system1.export_data(str(export_file), export_start, export_end)
        
        # 第二個系統：導入數據
        tmpdir2 = tempfile.mkdtemp()
        try:
            review_system2 = ReviewSystem(storage_dir=tmpdir2)
            review_system2.import_data(str(export_file))
            
            # 驗證：只有時間範圍內的交易被導入
            for trade_id, trade in review_system2.trades.items():
                assert export_start <= trade.entry_time <= export_end, \
                    f"Imported trade {trade_id} with entry_time {trade.entry_time} outside range [{export_start}, {export_end}]"
        finally:
            shutil.rmtree(tmpdir2)


# ========== 額外的正確性測試 ==========

@given(trade=trade_strategy())
@settings(max_examples=100, deadline=None)
def test_execution_quality_score_range(trade):
    """執行質量評分應該在 0-100 範圍內"""
    with tempfile.TemporaryDirectory() as tmpdir:
        review_system = ReviewSystem(storage_dir=tmpdir)
        review_system.record_trade(trade)
        
        quality = review_system.calculate_execution_quality(trade)
        
        # 驗證：所有評分都在 0-100 範圍內
        assert 0 <= quality.overall_score <= 100
        assert 0 <= quality.entry_quality <= 100
        assert 0 <= quality.exit_quality <= 100
        assert 0 <= quality.risk_management <= 100


@given(trades=st.lists(trade_strategy(), min_size=1, max_size=20))
@settings(max_examples=100, deadline=None)
def test_report_statistics_consistency(trades):
    """報告統計數據應該與實際交易一致"""
    with tempfile.TemporaryDirectory() as tmpdir:
        review_system = ReviewSystem(storage_dir=tmpdir)
        
        for trade in trades:
            review_system.record_trade(trade)
        
        # 生成報告（使用一個足夠大的時間範圍）
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        report = review_system._generate_report(start_date, end_date, "test")
        
        # 驗證：總交易數
        assert report.total_trades == len(report.trades)
        
        # 驗證：獲利和虧損交易數
        actual_winning = sum(1 for t in report.trades if t.is_winning())
        actual_losing = sum(1 for t in report.trades if not t.is_winning())
        assert report.winning_trades == actual_winning
        assert report.losing_trades == actual_losing
        
        # 驗證：勝率計算
        if report.total_trades > 0:
            expected_win_rate = (actual_winning / report.total_trades) * 100
            assert abs(report.win_rate - expected_win_rate) < 0.01
        
        # 驗證：總損益
        expected_total_pnl = sum(t.pnl for t in report.trades)
        assert abs(report.total_pnl - expected_total_pnl) < 0.01
