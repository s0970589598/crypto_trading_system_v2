"""
多策略執行器的屬性測試

測試多策略執行器的通用屬性，確保策略隔離和交易記錄完整性。
"""

import pytest
from hypothesis import given, strategies as st
from datetime import datetime, timedelta
import tempfile
import json
import os

from src.execution.multi_strategy_executor import MultiStrategyExecutor
from src.managers.strategy_manager import StrategyManager
from src.managers.risk_manager import RiskManager
from src.models.risk import RiskConfig
from src.models.trading import Trade


# Feature: multi-strategy-system, Property 7: 交易記錄完整性
@given(
    st.integers(min_value=2, max_value=5),  # 策略數量
    st.integers(min_value=1, max_value=10)  # 每個策略的交易數量
)
def test_trade_history_isolation(num_strategies, trades_per_strategy):
    """
    Property 7: 交易記錄完整性
    
    對於任何策略執行的交易，該交易應該被記錄在該策略的交易歷史中，
    且不會出現在其他策略的歷史中。
    
    Validates: Requirements 2.5, 7.1
    """
    # 創建臨時目錄
    with tempfile.TemporaryDirectory() as temp_dir:
        # 創建策略配置
        strategy_ids = [f"strategy_{i}" for i in range(num_strategies)]
        
        for strategy_id in strategy_ids:
            config = {
                "strategy_id": strategy_id,
                "strategy_name": f"測試策略 {strategy_id}",
                "version": "1.0.0",
                "enabled": True,
                "symbol": "ETHUSDT",
                "timeframes": ["1h"],
                "parameters": {
                    "stop_loss_atr": 1.5,
                    "take_profit_atr": 3.0,
                },
                "risk_management": {
                    "position_size": 0.2,
                    "leverage": 5,
                    "max_trades_per_day": 3,
                    "max_consecutive_losses": 3,
                    "daily_loss_limit": 0.1,
                    "stop_loss_atr": 1.5,
                    "take_profit_atr": 3.0,
                },
                "entry_conditions": [],
                "exit_conditions": {},
                "notifications": {}
            }
            
            config_path = os.path.join(temp_dir, f"{strategy_id}.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f)
        
        # 創建管理器
        strategy_manager = StrategyManager(strategies_dir=temp_dir)
        risk_config = RiskConfig(
            global_max_drawdown=0.2,
            daily_loss_limit=0.1,
            global_max_position=0.8
        )
        risk_manager = RiskManager(config=risk_config, initial_capital=10000.0)
        
        # 創建執行器
        executor = MultiStrategyExecutor(
            strategy_manager=strategy_manager,
            risk_manager=risk_manager
        )
        
        # 初始化每個策略的交易歷史
        for strategy_id in strategy_ids:
            executor.trade_history[strategy_id] = []
        
        # 為每個策略創建交易
        strategy_trade_map = {}
        for strategy_id in strategy_ids:
            trades = []
            for i in range(trades_per_strategy):
                trade = Trade(
                    trade_id=f"{strategy_id}_trade_{i}",
                    strategy_id=strategy_id,
                    symbol="ETHUSDT",
                    direction="long",
                    entry_time=datetime.now() - timedelta(hours=i+1),
                    exit_time=datetime.now() - timedelta(hours=i),
                    entry_price=3000.0 + i * 10,
                    exit_price=3100.0 + i * 10,
                    size=0.1,
                    leverage=5,
                    pnl=50.0,
                    pnl_pct=1.67,
                    commission=0.5,
                    exit_reason="獲利",
                    metadata={}
                )
                trades.append(trade)
                executor.trade_history[strategy_id].append(trade)
            
            strategy_trade_map[strategy_id] = trades
        
        # 驗證 Property 7：交易記錄完整性
        for strategy_id, expected_trades in strategy_trade_map.items():
            # 獲取該策略的交易歷史
            actual_trades = executor.get_trade_history(strategy_id)
            
            # 1. 驗證該策略的所有交易都被記錄
            assert len(actual_trades) == len(expected_trades), \
                f"策略 {strategy_id} 的交易數量不匹配"
            
            # 2. 驗證所有交易的 strategy_id 都正確
            for trade in actual_trades:
                assert trade.strategy_id == strategy_id, \
                    f"交易 {trade.trade_id} 的 strategy_id 不正確"
            
            # 3. 驗證該策略的交易不會出現在其他策略的歷史中
            for other_strategy_id in strategy_trade_map.keys():
                if other_strategy_id != strategy_id:
                    other_trades = executor.get_trade_history(other_strategy_id)
                    
                    # 檢查是否有交易 ID 重複
                    expected_trade_ids = {t.trade_id for t in expected_trades}
                    other_trade_ids = {t.trade_id for t in other_trades}
                    
                    overlap = expected_trade_ids & other_trade_ids
                    assert len(overlap) == 0, \
                        f"策略 {strategy_id} 的交易出現在策略 {other_strategy_id} 的歷史中：{overlap}"
        
        # 4. 驗證獲取所有交易時，總數正確
        all_trades = executor.get_trade_history()
        expected_total = sum(len(trades) for trades in strategy_trade_map.values())
        assert len(all_trades) == expected_total, \
            f"所有交易的總數不匹配：期望 {expected_total}，實際 {len(all_trades)}"
        
        # 5. 驗證每筆交易都屬於某個策略
        for trade in all_trades:
            assert trade.strategy_id in strategy_trade_map, \
                f"交易 {trade.trade_id} 的 strategy_id {trade.strategy_id} 不存在"
